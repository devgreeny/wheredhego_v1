from datetime import datetime, timedelta
from app.starting5.models import db, User

class Poll(db.Model):
    """Represents a weekly CFB poll"""
    id = db.Column(db.Integer, primary_key=True)
    week_number = db.Column(db.Integer, nullable=False)
    season_year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    votes = db.relationship('Vote', backref='poll', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Poll {self.season_year} Week {self.week_number}>'
    
    @property
    def is_open(self):
        """Check if poll is currently open for voting"""
        now = datetime.utcnow()
        
        # Poll is open from Sunday 3pm to Thursday 3pm
        # After Thursday 3pm, it's locked until the next Sunday 3pm (next week)
        if not self.is_active:
            return False
            
        # Check if we're in the voting window (Sunday 3pm to Thursday 3pm)
        return self.start_date <= now <= self.end_date
    
    @property
    def status_message(self):
        """Get a human-readable status message for the poll"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return "Poll closed"
        
        if now < self.start_date:
            return f"Poll opens {self.start_date.strftime('%A, %B %d at %I:%M %p EST')}"
        elif now > self.end_date:
            # Poll is locked, calculate when next poll opens
            next_week_start = self.start_date + timedelta(weeks=1)
            return f"Poll locked. Next poll opens {next_week_start.strftime('%A, %B %d at %I:%M %p EST')}"
        else:
            return f"Poll open until {self.end_date.strftime('%A, %B %d at %I:%M %p EST')}"
    
    def get_results(self):
        """Get poll results with vote counts and rankings"""
        from sqlalchemy import func
        results = db.session.query(
            Vote.team_name,
            func.count(Vote.id).label('vote_count'),
            func.avg(Vote.rank).label('avg_rank')
        ).filter_by(poll_id=self.id).group_by(Vote.team_name).order_by(func.avg(Vote.rank)).all()
        
        return results
    
    def get_previous_week_poll(self):
        """Get the poll from the previous week"""
        if self.week_number == 1:
            # If this is week 1, look for the last week of previous season
            previous_season = self.season_year - 1
            return Poll.query.filter_by(
                season_year=previous_season
            ).order_by(Poll.week_number.desc()).first()
        else:
            # Look for previous week in same season
            return Poll.query.filter_by(
                season_year=self.season_year,
                week_number=self.week_number - 1
            ).first()
    
    def get_results_with_movement(self):
        """Get poll results with movement compared to previous week"""
        current_results = self.get_results()
        previous_poll = self.get_previous_week_poll()
        
        # Create a dictionary of current rankings
        current_rankings = {}
        for i, result in enumerate(current_results, 1):
            current_rankings[result.team_name] = i
        
        # Get previous rankings if available
        previous_rankings = {}
        if previous_poll:
            previous_results = previous_poll.get_results()
            for i, result in enumerate(previous_results, 1):
                previous_rankings[result.team_name] = i
        
        # Calculate movements and enhance results
        enhanced_results = []
        for i, result in enumerate(current_results, 1):
            team_name = result.team_name
            previous_rank = previous_rankings.get(team_name)
            
            # Calculate movement
            movement = None
            movement_type = None
            if previous_rank is not None:
                movement = previous_rank - i  # Positive = moved up, negative = moved down
                if movement > 0:
                    movement_type = 'up'
                elif movement < 0:
                    movement_type = 'down'
                else:
                    movement_type = 'same'
            else:
                movement_type = 'new'  # New to rankings
            
            enhanced_results.append({
                'rank': i,
                'team_name': team_name,
                'vote_count': result.vote_count,
                'avg_rank': result.avg_rank,
                'previous_rank': previous_rank,
                'movement': movement,
                'movement_type': movement_type
            })
        
        return enhanced_results

class Vote(db.Model):
    """Represents a user's vote for a team in a specific poll"""
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for guest votes
    user_identifier = db.Column(db.String(120))  # For guest users (IP or session)
    team_name = db.Column(db.String(100), nullable=False)
    team_conference = db.Column(db.String(50))
    rank = db.Column(db.Integer, nullable=False)  # 1-25 ranking
    reasoning = db.Column(db.Text)  # Optional reasoning for the vote
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: one vote per user per team per poll
    __table_args__ = (
        db.UniqueConstraint('poll_id', 'user_id', 'rank', name='unique_user_rank_per_poll'),
        db.UniqueConstraint('poll_id', 'user_identifier', 'rank', name='unique_guest_rank_per_poll'),
    )
    
    def __repr__(self):
        return f'<Vote {self.team_name} #{self.rank}>'

class UserBallot(db.Model):
    """Represents a complete user ballot for a poll"""
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_identifier = db.Column(db.String(120))  # For guest users
    ballot_data = db.Column(db.JSON)  # Store complete top 25 as JSON
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one ballot per user per poll
    __table_args__ = (
        db.UniqueConstraint('poll_id', 'user_id', name='unique_user_ballot_per_poll'),
        db.UniqueConstraint('poll_id', 'user_identifier', name='unique_guest_ballot_per_poll'),
    )
    
    def __repr__(self):
        user_ref = f"User {self.user_id}" if self.user_id else f"Guest {self.user_identifier}"
        return f'<UserBallot {user_ref} Poll {self.poll_id}>'
