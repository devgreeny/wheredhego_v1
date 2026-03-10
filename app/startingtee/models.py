from app.starting5.models import db
from datetime import datetime


class StartingTeeScore(db.Model):
    """Track scores for StartingTee golf course guessing game."""
    __tablename__ = 'startingtee_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(100), nullable=False)  # course_id
    user_id = db.Column(db.Integer, nullable=True)  # NULL for guests
    score = db.Column(db.Integer, nullable=False)  # 1-4 based on hints used
    max_points = db.Column(db.Integer, default=4)
    time_taken = db.Column(db.Integer, nullable=True)  # seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StartingTeeScore {self.quiz_id}: {self.score}/{self.max_points}>'
