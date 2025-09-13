"""
CSV-based ballot storage - Excel compatible!
Super simple alternative to SQL database
"""

import csv
import os
from datetime import datetime
from collections import defaultdict
import pandas as pd  # Optional for easier analysis

class CSVBallotStorage:
    def __init__(self, storage_dir: str = "csv_ballots"):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
    
    def ensure_storage_dir(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def get_ballot_file(self, season: int, week: int) -> str:
        """Get CSV file path for a specific poll"""
        return os.path.join(self.storage_dir, f"ballots_{season}_week_{week}.csv")
    
    def save_ballot(self, season: int, week: int, user_id: str, ballot_data: list, user_type: str = "registered"):
        """Save ballot to CSV file"""
        csv_file = self.get_ballot_file(season, week)
        
        # Remove existing ballot for this user
        self.remove_user_ballot(season, week, user_id, user_type)
        
        # Append new ballot
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if file is empty
            if f.tell() == 0:
                writer.writerow(['user_id', 'user_type', 'rank', 'team_name', 'team_id', 'reasoning', 'submitted_at'])
            
            # Write ballot data
            timestamp = datetime.now().isoformat()
            for vote in ballot_data:
                writer.writerow([
                    user_id,
                    user_type,
                    vote['rank'],
                    vote['team_name'],
                    vote.get('team_id', ''),
                    vote.get('reasoning', ''),
                    timestamp
                ])
        
        print(f"✅ Saved {len(ballot_data)} votes for {user_type} {user_id}")
        return True
    
    def remove_user_ballot(self, season: int, week: int, user_id: str, user_type: str):
        """Remove existing ballot for user (for updates)"""
        csv_file = self.get_ballot_file(season, week)
        
        if not os.path.exists(csv_file):
            return
        
        # Read existing data
        rows_to_keep = []
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                rows_to_keep.append(header)
                
                for row in reader:
                    if len(row) >= 2 and not (row[0] == user_id and row[1] == user_type):
                        rows_to_keep.append(row)
        
        # Write back without user's old ballot
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows_to_keep)
    
    def load_user_ballot(self, season: int, week: int, user_id: str, user_type: str = "registered"):
        """Load a specific user's ballot"""
        csv_file = self.get_ballot_file(season, week)
        
        if not os.path.exists(csv_file):
            return None
        
        ballot = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['user_id'] == user_id and row['user_type'] == user_type:
                    ballot.append({
                        'rank': int(row['rank']),
                        'team_name': row['team_name'],
                        'team_id': row['team_id'],
                        'reasoning': row['reasoning']
                    })
        
        return sorted(ballot, key=lambda x: x['rank']) if ballot else None
    
    def calculate_poll_results(self, season: int, week: int):
        """Calculate poll results from CSV data"""
        csv_file = self.get_ballot_file(season, week)
        
        if not os.path.exists(csv_file):
            return []
        
        # Count votes by team
        team_votes = defaultdict(list)
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_name = row['team_name']
                rank = int(row['rank'])
                team_votes[team_name].append(rank)
        
        # Calculate results
        results = []
        for team_name, ranks in team_votes.items():
            avg_rank = sum(ranks) / len(ranks)
            vote_count = len(ranks)
            points = sum(26 - rank for rank in ranks)
            
            results.append({
                'team_name': team_name,
                'vote_count': vote_count,
                'avg_rank': round(avg_rank, 2),
                'points': points
            })
        
        # Sort by average rank
        results.sort(key=lambda x: x['avg_rank'])
        
        # Add rank numbers
        for i, result in enumerate(results, 1):
            result['rank'] = i
        
        return results
    
    def get_poll_stats(self, season: int, week: int):
        """Get poll statistics"""
        csv_file = self.get_ballot_file(season, week)
        
        if not os.path.exists(csv_file):
            return {'total_ballots': 0, 'registered_users': 0, 'guest_users': 0}
        
        users = set()
        user_types = defaultdict(int)
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_key = (row['user_id'], row['user_type'])
                users.add(user_key)
                user_types[row['user_type']] += 1
        
        return {
            'total_ballots': len(users),
            'registered_users': len([u for u in users if u[1] == 'registered']),
            'guest_users': len([u for u in users if u[1] == 'guest']),
            'total_votes': user_types['registered'] + user_types['guest']
        }
    
    def export_to_excel(self, season: int, week: int, output_file: str = None):
        """Export poll data to Excel (requires pandas)"""
        csv_file = self.get_ballot_file(season, week)
        
        if not output_file:
            output_file = f"poll_results_{season}_week_{week}.xlsx"
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            
            # Create Excel with multiple sheets
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Raw ballot data
                df.to_excel(writer, sheet_name='All Ballots', index=False)
                
                # Poll results
                results = self.calculate_poll_results(season, week)
                results_df = pd.DataFrame(results)
                results_df.to_excel(writer, sheet_name='Poll Results', index=False)
                
                # Stats
                stats = self.get_poll_stats(season, week)
                stats_df = pd.DataFrame([stats])
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            print(f"✅ Exported to {output_file}")
            return True
            
        except ImportError:
            print("❌ pandas required for Excel export: pip install pandas openpyxl")
            return False

# Example usage
if __name__ == "__main__":
    storage = CSVBallotStorage()
    
    # Sample ballot
    sample_ballot = [
        {"rank": 1, "team_name": "Georgia", "team_id": "61", "reasoning": "Undefeated"},
        {"rank": 2, "team_name": "Texas", "team_id": "251", "reasoning": "Great offense"},
        {"rank": 3, "team_name": "Michigan", "team_id": "130", "reasoning": "Strong defense"},
        # ... add 22 more for complete ballot
    ]
    
    # Save some test ballots
    storage.save_ballot(2025, 3, "user123", sample_ballot[:3], "registered")  # Short for testing
    storage.save_ballot(2025, 3, "192.168.1.100", sample_ballot[:3], "guest")
    
    # Get results
    results = storage.calculate_poll_results(2025, 3)
    print("Poll Results:", results)
    
    # Get stats
    stats = storage.get_poll_stats(2025, 3)
    print("Stats:", stats)
    
    # Load user ballot
    user_ballot = storage.load_user_ballot(2025, 3, "user123", "registered")
    print("User ballot:", user_ballot)
