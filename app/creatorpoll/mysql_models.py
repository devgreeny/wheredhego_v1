"""
MySQL Creator Poll Models
Updated models for MySQL database with movement tracking
"""

import mysql.connector
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import bcrypt
import secrets

class MySQLConnection:
    def __init__(self, config):
        self.config = config
    
    def get_connection(self):
        return mysql.connector.connect(**self.config)

class CreatorUser:
    def __init__(self, db_config):
        self.db = MySQLConnection(db_config)
    
    def create_creator(self, username: str, email: str, password: str, 
                      display_name: str, bio: str = "", twitter_handle: str = "") -> bool:
        """Create a new creator account"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO user_creator (username, email, password_hash, display_name, bio, twitter_handle)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, email, password_hash, display_name, bio, twitter_handle))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except mysql.connector.IntegrityError:
            return False
    
    def authenticate_creator(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate creator and return user data"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, username, email, password_hash, display_name, is_active, is_admin
            FROM user_creator 
            WHERE (username = %s OR email = %s) AND is_active = TRUE
        """, (username, username))
        
        creator = cursor.fetchone()
        
        if creator and bcrypt.checkpw(password.encode('utf-8'), creator['password_hash'].encode('utf-8')):
            # Update last login
            cursor.execute("""
                UPDATE user_creator SET last_login = NOW() WHERE id = %s
            """, (creator['id'],))
            
            # Create session
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=30)
            
            cursor.execute("""
                INSERT INTO creator_sessions (session_id, creator_id, expires_at)
                VALUES (%s, %s, %s)
            """, (session_id, creator['id'], expires_at))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'creator_id': creator['id'],
                'username': creator['username'],
                'display_name': creator['display_name'],
                'is_admin': creator['is_admin'],
                'session_id': session_id
            }
        
        cursor.close()
        conn.close()
        return None
    
    def validate_session(self, session_id: str) -> Optional[Dict]:
        """Validate creator session"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT cs.creator_id, cs.expires_at, uc.username, uc.display_name, uc.is_admin
            FROM creator_sessions cs
            JOIN user_creator uc ON cs.creator_id = uc.id
            WHERE cs.session_id = %s AND cs.expires_at > NOW() AND uc.is_active = TRUE
        """, (session_id,))
        
        session_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if session_data:
            return {
                'valid': True,
                'creator_id': session_data['creator_id'],
                'username': session_data['username'],
                'display_name': session_data['display_name'],
                'is_admin': session_data['is_admin']
            }
        
        return {'valid': False}

