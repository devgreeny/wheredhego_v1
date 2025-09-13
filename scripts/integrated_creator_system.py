"""
Complete Creator System: SQLite Auth + CSV Ballot Storage
Best of both worlds: Secure user management + Simple ballot storage
"""

from creator_auth_system import CreatorAuthSystem, login_required, admin_required
from csv_ballot_storage import CSVBallotStorage
from flask import Flask, request, session, render_template, redirect, url_for, flash, jsonify
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'change-this-to-a-secure-secret-key'

# Initialize systems
auth_system = CreatorAuthSystem("creator_poll_db.db")
ballot_storage = CSVBallotStorage("creator_ballots")

def get_current_poll_info():
    """Get current season and week info"""
    # You can implement your existing logic here
    return {"season": 2025, "week": 3}

@app.route('/')
def home():
    """Homepage showing current poll status"""
    poll_info = get_current_poll_info()
    results = ballot_storage.calculate_poll_results(poll_info["season"], poll_info["week"])
    stats = ballot_storage.get_poll_stats(poll_info["season"], poll_info["week"])
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CFB Creator Poll</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f172a; color: #e2e8f0; }
            .header { text-align: center; margin-bottom: 30px; }
            .poll-status { background: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .results { background: #1e293b; padding: 20px; border-radius: 10px; }
            .ranking-item { display: flex; justify-content: space-between; padding: 10px; margin: 5px 0; background: #334155; border-radius: 5px; }
            .login-section { background: #facc15; color: #0f172a; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
            a { color: #facc15; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .btn { background: #facc15; color: #0f172a; padding: 10px 20px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏈 CFB Creator Poll</h1>
            <p>{{ poll_info.season }} Season - Week {{ poll_info.week }}</p>
        </div>
        
        {% if session.creator_username %}
        <div class="poll-status">
            <h3>Welcome back, {{ session.creator_display_name }}!</h3>
            <a href="/creator/vote" class="btn">Submit Your Top 25</a>
            <a href="/creator/dashboard" class="btn">Dashboard</a>
            <a href="/creator/logout" class="btn">Logout</a>
        </div>
        {% else %}
        <div class="login-section">
            <h3>🎖️ Creator Access</h3>
            <p>Are you a verified college football creator?</p>
            <a href="/creator/login" class="btn">Creator Login</a>
            <a href="/creator/register" class="btn">Apply for Creator Access</a>
        </div>
        {% endif %}
        
        <div class="results">
            <h3>📊 Current Poll Results</h3>
            <p>{{ stats.total_ballots }} creator ballots submitted</p>
            
            {% if results %}
                {% for team in results[:10] %}
                <div class="ranking-item">
                    <span><strong>{{ team.rank }}.</strong> {{ team.team_name }}</span>
                    <span>{{ team.vote_count }} votes • Avg: {{ team.avg_rank }}</span>
                </div>
                {% endfor %}
                <p><a href="/results">View Full Top 25 →</a></p>
            {% else %}
                <p>No votes submitted yet this week.</p>
            {% endif %}
        </div>
    </body>
    </html>
    ''', poll_info=poll_info, results=results, stats=stats, session=session)

@app.route('/creator/register', methods=['GET', 'POST'])
def creator_register():
    """Creator registration form"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        bio = request.form.get('bio', '')
        twitter_handle = request.form.get('twitter_handle', '')
        
        # Basic validation
        if not all([username, email, password, display_name]):
            flash('Please fill in all required fields.', 'error')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
        else:
            success = auth_system.create_creator(username, email, password, display_name, bio, twitter_handle)
            if success:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('creator_login'))
            else:
                flash('Registration failed. Username or email may already exist.', 'error')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Creator Registration</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f172a; color: #e2e8f0; }
            .form-container { max-width: 500px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 10px; }
            input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #334155; border-radius: 5px; background: #334155; color: #e2e8f0; }
            button { background: #facc15; color: #0f172a; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold; }
            .note { background: #1e40af; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>🎖️ Apply for Creator Access</h2>
            
            <div class="note">
                <strong>Creator Requirements:</strong><br>
                • Verified college football content creator<br>
                • Regular social media presence<br>
                • Knowledge of college football<br>
                <em>Applications are reviewed manually.</em>
            </div>
            
            <form method="post">
                <input type="text" name="username" placeholder="Username*" required>
                <input type="email" name="email" placeholder="Email Address*" required>
                <input type="password" name="password" placeholder="Password (8+ characters)*" required minlength="8">
                <input type="text" name="display_name" placeholder="Display Name*" required>
                <input type="text" name="twitter_handle" placeholder="Twitter Handle (optional)">
                <textarea name="bio" placeholder="Brief bio / credentials (optional)" rows="3"></textarea>
                <button type="submit">Submit Application</button>
            </form>
            
            <p><a href="/creator/login">Already have an account? Login →</a></p>
        </div>
    </body>
    </html>
    ''')

@app.route('/creator/login', methods=['GET', 'POST'])
def creator_login():
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
            session['creator_id'] = auth_result['creator_id']
            
            flash(f'Welcome back, {auth_result["display_name"]}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Creator Login</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f172a; color: #e2e8f0; }
            .form-container { max-width: 400px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 10px; }
            input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #334155; border-radius: 5px; background: #334155; color: #e2e8f0; }
            button { background: #facc15; color: #0f172a; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-weight: bold; }
            a { color: #facc15; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>🎖️ Creator Login</h2>
            <form method="post">
                <input type="text" name="username" placeholder="Username or Email" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <p><a href="/creator/register">Need creator access? Apply here →</a></p>
            <p><a href="/">← Back to Poll</a></p>
        </div>
    </body>
    </html>
    ''')

@app.route('/creator/vote', methods=['GET', 'POST'])
@login_required
def creator_vote():
    """Creator voting page"""
    poll_info = get_current_poll_info()
    creator_id = session.get('creator_id')
    
    if request.method == 'POST':
        # Collect ballot data
        ballot_data = []
        for rank in range(1, 26):
            team_name = request.form.get(f'rank_{rank}', '').strip()
            reasoning = request.form.get(f'reasoning_{rank}', '').strip()
            
            if team_name:
                ballot_data.append({
                    'rank': rank,
                    'team_name': team_name,
                    'team_id': '',  # You can add team ID lookup here
                    'reasoning': reasoning
                })
        
        if len(ballot_data) < 25:
            flash('Please rank all 25 teams before submitting.', 'error')
        else:
            # Save ballot
            success = ballot_storage.save_ballot(
                poll_info["season"], 
                poll_info["week"], 
                str(creator_id),  # Use creator ID as user identifier
                ballot_data, 
                "creator"  # Special user type for creators
            )
            
            if success:
                # Record participation
                auth_system.record_ballot_submission(creator_id, poll_info["season"], poll_info["week"])
                flash('Your ballot has been submitted successfully!', 'success')
                return redirect(url_for('creator_dashboard'))
            else:
                flash('Error submitting ballot. Please try again.', 'error')
    
    # Load existing ballot if available
    existing_ballot = ballot_storage.load_user_ballot(
        poll_info["season"], 
        poll_info["week"], 
        str(creator_id), 
        "creator"
    )
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Submit Your Top 25</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #0f172a; color: #e2e8f0; }
            .form-container { max-width: 800px; margin: 0 auto; }
            .rank-input { display: flex; align-items: center; margin: 10px 0; padding: 10px; background: #1e293b; border-radius: 5px; }
            .rank-number { width: 40px; font-weight: bold; color: #facc15; }
            input[type="text"] { flex: 1; padding: 8px; margin: 0 10px; border: 1px solid #334155; border-radius: 3px; background: #334155; color: #e2e8f0; }
            input[type="text"]:focus { border-color: #facc15; outline: none; }
            button { background: #facc15; color: #0f172a; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 20px 0; }
            .header { text-align: center; margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <div class="header">
                <h1>📝 Submit Your Top 25</h1>
                <p>{{ poll_info.season }} Season - Week {{ poll_info.week }}</p>
                <p>Creator: <strong>{{ session.creator_display_name }}</strong></p>
            </div>
            
            <form method="post">
                {% for rank in range(1, 26) %}
                <div class="rank-input">
                    <div class="rank-number">{{ rank }}.</div>
                    <input type="text" 
                           name="rank_{{ rank }}" 
                           placeholder="Team name..."
                           {% if existing_ballot %}
                               {% for vote in existing_ballot %}
                                   {% if vote.rank == rank %}
                                       value="{{ vote.team_name }}"
                                   {% endif %}
                               {% endfor %}
                           {% endif %}
                           required>
                    <input type="text" 
                           name="reasoning_{{ rank }}" 
                           placeholder="Reason (optional)"
                           {% if existing_ballot %}
                               {% for vote in existing_ballot %}
                                   {% if vote.rank == rank %}
                                       value="{{ vote.reasoning }}"
                                   {% endif %}
                               {% endfor %}
                           {% endif %}
                           style="max-width: 200px;">
                </div>
                {% endfor %}
                
                <button type="submit">Submit Top 25 Ballot</button>
            </form>
            
            <p><a href="/creator/dashboard">← Back to Dashboard</a></p>
        </div>
    </body>
    </html>
    ''', poll_info=poll_info, existing_ballot=existing_ballot, session=session, range=range)

@app.route('/creator/dashboard')
@login_required
def creator_dashboard():
    """Creator dashboard"""
    creator_id = session.get('creator_id')
    profile = auth_system.get_creator_profile(creator_id)
    poll_info = get_current_poll_info()
    
    # Check if creator has voted this week
    existing_ballot = ballot_storage.load_user_ballot(
        poll_info["season"], 
        poll_info["week"], 
        str(creator_id), 
        "creator"
    )
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Creator Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f172a; color: #e2e8f0; }
            .dashboard { max-width: 800px; margin: 0 auto; }
            .card { background: #1e293b; padding: 20px; border-radius: 10px; margin: 20px 0; }
            .btn { background: #facc15; color: #0f172a; padding: 10px 20px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin: 5px; }
            .status-good { color: #22c55e; }
            .status-pending { color: #f59e0b; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <h1>👋 Welcome, {{ profile.display_name }}!</h1>
            
            <div class="card">
                <h3>📊 Current Poll Status</h3>
                <p><strong>{{ poll_info.season }} Season - Week {{ poll_info.week }}</strong></p>
                {% if existing_ballot %}
                    <p class="status-good">✅ You have submitted your Top 25 ballot</p>
                    <a href="/creator/vote" class="btn">Update Your Ballot</a>
                {% else %}
                    <p class="status-pending">⏰ Your Top 25 ballot is pending</p>
                    <a href="/creator/vote" class="btn">Submit Your Top 25</a>
                {% endif %}
            </div>
            
            <div class="card">
                <h3>👤 Your Profile</h3>
                <p><strong>Username:</strong> {{ profile.username }}</p>
                <p><strong>Email:</strong> {{ profile.email }}</p>
                {% if profile.twitter_handle %}
                <p><strong>Twitter:</strong> {{ profile.twitter_handle }}</p>
                {% endif %}
                {% if profile.bio %}
                <p><strong>Bio:</strong> {{ profile.bio }}</p>
                {% endif %}
                <p><strong>Member since:</strong> {{ profile.created_at }}</p>
            </div>
            
            <div class="card">
                <h3>🔗 Quick Links</h3>
                <a href="/results" class="btn">View Poll Results</a>
                <a href="/creator/export" class="btn">Export Data</a>
                <a href="/creator/logout" class="btn">Logout</a>
            </div>
        </div>
    </body>
    </html>
    ''', profile=profile, poll_info=poll_info, existing_ballot=existing_ballot)

@app.route('/creator/logout')
def creator_logout():
    """Creator logout"""
    session_id = session.get('creator_session_id')
    if session_id:
        auth_system.logout_creator(session_id)
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/results')
def results():
    """Public poll results"""
    poll_info = get_current_poll_info()
    results = ballot_storage.calculate_poll_results(poll_info["season"], poll_info["week"])
    stats = ballot_storage.get_poll_stats(poll_info["season"], poll_info["week"])
    
    top_25 = results[:25]
    others_receiving_votes = results[25:]
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Poll Results</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #0f172a; color: #e2e8f0; }
            .results { max-width: 800px; margin: 0 auto; }
            .ranking-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; margin: 5px 0; background: #1e293b; border-radius: 8px; }
            .rank-number { background: #facc15; color: #0f172a; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 15px; }
            .others { background: #334155; padding: 10px; border-radius: 5px; margin: 10px 0; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="results">
            <h1>🏆 CFB Creator Poll Results</h1>
            <p>{{ poll_info.season }} Season - Week {{ poll_info.week }}</p>
            <p>{{ stats.total_ballots }} creator ballots submitted</p>
            
            <h2>Top 25</h2>
            {% for team in top_25 %}
            <div class="ranking-item">
                <div style="display: flex; align-items: center;">
                    <div class="rank-number">
                        {{ team.rank }}
                    </div>
                    <div>
                        <strong>{{ team.team_name }}</strong><br>
                        <small>{{ team.vote_count }} votes • Avg: {{ team.avg_rank }}</small>
                    </div>
                </div>
                <div style="text-align: right;">
                    <strong>{{ "%.1f"|format(team.points) }} pts</strong>
                </div>
            </div>
            {% endfor %}
            
            {% if others_receiving_votes %}
            <h3>Others Receiving Votes</h3>
            <div>
                {% for team in others_receiving_votes %}
                <span class="others">{{ team.team_name }} ({{ team.vote_count }})</span>
                {% endfor %}
            </div>
            {% endif %}
            
            <p><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    ''', poll_info=poll_info, top_25=top_25, others_receiving_votes=others_receiving_votes, stats=stats)

if __name__ == '__main__':
    # Create sample creators for testing
    print("🚀 Setting up Creator Poll System...")
    
    # Create sample creators
    auth_system.create_creator(
        username="coach_brown",
        email="coach@cfb.com", 
        password="password123",
        display_name="Coach Brown",
        bio="Former SEC coach, now analyst",
        twitter_handle="@coachbrown"
    )
    
    auth_system.create_creator(
        username="cfb_writer",
        email="writer@sports.com",
        password="password123",
        display_name="CFB Writer",
        bio="College football beat writer"
    )
    
    print("✅ Sample creators created!")
    print("🔑 Login credentials:")
    print("   Username: coach_brown | Password: password123")
    print("   Username: cfb_writer | Password: password123")
    print()
    print("🌐 Starting server on http://localhost:5002")
    
    app.run(debug=True, port=5002)
