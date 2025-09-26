#!/usr/bin/env python3
"""
NFL Quiz Generator - Web Scraping Version
Generates NFL lineup quizzes by scraping pro-football-reference.com

This script:
1. Selects a random NFL team and season
2. Scrapes game data from pro-football-reference.com
3. Extracts starting lineup from a random game
4. Fetches college information for each player
5. Generates a quiz JSON file

Usage:
    python generate_nfl_quiz.py --count 5
    python generate_nfl_quiz.py --team phi --season 2023
"""

import json
import random
import time
import re
import csv
import os
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup, Comment
from io import StringIO
import pandas as pd
import argparse

# NFL team abbreviations
NFL_TEAMS = [
    'crd', 'atl', 'rav', 'buf', 'car', 'chi', 'cin', 'cle', 'dal', 'den',
    'det', 'gnb', 'htx', 'clt', 'jax', 'kan', 'rai', 'ram', 'mia', 'min',
    'nwe', 'nor', 'nyg', 'nyj', 'phi', 'pit', 'sfo', 'sea', 'tam', 'oti', 'was'
]

# Main skill positions only - the fun positions people remember!
SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]

# All offensive positions (only skill positions now)
OFFENSIVE_POSITIONS = set(SKILL_POSITIONS)

BASE_URL = "https://www.pro-football-reference.com"

# Path to college dataset
COLLEGE_DATA_FILE = "app/gridiron11/CFB/cbb25.csv"

# Global college data cache
_college_data = None