class CreatorPoll:
    def __init__(self, db_config):
        self.db = MySQLConnection(db_config)
    
    def create_poll(self, week_number: int, season_year: int, title: str, 
                   description: str, start_date: datetime, end_date: datetime) -> int:
        """Create a new poll"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO creator_polls (week_number, season_year, title, description, start_date, end_date, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """, (week_number, season_year, title, description, start_date, end_date))
        
        poll_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return poll_id
    
    def get_current_poll(self) -> Optional[Dict]:
        """Get the current active poll"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM creator_polls 
            WHERE is_active = TRUE AND start_date <= NOW() AND end_date >= NOW()
            ORDER BY created_at DESC 
            LIMIT 1
        """, )
        
        poll = cursor.fetchone()
        cursor.close()
        conn.close()
        return poll
    
    def get_poll_by_id(self, poll_id: int) -> Optional[Dict]:
        """Get poll by ID"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM creator_polls WHERE id = %s", (poll_id,))
        poll = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return poll
    
    def get_previous_week_poll(self, current_week: int, current_season: int) -> Optional[Dict]:
        """Get previous week's poll for movement calculation"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if current_week == 1:
            # Look for last week of previous season
            cursor.execute("""
                SELECT * FROM creator_polls 
                WHERE season_year = %s AND is_archived = TRUE
                ORDER BY week_number DESC 
                LIMIT 1
            """, (current_season - 1,))
        else:
            # Look for previous week in same season
            cursor.execute("""
                SELECT * FROM creator_polls 
                WHERE season_year = %s AND week_number = %s
                LIMIT 1
            """, (current_season, current_week - 1))
        
        poll = cursor.fetchone()
        cursor.close()
        conn.close()
        return poll
    
    def get_poll_results(self, poll_id: int) -> List[Dict]:
        """Get aggregated poll results"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                team_name,
                COUNT(*) as vote_count,
                AVG(rank_position) as avg_rank
            FROM creator_votes 
            WHERE poll_id = %s 
            GROUP BY team_name 
            ORDER BY avg_rank ASC
        """, (poll_id,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    
    def get_poll_results_with_movement(self, poll_id: int) -> List[Dict]:
        """Get poll results with week-to-week movement"""
        current_poll = self.get_poll_by_id(poll_id)
        if not current_poll:
            return []
        
        current_results = self.get_poll_results(poll_id)
        previous_poll = self.get_previous_week_poll(current_poll['week_number'], current_poll['season_year'])
        
        # Get previous week rankings
        previous_rankings = {}
        if previous_poll:
            # Check if poll is archived (use archive data) or calculate live
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT final_rankings FROM poll_archives WHERE poll_id = %s
            """, (previous_poll['id'],))
            
            archive = cursor.fetchone()
            
            if archive:
                # Use archived rankings
                archived_rankings = json.loads(archive['final_rankings'])
                for ranking in archived_rankings:
                    previous_rankings[ranking['team_name']] = ranking['rank']
            else:
                # Calculate live rankings
                previous_results = self.get_poll_results(previous_poll['id'])
                for i, result in enumerate(previous_results, 1):
                    previous_rankings[result['team_name']] = i
            
            cursor.close()
            conn.close()
        
        # Calculate movement
        enhanced_results = []
        for i, result in enumerate(current_results, 1):
            team_name = result['team_name']
            previous_rank = previous_rankings.get(team_name)
            
            # Calculate movement
            movement = None
            movement_type = None
            if previous_rank is not None:
                movement = previous_rank - i  # Positive = moved up
                if movement > 0:
                    movement_type = 'up'
                elif movement < 0:
                    movement_type = 'down'
                else:
                    movement_type = 'same'
            else:
                movement_type = 'new'
            
            enhanced_results.append({
                'rank': i,
                'team_name': team_name,
                'vote_count': result['vote_count'],
                'avg_rank': float(result['avg_rank']),
                'points': max(26 - result['avg_rank'], 0),
                'previous_rank': previous_rank,
                'movement': movement,
                'movement_type': movement_type
            })
        
        return enhanced_results
    
    def archive_poll(self, poll_id: int) -> bool:
        """Archive a completed poll"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get poll info
            poll = self.get_poll_by_id(poll_id)
            if not poll:
                return False
            
            # Calculate final rankings
            results = self.get_poll_results(poll_id)
            final_rankings = []
            
            for rank, result in enumerate(results, 1):
                final_rankings.append({
                    'rank': rank,
                    'team_name': result['team_name'],
                    'vote_count': int(result['vote_count']),
                    'avg_rank': float(result['avg_rank']),
                    'points': max(26 - result['avg_rank'], 0)
                })
            
            # Get total ballots
            cursor.execute("SELECT COUNT(*) FROM creator_ballots WHERE poll_id = %s", (poll_id,))
            total_ballots = cursor.fetchone()[0]
            
            # Archive the poll
            cursor.execute("""
                INSERT INTO poll_archives (poll_id, final_rankings, total_ballots, season_year, week_number)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                final_rankings = VALUES(final_rankings), total_ballots = VALUES(total_ballots)
            """, (poll_id, json.dumps(final_rankings), total_ballots, poll['season_year'], poll['week_number']))
            
            # Mark poll as archived
            cursor.execute("""
                UPDATE creator_polls 
                SET is_archived = TRUE, archived_at = NOW(), is_active = FALSE 
                WHERE id = %s
            """, (poll_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e

class CreatorBallot:
    def __init__(self, db_config):
        self.db = MySQLConnection(db_config)
    
    def submit_ballot(self, poll_id: int, creator_id: int, ballot_data: List[Dict]) -> bool:
        """Submit or update a creator's ballot"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Insert/update ballot
            cursor.execute("""
                INSERT INTO creator_ballots (poll_id, creator_id, ballot_data)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                ballot_data = VALUES(ballot_data), updated_at = NOW()
            """, (poll_id, creator_id, json.dumps(ballot_data)))
            
            # Delete existing votes
            cursor.execute("""
                DELETE FROM creator_votes WHERE poll_id = %s AND creator_id = %s
            """, (poll_id, creator_id))
            
            # Insert individual votes
            for vote in ballot_data:
                cursor.execute("""
                    INSERT INTO creator_votes 
                    (poll_id, creator_id, team_name, team_conference, team_id, rank_position, reasoning)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (poll_id, creator_id, vote['team_name'], vote.get('team_conference', ''), 
                     vote.get('team_id', ''), vote['rank'], vote.get('reasoning', '')))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e
    
    def get_creator_ballot(self, poll_id: int, creator_id: int) -> Optional[List[Dict]]:
        """Get creator's ballot for a poll"""
        conn = self.db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT ballot_data FROM creator_ballots 
            WHERE poll_id = %s AND creator_id = %s
        """, (poll_id, creator_id))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return json.loads(result['ballot_data'])
        return None
    
    def get_poll_ballot_count(self, poll_id: int) -> int:
        """Get total number of ballots for a poll"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM creator_ballots WHERE poll_id = %s", (poll_id,))
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return count

# Example usage and configuration
if __name__ == "__main__":
    # MySQL configuration - update with your credentials
    mysql_config = {
        'host': 'localhost',
        'user': 'your_username',
        'password': 'your_password',
        'database': 'devgreeny$default'
    }
    
    # Initialize models
    creator_user = CreatorUser(mysql_config)
    creator_poll = CreatorPoll(mysql_config)
    creator_ballot = CreatorBallot(mysql_config)
    
    # Example: Create a creator
    success = creator_user.create_creator(
        username="test_creator",
        email="test@example.com",
        password="secure_password",
        display_name="Test Creator",
        bio="Test creator account"
    )
    print(f"Creator creation: {'✅' if success else '❌'}")
    
    # Example: Authenticate creator
    auth_result = creator_user.authenticate_creator("test_creator", "secure_password")
    if auth_result:
        print(f"✅ Authenticated: {auth_result['display_name']}")
    
    # Example: Get current poll
    current_poll = creator_poll.get_current_poll()
    if current_poll:
        print(f"📊 Current poll: {current_poll['title']}")
        
        # Get results with movement
        results = creator_poll.get_poll_results_with_movement(current_poll['id'])
        print(f"📈 Poll has {len(results)} teams with movement tracking")
