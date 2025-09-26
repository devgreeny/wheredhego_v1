import os
import csv
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from app.starting5.models import db, User
from .models import Poll, Vote, UserBallot

bp = Blueprint('creatorpoll', __name__, 
              template_folder='templates',
              static_folder='static',
              static_url_path='/creatorpoll/static')

# Path to CFB data - using the new college_ids.csv
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
        
    except Exception as e:
        print(f"Error loading CFB data: {e}")
        return [], {}

def get_season_start_datetime():
    """Get the exact start datetime of the CFB season"""
    # First poll starts on Sunday, August 31st, 2025 at 3:00 PM EST
    # This gives a full week cycle: Sunday 3pm (open) -> Thursday 3pm (lock) -> Sunday 3pm (next week)
    return datetime(2025, 8, 31, 15, 0, 0)  # 3:00 PM EST

def get_current_season():
    """Get current CFB season year based on season start"""
    now = datetime.now()
    season_start = get_season_start_datetime()
    
    # If we're before the season start, use previous year
    if now < season_start:
        return season_start.year - 1
    return season_start.year

def get_current_week():
    """Calculate current CFB week based on Sunday-Thursday cycle"""
    now = datetime.now()
    season_start = get_season_start_datetime()
    
    # If we're before the season starts, it's week 0 (pre-season)
    if now < season_start:
        return 0
    
    # Calculate weeks since season start (every Sunday at 3 PM EST)
    time_diff = now - season_start
    weeks_since_start = time_diff.days // 7
    
    # Determine what week we should be displaying based on the cycle:
    # - Sunday 3pm to Thursday 3pm: Show current week (voting open)
    # - Thursday 3pm to Sunday 3pm: Show next week (locked, upcoming)
    
    # Get the day of week (0=Monday, 6=Sunday) and hour
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    hour = now.hour
    
    # Convert to our cycle: Sunday=0, Monday=1, ..., Saturday=6
    cycle_day = (weekday + 1) % 7  # Sunday becomes 0
    
    # If we're in lockout period (Thursday 3pm to Sunday 3pm), show next week
    if (cycle_day == 4 and hour >= 15) or cycle_day in [5, 6] or (cycle_day == 0 and hour < 15):
        # We're in lockout period, show next week
        weeks_since_start += 1
    
    # Week numbering starts at 1, max 17 weeks in CFB season
    current_week = max(weeks_since_start + 1, 1)
    return min(current_week, 17)

def get_poll_start_end_times(week_number, season_year):
    """Get the start and end times for a specific poll week"""
    season_start = get_season_start_datetime()
    
    # Each poll opens on Sunday at 3 PM EST and locks on Thursday at 3 PM EST
    # Week 1 starts on the season start date (first Sunday)
    poll_start = season_start + timedelta(weeks=week_number-1)
    poll_end = poll_start + timedelta(days=4)  # Thursday 3 PM EST (4 days after Sunday)
    
    return poll_start, poll_end

def cleanup_old_polls():
    """Deactivate polls that are no longer current"""
    current_week = get_current_week()
    current_season = get_current_season()
    
    # Deactivate all polls except the current one
    from app.starting5.models import db
    old_polls = Poll.query.filter(
        Poll.is_active == True,
        ~((Poll.season_year == current_season) & (Poll.week_number == current_week))
    ).all()
    
    for poll in old_polls:
        poll.is_active = False
        print(f"🔒 Deactivated old poll: {poll.title}")
    
    if old_polls:
        db.session.commit()

