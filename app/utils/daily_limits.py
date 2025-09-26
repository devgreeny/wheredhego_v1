"""
Simple daily limits system for wheredhego.com games
Uses existing GameScore table to track daily plays
"""
import hashlib
from datetime import date, datetime
from flask import request, session
from flask_login import current_user
from sqlalchemy import and_, func


def get_guest_identifier():
    """Create consistent identifier for guest users"""
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    user_agent = request.environ.get('HTTP_USER_AGENT', '')
    
    # Create hash for privacy
    identifier_string = f"{ip}:{user_agent}"
    return hashlib.sha256(identifier_string.encode()).hexdigest()[:16]


def has_played_today(game_type, today=None):
    """
    Check if user has already played this game type today
    Returns: (has_played: bool, score_record: GameScore or None)
    """
    if today is None:
        today = date.today()
    
    # For logged-in users, check GameScore table
    if current_user.is_authenticated:
        from app.auth.sqlite_models import GameScore
        
        score_record = GameScore.query.filter(
            and_(
                GameScore.user_id == current_user.id,
                GameScore.game_type == game_type,
                func.date(GameScore.created_at) == today
            )
        ).first()
        
        return score_record is not None, score_record
    
    # For guests, use session storage as backup
    guest_key = f"played_today_{game_type}_{today}"
    has_played = session.get(guest_key, False)
    return has_played, None


def mark_played_today(game_type, today=None):
    """Mark that guest user has played today (for non-logged in users)"""
    if today is None:
        today = date.today()
    
    if not current_user.is_authenticated:
        guest_key = f"played_today_{game_type}_{today}"
        session[guest_key] = True
        session.permanent = True  # Keep session across browser restarts


def get_today_quiz_id(game_type):
    """Get today's quiz ID for a game type"""
    if game_type == 'starting5':
        # Starting5 uses date-based quiz files
        return date.today().strftime("%Y-%m-%d")
    elif game_type == 'skill_positions':
        # Skill positions uses current quiz file
        return date.today().strftime("%Y-%m-%d") 
    elif game_type == 'creatorpoll':
        # Polls use week-based IDs
        return f"week_{date.today().isocalendar()[1]}_{date.today().year}"
    
    return "daily"
