"""
MySQL Creator Poll Routes
Updated Flask routes for MySQL database with creator authentication
"""

import os
import csv
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from .mysql_models import CreatorPoll, CreatorBallot
from functools import wraps

bp = Blueprint('creatorpoll', __name__, 
              template_folder='templates',
              static_folder='static',
              static_url_path='/creatorpoll/static')

# MySQL Configuration - Use environment variables or defaults
def get_mysql_config():
    """Get MySQL configuration from environment or defaults"""
    import os
    return {
        'host': os.environ.get('MYSQL_HOST', 'devgreeny.mysql.pythonanywhere-services.com'),
        'user': os.environ.get('MYSQL_USER', 'devgreeny'),
        'password': os.environ.get('MYSQL_PASSWORD', 'lebron69'),
        'database': os.environ.get('MYSQL_DATABASE', 'devgreeny$default')
    }

MYSQL_CONFIG = get_mysql_config()

# Initialize MySQL models (lazy loading) - removed creator_user
creator_poll = None
creator_ballot = None

def get_mysql_models():
    """Get MySQL models with lazy initialization"""
    global creator_poll, creator_ballot
    
    if creator_poll is None:
        try:
            creator_poll = CreatorPoll(MYSQL_CONFIG)
            creator_ballot = CreatorBallot(MYSQL_CONFIG)
            
            # Test connection first
            test_conn = creator_poll.db.get_connection()
            test_conn.close()
            
            # Create tables if they don't exist
            creator_poll.create_tables()
            creator_ballot.create_tables()
            
            print("✅ MySQL models initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing MySQL models: {e}")
            
            # Check if we're in a local development environment
            if (not os.environ.get('MYSQL_HOST') or 
                os.environ.get('USE_LOCAL_SQLITE') or 
                'localhost' in os.environ.get('MYSQL_HOST', '')):
                print("🔄 MySQL unavailable - using SQLite fallback for local development")
                raise Exception("MySQL unavailable - use SQLite-based creator poll system")
            else:
                print("🔄 Production MySQL connection failed - retrying...")
                raise
    
    return creator_poll, creator_ballot

# Skip MySQL initialization for local development
# Initialize models immediately but with error handling
# try:
#     get_mysql_models()
# except Exception as e:
#     print(f"⚠️ MySQL models not available: {e}")
#     print("🔧 Routes will attempt to initialize on first use")

# Path to CFB data
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CFB_CSV = os.path.join(PROJECT_ROOT, "static/Teams for Polls/college_ids.csv")