def ensure_current_poll_exists():
    """Ensure that the current week's poll exists, create if needed"""
    current_week = get_current_week()
    current_season = get_current_season()
    
    # Clean up old polls first
    cleanup_old_polls()
    
    # Don't create polls for week 0 (pre-season)
    if current_week <= 0:
        return None
    
    # Check if current poll exists
    existing_poll = Poll.query.filter_by(
        season_year=current_season,
        week_number=current_week,
        is_active=True
    ).first()
    
    if existing_poll:
        return existing_poll
    
    # Create new poll for current week
    poll_start, poll_end = get_poll_start_end_times(current_week, current_season)
    
    new_poll = Poll(
        title=f"CFB Creator Poll - Week {current_week}",
        description=f"Rank your top 25 college football teams for Week {current_week} of the {current_season} season. Submit anytime - polls are always open!",
        week_number=current_week,
        season_year=current_season,
        start_date=poll_start,
        end_date=poll_end,  # Keep for compatibility but not enforced
        is_active=True
    )
    
    from app.starting5.models import db
    db.session.add(new_poll)
    db.session.commit()
    
    print(f"✅ Auto-created poll for Week {current_week}, {current_season}")
    print(f"   Start: {poll_start}")
    print(f"   End: {poll_end}")
    
    return new_poll

@bp.route("/")
def home():
    """Home page showing current poll or poll results"""
    teams, conferences = load_cfb_teams()
    
    # Ensure current poll exists (auto-create if needed)
    current_poll = ensure_current_poll_exists()
    
    # Get current poll rankings if poll exists
    current_rankings = []
    total_ballots = 0
    if current_poll:
        # Get aggregated results for current poll
        results = current_poll.get_results()
        
        # Calculate weighted rankings (same logic as results page but limited to top 15)
        for i, result in enumerate(results[:15], 1):  # Top 15 for homepage
            # Find team data for logo
            team_data = next((t for t in teams if t['name'] == result.team_name), None)
            logo_url = team_data['logo_url'] if team_data else ''
            
            current_rankings.append({
                'rank': i,
                'team_name': result.team_name,
                'vote_count': result.vote_count,
                'avg_rank': round(result.avg_rank, 2),
                'points': max(26 - result.avg_rank, 0),  # Points calculation
                'logo_url': logo_url
            })
        
        # Get total number of ballots submitted
        total_ballots = UserBallot.query.filter_by(poll_id=current_poll.id).count()
    
    user_has_voted = False
    user_ballot = None
    
    if current_poll:
        # Check if user has already voted
        user_id = session.get('user_id')  # Assuming simple session-based auth
        user_identifier = session.get('guest_id', request.remote_addr)
        
        if user_id:
            user_ballot = UserBallot.query.filter_by(poll_id=current_poll.id, user_id=user_id).first()
        else:
            user_ballot = UserBallot.query.filter_by(poll_id=current_poll.id, user_identifier=user_identifier).first()
        
        user_has_voted = user_ballot is not None
    
    return render_template('creatorpoll/home.html', 
                         current_poll=current_poll,
                         current_rankings=current_rankings,
                         total_ballots=total_ballots,
                         teams=teams,
                         conferences=conferences,
                         user_has_voted=user_has_voted,
                         user_ballot=user_ballot)

