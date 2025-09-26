"""
MySQL Creator Poll Routes
Updated Flask routes for MySQL database with creator authentication
"""

import os
import csv
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from .mysql_models import CreatorUser, CreatorPoll, CreatorBallot
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

# Initialize MySQL models
creator_user = CreatorUser(MYSQL_CONFIG)
creator_poll = CreatorPoll(MYSQL_CONFIG)
creator_ballot = CreatorBallot(MYSQL_CONFIG)

# Create tables on import
try:
    creator_poll.create_tables()
    creator_ballot.create_tables()
    creator_user.create_tables()
except Exception as e:
    print(f"Warning: Could not create MySQL tables: {e}")

# Path to CFB data
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CFB_CSV = os.path.join(PROJECT_ROOT, "static/Teams for Polls/college_ids.csv")

def load_cfb_teams():
    """Load CFB teams from college_ids.csv file"""
    teams = []
    conferences = {}
    
    try:
        with open(CFB_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_id = row.get('id', '').strip('"')
                school = row.get('school', '').strip('"')
                abbreviation = row.get('abbreviation', '').strip('"')
                conference = row.get('conference', '').strip('"')
                division = row.get('division', '').strip('"')
                alternate_names = row.get('alternate_names', '').strip('"')
                
                if team_id and school:
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
                        'display_name': abbreviation if abbreviation else school
                    }
                    teams.append(team_data)
                    
                    if conference:
                        if conference not in conferences:
                            conferences[conference] = []
                        conferences[conference].append(school)
        
        print(f"📚 Loaded {len(teams)} CFB teams from {len(conferences)} conferences")
        return teams, conferences
        
    except FileNotFoundError:
        print(f"❌ CFB CSV file not found: {CFB_CSV}")
        return [], {}
    except Exception as e:
        print(f"❌ Error loading CFB teams: {e}")
        return [], {}

