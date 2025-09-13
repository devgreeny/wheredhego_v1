#!/usr/bin/env python3
"""
Enhanced Quiz Generator for wheredhego.com
Generates quizzes for both Starting5 (NBA) and Gridiron11 (NFL) games

This script combines the functionality of:
- NBA quiz generation with manual avatar assignment
- NFL quiz generation via web scraping
- Interactive prompts for both game types

Usage:
    # Generate NBA quizzes with manual avatars
    python generate_quiz_enhanced.py --game nba --manual-avatars --count 5
    
    # Generate NFL quizzes
    python generate_quiz_enhanced.py --game nfl --count 3
    
    # Generate both types
    python generate_quiz_enhanced.py --game both --count 5
    
    # Interactive mode (asks which game type)
    python generate_quiz_enhanced.py --interactive
"""

import json
import random
import time
import re
import argparse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

# NBA imports
from nba_api.stats.static import players
from nba_api.stats.endpoints import (
    leaguegamelog,
    boxscoretraditionalv2,
    boxscoresummaryv2,
    commonplayerinfo
)

# NFL imports
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup, Comment
from io import StringIO

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Directories for different game types
NBA_SAVE_DIR = "app/starting5/static/preloaded_quizzes"
NFL_SAVE_DIR = "app/gridiron11/preloaded_quizzes"

# College data path
COLLEGE_DATA_PATH = Path(__file__).resolve().parent / "starting5" / "app" / "static" / "json" / "cbb25.csv"

# ═══════════════════════════════════════════════════════════════════════════════
# NBA GENERATION (from original generate_quiz.py)
# ═══════════════════════════════════════════════════════════════════════════════

# Load and clean NCAA D1 schools
df_d1 = pd.read_csv(COLLEGE_DATA_PATH)
df_d1 = df_d1.rename(columns={"School": "Official", "Common name": "Common", "Primary": "Conference"})

