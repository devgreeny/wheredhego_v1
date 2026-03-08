#!/usr/bin/env python3
"""
Starting11 World Cup Batch Scraper (1998-2022)
Scrapes all World Cup match lineups from Transfermarkt.

Usage:
    python scrape_all_worldcups.py [--skip-existing] [--tournament TOURNAMENT]
    
Examples:
    python scrape_all_worldcups.py                    # Scrape all tournaments
    python scrape_all_worldcups.py --skip-existing   # Skip existing files
    python scrape_all_worldcups.py --tournament wc2018  # Single tournament
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import argparse

# Configuration
REQUEST_DELAY = 3  # Seconds between requests
BASE_URL = "https://www.transfermarkt.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

ALL_TOURNAMENTS = [
    {"code": "wc2022", "name": "World Cup 2022", "url": "https://www.transfermarkt.com/weltmeisterschaft-2022/gesamtspielplan/pokalwettbewerb/WM22/saison_id/2021"},
    {"code": "wc2018", "name": "World Cup 2018", "url": "https://www.transfermarkt.com/weltmeisterschaft-2018/gesamtspielplan/pokalwettbewerb/WM18/saison_id/2017"},
    {"code": "wc2014", "name": "World Cup 2014", "url": "https://www.transfermarkt.com/weltmeisterschaft-2014/gesamtspielplan/pokalwettbewerb/WM14/saison_id/2013"},
    {"code": "wc2010", "name": "World Cup 2010", "url": "https://www.transfermarkt.com/weltmeisterschaft-2010/gesamtspielplan/pokalwettbewerb/WM10/saison_id/2009"},
    {"code": "wc2006", "name": "World Cup 2006", "url": "https://www.transfermarkt.com/weltmeisterschaft-2006/gesamtspielplan/pokalwettbewerb/WM06/saison_id/2005"},
    {"code": "wc2002", "name": "World Cup 2002", "url": "https://www.transfermarkt.com/weltmeisterschaft-2002/gesamtspielplan/pokalwettbewerb/WM02/saison_id/2001"},
    {"code": "wc1998", "name": "World Cup 1998", "url": "https://www.transfermarkt.com/weltmeisterschaft-1998/gesamtspielplan/pokalwettbewerb/WM98/saison_id/1997"},
]


def fetch_page(url, delay=True):
    """Fetch a page with rate limiting and proper headers."""
    if delay:
        time.sleep(REQUEST_DELAY)
    
    full_url = url if url.startswith('http') else BASE_URL + url
    
    try:
        response = requests.get(full_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"    Error fetching {full_url}: {e}")
        return None


def scrape_lineup_page(lineup_url):
    """Scrape player details from the lineup page."""
    soup = fetch_page(lineup_url, delay=True)
    if not soup:
        return []
    
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
        
        players.append({
            'jersey': jersey,
            'name': player_name,
            'player_id': player_id,
            'club_name': club_name,
            'club_id': club_id
        })
    
    return players


def scrape_positions_page(index_url):
    """Scrape player positions from the index page."""
    soup = fetch_page(index_url, delay=True)
    if not soup:
        return []
    
    teams = []
    lineup_boxes = soup.find_all('div', class_=re.compile(r'large-6.*columns|columns.*large-6'))
    
    for box in lineup_boxes:
        team_players = []
        all_divs = box.find_all('div', style=True)
        
        for elem in all_divs:
            style = elem.get('style', '')
            text = elem.get_text(strip=True)
            
            if not text or not re.match(r'^\d+\D', text):
                continue
            
            top_match = re.search(r'top\s*:\s*([\d.]+)%', style)
            left_match = re.search(r'left\s*:\s*([\d.]+)%', style)
            
            if top_match and left_match:
                top_pct = float(top_match.group(1))
                left_pct = float(left_match.group(1))
                
                jersey_match = re.match(r'(\d+)', text)
                if jersey_match:
                    jersey = int(jersey_match.group(1))
                    name = text[len(jersey_match.group(1)):].strip()
                    
                    if not any(p['jersey'] == jersey for p in team_players):
                        team_players.append({
                            'jersey': jersey,
                            'name': name,
                            'x': left_pct,
                            'y': top_pct
                        })
        
        if len(team_players) == 11:
            teams.append(team_players)
    
    return teams


def merge_player_data(players_with_clubs, positions):
    """Merge player club data with position data by jersey number."""
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


def create_quiz(team_name, country_code, opponent, players, tournament, stage, date):
    """Create a Starting11 quiz JSON structure."""
    return {
        'answer': {
            'country': team_name,
            'country_code': country_code
        },
        'match': {
            'tournament': tournament,
            'stage': stage,
            'opponent': opponent,
            'date': date
        },
        'players': players
    }


def discover_matches(soup):
    """Discover all matches from a tournament page."""
    matches = []
    score_links = soup.find_all('a', class_='ergebnis-link')
    
    for link in score_links:
        match_id = link.get('id')
        if not match_id or not match_id.isdigit():
            continue
        if any(m['match_id'] == match_id for m in matches):
            continue
        
        row = link.find_parent('tr')
        if not row:
            continue
        
        team_links = row.find_all('a', href=re.compile(r'/startseite/verein/\d+'))
        teams = []
        for tl in team_links:
            title = tl.get('title', '')
            if title and title not in teams:
                teams.append(title)
        
        if len(teams) >= 2:
            matches.append({
                'match_id': match_id,
                'team1': teams[0],
                'team2': teams[1],
            })
    
    return matches


def scrape_tournament(tournament, output_base, skip_existing=True):
    """Scrape all matches for a single tournament."""
    t_code = tournament["code"]
    t_name = tournament["name"]
    t_url = tournament["url"]
    
    print(f"\n{'='*70}")
    print(f"  {t_name}")
    print(f"{'='*70}")
    
    # Fetch tournament page
    print("  Fetching schedule...")
    soup = fetch_page(t_url, delay=False)
    if not soup:
        print("  Failed to fetch tournament page")
        return 0, 0, []
    
    # Discover matches
    matches = discover_matches(soup)
    print(f"  Found {len(matches)} matches")
    
    if not matches:
        print("  No matches found, skipping")
        return 0, 0, []
    
    # Create output directory
    output_dir = os.path.join(output_base, t_code)
    os.makedirs(output_dir, exist_ok=True)
    
    success = 0
    skipped = 0
    failed = []
    
    for i, match in enumerate(matches):
        match_id = match['match_id']
        team1 = match['team1']
        team2 = match['team2']
        
        file1 = f"match_{match_id}_{team1.lower().replace(' ', '_')}.json"
        file2 = f"match_{match_id}_{team2.lower().replace(' ', '_')}.json"
        
        if skip_existing and os.path.exists(os.path.join(output_dir, file1)):
            skipped += 1
            continue
        
        print(f"  [{i+1}/{len(matches)}] {team1} vs {team2}...", end=" ", flush=True)
        
        lineup_url = f"/spielbericht/aufstellung/spielbericht/{match_id}"
        index_url = f"/spielbericht/index/spielbericht/{match_id}"
        
        try:
            lineup_data = scrape_lineup_page(lineup_url)
            if len(lineup_data) < 22:
                print(f"Not enough players ({len(lineup_data)})")
                failed.append((team1, team2, t_name, f"Not enough players ({len(lineup_data)})"))
                continue
            
            positions_data = scrape_positions_page(index_url)
            if len(positions_data) < 2:
                print("Missing positions")
                failed.append((team1, team2, t_name, "Missing positions"))
                continue
            
            team1_players = lineup_data[:11]
            team2_players = lineup_data[11:22]
            
            team1_merged = merge_player_data(team1_players, positions_data[0])
            team2_merged = merge_player_data(team2_players, positions_data[1])
            
            quiz1 = create_quiz(team1, team1[:3].upper(), team2, team1_merged, t_name, "Match", "")
            quiz2 = create_quiz(team2, team2[:3].upper(), team1, team2_merged, t_name, "Match", "")
            
            with open(os.path.join(output_dir, file1), 'w') as f:
                json.dump(quiz1, f, indent=2)
            with open(os.path.join(output_dir, file2), 'w') as f:
                json.dump(quiz2, f, indent=2)
            
            print("OK")
            success += 1
            
        except Exception as e:
            print(f"Error: {e}")
            failed.append((team1, team2, t_name, str(e)))
    
    print(f"\n  Summary: {success} scraped, {skipped} skipped, {len(failed)} failed")
    return success, skipped, failed


def main():
    parser = argparse.ArgumentParser(description='Scrape World Cup lineups from Transfermarkt')
    parser.add_argument('--skip-existing', '-s', action='store_true', help='Skip existing files')
    parser.add_argument('--tournament', '-t', type=str, help='Scrape specific tournament (e.g., wc2018)')
    args = parser.parse_args()
    
    # Determine output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_base = os.path.join(script_dir, '..', 'quizzes', 'starting11')
    
    # Filter tournaments if specified
    tournaments = ALL_TOURNAMENTS
    if args.tournament:
        tournaments = [t for t in ALL_TOURNAMENTS if t['code'] == args.tournament]
        if not tournaments:
            print(f"Unknown tournament: {args.tournament}")
            print(f"Available: {', '.join(t['code'] for t in ALL_TOURNAMENTS)}")
            return
    
    print("=" * 70)
    print("STARTING11 WORLD CUP BATCH SCRAPER")
    print("=" * 70)
    print(f"Tournaments: {len(tournaments)}")
    print(f"Skip existing: {args.skip_existing}")
    print(f"Output: {output_base}")
    print("=" * 70)
    
    grand_success = 0
    grand_skipped = 0
    all_failed = []
    
    for tournament in tournaments:
        success, skipped, failed = scrape_tournament(
            tournament, output_base, skip_existing=args.skip_existing
        )
        grand_success += success
        grand_skipped += skipped
        all_failed.extend(failed)
    
    print("\n" + "=" * 70)
    print("GRAND TOTAL")
    print("=" * 70)
    print(f"Scraped: {grand_success} matches ({grand_success * 2} quizzes)")
    print(f"Skipped: {grand_skipped} matches")
    print(f"Failed: {len(all_failed)} matches")
    
    if all_failed:
        print(f"\nFailed matches:")
        for t1, t2, tourn, reason in all_failed:
            print(f"  [{tourn}] {t1} vs {t2}: {reason}")


if __name__ == "__main__":
    main()
