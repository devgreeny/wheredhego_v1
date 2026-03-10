#!/usr/bin/env python3
"""
Scrape World Cup tournament data from Transfermarkt.
First discovers all matches, then scrapes lineups for each.

Usage:
    python scrape_tournament.py --tournament wc2022
    python scrape_tournament.py --tournament wc2018 --skip-existing
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import argparse

# =============================================================================
# Configuration
# =============================================================================

REQUEST_DELAY = 4
BASE_URL = "https://www.transfermarkt.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.join(SCRIPT_DIR, "..", "quizzes", "starting11")

# Tournament URLs on Transfermarkt
TOURNAMENTS = {
    "wc2022": {
        "name": "World Cup 2022",
        "url": "/weltmeisterschaft-2022/gesamtspielplan/pokalwettbewerb/WM22/saison_id/2021",
    },
    "wc2018": {
        "name": "World Cup 2018",
        "url": "/weltmeisterschaft-2018/gesamtspielplan/pokalwettbewerb/WM18/saison_id/2017",
    },
    "wc2014": {
        "name": "World Cup 2014",
        "url": "/weltmeisterschaft-2014/gesamtspielplan/pokalwettbewerb/WM14/saison_id/2013",
    },
    "wc2010": {
        "name": "World Cup 2010",
        "url": "/weltmeisterschaft-2010/gesamtspielplan/pokalwettbewerb/WM10/saison_id/2009",
    },
    "wc2006": {
        "name": "World Cup 2006",
        "url": "/weltmeisterschaft-2006/gesamtspielplan/pokalwettbewerb/WM06/saison_id/2005",
    },
}

# =============================================================================
# Helper Functions
# =============================================================================

def fetch_page(url, delay=True):
    """Fetch a page with rate limiting."""
    if delay:
        time.sleep(REQUEST_DELAY)
    
    full_url = url if url.startswith('http') else BASE_URL + url
    
    try:
        response = requests.get(full_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"  ❌ Fetch error: {e}")
        return None


def discover_matches(tournament_url, tournament_name):
    """
    Discover all matches from a tournament schedule page.
    Returns list of match dicts with: match_id, team1, team2, date, stage
    """
    print(f"\nDiscovering matches for {tournament_name}...")
    
    soup = fetch_page(tournament_url)
    if not soup:
        return []
    
    matches = []
    current_stage = "Group"
    
    # Find all match rows
    # Look for links to match pages (spielbericht)
    match_links = soup.find_all('a', href=re.compile(r'/spielbericht/spielbericht/(\d+)'))
    
    for link in match_links:
        href = link.get('href', '')
        match_id_search = re.search(r'/spielbericht/spielbericht/(\d+)', href)
        if not match_id_search:
            continue
        
        match_id = match_id_search.group(1)
        
        # Skip if we already have this match
        if any(m['match_id'] == match_id for m in matches):
            continue
        
        # Try to find the row containing this match
        row = link.find_parent('tr') or link.find_parent('div')
        if not row:
            continue
        
        # Extract team names - look for team links or text
        team_links = row.find_all('a', href=re.compile(r'/nationalmannschaft/'))
        teams = []
        for tl in team_links:
            team_name = tl.get('title') or tl.get_text(strip=True)
            if team_name and team_name not in teams and len(team_name) > 1:
                teams.append(team_name)
        
        if len(teams) < 2:
            # Try alternative: look for img alt text
            imgs = row.find_all('img', alt=True)
            for img in imgs:
                alt = img.get('alt', '')
                if alt and alt not in teams and len(alt) > 2:
                    teams.append(alt)
        
        if len(teams) < 2:
            continue
        
        # Extract date
        date_text = ""
        date_elem = row.find('td', class_=re.compile(r'datum|date')) or row.find(string=re.compile(r'\d{2}/\d{2}/\d{2,4}'))
        if date_elem:
            date_text = date_elem.get_text(strip=True) if hasattr(date_elem, 'get_text') else str(date_elem)
        
        matches.append({
            'match_id': match_id,
            'team1': teams[0],
            'team2': teams[1] if len(teams) > 1 else "Unknown",
            'date': date_text,
            'stage': current_stage,
        })
    
    print(f"  Found {len(matches)} matches")
    return matches


def scrape_match_lineup(match_id, team1, team2, date, stage, tournament_code, tournament_name, skip_existing=False):
    """
    Scrape lineup and positions for a single match.
    Returns (success, reason)
    """
    print(f"\n  [{team1} vs {team2}] ({stage})")
    
    # Check if files exist
    output_dir = os.path.join(OUTPUT_BASE, tournament_code)
    os.makedirs(output_dir, exist_ok=True)
    
    stage_slug = stage.lower().replace(' ', '-').replace('/', '-')
    file1 = f"{stage_slug}_{team1.lower().replace(' ', '_')}.json"
    file2 = f"{stage_slug}_{team2.lower().replace(' ', '_')}.json"
    
    if skip_existing:
        if os.path.exists(os.path.join(output_dir, file1)) and os.path.exists(os.path.join(output_dir, file2)):
            print(f"    ⏭️  Skipped (files exist)")
            return True, "Skipped (existing)"
    
    # Build URLs - try different URL patterns
    slug = f"{team1.lower().replace(' ', '-')}_{team2.lower().replace(' ', '-')}"
    lineup_url = f"{BASE_URL}/{slug}/aufstellung/spielbericht/{match_id}"
    index_url = f"{BASE_URL}/{slug}/index/spielbericht/{match_id}"
    
    # === SCRAPE LINEUP PAGE ===
    print(f"    Fetching lineup...")
    soup = fetch_page(lineup_url, delay=True)
    if not soup:
        return False, "Failed to fetch lineup page"
    
    # Parse players
    players = []
    inline_tables = soup.find_all('table', class_='inline-table')
    
    for inline_table in inline_tables:
        outer_td = inline_table.find_parent('td')
        if not outer_td:
            continue
        outer_row = outer_td.find_parent('tr')
        if not outer_row:
            continue
            
        cells = outer_row.find_all('td', recursive=False)
        if len(cells) < 4:
            continue
        
        jersey_text = cells[0].get_text(strip=True)
        jersey = int(jersey_text) if jersey_text.isdigit() else None
        if jersey is None:
            continue
        
        player_link = cells[1].find('a', href=re.compile(r'/profil/spieler/\d+'))
        if not player_link:
            continue
            
        href = player_link.get('href', '')
        player_match = re.search(r'/([^/]+)/profil/spieler/(\d+)', href)
        if not player_match:
            continue
            
        player_slug = player_match.group(1)
        player_id = player_match.group(2)
        
        name_link = cells[1].find('a', href=re.compile(r'/leistungsdatendetails/'))
        player_name = name_link.get('title', '') if name_link else player_slug.replace('-', ' ').title()
        
        club_link = cells[3].find('a', href=re.compile(r'/startseite/verein/\d+'))
        if not club_link:
            continue
            
        club_href = club_link.get('href', '')
        club_match = re.search(r'/([^/]+)/startseite/verein/(\d+)', club_href)
        if not club_match:
            continue
            
        club_id = club_match.group(2)
        club_name = club_link.get('title', '') or club_match.group(1).replace('-', ' ').title()
        
        if not club_name or not club_id:
            continue
        
        players.append({
            'jersey': jersey,
            'name': player_name,
            'player_id': player_id,
            'club_name': club_name,
            'club_id': club_id
        })
    
    print(f"    Found {len(players)} players with complete data")
    
    if len(players) < 22:
        return False, f"Not enough players ({len(players)}/22)"
    
    # === SCRAPE POSITIONS PAGE ===
    print(f"    Fetching positions...")
    soup = fetch_page(index_url, delay=True)
    if not soup:
        return False, "Failed to fetch index page"
    
    teams_positions = []
    lineup_boxes = soup.find_all('div', class_=re.compile(r'large-6.*columns|columns.*large-6'))
    
    for box in lineup_boxes:
        team_players = []
        all_divs = box.find_all('div', style=True)
        
        for elem in all_divs:
            style = elem.get('style', '')
            text = elem.get_text(strip=True)
            
            if not text or not re.match(r'^\d+[A-Za-z]', text):
                continue
            
            top_match = re.search(r'top\s*:\s*([\d.]+)%', style)
            left_match = re.search(r'left\s*:\s*([\d.]+)%', style)
            
            if top_match and left_match:
                top_pct = float(top_match.group(1))
                left_pct = float(left_match.group(1))
                
                jersey_match = re.match(r'(\d+)', text)
                if jersey_match:
                    jersey = int(jersey_match.group(1))
                    
                    if not any(p['jersey'] == jersey for p in team_players):
                        team_players.append({
                            'jersey': jersey,
                            'x': left_pct,
                            'y': top_pct
                        })
        
        if len(team_players) == 11:
            teams_positions.append(team_players)
    
    print(f"    Found positions for {len(teams_positions)} teams")
    
    if len(teams_positions) < 2:
        return False, f"Missing position data ({len(teams_positions)}/2 teams)"
    
    # === MERGE AND VALIDATE ===
    team1_players = players[:11]
    team2_players = players[11:22]
    team1_positions = teams_positions[0]
    team2_positions = teams_positions[1]
    
    team1_jerseys = {p['jersey'] for p in team1_players}
    team1_pos_jerseys = {p['jersey'] for p in team1_positions}
    team2_jerseys = {p['jersey'] for p in team2_players}
    team2_pos_jerseys = {p['jersey'] for p in team2_positions}
    
    if team1_jerseys != team1_pos_jerseys:
        missing = team1_jerseys - team1_pos_jerseys
        return False, f"{team1}: Missing positions for jerseys {missing}"
    
    if team2_jerseys != team2_pos_jerseys:
        missing = team2_jerseys - team2_pos_jerseys
        return False, f"{team2}: Missing positions for jerseys {missing}"
    
    # === MERGE DATA ===
    def merge_player_data(players_with_clubs, positions):
        pos_by_jersey = {p['jersey']: p for p in positions}
        merged = []
        
        x_values = [p['x'] for p in positions]
        avg_x = sum(x_values) / len(x_values) if x_values else 50
        x_offset = 50 - avg_x
        
        def scale_pos(val, padding=15):
            return padding + (val * (100 - 2 * padding) / 100)
        
        for player in players_with_clubs:
            jersey = player['jersey']
            pos = pos_by_jersey.get(jersey, {})
            
            raw_x = pos.get('x', 50) + x_offset
            raw_y = pos.get('y', 50)
            
            merged.append({
                'jersey': jersey,
                'name': player['name'],
                'player_id': player['player_id'],
                'club': {
                    'name': player['club_name'],
                    'club_id': player['club_id'],
                    'badge_url': f"https://tmssl.akamaized.net/images/wappen/head/{player['club_id']}.png"
                },
                'position': {
                    'x': scale_pos(raw_x),
                    'y': scale_pos(raw_y)
                }
            })
        
        return merged
    
    team1_merged = merge_player_data(team1_players, team1_positions)
    team2_merged = merge_player_data(team2_players, team2_positions)
    
    # === CREATE QUIZZES ===
    match_info = {
        "tournament": tournament_name,
        "stage": stage,
        "date": date,
    }
    
    quiz1 = {
        'answer': {'country': team1, 'country_code': team1[:3].upper()},
        'match': {**match_info, 'opponent': team2},
        'players': team1_merged
    }
    
    quiz2 = {
        'answer': {'country': team2, 'country_code': team2[:3].upper()},
        'match': {**match_info, 'opponent': team1},
        'players': team2_merged
    }
    
    # === SAVE FILES ===
    with open(os.path.join(output_dir, file1), 'w') as f:
        json.dump(quiz1, f, indent=2)
    
    with open(os.path.join(output_dir, file2), 'w') as f:
        json.dump(quiz2, f, indent=2)
    
    print(f"    ✅ Saved: {file1}, {file2}")
    return True, "Success"


def main():
    parser = argparse.ArgumentParser(description='Scrape World Cup tournament data')
    parser.add_argument('--tournament', '-t',
                       choices=list(TOURNAMENTS.keys()) + ['all'],
                       required=True,
                       help='Which tournament to scrape')
    parser.add_argument('--skip-existing', '-s',
                       action='store_true',
                       help='Skip matches where quiz files already exist')
    parser.add_argument('--discover-only', '-d',
                       action='store_true',
                       help='Only discover matches, do not scrape lineups')
    args = parser.parse_args()
    
    if args.tournament == 'all':
        to_scrape = list(TOURNAMENTS.items())
    else:
        to_scrape = [(args.tournament, TOURNAMENTS[args.tournament])]
    
    print("\n" + "="*60)
    print("STARTING11 TOURNAMENT SCRAPER")
    print("="*60)
    
    all_countries = set()
    
    for tournament_code, tournament_info in to_scrape:
        tournament_name = tournament_info['name']
        tournament_url = tournament_info['url']
        
        # Step 1: Discover matches
        matches = discover_matches(tournament_url, tournament_name)
        
        if args.discover_only:
            print(f"\nMatches for {tournament_name}:")
            for m in matches:
                print(f"  {m['match_id']}: {m['team1']} vs {m['team2']} ({m['stage']})")
            continue
        
        if not matches:
            print(f"  ⚠️  No matches found for {tournament_name}")
            continue
        
        # Step 2: Scrape each match
        print(f"\n{'='*60}")
        print(f"SCRAPING {tournament_name} ({len(matches)} matches)")
        print(f"{'='*60}")
        
        success_count = 0
        skip_count = 0
        failed = []
        
        for i, match in enumerate(matches, 1):
            print(f"\n[{i}/{len(matches)}]", end="")
            
            success, reason = scrape_match_lineup(
                match_id=match['match_id'],
                team1=match['team1'],
                team2=match['team2'],
                date=match['date'],
                stage=match['stage'],
                tournament_code=tournament_code,
                tournament_name=tournament_name,
                skip_existing=args.skip_existing
            )
            
            if success:
                if reason == "Skipped (existing)":
                    skip_count += 1
                else:
                    success_count += 1
                    all_countries.add(match['team1'])
                    all_countries.add(match['team2'])
            else:
                failed.append((match['team1'], match['team2'], match['stage'], reason))
                print(f"    ⚠️  FAILED: {reason}")
        
        # Summary for this tournament
        print(f"\n{tournament_name} Summary:")
        print(f"  ✅ Scraped: {success_count} matches")
        print(f"  ⏭️  Skipped: {skip_count} matches")
        print(f"  ❌ Failed: {len(failed)} matches")
    
    # Final summary
    if all_countries:
        print("\n" + "="*60)
        print("UNIQUE COUNTRIES SCRAPED")
        print("="*60)
        for country in sorted(all_countries):
            print(f"  {country}")
        print(f"\nTotal: {len(all_countries)} countries")
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