def load_college_data() -> dict:
    """Load and cache college data from CSV file."""
    global _college_data
    if _college_data is not None:
        return _college_data
    
    colleges = {}
    try:
        with open(COLLEGE_DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                common_name = row.get('Common name', '').strip()
                school_name = row.get('School', '').strip()
                
                if common_name:
                    # Store both common name and school name as keys
                    colleges[normalize_college_name(common_name)] = common_name
                    if school_name and school_name != common_name:
                        colleges[normalize_college_name(school_name)] = common_name
        
        print(f"📚 Loaded {len(set(colleges.values()))} unique colleges with {len(colleges)} name variations")
        _college_data = colleges
        return colleges
        
    except Exception as e:
        print(f"❌ Error loading college data: {e}")
        _college_data = {}
        return {}

def normalize_college_name(name: str) -> str:
    """Normalize college names for consistent matching with special cases."""
    if not name or name.lower().strip() in {"unknown", "none", ""}:
        return ""
    
    # Convert to lowercase and strip
    normalized = name.lower().strip()
    
    # Handle special cases first (before other normalization)
    special_cases = {
        "miami (fl)": "miami",
        "miami (florida)": "miami", 
        "miami (ohio)": "miami of ohio",
        "miami (oh)": "miami of ohio",
        "university of miami": "miami",
        "university of miami (florida)": "miami",
        "university of miami (fl)": "miami",
        "mississippi": "ole miss",
        "university of mississippi": "ole miss",
        "sam houston state": "sam houston",
        "north carolina st.": "nc state",
        "north carolina state": "nc state"
    }
    
    if normalized in special_cases:
        result = special_cases[normalized]
        print(f"🔄 Special case applied: '{name}' -> '{result}'")
        return result
    
    # Remove common punctuation
    normalized = re.sub(r'[.,\-()\[\]{}]', ' ', normalized)
    
    # Handle common abbreviations
    abbreviations = {
        r'\bst\b': 'state',
        r'\bst\.\b': 'state',
        r'\buniv\b': 'university',
        r'\buniv\.\b': 'university',
        r'\bcol\b': 'college',
        r'\bcol\.\b': 'college',
        r'\bu\b': 'university',
        r'\bu\.\b': 'university',
        r'\btech\b': 'technology',
        r'\btech\.\b': 'technology',
        r'\binst\b': 'institute',
        r'\binst\.\b': 'institute',
        r'\ba&m\b': 'agricultural and mechanical',
        r'\ba & m\b': 'agricultural and mechanical',
        r'\bunc\b': 'university of north carolina',
        r'\busc\b': 'university of southern california',
        r'\bucla\b': 'university of california los angeles',
        r'\blsu\b': 'louisiana state university',
        r'\btcu\b': 'texas christian university',
        r'\bsmu\b': 'southern methodist university',
        r'\bbyu\b': 'brigham young university',
    }
    
    for abbrev, full in abbreviations.items():
        normalized = re.sub(abbrev, full, normalized)
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Remove "university of" and "college of" prefixes for better matching
    normalized = re.sub(r'^(university of |college of )', '', normalized)
    
    return normalized

def match_college_name(scraped_name: str, college_data: dict) -> str:
    """Match scraped college name to our dataset - EXACT MATCHES ONLY."""
    if not scraped_name or scraped_name.lower().strip() in {"unknown", "none", ""}:
        return None
    
    normalized_scraped = normalize_college_name(scraped_name)
    
    # Only accept exact matches after normalization
    if normalized_scraped in college_data:
        matched_name = college_data[normalized_scraped]
        print(f"✅ Exact match: '{scraped_name}' -> '{matched_name}'")
        return matched_name
    
    print(f"❌ No exact match found for college: '{scraped_name}' (normalized: '{normalized_scraped}')")
    return None

def normalize_pos(position: str) -> str:
    """Normalize position abbreviations."""
    if not position:
        return ""
    
    pos = position.upper().strip()
    
    # Handle common variations
    position_map = {
        "HB": "RB", "FB": "FB", "WR": "WR", "TE": "TE",
        "QB": "QB", "C": "C", "G": "LG", "T": "LT",
        "LT": "LT", "LG": "LG", "RG": "RG", "RT": "RT"
    }
    
    return position_map.get(pos, pos)

def get_college_info(player_url: str, player_name: str, college_data: dict) -> tuple:
    """Scrape college information for a player and match to dataset.
    Returns (matched_college_name, raw_scraped_name) or (None, None) if no match.
    """
    try:
        time.sleep(random.uniform(8, 12))  # Be very respectful - avoid IP ban
        
        req = Request(player_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        # Find the meta information box
        meta = soup.find(id="meta")
        if not meta:
            print(f"❌ {player_name}: No meta box found")
            return None, None
        
        # Look for College label
        label = meta.find("strong", string=lambda s: s and s.strip().startswith("College"))
        if not label:
            print(f"❌ {player_name}: No College label found")
            return None, None
        
        # Extract college links
        colleges = []
        for node in label.next_siblings:
            if getattr(node, "name", None) == "br":
                break
            if getattr(node, "name", None) == "a":
                href = node.get("href", "")
                if href.startswith("/schools/") and "high_schools" not in href:
                    colleges.append(node.get_text(strip=True))
        
        if colleges:
            raw_college = colleges[-1]  # Take the last (most recent) college
            matched_college = match_college_name(raw_college, college_data)
            
            if matched_college:
                print(f"✅ {player_name}: {raw_college} -> {matched_college}")
                return matched_college, raw_college
            else:
                print(f"❌ {player_name}: {raw_college} (no dataset match)")
                return None, raw_college
        
        print(f"❌ {player_name}: No college links found")
        return None, None
        
    except Exception as e:
        print(f"❌ Error fetching college for {player_name}: {e}")
        return None, None

def scrape_team_games(team: str, season: int) -> list:
    """Scrape all game URLs for a team in a given season."""
    try:
        url = f"{BASE_URL}/teams/{team}/{season}.htm"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        
        soup = BeautifulSoup(html, "lxml")
        boxscore_links = soup.select("table#games a[href*='/boxscores/']")
        
        if not boxscore_links:
            print(f"❌ No games found for {team} in {season}")
            return []
        
        boxscore_urls = [BASE_URL + link["href"] for link in boxscore_links]
        print(f"📅 Found {len(boxscore_urls)} games for {team} in {season}")
        return boxscore_urls
        
    except Exception as e:
        print(f"❌ Error scraping games for {team} {season}: {e}")
        return []

def scrape_starting_lineup(boxscore_url: str, target_team: str) -> tuple:
    """Scrape starting lineup from a boxscore page for a specific team."""
    try:
        req = Request(boxscore_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        # Extract team abbreviation from URL
        # URL format: /boxscores/201511010nor.htm - extract "nor"
        url_parts = boxscore_url.split('/')
        if len(url_parts) > 0:
            filename = url_parts[-1]  # "201511010nor.htm"
            # Extract team from end of filename (last 3 chars before .htm)
            team_from_url = filename.replace('.htm', '')[-3:]
            print(f"🔍 URL team: {team_from_url}, Target team: {target_team}")
        
        # Look for both home_starters and vis_starters tables in comments
        comments = soup.find_all(string=lambda t: isinstance(t, Comment))
        starters_html = None
        table_id = None
        
        # Determine if target team is home or visitor based on URL
        # URL format: /boxscores/201512130tam.htm means TAM is home team
        is_target_home = (team_from_url.lower() == target_team.lower())
        
        if is_target_home:
            # Target team is home team, look for home_starters
            for comment in comments:
                if "home_starters" in comment:
                    starters_html = comment
                    table_id = "home_starters"
                    print(f"✅ Found {target_team} as home team (from URL)")
                    break
        else:
            # Target team is visiting team, look for vis_starters
            for comment in comments:
                if "vis_starters" in comment:
                    starters_html = comment
                    table_id = "vis_starters"
                    print(f"✅ Found {target_team} as visiting team (from URL)")
                    break
        
        # Fallback: if we didn't find the expected table, try the other one
        if not starters_html:
            print(f"⚠️ Expected table not found, trying fallback...")
            for comment in comments:
                if "home_starters" in comment and not is_target_home:
                    starters_html = comment
                    table_id = "home_starters"
                    print(f"🔄 Fallback: trying home_starters table")
                    break
                elif "vis_starters" in comment and is_target_home:
                    starters_html = comment
                    table_id = "vis_starters" 
                    print(f"🔄 Fallback: trying vis_starters table")
                    break
        
        if not starters_html:
            print(f"❌ No starters table found for {target_team}")
            return None, None
        
        # Parse the starting lineup table
        starters_df = pd.read_html(StringIO(starters_html), header=0, attrs={"id": table_id})[0]
        soup_table = BeautifulSoup(starters_html, "lxml")
        
        # Extract player names and links
        player_links = soup_table.select(f"table#{table_id} th[data-stat='player'] a")
        
        players = []
        for i, link in enumerate(player_links):
            if i >= len(starters_df):
                break
                
            player_name = link.get_text(strip=True)
            player_href = link["href"]
            player_url = BASE_URL + player_href
            
            # Get position from dataframe
            row = starters_df.iloc[i]
            position = normalize_pos(str(row.get("Pos", "")))
            
            # Only include offensive players
            if position in OFFENSIVE_POSITIONS:
                players.append({
                    "name": player_name,
                    "position": position,
                    "url": player_url,
                    "href": player_href
                })
        
        print(f"🏈 Extracted {len(players)} skill position players from {table_id}")
        return players, boxscore_url
        
    except Exception as e:
        print(f"❌ Error scraping lineup from {boxscore_url}: {e}")
        return None, None

def build_formation(players: list) -> dict:
    """Build a 5-6 skill position formation from available players.
    Takes any combination of QB, RB, WR, TE that totals 5-6 players.
    """
    
    # Group players by position
    buckets = {pos: [] for pos in OFFENSIVE_POSITIONS}
    
    for player in players:
        pos = player["position"]
        if pos in buckets:
            buckets[pos].append(player)
    
    lineup = {}
    formation_order = []
    
    # Target 5-6 total skill players
    target_total_players = random.randint(5, 6)
    
    # Add players from all skill positions until we reach target
    # Priority: QB first, then RB, then WR, then TE
    skill_priority = [
        ("QB", buckets["QB"]),
        ("RB", buckets["RB"]),
        ("WR", buckets["WR"]),
        ("TE", buckets["TE"])
    ]
    
    players_added = 0
    
    for pos_type, available_players in skill_priority:
        for i, player in enumerate(available_players):
            if players_added >= target_total_players:
                break
                
            # Create numbered position (QB1, RB1, RB2, WR1, WR2, WR3, TE1, etc.)
            position_name = f"{pos_type}{i + 1}"
            lineup[position_name] = player
            formation_order.append(position_name)
            players_added += 1
        
        # Stop if we've reached our target
        if players_added >= target_total_players:
            break
    
    # Verify we have at least 5 skill players total
    if len(formation_order) < 5:
        print(f"❌ Not enough skill players: {len(formation_order)} (need at least 5)")
        return None
    
    print(f"✅ Built skill formation with {len(formation_order)} players: {', '.join(formation_order)}")
    return {"order": formation_order, "by_pos": lineup}

def generate_nfl_quiz_for_team_season(team: str, season: int, save_dir: str) -> tuple:
    """Try to generate a quiz for a specific team/season combination.
    Only saves lineups with 100% college matches for all 5-6 skill players.
    """
    print(f"🏈 Trying NFL quiz for {team.upper()} {season}")
    
    # Load college data
    college_data = load_college_data()
    if not college_data:
        print(f"❌ Could not load college dataset")
        return False, None
    
    # Get all games for the team/season
    boxscore_urls = scrape_team_games(team, season)
    if not boxscore_urls:
        print(f"❌ No games found for {team.upper()} {season}")
        return False, None
    
    # Try random games until we find a valid starting lineup
    random.shuffle(boxscore_urls)
    
    for i, boxscore_url in enumerate(boxscore_urls):
        print(f"🎯 Trying game: {boxscore_url}")
        
        # Add respectful delay between requests (except for first attempt)
        if i > 0:
            print("⏳ Waiting 10 seconds to be respectful to pro-football-reference...")
            time.sleep(10)
        
        players, game_url = scrape_starting_lineup(boxscore_url, team)
        if not players:
            print(f"⚠️  No players found, trying next game")
            continue
        
        print(f"👥 Found {len(players)} offensive players")
        
        # DEBUG: Show actual positions found
        positions_found = [f"{player['name']} ({player['position']})" for player in players]
        print(f"🔍 Positions scraped: {', '.join(positions_found)}")
        
        # Build formation - focus on skill positions
        formation = build_formation(players)
        if not formation:
            print(f"⚠️  Invalid formation, trying next game")
            continue
        
        if len(formation["order"]) < 5:
            print(f"⚠️  Incomplete skill lineup ({len(formation['order'])} players), trying next game")
            continue
        
        # Fetch college information for each player - require 100% match
        quiz_players = []
        failed_matches = []
        
        for pos in formation["order"]:
            player = formation["by_pos"][pos]
            matched_college, raw_college = get_college_info(player["url"], player["name"], college_data)
            
            if matched_college:
                quiz_players.append({
                    "name": player["name"],
                    "position": pos,
                    "college": matched_college,
                    "player_url": player["url"]
                })
            else:
                failed_matches.append(f"{player['name']} ({pos}): {raw_college or 'No college found'}")
        
        # Require 100% match - all 5-6 skill players must have matched colleges
        expected_players = len(formation["order"])
        if len(quiz_players) < expected_players:
            print(f"❌ Only {len(quiz_players)}/{expected_players} skill players matched to dataset:")
            for failure in failed_matches:
                print(f"   • {failure}")
            print(f"🚫 Team {team.upper()} {season} has non-college players, trying completely different team/season")
            return False, None
        
        # Success! We have a complete lineup with 100% college matches
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quiz_data = {
            "team": team.upper(),
            "season": season,
            "game_url": game_url,
            "generated_at": timestamp,
            "players": quiz_players,
            "match_rate": "100%",
            "notes": f"All {len(quiz_players)} skill players matched to college dataset"
        }
        
        print(f"✅ Perfect match! All {len(quiz_players)} skill players have validated colleges")
        return True, quiz_data
    
    print(f"❌ Could not find 100% matched roster for {team.upper()} {season}")
    return False, None

def generate_nfl_quiz(team: str = None, season: int = None, save_dir: str = "quizzes/gridiron11/preloaded") -> bool:
    """Generate a single NFL quiz with robust failsafe for missing players."""
    
    max_attempts = 10  # Try up to 10 different team/season combinations
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        # Select random team and season if not specified, or if previous attempts failed
        if not team or attempt > 1:
            current_team = random.choice(NFL_TEAMS)
        else:
            current_team = team
            
        if not season or attempt > 1:
            current_season = random.randint(2010, 2023)  # Modern era with good data
        else:
            current_season = season
        
        print(f"🔄 Attempt {attempt}/{max_attempts}")
        
        # Try to generate quiz for this team/season
        success, quiz_data = generate_nfl_quiz_for_team_season(current_team, current_season, save_dir)
        
        if success:
            # Save the successful quiz
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            filename = f"players_{quiz_data['generated_at']}.json"
            file_path = save_path / filename
            
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(quiz_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved NFL quiz: {file_path}")
            print(f"📊 Quiz contains {len(quiz_data['players'])} players")
            return True
        
        # If this attempt failed, try a different team/season combination
        print(f"⚠️  Attempt {attempt} failed, trying different team/season...")
        time.sleep(10)  # Wait 15 seconds before trying next team to avoid rate limiting
    
    print(f"❌ Could not generate valid quiz after {max_attempts} attempts")
    return False

def generate_multiple_nfl_quizzes(count: int = 5, save_dir: str = "quizzes/gridiron11/preloaded"):
    """Generate multiple NFL quizzes."""
    print(f"🚀 Generating {count} NFL quizzes...")
    
    generated = 0
    attempts = 0
    max_attempts = count * 3  # Allow some failures
    
    while generated < count and attempts < max_attempts:
        attempts += 1
        print(f"\n--- Attempt {attempts}/{max_attempts} (Generated: {generated}/{count}) ---")
        
        if generate_nfl_quiz(save_dir=save_dir):
            generated += 1
        
        # Longer delay between generations to avoid rate limiting
        time.sleep(10)
    
    print(f"\n🎯 Generation complete: {generated}/{count} quizzes created")

def manually_assign_sprites(quiz_file_path: str):
    """Manually assign sprite numbers to players in a quiz file."""
    try:
        with open(quiz_file_path, 'r') as f:
            quiz_data = json.load(f)
        
        team_abbrev = quiz_data.get("team", "").upper()
        players = quiz_data.get("players", [])
        
        print(f"\n🏈 Team: {team_abbrev}")
        print(f"📁 Available sprites: {team_abbrev.lower()}_01.png to {team_abbrev.lower()}_10.png")
        print(f"👥 Players in quiz: {len(players)}")
        print("-" * 50)
        
        for i, player in enumerate(players):
            current_avatar = player.get("avatar", f"{i+1:02d}")
            print(f"\n{i+1}. {player['name']} ({player['position']})")
            print(f"   Current sprite: {team_abbrev.lower()}_{current_avatar}.png")
            
            while True:
                new_avatar = input(f"   Enter new sprite number (01-10) or press Enter to keep {current_avatar}: ").strip()
                
                if not new_avatar:
                    # Keep current avatar
                    break
                
                if new_avatar.isdigit() and 1 <= int(new_avatar) <= 10:
                    new_avatar = f"{int(new_avatar):02d}"
                    player["avatar"] = new_avatar
                    print(f"   ✅ Updated to {team_abbrev.lower()}_{new_avatar}.png")
                    break
                else:
                    print(f"   ❌ Invalid input. Enter a number between 1-10.")
        
        # Save updated quiz
        with open(quiz_file_path, 'w') as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Sprite assignments saved to {quiz_file_path}")
        
    except Exception as e:
        print(f"❌ Error assigning sprites: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate NFL quizzes by web scraping")
    parser.add_argument("--count", type=int, default=5, help="Number of quizzes to generate")
    parser.add_argument("--team", type=str, help="Specific NFL team (e.g., 'phi', 'dal')")
    parser.add_argument("--season", type=int, help="Specific season year (e.g., 2023)")
    parser.add_argument("--save-dir", type=str, default="quizzes/gridiron11/preloaded", 
                       help="Directory to save quiz files")
    parser.add_argument("--assign-sprites", "-a", type=str,
                       help="Manually assign sprites to players in a quiz file")
    
    args = parser.parse_args()
    
    if args.assign_sprites:
        # Manual sprite assignment mode
        if os.path.exists(args.assign_sprites):
            manually_assign_sprites(args.assign_sprites)
        else:
            print(f"❌ Quiz file not found: {args.assign_sprites}")
    elif args.team or args.season:
        # Generate single quiz with specific parameters
        generate_nfl_quiz(args.team, args.season, args.save_dir)
    else:
        # Generate multiple random quizzes
        generate_multiple_nfl_quizzes(args.count, args.save_dir)

if __name__ == "__main__":
    main()