def load_cfb_teams():
    """Load CFB teams from college_ids.csv file"""
    teams = []
    conferences = {}
    
    try:
        with open(CFB_CSV, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            for row in reader:
                team_id = row.get('Id', '').strip().strip('"')  # Remove quotes
                school = row.get('School', '').strip().strip('"')
                abbreviation = row.get('Abbreviation', '').strip().strip('"')
                conference = row.get('Conference', '').strip().strip('"')
                division = row.get('Division', '').strip().strip('"')
                alternate_names = row.get('AlternateNames', '').strip().strip('"')
                
                if team_id and school and conference:  # Valid team data
                    # Create logo URL path using custom route
                    logo_url = f"/creatorpoll/logo/{team_id}.png"
                    
                    team_data = {
                        'id': team_id,
                        'name': school,
                        'abbreviation': abbreviation,
                        'conference': conference,
                        'division': division,
                        'alternate_names': alternate_names,
                        'logo_url': logo_url,
                        'full_name': school,
                        'display_name': f"{school} ({abbreviation})" if abbreviation else school
                    }
                    teams.append(team_data)
                    
                    if conference not in conferences:
                        conferences[conference] = []
                    conferences[conference].append(team_data)
        
        # Sort teams alphabetically by school name
        teams.sort(key=lambda x: x['name'])
        
        # Sort conferences
        for conf_teams in conferences.values():
            conf_teams.sort(key=lambda x: x['name'])
            
        print(f"📚 Loaded {len(teams)} CFB teams from {len(conferences)} conferences")
        return teams, conferences
        
    except FileNotFoundError:
        print(f"❌ CFB CSV file not found: {CFB_CSV}")
        return [], {}
    except Exception as e:
        print(f"❌ Error loading CFB teams: {e}")
        return [], {}

# Using Flask-Login's login_required decorator instead of custom auth system

def get_season_start_datetime():
    """Get the season start date (Wednesday, August 27th, 2025 at 3:00 PM)"""
    return datetime(2025, 8, 27, 15, 0, 0)

def get_current_season():
    """Get current season year"""
    now = datetime.now()
    season_start = get_season_start_datetime()
    
    if now >= season_start:
        return 2025
    else:
        return 2024

def get_current_week():
    """Get current week number"""
    now = datetime.now()
    season_start = get_season_start_datetime()
    
    if now < season_start:
        return 0  # Pre-season
    
    # Calculate weeks since season start (Wednesday to Wednesday)
    days_since_start = (now - season_start).days
    week_number = (days_since_start // 7) + 1
    
    return min(week_number, 17)  # Cap at week 17

def get_poll_start_end_times(week_number: int, season_year: int):
    """Get poll start and end times for a specific week"""
    season_start = get_season_start_datetime()
    
    # Each week starts on Wednesday at 3 PM
    week_start = season_start + timedelta(weeks=week_number - 1)
    # Poll ends Tuesday at 11:59 PM (6 days, 8 hours, 59 minutes later)
    week_end = week_start + timedelta(days=6, hours=8, minutes=59)
    
    return week_start, week_end

def ensure_current_poll_exists():
    """Ensure that the current week's poll exists"""
    # Initialize MySQL models first to avoid NoneType error
    try:
        creator_poll_model, creator_ballot_model = get_mysql_models()
    except Exception as e:
        print(f"❌ Error initializing MySQL models: {e}")
        return None
        
    current_week = get_current_week()
    current_season = get_current_season()
    
    if current_week <= 0:
        return None
    
    # Check if current poll exists
    current_poll = creator_poll_model.get_current_poll()
    if current_poll and current_poll['week_number'] == current_week and current_poll['season_year'] == current_season:
        return current_poll
    
    # Create new poll for current week
    poll_start, poll_end = get_poll_start_end_times(current_week, current_season)
    
    poll_id = creator_poll_model.create_poll(
        week_number=current_week,
        season_year=current_season,
        title=f"CFB Creator Poll - Week {current_week}",
        description=f"Rank your top 25 college football teams for Week {current_week} of the {current_season} season.",
        start_date=poll_start,
        end_date=poll_end
    )
    
    print(f"✅ Auto-created poll for Week {current_week}, {current_season}")
    return creator_poll_model.get_poll_by_id(poll_id)

@bp.route("/")
def home():
    """Home page showing current poll or results"""
    try:
        current_poll = ensure_current_poll_exists()
        teams, _ = load_cfb_teams()
    except Exception as e:
        print(f"❌ Error in creator poll home: {e}")
        
        # Check if this is a development environment with no MySQL
        if "MySQL unavailable" in str(e):
            return render_template('creatorpoll/error.html', 
                                 error_message="Creator Poll MySQL system is not available in development. Please use the SQLite version or configure MySQL.",
                                 technical_details="Run in production environment or configure MySQL connection.")
        else:
            return render_template('creatorpoll/error.html', 
                                 error_message="Creator Poll system is temporarily unavailable. Please try again later.",
                                 technical_details=str(e))
    
    current_rankings = []
    total_ballots = 0
    
    if current_poll:
        # Get poll results with movement
        try:
            creator_poll_model, creator_ballot_model = get_mysql_models()
            results = creator_poll_model.get_poll_results_with_movement(current_poll['id'])
            total_ballots = creator_ballot_model.get_poll_ballot_count(current_poll['id'])
        except Exception as e:
            print(f"❌ Error getting poll results: {e}")
            results = []
            total_ballots = 0
        
        # Get top 15 with logos
        for result in results[:15]:
            team_data = next((t for t in teams if t['name'] == result['team_name']), None)
            logo_url = team_data['logo_url'] if team_data else ''
            
            current_rankings.append({
                'rank': result['rank'],
                'team_name': result['team_name'],
                'vote_count': result['vote_count'],
                'avg_rank': result['avg_rank'],
                'points': result['points'],
                'logo_url': logo_url
            })
    
    # Check if user is logged in (using unified auth)
    creator_logged_in = current_user.is_authenticated
    creator_display_name = current_user.username if creator_logged_in else ""
    
    return render_template('creatorpoll/home.html',
                         current_poll=current_poll,
                         current_rankings=current_rankings,
                         total_ballots=total_ballots,
                         creator_logged_in=creator_logged_in,
                         creator_display_name=creator_display_name)

@bp.route("/login")
def login():
    """Redirect to unified auth login"""
    return redirect(url_for('auth.login', next=url_for('creatorpoll.home')))

@bp.route("/register")
def register():
    """Redirect to unified auth registration"""
    return redirect(url_for('auth.register', next=url_for('creatorpoll.home')))

@bp.route("/vote/<int:poll_id>", methods=['GET', 'POST'])
@login_required
def vote(poll_id):
    """Creator voting page"""
    try:
        creator_poll, creator_ballot = get_mysql_models()
    except Exception as e:
        return render_template('creatorpoll/error.html', 
                             error_message="Creator Poll system is temporarily unavailable.",
                             technical_details=str(e))
    
    poll = creator_poll.get_poll_by_id(poll_id)
    if not poll:
        flash('Poll not found.', 'error')
        return redirect(url_for('creatorpoll.home'))
    
    teams, conferences = load_cfb_teams()
    user_id = current_user.id  # Use unified auth user ID
    
    # Poll locking removed - always allow submissions
    # Check if poll is open
    # now = datetime.now()
    # if now < poll['start_date'] or now > poll['end_date']:
    #     flash('This poll is no longer accepting votes.', 'warning')
    #     return redirect(url_for('creatorpoll.results', poll_id=poll_id))
    
    if request.method == 'POST':
        # Collect ballot data
        ballot_data = []
        for rank in range(1, 26):
            team_name = request.form.get(f'rank_{rank}', '').strip()
            reasoning = request.form.get(f'reasoning_{rank}', '').strip()
            
            if team_name:
                # Find team data
                team_data = next((t for t in teams if 
                                t['name'] == team_name or 
                                t['display_name'] == team_name or 
                                t['abbreviation'] == team_name), None)
                
                ballot_data.append({
                    'rank': rank,
                    'team_name': team_name,
                    'team_id': team_data['id'] if team_data else '',
                    'team_conference': team_data['conference'] if team_data else '',
                    'reasoning': reasoning
                })
        
        if len(ballot_data) < 25:
            flash('Please rank all 25 teams before submitting.', 'error')
        else:
            try:
                success = creator_ballot.submit_ballot(poll_id, user_id, ballot_data)
                if success:
                    flash('Your ballot has been submitted successfully!', 'success')
                    return redirect(url_for('creatorpoll.results', poll_id=poll_id))
                else:
                    flash('Error submitting ballot. Please try again.', 'error')
            except Exception as e:
                flash(f'Error submitting ballot: {str(e)}', 'error')
    
    # Load existing ballot
    existing_ballot = creator_ballot.get_creator_ballot(poll_id, user_id)
    
    return render_template('creatorpoll/vote.html',
                         poll=poll,
                         teams=teams,
                         conferences=conferences,
                         existing_ballot=existing_ballot)

@bp.route("/results/<int:poll_id>")
def results(poll_id):
    """Show poll results with movement tracking"""
    try:
        creator_poll_model, creator_ballot_model = get_mysql_models()
    except Exception as e:
        flash('Creator Poll system is temporarily unavailable.', 'error')
        return redirect(url_for('creatorpoll.home'))
        
    poll = creator_poll_model.get_poll_by_id(poll_id)
    if not poll:
        flash('Poll not found.', 'error')
        return redirect(url_for('creatorpoll.home'))
    
    # Get results with movement
    enhanced_results = creator_poll_model.get_poll_results_with_movement(poll_id)
    teams, _ = load_cfb_teams()
    
    # Add logos to results
    final_rankings = []
    for result in enhanced_results[:25]:  # Top 25
        team_data = next((t for t in teams if t['name'] == result['team_name']), None)
        logo_url = team_data['logo_url'] if team_data else ''
        
        final_rankings.append({
            **result,
            'logo_url': logo_url
        })
    
    # Others receiving votes
    others_receiving_votes = []
    for result in enhanced_results[25:]:
        team_data = next((t for t in teams if t['name'] == result['team_name']), None)
        logo_url = team_data['logo_url'] if team_data else ''
        
        others_receiving_votes.append({
            'team_name': result['team_name'],
            'vote_count': result['vote_count'],
            'logo_url': logo_url
        })
    
    total_ballots = creator_ballot_model.get_poll_ballot_count(poll_id)
    
    return render_template('creatorpoll/results.html',
                         poll=poll,
                         rankings=final_rankings,
                         others_receiving_votes=others_receiving_votes,
                         total_ballots=total_ballots)

@bp.route("/logout")
def logout():
    """Redirect to unified auth logout"""
    return redirect(url_for('auth.logout'))

@bp.route("/api/search_teams")
def search_teams():
    """API endpoint for team search"""
    query = request.args.get('q', '').lower()
    teams, _ = load_cfb_teams()
    
    if not query:
        return jsonify([])
    
    matching_teams = []
    for team in teams:
        if (query in team['name'].lower() or 
            query in team.get('abbreviation', '').lower() or
            query in team.get('alternate_names', '').lower() or
            query in team.get('display_name', '').lower()):
            
            matching_teams.append({
                'id': team['id'],
                'name': team['name'],
                'abbreviation': team['abbreviation'],
                'display_name': team['display_name'],
                'conference': team['conference'],
                'division': team['division'],
                'logo_url': team['logo_url']
            })
    
    return jsonify(matching_teams[:20])  # Limit to 20 results

@bp.route("/logo/<filename>")
def serve_logo(filename):
    """Serve team logo files"""
    try:
        logo_path = os.path.join(PROJECT_ROOT, "static/Teams for Polls/logos", filename)
        return send_file(logo_path, mimetype='image/png')
    except FileNotFoundError:
        return "Logo not found", 404

@bp.route("/debug")
def debug_status():
    """Debug route to check system status"""
    current_week = get_current_week()
    current_season = get_current_season()
    current_poll = ensure_current_poll_exists()
    
    # Get poll results if poll exists
    poll_results = []
    total_ballots = 0
    if current_poll:
        try:
            creator_poll_model, creator_ballot_model = get_mysql_models()
            poll_results = creator_poll_model.get_poll_results(current_poll['id'])
            total_ballots = creator_ballot_model.get_poll_ballot_count(current_poll['id'])
        except Exception as e:
            print(f"❌ Error getting debug poll results: {e}")
            poll_results = []
            total_ballots = 0
    
    debug_info = {
        'system_status': 'MySQL Creator Poll System Active',
        'current_week': current_week,
        'current_season': current_season,
        'current_poll': current_poll,
        'total_ballots': total_ballots,
        'poll_results': poll_results,
        'database_config': {
            'host': MYSQL_CONFIG['host'],
            'database': MYSQL_CONFIG['database'],
            'user': MYSQL_CONFIG['user']
        }
    }
    
    return jsonify(debug_info)

@bp.route("/admin/archive_polls")
@login_required
def archive_polls():
    """Admin endpoint to archive completed polls"""
    try:
        creator_poll_model, creator_ballot_model = get_mysql_models()
        # Archive completed polls
        current_poll = creator_poll_model.get_current_poll()
        if current_poll:
            # Archive previous polls
            conn = creator_poll_model.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id FROM creator_polls 
                WHERE end_date < NOW() AND is_archived = FALSE AND id != %s
            """, (current_poll['id'],))
            
            completed_polls = cursor.fetchall()
            
            for poll in completed_polls:
                creator_poll_model.archive_poll(poll['id'])
                flash(f'Archived poll ID {poll["id"]}', 'success')
            
            cursor.close()
            conn.close()
        
        return redirect(url_for('creatorpoll.home'))
        
    except Exception as e:
        flash(f'Error archiving polls: {str(e)}', 'error')
        return redirect(url_for('creatorpoll.home'))

if __name__ == "__main__":
    print("🏈 Creator Poll MySQL Routes Ready!")
    print("📊 Features:")
    print("  ✅ Creator authentication with user_creator table")
    print("  ✅ Weekly poll archiving for movement tracking")
    print("  ✅ MySQL database integration")
    print("  ✅ Team logos and autocomplete")
    print("  ✅ Week-to-week movement indicators")