def clean_name(name):
    if not isinstance(name, str):
        return ""

    cleaned = (
        name.lower()
        .replace("university of ", "")
        .replace("univ. of ", "")
        .replace("state university", "state")
        .replace("university", "")
        .replace(" at ", " ")
        .replace("the ", "")
        .replace("st.", "state")
        .replace("st ", "state ")
        .replace("state.", "state")
        .replace("-", " ")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

df_d1["Cleaned_Official"] = df_d1["Official"].apply(clean_name)
df_d1["Cleaned_Common"] = df_d1["Common"].apply(clean_name)
_cleaned_map = {}
for _, row in df_d1.iterrows():
    _cleaned_map[row["Cleaned_Common"]] = (row["Common"], row["Conference"])
    _cleaned_map[row["Cleaned_Official"]] = (row["Common"], row["Conference"])

def match_college_to_conf(school_raw: str):
    if not school_raw or school_raw.lower().strip() in {"unknown", "none"}:
        return "Unknown", "Other", "Other", 0

    cleaned = clean_name(school_raw)

    # Handle Southern California -> USC
    if cleaned in {"southern california", "university of southern california"}:
        school, conf = _cleaned_map.get("usc", ("USC", "Other"))
        return school, "College", conf, 100

    if cleaned in _cleaned_map:
        school, conf = _cleaned_map[cleaned]
        return school, "College", conf, 100

    if any(w in cleaned for w in ["high", "prep", "academy", "charter", "school"]):
        return school_raw, "High School", "Other", 0
    if any(w in cleaned for w in ["paris", "vasco", "canada", "real madrid", "bahamas", "belgrade", "france", "europe", "australia", "london", "international", "club"]):
        return school_raw, "International", "Other", 0
    return school_raw, "Other", "Other", 0

def get_college_info(player_name: str):
    match = [p for p in players.get_players() if p["full_name"].lower() == player_name.lower()]
    if not match:
        return "Unknown", "Other", "Other", None, "Unknown", "Unknown", 0

    player_id = match[0]["id"]
    time.sleep(0.6)
    info_df = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
    school_raw = info_df.iloc[0].get("SCHOOL", "Unknown")
    position = info_df.iloc[0].get("POSITION", "Unknown")
    country = info_df.iloc[0].get("COUNTRY", "Unknown")
    school, school_type, conf, score = match_college_to_conf(school_raw)
    return school, school_type, conf, player_id, position, country, score

def get_all_game_ids(season: str):
    time.sleep(0.6)
    gl = leaguegamelog.LeagueGameLog(season=season, season_type_all_star="Regular Season")
    return gl.get_data_frames()[0]["GAME_ID"].unique().tolist()

def _prompt_avatar(player_name, default):
    """Ask the user which avatar number to use for player_name."""
    try:
        raw = input(f"🏀 Avatar for {player_name} [1-14] (enter for {default}): ").strip()
    except EOFError:
        return default
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= 14:
        return int(raw)
    print("Invalid input, using", default)
    return default

def generate_nba_quiz(season=None, manual_avatars=False, avatar_map=None, save_dir=NBA_SAVE_DIR):
    """Generate a single NBA quiz."""
    if not season:
        seasons = [f"{year}-{str(year+1)[-2:]}" for year in range(2005, 2024)]
        season = random.choice(seasons)
    
    print(f"🏀 Generating NBA quiz for season {season}")
    
    game_ids = get_all_game_ids(season)
    random.shuffle(game_ids)
    
    for game_id in game_ids:
        try:
            time.sleep(0.6)
            box = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
            df = box.get_data_frames()[0]
            starters = df[df["START_POSITION"].notna() & (df["START_POSITION"] != "")]
            if len(starters["TEAM_ID"].unique()) < 2:
                continue

            summary = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
            header = summary.get_data_frames()[0].iloc[0]
            home_id, away_id = header["HOME_TEAM_ID"], header["VISITOR_TEAM_ID"]
            home_abbr = df[df["TEAM_ID"] == home_id]["TEAM_ABBREVIATION"].iloc[0]
            away_abbr = df[df["TEAM_ID"] == away_id]["TEAM_ABBREVIATION"].iloc[0]

            matchup_str = f"{home_abbr} vs {away_abbr}"
            game_date = header.get("GAME_DATE_EST") or header.get("GAME_DATE")
            try:
                game_date = pd.to_datetime(game_date).date().strftime("%Y-%m-%d")
            except Exception:
                game_date = str(game_date)

            team_lineups = []
            for team_id in [home_id, away_id]:
                team_starters = starters[starters["TEAM_ID"] == team_id].head(5)
                if len(team_starters) < 5:
                    continue

                team_abbr = team_starters["TEAM_ABBREVIATION"].iloc[0]
                opp_abbr = away_abbr if team_id == home_id else home_abbr
                t_pts = team_starters["PTS"].sum()
                t_ast = team_starters["AST"].sum()
                t_reb = team_starters["REB"].sum()
                t_def = team_starters["STL"].sum() + team_starters["BLK"].sum()

                player_rows = []
                lineup_valid = True
                for _, row in team_starters.iterrows():
                    name = row["PLAYER_NAME"]
                    school, typ, conf, pid, pos, country, m_score = get_college_info(name)
                    if typ != "College" or m_score < 100:
                        lineup_valid = False
                        break
                    player_rows.append({
                        "row": row,
                        "name": name,
                        "school": school,
                        "typ": typ,
                        "conf": conf,
                        "pid": pid,
                        "pos": pos,
                        "country": country,
                        "match": m_score,
                    })

                if not lineup_valid or len(player_rows) < 5:
                    continue

                quiz = {
                    "season": season,
                    "game_id": game_id,
                    "team_abbr": team_abbr,
                    "opponent_abbr": opp_abbr,
                    "matchup": matchup_str,
                    "game_date": game_date,
                    "players": []
                }

                for pr in player_rows:
                    row = pr["row"]
                    name = pr["name"]
                    school = pr["school"]
                    typ = pr["typ"]
                    conf = pr["conf"]
                    pid = pr["pid"]
                    pos = pr["pos"]
                    country = pr["country"]

                    sprite = random.randint(1, 14)
                    if avatar_map:
                        val = avatar_map.get(str(pid)) or avatar_map.get(pid)
                        if isinstance(val, (int, str)) and str(val).isdigit():
                            num = int(val)
                            if 1 <= num <= 14:
                                sprite = num

                    if manual_avatars:
                        sprite = _prompt_avatar(name, sprite)

                    pts = row["PTS"]
                    ast = row["AST"]
                    reb = row["REB"]
                    stl = row["STL"]
                    blk = row["BLK"]
                    defense = stl + blk

                    quiz["players"].append({
                        "name": name,
                        "school": school,
                        "school_type": typ,
                        "spriteIndex": sprite,
                        "team_abbrev": team_abbr,
                        "avatar": f"{sprite:02d}",
                        "conference": conf,
                        "player_id": pid,
                        "position": pos,
                        "country": country,
                        "game_stats": {
                            "pts": pts,
                            "ast": ast,
                            "reb": reb,
                            "stl": stl,
                            "blk": blk,
                        },
                        "game_contribution_pct": {
                            "points_pct": round(pts / t_pts, 3) if t_pts else 0,
                            "assists_pct": round(ast / t_ast, 3) if t_ast else 0,
                            "rebounds_pct": round(reb / t_reb, 3) if t_reb else 0,
                            "defense_pct": round(defense / t_def, 3) if t_def else 0,
                        },
                    })

                team_lineups.append(quiz)

            if team_lineups:
                selected = random.choice(team_lineups)
                fname = f"{selected['season']}_{selected['game_id']}_{selected['team_abbr']}.json"
                
                save_path = Path(save_dir)
                save_path.mkdir(parents=True, exist_ok=True)
                out_path = save_path / fname
                
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(selected, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved NBA quiz: {out_path}")
                return True
        except Exception as e:
            print(f"⚠️ Skipping NBA game {game_id}: {e}")
            continue
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# NFL GENERATION (from generate_nfl_quiz.py)
# ═══════════════════════════════════════════════════════════════════════════════

# NFL team abbreviations
NFL_TEAMS = [
    'crd', 'atl', 'rav', 'buf', 'car', 'chi', 'cin', 'cle', 'dal', 'den',
    'det', 'gnb', 'htx', 'clt', 'jax', 'kan', 'rai', 'ram', 'mia', 'min',
    'nwe', 'nor', 'nyg', 'nyj', 'phi', 'pit', 'sfo', 'sea', 'tam', 'oti', 'was'
]

FIXED_POSITIONS = ["QB", "RB", "C", "LT", "LG", "RG", "RT"]
SKILL_POSITIONS = ["WR", "TE", "FB"]
OFFENSIVE_POSITIONS = set(FIXED_POSITIONS + SKILL_POSITIONS)
BASE_URL = "https://www.pro-football-reference.com"

def normalize_pos(position: str) -> str:
    """Normalize position abbreviations."""
    if not position:
        return ""
    
    pos = position.upper().strip()
    position_map = {
        "HB": "RB", "FB": "FB", "WR": "WR", "TE": "TE",
        "QB": "QB", "C": "C", "G": "LG", "T": "LT",
        "LT": "LT", "LG": "LG", "RG": "RG", "RT": "RT"
    }
    
    return position_map.get(pos, pos)

def get_nfl_college_info(player_url: str, player_name: str) -> str:
    """Scrape college information for an NFL player."""
    try:
        time.sleep(random.uniform(2, 4))
        
        req = Request(player_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        meta = soup.find(id="meta")
        if not meta:
            print(f"❌ {player_name}: No meta box found")
            return "Unknown"
        
        label = meta.find("strong", string=lambda s: s and s.strip().startswith("College"))
        if not label:
            print(f"❌ {player_name}: No College label found")
            return "Unknown"
        
        colleges = []
        for node in label.next_siblings:
            if getattr(node, "name", None) == "br":
                break
            if getattr(node, "name", None) == "a":
                href = node.get("href", "")
                if href.startswith("/schools/") and "high_schools" not in href:
                    colleges.append(node.get_text(strip=True))
        
        if colleges:
            college = colleges[-1]
            print(f"✅ {player_name}: {college}")
            return college
        
        print(f"❌ {player_name}: No college links found")
        return "Unknown"
        
    except Exception as e:
        print(f"❌ Error fetching college for {player_name}: {e}")
        return "Unknown"

def scrape_nfl_team_games(team: str, season: int) -> list:
    """Scrape all game URLs for an NFL team in a given season."""
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

def scrape_nfl_starting_lineup(boxscore_url: str) -> tuple:
    """Scrape starting lineup from an NFL boxscore page."""
    try:
        req = Request(boxscore_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        comments = soup.find_all(string=lambda t: isinstance(t, Comment))
        starters_html = None
        
        for comment in comments:
            if "home_starters" in comment:
                starters_html = comment
                break
        
        if not starters_html:
            return None, None
        
        starters_df = pd.read_html(StringIO(starters_html), header=0, attrs={"id": "home_starters"})[0]
        soup_table = BeautifulSoup(starters_html, "lxml")
        
        player_links = soup_table.select("table#home_starters th[data-stat='player'] a")
        
        players = []
        for i, link in enumerate(player_links):
            if i >= len(starters_df):
                break
                
            player_name = link.get_text(strip=True)
            player_href = link["href"]
            player_url = BASE_URL + player_href
            
            row = starters_df.iloc[i]
            position = normalize_pos(str(row.get("Pos", "")))
            
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

def build_nfl_formation(players: list) -> dict:
    """Build a flexible 11-player formation from available players."""
    buckets = {pos: [] for pos in OFFENSIVE_POSITIONS}
    
    for player in players:
        pos = player["position"]
        if pos in buckets:
            buckets[pos].append(player)
    
    lineup = {}
    formation_order = []
    
    # Fixed positions
    for pos in FIXED_POSITIONS:
        if buckets[pos]:
            lineup[pos] = buckets[pos][0]
            formation_order.append(pos)
        else:
            print(f"⚠️  Warning: No {pos} found in lineup")
    
    # Skill positions
    skill_slots_filled = 0
    target_skill_slots = 4
    
    skill_priority = [
        ("WR", buckets["WR"]),
        ("TE", buckets["TE"]), 
        ("FB", buckets["FB"])
    ]
    
    for pos_type, available_players in skill_priority:
        for i, player in enumerate(available_players):
            if skill_slots_filled >= target_skill_slots:
                break
                
            position_name = f"{pos_type}{i + 1}"
            lineup[position_name] = player
            formation_order.append(position_name)
            skill_slots_filled += 1
    
    return {"order": formation_order, "by_pos": lineup}

def generate_nfl_quiz(team=None, season=None, save_dir=NFL_SAVE_DIR):
    """Generate a single NFL quiz."""
    if not team:
        team = random.choice(NFL_TEAMS)
    if not season:
        season = random.randint(2010, 2023)
    
    print(f"🏈 Generating NFL quiz for {team.upper()} {season}")
    
    boxscore_urls = scrape_nfl_team_games(team, season)
    if not boxscore_urls:
        return False
    
    random.shuffle(boxscore_urls)
    
    for boxscore_url in boxscore_urls:
        print(f"🎯 Trying game: {boxscore_url}")
        
        players, game_url = scrape_nfl_starting_lineup(boxscore_url)
        if not players:
            continue
        
        print(f"👥 Found {len(players)} offensive players")
        
        formation = build_nfl_formation(players)
        if len(formation["order"]) < 8:
            print(f"⚠️  Not enough players ({len(formation['order'])}), trying next game")
            continue
        
        quiz_players = []
        valid_players = 0
        
        for pos in formation["order"]:
            player = formation["by_pos"][pos]
            college = get_nfl_college_info(player["url"], player["name"])
            
            if college != "Unknown":
                valid_players += 1
            
            quiz_players.append({
                "name": player["name"],
                "position": pos,
                "college": college,
                "player_url": player["url"]
            })
        
        if valid_players < 8:
            print(f"⚠️  Not enough players with known colleges ({valid_players}), trying next game")
            continue
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quiz_data = {
            "team": team.upper(),
            "season": season,
            "game_url": game_url,
            "generated_at": timestamp,
            "players": quiz_players
        }
        
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

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_quizzes(game_type="both", count=5, manual_avatars=False, avatar_map=None):
    """Generate quizzes for specified game type(s)."""
    
    if game_type in ["nba", "both"]:
        print(f"\n🏀 === GENERATING {count} NBA QUIZZES ===")
        nba_generated = 0
        nba_attempts = 0
        max_attempts = count * 3
        
        while nba_generated < count and nba_attempts < max_attempts:
            nba_attempts += 1
            print(f"\n--- NBA Attempt {nba_attempts} (Generated: {nba_generated}/{count}) ---")
            
            if generate_nba_quiz(manual_avatars=manual_avatars, avatar_map=avatar_map):
                nba_generated += 1
        
        print(f"🏀 NBA Generation complete: {nba_generated}/{count} quizzes created")
    
    if game_type in ["nfl", "both"]:
        print(f"\n🏈 === GENERATING {count} NFL QUIZZES ===")
        nfl_generated = 0
        nfl_attempts = 0
        max_attempts = count * 3
        
        while nfl_generated < count and nfl_attempts < max_attempts:
            nfl_attempts += 1
            print(f"\n--- NFL Attempt {nfl_attempts} (Generated: {nfl_generated}/{count}) ---")
            
            if generate_nfl_quiz():
                nfl_generated += 1
            
            time.sleep(2)  # Be respectful to web scraping
        
        print(f"🏈 NFL Generation complete: {nfl_generated}/{count} quizzes created")

def interactive_mode():
    """Interactive mode for quiz generation."""
    print("🎮 Welcome to the Enhanced Quiz Generator!")
    print("This tool can generate quizzes for both Starting5 (NBA) and Gridiron11 (NFL)")
    
    while True:
        print("\nWhat would you like to generate?")
        print("1. NBA quizzes (Starting5)")
        print("2. NFL quizzes (Gridiron11)")
        print("3. Both NBA and NFL quizzes")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "4":
            print("👋 Goodbye!")
            break
        
        if choice not in ["1", "2", "3"]:
            print("❌ Invalid choice. Please try again.")
            continue
        
        # Get count
        try:
            count = int(input("How many quizzes of each type? (default: 5): ").strip() or "5")
        except ValueError:
            count = 5
        
        # Get manual avatars preference for NBA
        manual_avatars = False
        if choice in ["1", "3"]:
            manual_choice = input("Use manual avatar assignment for NBA quizzes? (y/n, default: n): ").strip().lower()
            manual_avatars = manual_choice.startswith("y")
        
        # Generate based on choice
        game_type_map = {"1": "nba", "2": "nfl", "3": "both"}
        game_type = game_type_map[choice]
        
        print(f"\n🚀 Starting generation of {count} {game_type.upper()} quiz(es)...")
        generate_quizzes(game_type, count, manual_avatars)
        
        print("\n✅ Generation complete!")
        
        continue_choice = input("Generate more quizzes? (y/n): ").strip().lower()
        if not continue_choice.startswith("y"):
            print("👋 Goodbye!")
            break

def main():
    parser = argparse.ArgumentParser(description="Enhanced Quiz Generator for NBA and NFL games")
    parser.add_argument("--game", choices=["nba", "nfl", "both"], default="both",
                       help="Type of quiz to generate (default: both)")
    parser.add_argument("--count", type=int, default=5,
                       help="Number of quizzes to generate per game type (default: 5)")
    parser.add_argument("--manual-avatars", action="store_true",
                       help="Prompt for avatar numbers for NBA quizzes")
    parser.add_argument("--avatar-mapping", 
                       help="JSON mapping of player_id to avatar number for NBA")
    parser.add_argument("--interactive", action="store_true",
                       help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
        return
    
    # Parse avatar mapping if provided
    avatar_map = None
    if args.avatar_mapping:
        try:
            if Path(args.avatar_mapping).is_file():
                with open(args.avatar_mapping, encoding="utf-8") as f:
                    avatar_map = json.load(f)
            else:
                avatar_map = json.loads(args.avatar_mapping)
        except Exception as e:
            print(f"❌ Failed to parse avatar mapping: {e}")
    
    generate_quizzes(args.game, args.count, args.manual_avatars, avatar_map)

if __name__ == "__main__":
    main()
