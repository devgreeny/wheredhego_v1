"""
SQLite-based User Authentication Models for Local Development
Uses Flask-SQLAlchemy for compatibility with existing setup
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

# Use the existing db instance from starting5
from app.starting5.models import db

class User(UserMixin, db.Model):
    """Unified User model using SQLAlchemy for local development"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # Removed display_name - using username only
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    game_scores = db.relationship('GameScore', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, username, email):
        self.username = username
        self.email = email
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    @classmethod
    def create_user(cls, username: str, email: str, password: str):
        """Create a new user account"""
        try:
            # Check if user already exists
            existing_user = cls.query.filter(
                (cls.username == username) | (cls.email == email)
            ).first()
            
            if existing_user:
                return None  # User already exists
            
            # Create new user
            user = cls(username=username, email=email)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            return user
            
        except Exception as e:
            db.session.rollback()
            print(f"User creation error: {e}")
            return None
    
    @classmethod
    def authenticate(cls, username: str, password: str):
        """Authenticate user and return User object"""
        try:
            user = cls.query.filter(
                (cls.username == username) | (cls.email == username),
                cls.is_active == True
            ).first()
            
            if user and user.check_password(password):
                # Update last login
                user.last_login = datetime.utcnow()
                db.session.commit()
                return user
            
            return None
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, user_id: int):
        """Get user by ID for Flask-Login"""
        try:
            return cls.query.filter_by(id=user_id, is_active=True).first()
        except Exception as e:
            print(f"Get user by ID error: {e}")
            return None
    
    def save_game_score(self, game_type: str, quiz_id: str, score: float, 
                       max_points: float = None, time_taken: int = None, metadata: dict = None):
        """Save a game score for this user"""
        try:
            game_score = GameScore(
                user_id=self.id,
                game_type=game_type,
                quiz_id=quiz_id,
                score=score,
                max_points=max_points,
                time_taken=time_taken,
                metadata_json=json.dumps(metadata) if metadata else None
            )
            
            db.session.add(game_score)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Save game score error: {e}")
            return False
    
    def get_game_scores(self, game_type: str = None, limit: int = 50):
        """Get user's game scores"""
        try:
            query = GameScore.query.filter_by(user_id=self.id)
            
            if game_type:
                query = query.filter_by(game_type=game_type)
            
            scores = query.order_by(GameScore.created_at.desc()).limit(limit).all()
            
            # Convert to dict format for compatibility
            return [{
                'id': s.id,
                'game_type': s.game_type,
                'quiz_id': s.quiz_id,
                'score': s.score,
                'max_points': s.max_points,
                'time_taken': s.time_taken,
                'metadata': json.loads(s.metadata_json) if s.metadata_json else None,
                'created_at': s.created_at
            } for s in scores]
            
        except Exception as e:
            print(f"Get game scores error: {e}")
            return []
    
    def get_stats_summary(self):
        """Get user's overall gaming stats"""
        try:
            from sqlalchemy import func
            
            stats = db.session.query(
                GameScore.game_type,
                func.count(GameScore.id).label('total_games'),
                func.avg(GameScore.score).label('avg_score'),
                func.max(GameScore.score).label('best_score'),
                func.sum(GameScore.score).label('total_points')
            ).filter_by(user_id=self.id).group_by(GameScore.game_type).all()
            
            return [{
                'game_type': stat.game_type,
                'total_games': stat.total_games,
                'avg_score': float(stat.avg_score) if stat.avg_score else 0,
                'best_score': float(stat.best_score) if stat.best_score else 0,
                'total_points': float(stat.total_points) if stat.total_points else 0
            } for stat in stats]
            
        except Exception as e:
            print(f"Get stats summary error: {e}")
            return []

class GameScore(db.Model):
    """Unified game scores table"""
    __tablename__ = 'game_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    game_type = db.Column(db.String(50), nullable=False)  # 'starting5', 'gridiron11', 'creatorpoll'
    quiz_id = db.Column(db.String(120))
    score = db.Column(db.Float, nullable=False)
    max_points = db.Column(db.Float)
    time_taken = db.Column(db.Integer)
    metadata_json = db.Column(db.Text)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<GameScore {self.user_id}:{self.game_type}:{self.score}>'
