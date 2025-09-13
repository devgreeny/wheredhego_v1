#!/usr/bin/env python3
"""
Simple script to create a sample CFB poll for testing
Run this once to set up the first poll
"""

import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.starting5.models import db
from app.creatorpoll.models import Poll

def create_sample_poll():
    """Create a sample poll for testing"""
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if poll already exists
        existing_poll = Poll.query.filter_by(
            season_year=2024,
            week_number=1,
            is_active=True
        ).first()
        
        if existing_poll:
            print(f"Poll already exists: {existing_poll.title}")
            return
        
        # Create sample poll
        poll = Poll(
            title="CFB Creator Poll - Week 1",
            description="Welcome to the inaugural CFB Creator Poll! Rank your top 25 college football teams.",
            week_number=1,
            season_year=2024,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            is_active=True
        )
        
        db.session.add(poll)
        db.session.commit()
        
        print(f"✅ Created sample poll: {poll.title}")
        print(f"   Poll ID: {poll.id}")
        print(f"   Closes: {poll.end_date}")
        print(f"   Access at: /creatorpoll")

if __name__ == "__main__":
    create_sample_poll()
