"""
Unified Authentication Routes
Handles login/register for all games
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
import os

# Use SQLite models for local development, MySQL for production
if os.environ.get('USE_LOCAL_SQLITE') or not os.environ.get('MYSQL_HOST'):
    from .sqlite_models import User
    print("🔧 Using SQLite models for local development")
else:
    from .models import User
    print("🔧 Using MySQL models for production")

bp = Blueprint('auth', __name__, template_folder='../templates/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        user = User.authenticate(username, password)
        if user:
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to the page they were trying to access
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all required fields.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/register.html')
        
        # Create user
        user = User.create_user(username, email, password)
        if user:
            login_user(user)
            flash(f'Account created successfully! Welcome, {user.username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Username or email already exists. Please choose different ones.', 'error')
    
    return render_template('auth/register.html')

@bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@bp.route('/profile')
@login_required
def profile():
    """User profile with game stats"""
    stats = current_user.get_stats_summary()
    recent_scores = current_user.get_game_scores(limit=20)
    
    return render_template('auth/profile.html', 
                         user=current_user, 
                         stats=stats, 
                         recent_scores=recent_scores)

@bp.route('/scores')
@login_required
def scores():
    """Comprehensive scores tracking page for all games"""
    # Get scores for each game type
    starting5_scores = current_user.get_game_scores(game_type='starting5', limit=50)
    skill_positions_scores = current_user.get_game_scores(game_type='skill_positions', limit=50)
    creatorpoll_scores = current_user.get_game_scores(game_type='creatorpoll', limit=50)
    
    # Get poll submissions
    poll_submissions = []
    poll_count = 0
    
    try:
        # Import poll models based on environment
        if os.environ.get('USE_LOCAL_SQLITE') or not os.environ.get('MYSQL_HOST'):
            from app.creatorpoll.models import UserBallot, Poll
            from app.starting5.models import db
            
            # Get user's poll submissions
            ballots = db.session.query(UserBallot, Poll).join(
                Poll, UserBallot.poll_id == Poll.id
            ).filter(UserBallot.user_id == current_user.id).order_by(
                UserBallot.submitted_at.desc()
            ).limit(20).all()
            
            poll_submissions = []
            for ballot, poll in ballots:
                poll_submissions.append({
                    'week_number': poll.week_number,
                    'season_year': poll.season_year,
                    'submitted_at': ballot.submitted_at,
                    'ballot_data': ballot.ballot_data or []
                })
            
            poll_count = db.session.query(UserBallot).filter_by(user_id=current_user.id).count()
            
        else:
            # MySQL implementation would go here
            pass
            
    except Exception as e:
        print(f"Error getting poll submissions: {e}")
    
    # Calculate overall stats
    all_scores = starting5_scores + skill_positions_scores + creatorpoll_scores
    stats = {
        'total_games': len(all_scores),
        'avg_score': 0,
        'best_game': 'N/A'
    }
    
    if all_scores:
        # Calculate average percentage
        percentages = []
        best_score = 0
        best_game_type = 'N/A'
        
        for score in all_scores:
            if score['max_points'] and score['max_points'] > 0:
                percentage = (score['score'] / score['max_points']) * 100
                percentages.append(percentage)
                
                if percentage > best_score:
                    best_score = percentage
                    best_game_type = score['game_type'].title()
        
        if percentages:
            stats['avg_score'] = sum(percentages) / len(percentages)
            stats['best_game'] = f"{best_game_type} ({best_score:.0f}%)"
    
    return render_template('auth/scores.html',
                         user=current_user,
                         stats=stats,
                         starting5_scores=starting5_scores,
                         skill_positions_scores=skill_positions_scores,
                         creatorpoll_scores=creatorpoll_scores,
                         poll_submissions=poll_submissions,
                         poll_count=poll_count)
