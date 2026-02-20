"""
Simple JSON-based ballot storage system
Alternative to SQL database for CFB Creator Poll
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid

class BallotStorage:
    def __init__(self, storage_dir: str = "ballot_data"):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
    
    def ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def get_poll_dir(self, season: int, week: int) -> str:
        """Get directory path for a specific poll"""
        poll_dir = os.path.join(self.storage_dir, f"season_{season}", f"week_{week}")
        if not os.path.exists(poll_dir):
            os.makedirs(poll_dir)
        return poll_dir
    
    def get_user_filename(self, user_id: str, user_type: str = "registered") -> str:
        """Generate filename for user ballot"""
        if user_type == "guest":
            # Clean up IP addresses or session IDs for filename
            safe_id = user_id.replace(".", "_").replace(":", "_")
            return f"guest_{safe_id}.json"
        else:
            return f"user_{user_id}.json"
    
    def save_ballot(self, season: int, week: int, user_id: str, ballot_data: List[Dict], 
                   user_type: str = "registered") -> bool:
        """Save a user's complete ballot"""
        try:
            poll_dir = self.get_poll_dir(season, week)
            filename = self.get_user_filename(user_id, user_type)
            filepath = os.path.join(poll_dir, filename)
            
            # Check if ballot already exists
            existing_ballot = self.load_ballot(season, week, user_id, user_type)
            
            ballot_record = {
                "user_id": user_id,
                "user_type": user_type,
                "poll_season": season,
                "poll_week": week,
                "ballot": ballot_data,
                "submitted_at": existing_ballot.get("submitted_at", datetime.now().isoformat()) if existing_ballot else datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "ballot_id": existing_ballot.get("ballot_id", str(uuid.uuid4())) if existing_ballot else str(uuid.uuid4())
            }
            
            with open(filepath, 'w') as f:
                json.dump(ballot_record, f, indent=2)
            
            print(f"✅ Saved ballot for {user_type} {user_id} - Week {week}, Season {season}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving ballot: {e}")
            return False
    
    def load_ballot(self, season: int, week: int, user_id: str, 
                   user_type: str = "registered") -> Optional[Dict]:
        """Load a user's ballot"""
        try:
            poll_dir = self.get_poll_dir(season, week)
            filename = self.get_user_filename(user_id, user_type)
            filepath = os.path.join(poll_dir, filename)
            
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
            return None
            
        except Exception as e:
            print(f"❌ Error loading ballot: {e}")
            return None
    
    def get_all_ballots(self, season: int, week: int) -> List[Dict]:
        """Get all ballots for a specific poll"""
        try:
            poll_dir = self.get_poll_dir(season, week)
            ballots = []
            
            if os.path.exists(poll_dir):
                for filename in os.listdir(poll_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(poll_dir, filename)
                        with open(filepath, 'r') as f:
                            ballot = json.load(f)
                            ballots.append(ballot)
            
            return ballots
            
        except Exception as e:
            print(f"❌ Error loading ballots: {e}")
            return []
    
    def calculate_poll_results(self, season: int, week: int) -> List[Dict]:
        """Calculate aggregated poll results"""
        ballots = self.get_all_ballots(season, week)
        
        # Aggregate votes by team
        team_votes = {}
        
        for ballot in ballots:
            for vote in ballot['ballot']:
                team_name = vote['team_name']
                rank = vote['rank']
                
                if team_name not in team_votes:
                    team_votes[team_name] = []
                team_votes[team_name].append(rank)
        
        # Calculate averages and sort
        results = []
        for team_name, ranks in team_votes.items():
            avg_rank = sum(ranks) / len(ranks)
            vote_count = len(ranks)
            points = sum(26 - rank for rank in ranks)  # Points system
            
            results.append({
                'team_name': team_name,
                'vote_count': vote_count,
                'avg_rank': round(avg_rank, 2),
                'points': points
            })
        
        # Sort by average rank (lower = better)
        results.sort(key=lambda x: x['avg_rank'])
        
        # Add ranking numbers
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return results
    
    def get_poll_stats(self, season: int, week: int) -> Dict:
        """Get statistics for a poll"""
        ballots = self.get_all_ballots(season, week)
        
        return {
            'total_ballots': len(ballots),
            'registered_users': len([b for b in ballots if b['user_type'] == 'registered']),
            'guest_users': len([b for b in ballots if b['user_type'] == 'guest']),
            'unique_teams_voted': len(set(
                vote['team_name'] 
                for ballot in ballots 
                for vote in ballot['ballot']
            ))
        }

# Example usage
if __name__ == "__main__":
    storage = BallotStorage()
    
    # Sample ballot data
    sample_ballot = [
        {"rank": 1, "team_name": "Georgia", "team_id": "61", "reasoning": "Undefeated"},
        {"rank": 2, "team_name": "Texas", "team_id": "251", "reasoning": "Great offense"},
        {"rank": 3, "team_name": "Michigan", "team_id": "130", "reasoning": "Strong defense"},
        # ... would have 22 more teams for complete Top 25
    ]
    
    # Save ballots
    storage.save_ballot(2025, 3, "user_12345", sample_ballot, "registered")
    storage.save_ballot(2025, 3, "192.168.1.100", sample_ballot, "guest")
    
    # Load specific ballot
    ballot = storage.load_ballot(2025, 3, "user_12345", "registered")
    print(f"Loaded ballot: {ballot['ballot_id']}")
    
    # Get poll results
    results = storage.calculate_poll_results(2025, 3)
    print(f"Poll results: {results[:5]}")  # Top 5
    
    # Get stats
    stats = storage.get_poll_stats(2025, 3)
    print(f"Poll stats: {stats}")
