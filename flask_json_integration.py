"""
Flask integration example using JSON storage instead of SQL
"""

from flask import Flask, request, session, flash, redirect, url_for, render_template
from ballot_storage import BallotStorage
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Initialize ballot storage
storage = BallotStorage("poll_ballots")

@app.route("/vote/<int:season>/<int:week>", methods=['GET', 'POST'])
def vote(season, week):
    """Vote on a specific poll using JSON storage"""
    
    if request.method == 'POST':
        # Get user identification
        user_id = session.get('user_id', request.remote_addr)
        user_type = 'registered' if session.get('user_id') else 'guest'
        
        # Collect ballot data
        ballot_data = []
        for rank in range(1, 26):
            team_name = request.form.get(f'rank_{rank}', '').strip()
            reasoning = request.form.get(f'reasoning_{rank}', '').strip()
            
            if team_name:
                ballot_data.append({
                    'rank': rank,
                    'team_name': team_name,
                    'team_id': get_team_id(team_name),  # Your team lookup function
                    'reasoning': reasoning
                })
        
        # Validate complete ballot
        if len(ballot_data) < 25:
            flash('Please rank all 25 teams before submitting.', 'error')
            return render_template('vote.html', existing_ballot=ballot_data)
        
        # Save ballot
        success = storage.save_ballot(season, week, user_id, ballot_data, user_type)
        
        if success:
            flash('Your ballot has been submitted!', 'success')
            return redirect(url_for('results', season=season, week=week))
        else:
            flash('Error submitting ballot. Please try again.', 'error')
    
    # GET request - load existing ballot if available
    user_id = session.get('user_id', request.remote_addr)
    user_type = 'registered' if session.get('user_id') else 'guest'
    
    existing_ballot = storage.load_ballot(season, week, user_id, user_type)
    
    return render_template('vote.html', 
                         season=season, 
                         week=week,
                         existing_ballot=existing_ballot)

@app.route("/results/<int:season>/<int:week>")
def results(season, week):
    """Show poll results using JSON storage"""
    
    # Get aggregated results
    poll_results = storage.calculate_poll_results(season, week)
    poll_stats = storage.get_poll_stats(season, week)
    
    # Split into Top 25 and Others Receiving Votes
    top_25 = poll_results[:25]
    others_receiving_votes = poll_results[25:]
    
    return render_template('results.html',
                         season=season,
                         week=week,
                         rankings=top_25,
                         others_receiving_votes=others_receiving_votes,
                         total_ballots=poll_stats['total_ballots'])

@app.route("/admin/export/<int:season>/<int:week>")
def export_ballots(season, week):
    """Export ballots to CSV for external analysis"""
    import csv
    from io import StringIO
    from flask import Response
    
    ballots = storage.get_all_ballots(season, week)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['user_id', 'user_type', 'rank', 'team_name', 'team_id', 'reasoning', 'submitted_at'])
    
    # Write ballot data
    for ballot in ballots:
        for vote in ballot['ballot']:
            writer.writerow([
                ballot['user_id'],
                ballot['user_type'],
                vote['rank'],
                vote['team_name'],
                vote.get('team_id', ''),
                vote.get('reasoning', ''),
                ballot['submitted_at']
            ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=ballots_week_{week}_{season}.csv'}
    )

def get_team_id(team_name):
    """Your existing team lookup function"""
    # This would use your existing CFB team data
    pass

if __name__ == '__main__':
    app.run(debug=True)
