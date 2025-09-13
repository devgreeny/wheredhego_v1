from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GuessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    player_name = db.Column(db.String(120), nullable=False)
    school = db.Column(db.String(120), nullable=False)
    guess = db.Column(db.String(120), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    used_hint = db.Column(db.Boolean, nullable=False, default=False)
    quiz_id = db.Column(db.String(120), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ScoreLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    quiz_id = db.Column(db.String(120), nullable=False)
    score = db.Column(db.Float, nullable=False)
    max_points = db.Column(db.Float, nullable=True)
    time_taken = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
