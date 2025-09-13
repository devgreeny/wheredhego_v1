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

# Fixed positions that are always present (7 players)
FIXED_POSITIONS = ["QB", "RB", "C", "LT", "LG", "RG", "RT"]

# Skill positions that vary by formation (4 players total)
SKILL_POSITIONS = ["WR", "TE", "FB"]

# All offensive positions
OFFENSIVE_POSITIONS = set(FIXED_POSITIONS + SKILL_POSITIONS)

BASE_URL = "https://www.pro-football-reference.com"

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

def get_college_info(player_url: str, player_name: str) -> str:
    """Scrape college information for a player."""
    try:
        time.sleep(random.uniform(2, 4))  # Be respectful to the server
        
        req = Request(player_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        # Find the meta information box
        meta = soup.find(id="meta")
        if not meta:
            print(f"❌ {player_name}: No meta box found")
            return "Unknown"
        
        # Look for College label
        label = meta.find("strong", string=lambda s: s and s.strip().startswith("College"))
        if not label:
            print(f"❌ {player_name}: No College label found")
            return "Unknown"
        
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
            college = colleges[-1]  # Take the last (most recent) college
            print(f"✅ {player_name}: {college}")
            return college
        
        print(f"❌ {player_name}: No college links found")
        return "Unknown"
        
    except Exception as e:
        print(f"❌ Error fetching college for {player_name}: {e}")
        return "Unknown"

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

def scrape_starting_lineup(boxscore_url: str) -> tuple:
    """Scrape starting lineup from a boxscore page."""
    try:
        req = Request(boxscore_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        # Find the home_starters table in HTML comments
        comments = soup.find_all(string=lambda t: isinstance(t, Comment))
        starters_html = None
        
        for comment in comments:
            if "home_starters" in comment:
                starters_html = comment
                break
        
        if not starters_html:
            return None, None
        
        # Parse the starting lineup table
        starters_df = pd.read_html(StringIO(starters_html), header=0, attrs={"id": "home_starters"})[0]
        soup_table = BeautifulSoup(starters_html, "lxml")
        
        # Extract player names and links
        player_links = soup_table.select("table#home_starters th[data-stat='player'] a")
        
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
        
        return players, boxscore_url
        
    except Exception as e:
        print(f"❌ Error scraping lineup from {boxscore_url}: {e}")
        return None, None

def build_formation(players: list) -> dict:
    """Build a flexible 11-player formation from available players."""
    
    # Group players by position
    buckets = {pos: [] for pos in OFFENSIVE_POSITIONS}
    
    for player in players:
        pos = player["position"]
        if pos in buckets:
            buckets[pos].append(player)
    
    lineup = {}
    formation_order = []
    
    # Step 1: Assign fixed positions (7 players)
    for pos in FIXED_POSITIONS:
        if buckets[pos]:
            lineup[pos] = buckets[pos][0]
            formation_order.append(pos)
        else:
            print(f"⚠️  Warning: No {pos} found in lineup")
    
    # Step 2: Assign skill positions (4 players)
    skill_slots_filled = 0
    target_skill_slots = 4
    
    # Priority order for skill positions
    skill_priority = [
        ("WR", buckets["WR"]),
        ("TE", buckets["TE"]), 
        ("FB", buckets["FB"])
    ]
    
    for pos_type, available_players in skill_priority:
        for i, player in enumerate(available_players):
            if skill_slots_filled >= target_skill_slots:
                break
                
            # Create numbered position (WR1, WR2, TE1, etc.)
            position_name = f"{pos_type}{i + 1}"
            lineup[position_name] = player
            formation_order.append(position_name)
            skill_slots_filled += 1
    
    return {"order": formation_order, "by_pos": lineup}

def generate_nfl_quiz(team: str = None, season: int = None, save_dir: str = "app/gridiron11/preloaded_quizzes") -> bool:
    """Generate a single NFL quiz."""
    
    # Select random team and season if not specified
    if not team:
        team = random.choice(NFL_TEAMS)
    if not season:
        season = random.randint(2010, 2023)  # Modern era with good data
    
    print(f"🏈 Generating NFL quiz for {team.upper()} {season}")
    
    # Get all games for the team/season
    boxscore_urls = scrape_team_games(team, season)
    if not boxscore_urls:
        return False
    
    # Try random games until we find a valid starting lineup
    random.shuffle(boxscore_urls)
    
    for boxscore_url in boxscore_urls:
        print(f"🎯 Trying game: {boxscore_url}")
        
        players, game_url = scrape_starting_lineup(boxscore_url)
        if not players:
            continue
        
        print(f"👥 Found {len(players)} offensive players")
        
        # Build formation
        formation = build_formation(players)
        if len(formation["order"]) < 8:  # Need at least 8 players for a valid quiz
            print(f"⚠️  Not enough players ({len(formation['order'])}), trying next game")
            continue
        
        # Fetch college information for each player
        quiz_players = []
        valid_players = 0
        
        for pos in formation["order"]:
            player = formation["by_pos"][pos]
            college = get_college_info(player["url"], player["name"])
            
            if college != "Unknown":
                valid_players += 1
            
            quiz_players.append({
                "name": player["name"],
                "position": pos,
                "college": college,
                "player_url": player["url"]
            })
        
        # Need at least 8 players with known colleges
        if valid_players < 8:
            print(f"⚠️  Not enough players with known colleges ({valid_players}), trying next game")
            continue
        
        # Create quiz data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quiz_data = {
            "team": team.upper(),
            "season": season,
            "game_url": game_url,
            "generated_at": timestamp,
            "players": quiz_players
        }
        
        # Save quiz file
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"players_{timestamp}.json"
        file_path = save_path / filename
        
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved NFL quiz: {file_path}")
        print(f"📊 Quiz contains {len(quiz_players)} players ({valid_players} with known colleges)")
        return True
    
    print(f"❌ Could not generate valid quiz for {team.upper()} {season}")
    return False

def generate_multiple_nfl_quizzes(count: int = 5, save_dir: str = "app/gridiron11/preloaded_quizzes"):
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
        
        # Small delay between generations
        time.sleep(2)
    
    print(f"\n🎯 Generation complete: {generated}/{count} quizzes created")

def main():
    parser = argparse.ArgumentParser(description="Generate NFL quizzes by web scraping")
    parser.add_argument("--count", type=int, default=5, help="Number of quizzes to generate")
    parser.add_argument("--team", type=str, help="Specific NFL team (e.g., 'phi', 'dal')")
    parser.add_argument("--season", type=int, help="Specific season year (e.g., 2023)")
    parser.add_argument("--save-dir", type=str, default="app/gridiron11/preloaded_quizzes", 
                       help="Directory to save quiz files")
    
    args = parser.parse_args()
    
    if args.team or args.season:
        # Generate single quiz with specific parameters
        generate_nfl_quiz(args.team, args.season, args.save_dir)
    else:
        # Generate multiple random quizzes
        generate_multiple_nfl_quizzes(args.count, args.save_dir)

if __name__ == "__main__":
    main()