def login_required(f):
    """Decorator to require creator login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get('creator_session_id')
        if not session_id:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('creatorpoll.login'))
        
        session_data = creator_user.validate_session(session_id)
        if not session_data['valid']:
            session.clear()
            flash('Your session has expired. Please log in again.', 'error')
            return redirect(url_for('creatorpoll.login'))
        
        # Add creator info to request
        request.creator = session_data
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get('creator_session_id')
        if not session_id:
            flash('Admin access required.', 'error')
            return redirect(url_for('creatorpoll.login'))
        
        session_data = creator_user.validate_session(session_id)
        if not session_data['valid'] or not session_data['is_admin']:
            flash('Admin access required.', 'error')
            return redirect(url_for('creatorpoll.login'))
        
        request.creator = session_data
        return f(*args, **kwargs)
    
    return decorated_function

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
    current_week = get_current_week()
    current_season = get_current_season()
    
    if current_week <= 0:
        return None
    
    # Check if current poll exists
    current_poll = creator_poll.get_current_poll()
    if current_poll and current_poll['week_number'] == current_week and current_poll['season_year'] == current_season:
        return current_poll
    
    # Create new poll for current week
    poll_start, poll_end = get_poll_start_end_times(current_week, current_season)
    
    poll_id = creator_poll.create_poll(
        week_number=current_week,
        season_year=current_season,
        title=f"CFB Creator Poll - Week {current_week}",
        description=f"Rank your top 25 college football teams for Week {current_week} of the {current_season} season.",
        start_date=poll_start,
        end_date=poll_end
    )
    
    print(f"✅ Auto-created poll for Week {current_week}, {current_season}")
    return creator_poll.get_poll_by_id(poll_id)

@bp.route("/")
def home():
    """Home page showing current poll or results"""
    current_poll = ensure_current_poll_exists()
    teams, _ = load_cfb_teams()
    
    current_rankings = []
    total_ballots = 0
    
    if current_poll:
        # Get poll results with movement
        results = creator_poll.get_poll_results_with_movement(current_poll['id'])
        total_ballots = creator_ballot.get_poll_ballot_count(current_poll['id'])
        
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
    
    # Check if creator is logged in
    creator_logged_in = False
    creator_display_name = ""
    if session.get('creator_session_id'):
        session_data = creator_user.validate_session(session.get('creator_session_id'))
        if session_data['valid']:
            creator_logged_in = True
            creator_display_name = session_data['display_name']
    
    return render_template('creatorpoll/home.html',
                         current_poll=current_poll,
                         current_rankings=current_rankings,
                         total_ballots=total_ballots,
                         creator_logged_in=creator_logged_in,
                         creator_display_name=creator_display_name)

@bp.route("/login", methods=['GET', 'POST'])
def login():
    """Creator login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        auth_result = creator_user.authenticate_creator(username, password)
        
        if auth_result:
            session['creator_session_id'] = auth_result['session_id']
            session['creator_username'] = auth_result['username']
            session['creator_display_name'] = auth_result['display_name']
            session['creator_id'] = auth_result['creator_id']
            
            flash(f'Welcome back, {auth_result["display_name"]}!', 'success')
            return redirect(url_for('creatorpoll.home'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('creatorpoll/login.html')

@bp.route("/register", methods=['GET', 'POST'])
def register():
    """Creator registration page"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio', '')
        twitter_handle = request.form.get('twitter_handle', '')
        
        if not all([username, email, password, display_name]):
            flash('Please fill in all required fields.', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
        else:
            success = creator_user.create_creator(username, email, password, display_name, bio, twitter_handle)
            if success:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('creatorpoll.login'))
            else:
                flash('Registration failed. Username or email may already exist.', 'error')
    
    return render_template('creatorpoll/register.html')

@bp.route("/vote/<int:poll_id>", methods=['GET', 'POST'])
@login_required
def vote(poll_id):
    """Creator voting page"""
    poll = creator_poll.get_poll_by_id(poll_id)
    if not poll:
        flash('Poll not found.', 'error')
        return redirect(url_for('creatorpoll.home'))
    
    teams, conferences = load_cfb_teams()
    creator_id = request.creator['creator_id']
    
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
                success = creator_ballot.submit_ballot(poll_id, creator_id, ballot_data)
                if success:
                    flash('Your ballot has been submitted successfully!', 'success')
                    return redirect(url_for('creatorpoll.results', poll_id=poll_id))
                else:
                    flash('Error submitting ballot. Please try again.', 'error')
            except Exception as e:
                flash(f'Error submitting ballot: {str(e)}', 'error')
    
    # Load existing ballot
    existing_ballot = creator_ballot.get_creator_ballot(poll_id, creator_id)
    
    return render_template('creatorpoll/vote.html',
                         poll=poll,
                         teams=teams,
                         conferences=conferences,
                         existing_ballot=existing_ballot)

@bp.route("/results/<int:poll_id>")
def results(poll_id):
    """Show poll results with movement tracking"""
    poll = creator_poll.get_poll_by_id(poll_id)
    if not poll:
        flash('Poll not found.', 'error')
        return redirect(url_for('creatorpoll.home'))
    
    # Get results with movement
    enhanced_results = creator_poll.get_poll_results_with_movement(poll_id)
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
    
    total_ballots = creator_ballot.get_poll_ballot_count(poll_id)
    
    return render_template('creatorpoll/results.html',
                         poll=poll,
                         rankings=final_rankings,
                         others_receiving_votes=others_receiving_votes,
                         total_ballots=total_ballots)

@bp.route("/logout")
def logout():
    """Creator logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('creatorpoll.home'))

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

@bp.route("/admin/archive_polls")
@admin_required
def archive_polls():
    """Admin endpoint to archive completed polls"""
    try:
        # Archive completed polls
        current_poll = creator_poll.get_current_poll()
        if current_poll:
            # Archive previous polls
            conn = creator_poll.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id FROM creator_polls 
                WHERE end_date < NOW() AND is_archived = FALSE AND id != %s
            """, (current_poll['id'],))
            
            completed_polls = cursor.fetchall()
            
            for poll in completed_polls:
                creator_poll.archive_poll(poll['id'])
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