@bp.route("/vote/<int:poll_id>", methods=['GET', 'POST'])
def vote(poll_id):
    """Vote on a specific poll"""
    poll = Poll.query.get_or_404(poll_id)
    teams, conferences = load_cfb_teams()
    
    # Poll locking removed - always allow submissions
    # if not poll.is_open:
    #     flash('This poll is no longer accepting votes.', 'warning')
    #     return redirect(url_for('creatorpoll.results', poll_id=poll_id))
    
    if request.method == 'POST':
        from app.utils.daily_limits import has_played_today, mark_played_today
        
        # Check daily voting limit
        has_voted_today, _ = has_played_today('creatorpoll')
        
        # Process the vote submission
        ballot_data = []
        user_id = session.get('user_id')
        user_identifier = session.get('guest_id', request.remote_addr)
        
        # Collect all 25 rankings from the form
        for rank in range(1, 26):
            team_name = request.form.get(f'rank_{rank}', '').strip()
            reasoning = request.form.get(f'reasoning_{rank}', '').strip()
            
            if team_name:
                # Find team data (search by name, display_name, or abbreviation)
                team_data = None
                for t in teams:
                    if (t['name'] == team_name or 
                        t['display_name'] == team_name or 
                        t['abbreviation'] == team_name):
                        team_data = t
                        break
                
                team_conference = team_data['conference'] if team_data else ''
                team_id = team_data['id'] if team_data else ''
                
                ballot_data.append({
                    'rank': rank,
                    'team_name': team_name,
                    'team_id': team_id,
                    'team_conference': team_conference,
                    'reasoning': reasoning
                })
        
        if len(ballot_data) < 25:
            flash('Please rank all 25 teams before submitting.', 'error')
            return render_template('creatorpoll/vote.html', poll=poll, teams=teams, conferences=conferences)
        
        try:
            # Check if user already has a ballot
            if user_id:
                existing_ballot = UserBallot.query.filter_by(poll_id=poll_id, user_id=user_id).first()
            else:
                existing_ballot = UserBallot.query.filter_by(poll_id=poll_id, user_identifier=user_identifier).first()
            
            if existing_ballot:
                # Update existing ballot (allow updates to existing ballots)
                existing_ballot.ballot_data = ballot_data
                existing_ballot.updated_at = datetime.utcnow()
                flash('Your ballot has been updated!', 'success')
            else:
                # Check daily limit for new ballots only
                if has_voted_today:
                    flash('You have already voted on a poll today. Come back tomorrow to vote on new polls!', 'warning')
                    return redirect(url_for('creatorpoll.vote', poll_id=poll_id))
                
                # Create new ballot
                ballot = UserBallot(
                    poll_id=poll_id,
                    user_id=user_id,
                    user_identifier=user_identifier if not user_id else None,
                    ballot_data=ballot_data
                )
                db.session.add(ballot)
                flash('Your ballot has been submitted!', 'success')
                
                # Mark as played today only for new ballots
                mark_played_today('creatorpoll')
            
            # Also create/update individual vote records for easier querying
            # Delete existing votes first
            if user_id:
                Vote.query.filter_by(poll_id=poll_id, user_id=user_id).delete()
            else:
                Vote.query.filter_by(poll_id=poll_id, user_identifier=user_identifier).delete()
            
            # Add new votes
            for vote_data in ballot_data:
                vote = Vote(
                    poll_id=poll_id,
                    user_id=user_id,
                    user_identifier=user_identifier if not user_id else None,
                    team_name=vote_data['team_name'],
                    team_conference=vote_data['team_conference'],
                    rank=vote_data['rank'],
                    reasoning=vote_data['reasoning']
                )
                db.session.add(vote)
            
            db.session.commit()
            
            # Save to unified game scores for tracking (if user is logged in)
            if user_id:
                from flask_login import current_user
                if current_user.is_authenticated:
                    # Calculate a "score" for the poll submission (25 points for completing all 25 rankings)
                    score = len(ballot_data)  # Number of teams ranked
                    max_points = 25  # Maximum possible teams to rank
                    
                    current_user.save_game_score(
                        game_type='creatorpoll',
                        quiz_id=f"poll_{poll_id}_week_{poll.week_number}_{poll.season_year}",
                        score=score,
                        max_points=max_points,
                        time_taken=None,  # Not tracked for polls
                        metadata={
                            'poll_id': poll_id,
                            'week_number': poll.week_number,
                            'season_year': poll.season_year,
                            'submission_type': 'update' if existing_ballot else 'new'
                        }
                    )
            
            return redirect(url_for('creatorpoll.results', poll_id=poll_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting ballot: {str(e)}', 'error')
            return render_template('creatorpoll/vote.html', poll=poll, teams=teams, conferences=conferences)
    
    # GET request - show voting form
    # Check if user already voted
    user_id = session.get('user_id')
    user_identifier = session.get('guest_id', request.remote_addr)
    
    existing_ballot = None
    if user_id:
        existing_ballot = UserBallot.query.filter_by(poll_id=poll_id, user_id=user_id).first()
    else:
        existing_ballot = UserBallot.query.filter_by(poll_id=poll_id, user_identifier=user_identifier).first()
    
    return render_template('creatorpoll/vote.html', 
                         poll=poll, 
                         teams=teams, 
                         conferences=conferences,
                         existing_ballot=existing_ballot)

@bp.route("/results/<int:poll_id>")
def results(poll_id):
    """Show results for a specific poll"""
    poll = Poll.query.get_or_404(poll_id)
    
    # Get aggregated results
    results = poll.get_results()
    
    # Get enhanced results with movement tracking
    enhanced_results = poll.get_results_with_movement()
    teams, _ = load_cfb_teams()  # Load team data for logos
    
    # Top 25 rankings with movement
    final_rankings = []
    for result in enhanced_results[:25]:  # Top 25 only
        # Find team data for logo
        team_data = next((t for t in teams if t['name'] == result['team_name']), None)
        logo_url = team_data['logo_url'] if team_data else ''
        
        final_rankings.append({
            'rank': result['rank'],
            'team_name': result['team_name'],
            'vote_count': result['vote_count'],
            'avg_rank': round(result['avg_rank'], 2),
            'points': max(26 - result['avg_rank'], 0),  # Points calculation
            'logo_url': logo_url,
            'previous_rank': result['previous_rank'],
            'movement': result['movement'],
            'movement_type': result['movement_type']
        })
    
    # Others receiving votes (teams ranked 26+)
    others_receiving_votes = []
    for result in enhanced_results[25:]:  # Teams beyond top 25
        # Find team data for logo
        team_data = next((t for t in teams if t['name'] == result['team_name']), None)
        logo_url = team_data['logo_url'] if team_data else ''
        
        others_receiving_votes.append({
            'team_name': result['team_name'],
            'vote_count': result['vote_count'],
            'logo_url': logo_url
        })
    
    # Get total number of ballots submitted
    total_ballots = UserBallot.query.filter_by(poll_id=poll_id).count()
    
    return render_template('creatorpoll/results.html', 
                         poll=poll, 
                         rankings=final_rankings, 
                         others_receiving_votes=others_receiving_votes,
                         total_ballots=total_ballots)

@bp.route("/admin/create_poll", methods=['GET', 'POST'])
def create_poll():
    """Admin function to create a new poll"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        week_number = int(request.form.get('week_number', get_current_week()))
        season_year = int(request.form.get('season_year', get_current_season()))
        
        # Use scheduled start/end times for consistency
        poll_start, poll_end = get_poll_start_end_times(week_number, season_year)
        
        # Create poll
        poll = Poll(
            title=title or f"CFB Creator Poll - Week {week_number}",
            description=description or f"Rank your top 25 college football teams for Week {week_number} of the {season_year} season. Voting opens Sunday 3pm EST and locks Thursday 3pm EST.",
            week_number=week_number,
            season_year=season_year,
            start_date=poll_start,
            end_date=poll_end,
            is_active=True
        )
        
        from app.starting5.models import db
        db.session.add(poll)
        db.session.commit()
        
        flash(f'Poll "{poll.title}" created successfully!', 'success')
        return redirect(url_for('creatorpoll.home'))
    
    return render_template('creatorpoll/create_poll.html',
                         current_week=get_current_week(),
                         current_season=get_current_season())

@bp.route("/api/search_teams")
def search_teams():
    """API endpoint to search for teams"""
    query = request.args.get('q', '').lower()
    teams, _ = load_cfb_teams()
    
    if not query:
        return jsonify([])
    
    matching_teams = []
    for team in teams:
        # Search in name, abbreviation, and alternate names
        searchable_text = ' '.join([
            team['name'].lower(),
            team['abbreviation'].lower(),
            team['alternate_names'].lower(),
            team['display_name'].lower()
        ])
        
        if query in searchable_text:
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
        if os.path.exists(logo_path):
            return send_file(logo_path, mimetype='image/png')
        else:
            # Return 404 if file doesn't exist
            return "Logo not found", 404
    except Exception as e:
        return "Error serving logo", 500
