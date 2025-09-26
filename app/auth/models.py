"""
Unified User Authentication Models for MySQL
Handles authentication across all games: Starting5, Gridiron11, CreatorPoll
"""

import mysql.connector
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from flask_login import UserMixin

class MySQLConnection:
    def __init__(self, config):
        self.config = config
    
    def get_connection(self):
        return mysql.connector.connect(**self.config)

class User(UserMixin):
    def __init__(self, user_id, username, email, display_name=None, is_active=True):
        self.id = str(user_id)  # Flask-Login requires string ID
        self.username = username
        self.email = email
        self.display_name = display_name or username
        self.is_active = is_active
    
    @staticmethod
    def get_mysql_config():
        """Get MySQL configuration from environment or defaults"""
        import os
        # For local development, use SQLite if MySQL host is not accessible
        if os.environ.get('USE_LOCAL_SQLITE') or not os.environ.get('MYSQL_HOST'):
            return None  # Signal to use SQLite
        return {
            'host': os.environ.get('MYSQL_HOST', 'devgreeny.mysql.pythonanywhere-services.com'),
            'user': os.environ.get('MYSQL_USER', 'devgreeny'),
            'password': os.environ.get('MYSQL_PASSWORD', 'lebron69'),
            'database': os.environ.get('MYSQL_DATABASE', 'devgreeny$default')
        }
    
    @classmethod
    def create_tables(cls):
        """Create user tables if they don't exist"""
        config = cls.get_mysql_config()
        if config is None:
            # Use SQLite for local development
            cls._create_sqlite_tables()
            return
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Main users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(120),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL
                )
            """)
            
            # User sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id INT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Game scores table - unified across all games
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_scores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    game_type ENUM('starting5', 'gridiron11', 'creatorpoll') NOT NULL,
                    quiz_id VARCHAR(120),
                    score FLOAT NOT NULL,
                    max_points FLOAT,
                    time_taken INT,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_game (user_id, game_type),
                    INDEX idx_quiz (quiz_id)
                )
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ User authentication tables created successfully")
            
        except Exception as e:
            print(f"❌ Error creating user tables: {e}")
            # Fallback to SQLite for local development
            print("🔄 Falling back to SQLite for local development...")
            cls._create_sqlite_tables()
    
    @classmethod
    def _create_sqlite_tables(cls):
        """Create SQLite tables for local development"""
        from flask_sqlalchemy import SQLAlchemy
        from flask import current_app
        
        # This will be handled by the existing SQLAlchemy setup
        print("✅ Using existing SQLAlchemy setup for local development")
        return True
    
    @classmethod
    def create_user(cls, username: str, email: str, password: str, display_name: str = None) -> Optional['User']:
        """Create a new user account"""
        config = cls.get_mysql_config()
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, display_name)
                VALUES (%s, %s, %s, %s)
            """, (username, email, password_hash, display_name or username))
            
            user_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            return cls(user_id, username, email, display_name)
            
        except mysql.connector.IntegrityError as e:
            print(f"User creation failed - duplicate username/email: {e}")
            return None
        except Exception as e:
            print(f"User creation error: {e}")
            return None
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        """Authenticate user and return User object"""
        config = cls.get_mysql_config()
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, username, email, password_hash, display_name, is_active
                FROM users 
                WHERE (username = %s OR email = %s) AND is_active = TRUE
            """, (username, username))
            
            user_data = cursor.fetchone()
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = NOW() WHERE id = %s
                """, (user_data['id'],))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                return cls(
                    user_data['id'],
                    user_data['username'],
                    user_data['email'],
                    user_data['display_name'],
                    user_data['is_active']
                )
            
            cursor.close()
            conn.close()
            return None
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['User']:
        """Get user by ID for Flask-Login"""
        config = cls.get_mysql_config()
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, username, email, display_name, is_active
                FROM users 
                WHERE id = %s AND is_active = TRUE
            """, (user_id,))
            
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user_data:
                return cls(
                    user_data['id'],
                    user_data['username'],
                    user_data['email'],
                    user_data['display_name'],
                    user_data['is_active']
                )
            
            return None
            
        except Exception as e:
            print(f"Get user by ID error: {e}")
            return None
    
    def save_game_score(self, game_type: str, quiz_id: str, score: float, 
                       max_points: float = None, time_taken: int = None, metadata: dict = None):
        """Save a game score for this user"""
        config = self.get_mysql_config()
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO game_scores 
                (user_id, game_type, quiz_id, score, max_points, time_taken, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (int(self.id), game_type, quiz_id, score, max_points, time_taken, 
                  str(metadata) if metadata else None))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Save game score error: {e}")
            return False
    
    def get_game_scores(self, game_type: str = None, limit: int = 50):
        """Get user's game scores"""
        config = self.get_mysql_config()
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if game_type:
                cursor.execute("""
                    SELECT * FROM game_scores 
                    WHERE user_id = %s AND game_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (int(self.id), game_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM game_scores 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (int(self.id), limit))
            
            scores = cursor.fetchall()
            cursor.close()
            conn.close()
            return scores
            
        except Exception as e:
            print(f"Get game scores error: {e}")
            return []
    
    def get_stats_summary(self):
        """Get user's overall gaming stats"""
        config = self.get_mysql_config()
        db = MySQLConnection(config)
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    game_type,
                    COUNT(*) as total_games,
                    AVG(score) as avg_score,
                    MAX(score) as best_score,
                    SUM(score) as total_points
                FROM game_scores 
                WHERE user_id = %s
                GROUP BY game_type
            """, (int(self.id),))
            
            stats = cursor.fetchall()
            cursor.close()
            conn.close()
            return stats
            
        except Exception as e:
            print(f"Get stats summary error: {e}")
            return []
