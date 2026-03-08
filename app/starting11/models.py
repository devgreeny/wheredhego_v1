from datetime import datetime
from app.starting5.models import db

class Starting11Score(db.Model):
    __tablename__ = 'starting11_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)
    score = db.Column(db.Float, nullable=False)
    max_points = db.Column(db.Float, nullable=False)
    time_taken = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Starting11Score {self.quiz_id}: {self.score}/{self.max_points}>'
