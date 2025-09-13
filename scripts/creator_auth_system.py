"""
Secure Creator Authentication System
SQLite for user management + CSV for ballot storage
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta
import bcrypt
from functools import wraps
from flask import Flask, request, session, redirect, url_for, flash, render_template_string

class CreatorAuthSystem:
    def __init__(self, db_path="creators.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the creators database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Creators table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS creators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                bio TEXT,
                twitter_handle TEXT,
                profile_image TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Sessions table for secure session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS creator_sessions (
                session_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (creator_id) REFERENCES creators (id)
            )
        ''')
        
        # Poll participation tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS creator_poll_participation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                season INTEGER,
                week INTEGER,
                ballot_submitted_at TIMESTAMP,
                ballot_updated_at TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES creators (id),
                UNIQUE(creator_id, season, week)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Securely hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_creator(self, username: str, email: str, password: str, 
                      display_name: str, bio: str = "", twitter_handle: str = "") -> bool:
        """Create a new creator account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            cursor.execute('''
                INSERT INTO creators (username, email, password_hash, display_name, bio, twitter_handle)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, display_name, bio, twitter_handle))
            
            conn.commit()
            conn.close()
            print(f"✅ Created creator account: {username}")
            return True
            
        except sqlite3.IntegrityError as e:
            print(f"❌ Creator creation failed: {e}")
            return False
    
    def authenticate_creator(self, username: str, password: str, ip_address: str = "", user_agent: str = "") -> dict:
        """Authenticate a creator and create session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, password_hash, display_name, is_active, is_admin
            FROM creators WHERE username = ? OR email = ?
        ''', (username, username))
        
        creator = cursor.fetchone()
        
        if creator and creator[5] and self.verify_password(password, creator[3]):  # is_active and password check
            # Update last login
            cursor.execute('UPDATE creators SET last_login = ? WHERE id = ?', 
                         (datetime.now(), creator[0]))
            
            # Create session
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=30)  # 30-day sessions
            
            cursor.execute('''
                INSERT INTO creator_sessions (session_id, creator_id, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, creator[0], expires_at, ip_address, user_agent))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'creator_id': creator[0],
                'username': creator[1],
                'email': creator[2],
                'display_name': creator[4],
                'is_admin': creator[6],
                'session_id': session_id
            }
        
        conn.close()
        return {'success': False}
    
    def validate_session(self, session_id: str) -> dict:
        """Validate a creator session"""
        if not session_id:
            return {'valid': False}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cs.creator_id, cs.expires_at, c.username, c.display_name, c.is_admin, c.is_active
            FROM creator_sessions cs
            JOIN creators c ON cs.creator_id = c.id
            WHERE cs.session_id = ? AND cs.expires_at > ? AND c.is_active = 1
        ''', (session_id, datetime.now()))
        
        session_data = cursor.fetchone()
        conn.close()
        
        if session_data:
            return {
                'valid': True,
                'creator_id': session_data[0],
                'username': session_data[2],
                'display_name': session_data[3],
                'is_admin': session_data[4]
            }
        
        return {'valid': False}
    
    def logout_creator(self, session_id: str):
        """Logout a creator by removing their session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM creator_sessions WHERE session_id = ?', (session_id,))
        conn.commit()
        conn.close()
    
    def get_creator_profile(self, creator_id: int) -> dict:
        """Get creator profile information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, email, display_name, bio, twitter_handle, created_at, last_login
            FROM creators WHERE id = ?
        ''', (creator_id,))
        
        profile = cursor.fetchone()
        conn.close()
        
        if profile:
            return {
                'username': profile[0],
                'email': profile[1],
                'display_name': profile[2],
                'bio': profile[3],
                'twitter_handle': profile[4],
                'created_at': profile[5],
                'last_login': profile[6]
            }
        
        return {}
    
    def record_ballot_submission(self, creator_id: int, season: int, week: int):
        """Record that a creator submitted a ballot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO creator_poll_participation 
            (creator_id, season, week, ballot_submitted_at, ballot_updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (creator_id, season, week, datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()

# Flask integration
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
auth_system = CreatorAuthSystem()

def login_required(f):
    """Decorator to require creator login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get('creator_session_id')
        session_data = auth_system.validate_session(session_id)
        
        if not session_data['valid']:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Add creator info to request context
        request.creator = session_data
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get('creator_session_id')
        session_data = auth_system.validate_session(session_id)
        
        if not session_data['valid'] or not session_data['is_admin']:
            flash('Admin access required.', 'error')
            return redirect(url_for('login'))
        
        request.creator = session_data
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/creator/login', methods=['GET', 'POST'])
def login():
    """Creator login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        auth_result = auth_system.authenticate_creator(
            username, password, 
            request.remote_addr, 
            request.headers.get('User-Agent', '')
        )
        
        if auth_result['success']:
            session['creator_session_id'] = auth_result['session_id']
            session['creator_username'] = auth_result['username']
            session['creator_display_name'] = auth_result['display_name']
            
            flash(f'Welcome back, {auth_result["display_name"]}!', 'success')
            return redirect(url_for('creator_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template_string('''
    <form method="post">
        <h2>Creator Login</h2>
        <input type="text" name="username" placeholder="Username or Email" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    ''')

@app.route('/creator/dashboard')
@login_required
def creator_dashboard():
    """Creator dashboard"""
    profile = auth_system.get_creator_profile(request.creator['creator_id'])
    
    return render_template_string('''
    <h1>Welcome, {{ creator.display_name }}!</h1>
    <p>Username: {{ profile.username }}</p>
    <p>Member since: {{ profile.created_at }}</p>
    <a href="/creator/vote">Submit Poll Ballot</a> |
    <a href="/creator/profile">Edit Profile</a> |
    <a href="/creator/logout">Logout</a>
    ''', creator=request.creator, profile=profile)

@app.route('/creator/logout')
def logout():
    """Creator logout"""
    session_id = session.get('creator_session_id')
    if session_id:
        auth_system.logout_creator(session_id)
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Example usage
if __name__ == '__main__':
    # Create some sample creators
    auth_system.create_creator(
        username="coach_smith",
        email="coach@example.com", 
        password="secure_password_123",
        display_name="Coach Smith",
        bio="Former college football coach and analyst",
        twitter_handle="@coachsmith"
    )
    
    auth_system.create_creator(
        username="sports_writer",
        email="writer@sports.com",
        password="another_secure_pass",
        display_name="Sports Writer",
        bio="College football journalist for 15+ years"
    )
    
    print("✅ Sample creators created!")
    print("Login with: coach_smith / secure_password_123")
    print("Or: sports_writer / another_secure_pass")
    
    app.run(debug=True, port=5001)
