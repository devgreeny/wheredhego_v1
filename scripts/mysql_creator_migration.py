"""
MySQL Creator Poll Migration Script
- Migrates from SQLite to existing MySQL database
- Creates separate user_creator table for creators
- Archives all poll weeks for movement tracking
- Preserves all existing data
"""

import mysql.connector
import sqlite3
import json
from datetime import datetime
import os

class MySQLCreatorMigration:
    def __init__(self, mysql_config):
        """
        mysql_config = {
            'host': 'localhost',
            'user': 'your_user',
            'password': 'your_password', 
            'database': 'devgreeny$default'  # Your existing DB
        }
        """
        self.mysql_config = mysql_config
        self.sqlite_path = '/Users/noah/Desktop/wheredhego_v1/app/wheredhego.db'
    
    def connect_mysql(self):
        """Connect to MySQL database"""
        return mysql.connector.connect(**self.mysql_config)
    
    def connect_sqlite(self):
        """Connect to SQLite database"""
        return sqlite3.connect(self.sqlite_path)
    
    def create_creator_tables(self):
        """Create new MySQL tables for creator poll system"""
        mysql_conn = self.connect_mysql()
        cursor = mysql_conn.cursor()
        
        # 1. Creator users table (separate from regular users)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_creator (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                bio TEXT,
                twitter_handle VARCHAR(50),
                profile_image VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                INDEX idx_username (username),
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 2. Weekly polls table (archives all weeks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_polls (
                id INT PRIMARY KEY AUTO_INCREMENT,
                week_number INT NOT NULL,
                season_year INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                start_date DATETIME NOT NULL,
                end_date DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived_at TIMESTAMP NULL,
                UNIQUE KEY unique_week_season (week_number, season_year),
                INDEX idx_active_polls (is_active, season_year, week_number),
                INDEX idx_archive_status (is_archived)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 3. Creator ballots (complete Top 25 rankings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_ballots (
                id INT PRIMARY KEY AUTO_INCREMENT,
                poll_id INT NOT NULL,
                creator_id INT NOT NULL,
                ballot_data JSON NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (poll_id) REFERENCES creator_polls(id) ON DELETE CASCADE,
                FOREIGN KEY (creator_id) REFERENCES user_creator(id) ON DELETE CASCADE,
                UNIQUE KEY unique_creator_poll (creator_id, poll_id),
                INDEX idx_poll_ballots (poll_id),
                INDEX idx_creator_ballots (creator_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 4. Individual votes (for aggregation queries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_votes (
                id INT PRIMARY KEY AUTO_INCREMENT,
                poll_id INT NOT NULL,
                creator_id INT NOT NULL,
                team_name VARCHAR(100) NOT NULL,
                team_conference VARCHAR(50),
                team_id VARCHAR(20),
                rank_position INT NOT NULL,
                reasoning TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (poll_id) REFERENCES creator_polls(id) ON DELETE CASCADE,
                FOREIGN KEY (creator_id) REFERENCES user_creator(id) ON DELETE CASCADE,
                UNIQUE KEY unique_creator_rank (creator_id, poll_id, rank_position),
                INDEX idx_poll_votes (poll_id),
                INDEX idx_team_votes (team_name),
                INDEX idx_rankings (poll_id, team_name, rank_position)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 5. Creator sessions (secure login management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_sessions (
                session_id VARCHAR(64) PRIMARY KEY,
                creator_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (creator_id) REFERENCES user_creator(id) ON DELETE CASCADE,
                INDEX idx_creator_sessions (creator_id),
                INDEX idx_session_expiry (expires_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 6. Poll archives (for historical movement tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_archives (
                id INT PRIMARY KEY AUTO_INCREMENT,
                poll_id INT NOT NULL,
                final_rankings JSON NOT NULL,
                total_ballots INT NOT NULL,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                season_year INT NOT NULL,
                week_number INT NOT NULL,
                FOREIGN KEY (poll_id) REFERENCES creator_polls(id),
                UNIQUE KEY unique_poll_archive (poll_id),
                INDEX idx_archive_season (season_year, week_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        mysql_conn.commit()
        cursor.close()
        mysql_conn.close()
        print("✅ Created all MySQL creator poll tables")
    
    def migrate_existing_data(self):
        """Migrate existing SQLite data to MySQL"""
        sqlite_conn = self.connect_sqlite()
        mysql_conn = self.connect_mysql()
        
        sqlite_cursor = sqlite_conn.cursor()
        mysql_cursor = mysql_conn.cursor()
        
        # Migrate polls
        sqlite_cursor.execute("SELECT * FROM poll")
        polls = sqlite_cursor.fetchall()
        
        for poll in polls:
            mysql_cursor.execute("""
                INSERT INTO creator_polls 
                (id, week_number, season_year, title, description, start_date, end_date, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                title = VALUES(title), description = VALUES(description)
            """, poll)
        
        # Migrate user ballots (create temp creators)
        sqlite_cursor.execute("SELECT * FROM user_ballot")
        ballots = sqlite_cursor.fetchall()
        
        creator_mapping = {}
        for ballot in ballots:
            ballot_id, poll_id, user_id, user_identifier, ballot_data, submitted_at, updated_at = ballot
            
            # Create temporary creator if doesn't exist
            if user_identifier and user_identifier not in creator_mapping:
                temp_username = f"creator_{user_identifier.replace('.', '_')}"
                temp_email = f"{temp_username}@temp.com"
                
                mysql_cursor.execute("""
                    INSERT INTO user_creator (username, email, password_hash, display_name, bio)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
                """, (temp_username, temp_email, 'temp_hash', f"Creator {user_identifier}", 'Migrated from SQLite'))
                
                creator_mapping[user_identifier] = mysql_cursor.lastrowid
            
            creator_id = creator_mapping.get(user_identifier, 1)
            
            # Insert ballot
            mysql_cursor.execute("""
                INSERT INTO creator_ballots (poll_id, creator_id, ballot_data, submitted_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                ballot_data = VALUES(ballot_data), updated_at = VALUES(updated_at)
            """, (poll_id, creator_id, ballot_data, submitted_at, updated_at))
        
        # Migrate individual votes
        sqlite_cursor.execute("SELECT * FROM vote")
        votes = sqlite_cursor.fetchall()
        
        for vote in votes:
            vote_id, poll_id, user_id, user_identifier, team_name, team_conference, rank, reasoning, timestamp = vote
            creator_id = creator_mapping.get(user_identifier, 1)
            
            mysql_cursor.execute("""
                INSERT INTO creator_votes 
                (poll_id, creator_id, team_name, team_conference, rank_position, reasoning, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                reasoning = VALUES(reasoning)
            """, (poll_id, creator_id, team_name, team_conference, rank, reasoning, timestamp))
        
        mysql_conn.commit()
        sqlite_cursor.close()
        mysql_cursor.close()
        sqlite_conn.close()
        mysql_conn.close()
        print("✅ Migrated existing SQLite data to MySQL")
    
    def create_sample_creators(self):
        """Create sample creator accounts"""
        mysql_conn = self.connect_mysql()
        cursor = mysql_conn.cursor()
        
        sample_creators = [
            ('coach_thompson', 'coach@cfb.com', 'hashed_password_123', 'Coach Thompson', 'Former SEC coach, now analyst', '@coachthompson'),
            ('cfb_insider', 'insider@sports.com', 'hashed_password_456', 'CFB Insider', 'College football beat writer', '@cfbinsider'),
            ('poll_expert', 'expert@ranking.com', 'hashed_password_789', 'Poll Expert', 'College football polling specialist', '@pollexpert')
        ]
        
        for username, email, password_hash, display_name, bio, twitter in sample_creators:
            cursor.execute("""
                INSERT INTO user_creator (username, email, password_hash, display_name, bio, twitter_handle)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
            """, (username, email, password_hash, display_name, bio, twitter))
        
        mysql_conn.commit()
        cursor.close()
        mysql_conn.close()
        print("✅ Created sample creator accounts")
    
    def archive_completed_polls(self):
        """Archive polls that have ended"""
        mysql_conn = self.connect_mysql()
        cursor = mysql_conn.cursor()
        
        # Find completed polls that aren't archived
        cursor.execute("""
            SELECT id, week_number, season_year
            FROM creator_polls 
            WHERE end_date < NOW() AND is_archived = FALSE
        """)
        
        completed_polls = cursor.fetchall()
        
        for poll_id, week_number, season_year in completed_polls:
            # Calculate final rankings
            cursor.execute("""
                SELECT team_name, COUNT(*) as vote_count, AVG(rank_position) as avg_rank
                FROM creator_votes 
                WHERE poll_id = %s 
                GROUP BY team_name 
                ORDER BY avg_rank ASC
            """, (poll_id,))
            
            rankings = cursor.fetchall()
            final_rankings = []
            
            for rank, (team_name, vote_count, avg_rank) in enumerate(rankings, 1):
                final_rankings.append({
                    'rank': rank,
                    'team_name': team_name,
                    'vote_count': int(vote_count),
                    'avg_rank': float(avg_rank),
                    'points': max(26 - avg_rank, 0)
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
            """, (poll_id, json.dumps(final_rankings), total_ballots, season_year, week_number))
            
            # Mark poll as archived
            cursor.execute("""
                UPDATE creator_polls 
                SET is_archived = TRUE, archived_at = NOW(), is_active = FALSE 
                WHERE id = %s
            """, (poll_id,))
            
            print(f"✅ Archived poll: {season_year} Week {week_number}")
        
        mysql_conn.commit()
        cursor.close()
        mysql_conn.close()
    
    def run_full_migration(self):
        """Run complete migration process"""
        print("🚀 Starting Creator Poll MySQL Migration...")
        
        try:
            self.create_creator_tables()
            self.migrate_existing_data()
            self.create_sample_creators()
            self.archive_completed_polls()
            
            print("\n🎉 Migration Complete!")
            print("📊 Creator poll system now running on MySQL")
            print("🏆 All historical data preserved")
            print("📈 Week-to-week movement tracking enabled")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

# Usage example
if __name__ == "__main__":
    # Update these with your MySQL credentials
    mysql_config = {
        'host': 'localhost',  # or your MySQL host
        'user': 'your_username',
        'password': 'your_password',
        'database': 'devgreeny$default'  # Your existing database name
    }
    
    migration = MySQLCreatorMigration(mysql_config)
    migration.run_full_migration()
