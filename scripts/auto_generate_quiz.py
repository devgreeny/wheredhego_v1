#!/usr/bin/env python3
"""
Automated Quiz Generator for wheredhego.com
Generates quizzes automatically without user input, using AI for avatar selection.

This script is designed to run in CI/CD pipelines (GitHub Actions) and:
1. Generates NBA or NFL quizzes automatically
2. Uses AI (Claude) to select appropriate avatars based on player appearance
3. Handles rate limiting and retries gracefully
4. Logs all operations for debugging

Usage:
    python auto_generate_quiz.py --game nba --count 1
    python auto_generate_quiz.py --game nfl --count 1
    python auto_generate_quiz.py --game both --count 2
"""

import json
import random
import time
import re
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, List

import pandas as pd

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NBA_SAVE_DIR = PROJECT_ROOT / "quizzes" / "starting5" / "preloaded"
NFL_SAVE_DIR = PROJECT_ROOT / "quizzes" / "gridiron11" / "preloaded"
COLLEGE_DATA_PATH = PROJECT_ROOT / "app" / "starting5" / "static" / "json" / "cbb25.csv"
NFL_COLLEGE_DATA_FILE = PROJECT_ROOT / "app" / "gridiron11" / "CFB" / "cbb25.csv"

# Avatar descriptions for AI matching (skin tone variations in your sprites)
NBA_AVATAR_DESCRIPTIONS = {
    "01": "dark skin, full beard, short hair",
    "02": "medium-dark skin, short beard, short hair", 
    "03": "light skin, clean shaven, short hair",
    "04": "dark skin, goatee, bald",
    "05": "light skin, clean shaven, bald",
    "06": "medium skin, stubble, short curly hair",
    "07": "dark skin, clean shaven, high top fade",
    "08": "light skin, beard, longer hair",
    "09": "medium-dark skin, full beard, dreads",
    "10": "dark skin, clean shaven, short hair",
    "11": "medium skin, goatee, braids",
    "12": "light skin, clean shaven, buzz cut",
    "13": "dark skin, stubble, mohawk",
    "14": "medium-dark skin, beard, afro",
}

NFL_AVATAR_DESCRIPTIONS = {
    "01": "dark skin, full beard",
    "02": "medium skin, clean shaven",
    "03": "light skin, stubble",
    "04": "dark skin, bald, goatee",
    "05": "light skin, short hair",
    "06": "medium-dark skin, beard",
    "07": "dark skin, dreads",
    "08": "light skin, clean shaven",
    "09": "medium skin, facial hair",
    "10": "dark skin, short hair",
}

# ═══════════════════════════════════════════════════════════════════════════════
# AI AVATAR SELECTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_ai_avatar_selection(player_name: str, team: str, is_nba: bool = True) -> str:
    """
    Use Claude AI to select the most appropriate avatar for a player.
    Falls back to random selection if AI is unavailable.
    """
    try:
        import anthropic
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"⚠️ No ANTHROPIC_API_KEY, using random avatar for {player_name}")
            return random.choice(list(NBA_AVATAR_DESCRIPTIONS.keys() if is_nba else NFL_AVATAR_DESCRIPTIONS.keys()))
        
        client = anthropic.Anthropic(api_key=api_key)
        
        avatar_options = NBA_AVATAR_DESCRIPTIONS if is_nba else NFL_AVATAR_DESCRIPTIONS
        options_text = "\n".join([f"  {k}: {v}" for k, v in avatar_options.items()])
        
        prompt = f"""You are helping select an 8-bit pixel art avatar for an {'NBA' if is_nba else 'NFL'} player in a sports trivia game.

Player: {player_name}
Team: {team}

Available avatar options (number: description):
{options_text}

Based on your knowledge of what {player_name} looks like (skin tone, facial hair, hair style), 
which avatar number (01-{len(avatar_options):02d}) would be the best match?

Reply with ONLY the two-digit number (e.g., "07"). Nothing else."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = message.content[0].text.strip()
        
        # Validate response
        if response in avatar_options:
            print(f"🤖 AI selected avatar {response} for {player_name}")
            return response
        
        # Try to extract a number
        match = re.search(r'(\d{1,2})', response)
        if match:
            num = match.group(1).zfill(2)
            if num in avatar_options:
                print(f"🤖 AI selected avatar {num} for {player_name}")
                return num
        
        print(f"⚠️ Invalid AI response '{response}', using random for {player_name}")
        
    except ImportError:
        print(f"⚠️ anthropic package not installed, using random avatar for {player_name}")
    except Exception as e:
        print(f"⚠️ AI error for {player_name}: {e}, using random")
    
    # Fallback to random
    avatars = list(NBA_AVATAR_DESCRIPTIONS.keys() if is_nba else NFL_AVATAR_DESCRIPTIONS.keys())
    return random.choice(avatars)


def get_skin_tone_based_avatar(player_name: str, is_nba: bool = True) -> str:
    """
    Simple heuristic-based avatar selection as a fallback.
    Uses player name patterns and common characteristics.
    """
    avatars = list(NBA_AVATAR_DESCRIPTIONS.keys() if is_nba else NFL_AVATAR_DESCRIPTIONS.keys())
    return random.choice(avatars)


# ═══════════════════════════════════════════════════════════════════════════════
# NBA GENERATION (adapted from generate_quiz_enhanced.py)
# ═══════════════════════════════════════════════════════════════════════════════

def load_college_data():
    """Load and process college data."""
    try:
        df_d1 = pd.read_csv(COLLEGE_DATA_PATH)
        df_d1 = df_d1.rename(columns={"School": "Official", "Common name": "Common", "Primary": "Conference"})
        return df_d1
    except Exception as e:
        print(f"❌ Error loading college data: {e}")
        return None


def clean_name(name):
    """Clean school name for matching."""
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
    return re.sub(r"\s+", " ", cleaned).strip()


def build_college_map(df_d1):
    """Build a mapping of cleaned names to (common_name, conference)."""
    _cleaned_map = {}
    for _, row in df_d1.iterrows():
        cleaned_common = clean_name(row.get("Common", ""))
        cleaned_official = clean_name(row.get("Official", ""))
        common = row.get("Common", "")
        conf = row.get("Conference", "Other")
        
        if cleaned_common:
            _cleaned_map[cleaned_common] = (common, conf)
        if cleaned_official:
            _cleaned_map[cleaned_official] = (common, conf)
    
    return _cleaned_map


def match_college_to_conf(school_raw: str, cleaned_map: dict):
    """Match a school name to our database."""
    if not school_raw or school_raw.lower().strip() in {"unknown", "none"}:
        return "Unknown", "Other", "Other", 0

    cleaned = clean_name(school_raw)

    if cleaned in {"southern california", "university of southern california"}:
        school, conf = cleaned_map.get("usc", ("USC", "Other"))
        return school, "College", conf, 100

    if cleaned in cleaned_map:
        school, conf = cleaned_map[cleaned]
        return school, "College", conf, 100

    if any(w in cleaned for w in ["high", "prep", "academy", "charter", "school"]):
        return school_raw, "High School", "Other", 0
    if any(w in cleaned for w in ["paris", "vasco", "canada", "real madrid", "bahamas", "belgrade", "france", "europe", "australia", "london", "international", "club"]):
        return school_raw, "International", "Other", 0
    
    return school_raw, "Other", "Other", 0


def generate_nba_quiz(count: int = 1) -> int:
    """Generate NBA quizzes automatically."""
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import (
        leaguegamelog,
        boxscoretraditionalv2,
        boxscoresummaryv2,
        commonplayerinfo
    )
    
    print(f"🏀 Generating {count} NBA quiz(es)...")
    
    df_d1 = load_college_data()
    if df_d1 is None:
        return 0
    
    cleaned_map = build_college_map(df_d1)
    generated = 0
    seasons = [f"{year}-{str(year+1)[-2:]}" for year in range(2010, 2024)]
    
    attempts = 0
    max_attempts = count * 5
    
    while generated < count and attempts < max_attempts:
        attempts += 1
        season = random.choice(seasons)
        print(f"\n--- Attempt {attempts}: Season {season} ---")
        
        try:
            time.sleep(1)
            gl = leaguegamelog.LeagueGameLog(season=season, season_type_all_star="Regular Season")
            game_ids = gl.get_data_frames()[0]["GAME_ID"].unique().tolist()
            random.shuffle(game_ids)
            
            for game_id in game_ids[:20]:  # Try up to 20 games per season
                try:
                    time.sleep(0.8)
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
                    
                    game_date = header.get("GAME_DATE_EST") or header.get("GAME_DATE")
                    try:
                        game_date = pd.to_datetime(game_date).date().strftime("%Y-%m-%d")
                    except:
                        game_date = str(game_date)
                    
                    # Try each team
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
                        
                        # Check all players have valid colleges
                        player_rows = []
                        lineup_valid = True
                        
                        for _, row in team_starters.iterrows():
                            name = row["PLAYER_NAME"]
                            
                            # Get player info
                            match = [p for p in players.get_players() if p["full_name"].lower() == name.lower()]
                            if not match:
                                lineup_valid = False
                                break
                            
                            player_id = match[0]["id"]
                            time.sleep(0.6)
                            
                            try:
                                info_df = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
                                school_raw = info_df.iloc[0].get("SCHOOL", "Unknown")
                                position = info_df.iloc[0].get("POSITION", "Unknown")
                                country = info_df.iloc[0].get("COUNTRY", "Unknown")
                            except:
                                lineup_valid = False
                                break
                            
                            school, school_type, conf, score = match_college_to_conf(school_raw, cleaned_map)
                            
                            if school_type != "College" or score < 100:
                                lineup_valid = False
                                break
                            
                            player_rows.append({
                                "row": row,
                                "name": name,
                                "school": school,
                                "school_type": school_type,
                                "conf": conf,
                                "player_id": player_id,
                                "position": position,
                                "country": country,
                            })
                        
                        if not lineup_valid or len(player_rows) < 5:
                            continue
                        
                        # Build quiz with AI avatar selection
                        quiz = {
                            "season": season,
                            "game_id": game_id,
                            "team_abbr": team_abbr,
                            "opponent_abbr": opp_abbr,
                            "matchup": f"{home_abbr} vs {away_abbr}",
                            "game_date": game_date,
                            "players": []
                        }
                        
                        for pr in player_rows:
                            row = pr["row"]
                            name = pr["name"]
                            
                            # AI avatar selection
                            avatar = get_ai_avatar_selection(name, team_abbr, is_nba=True)
                            
                            pts = row["PTS"]
                            ast = row["AST"]
                            reb = row["REB"]
                            stl = row["STL"]
                            blk = row["BLK"]
                            
                            quiz["players"].append({
                                "name": name,
                                "school": pr["school"],
                                "school_type": pr["school_type"],
                                "spriteIndex": int(avatar),
                                "team_abbrev": team_abbr,
                                "avatar": avatar,
                                "conference": pr["conf"],
                                "player_id": pr["player_id"],
                                "position": pr["position"],
                                "country": pr["country"],
                                "game_stats": {
                                    "pts": int(pts),
                                    "ast": int(ast),
                                    "reb": int(reb),
                                    "stl": int(stl),
                                    "blk": int(blk),
                                },
                                "game_contribution_pct": {
                                    "points_pct": round(pts / t_pts, 3) if t_pts else 0,
                                    "assists_pct": round(ast / t_ast, 3) if t_ast else 0,
                                    "rebounds_pct": round(reb / t_reb, 3) if t_reb else 0,
                                    "defense_pct": round((stl + blk) / t_def, 3) if t_def else 0,
                                },
                            })
                        
                        # Save quiz
                        NBA_SAVE_DIR.mkdir(parents=True, exist_ok=True)
                        fname = f"{season}_{game_id}_{team_abbr}.json"
                        out_path = NBA_SAVE_DIR / fname
                        
                        with out_path.open("w", encoding="utf-8") as f:
                            json.dump(quiz, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ Saved NBA quiz: {fname}")
                        generated += 1
                        
                        if generated >= count:
                            return generated
                        
                        break  # Move to next game
                    
                except Exception as e:
                    print(f"⚠️ Error processing game {game_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error with season {season}: {e}")
            continue
    
    return generated


# ═══════════════════════════════════════════════════════════════════════════════
# NFL GENERATION (adapted from generate_quiz_enhanced.py)
# ═══════════════════════════════════════════════════════════════════════════════

NFL_TEAMS = [
    'crd', 'atl', 'rav', 'buf', 'car', 'chi', 'cin', 'cle', 'dal', 'den',
    'det', 'gnb', 'htx', 'clt', 'jax', 'kan', 'rai', 'ram', 'mia', 'min',
    'nwe', 'nor', 'nyg', 'nyj', 'phi', 'pit', 'sfo', 'sea', 'tam', 'oti', 'was'
]

SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]
BASE_URL = "https://www.pro-football-reference.com"


def load_nfl_college_data() -> dict:
    """Load college data for NFL matching."""
    colleges = {}
    try:
        import csv
        with open(NFL_COLLEGE_DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                common_name = row.get('Common name', '').strip()
                school_name = row.get('School', '').strip()
                
                if common_name:
                    colleges[normalize_nfl_college_name(common_name)] = common_name
                    if school_name and school_name != common_name:
                        colleges[normalize_nfl_college_name(school_name)] = common_name
        
        return colleges
    except Exception as e:
        print(f"❌ Error loading NFL college data: {e}")
        return {}


def normalize_nfl_college_name(name: str) -> str:
    """Normalize college names for matching."""
    if not name or name.lower().strip() in {"unknown", "none", ""}:
        return ""
    
    normalized = name.lower().strip()
    
    special_cases = {
        "miami (fl)": "miami",
        "miami (florida)": "miami",
        "miami (ohio)": "miami of ohio",
        "miami (oh)": "miami of ohio",
        "university of miami": "miami",
        "mississippi": "ole miss",
        "university of mississippi": "ole miss",
        "north carolina st.": "nc state",
        "north carolina state": "nc state",
        "sam houston state": "sam houston"
    }
    
    if normalized in special_cases:
        return special_cases[normalized]
    
    normalized = (normalized
                 .replace("university of ", "")
                 .replace("univ. of ", "")
                 .replace("state university", "state")
                 .replace("university", "")
                 .replace(" at ", " ")
                 .replace("the ", "")
                 .replace("st.", "state")
                 .replace("st ", "state ")
                 .replace("-", " ")
                 .replace(".", "")
                 .replace("(", "")
                 .replace(")", ""))
    
    return re.sub(r'\s+', ' ', normalized).strip()


def normalize_pos(position: str) -> str:
    """Normalize NFL position."""
    if not position:
        return ""
    
    pos = position.upper().strip()
    pos = re.sub(r'\d+$', '', pos)
    
    synonyms = {
        "HB": "RB", "TB": "RB", "HALFBACK": "RB", "TAILBACK": "RB",
        "WIDE RECEIVER": "WR", "TIGHT END": "TE", "FULLBACK": "FB", "QUARTERBACK": "QB",
    }
    return synonyms.get(pos, pos)


def generate_nfl_quiz(count: int = 1) -> int:
    """Generate NFL quizzes automatically."""
    from urllib.request import Request, urlopen
    from bs4 import BeautifulSoup, Comment
    from io import StringIO
    
    print(f"🏈 Generating {count} NFL quiz(es)...")
    
    college_data = load_nfl_college_data()
    if not college_data:
        print("❌ Failed to load college data")
        return 0
    
    generated = 0
    attempts = 0
    max_attempts = count * 10
    
    while generated < count and attempts < max_attempts:
        attempts += 1
        team = random.choice(NFL_TEAMS)
        season = random.randint(2015, 2023)
        
        print(f"\n--- Attempt {attempts}: {team.upper()} {season} ---")
        
        try:
            # Get team games
            url = f"{BASE_URL}/teams/{team}/{season}.htm"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            html = urlopen(req).read().decode("utf-8")
            soup = BeautifulSoup(html, "lxml")
            
            boxscore_links = soup.select("table#games a[href*='/boxscores/']")
            if not boxscore_links:
                continue
            
            boxscore_urls = [BASE_URL + link["href"] for link in boxscore_links]
            random.shuffle(boxscore_urls)
            
            for boxscore_url in boxscore_urls[:5]:  # Try up to 5 games
                time.sleep(random.uniform(2, 4))
                
                try:
                    req = Request(boxscore_url, headers={"User-Agent": "Mozilla/5.0"})
                    html = urlopen(req).read().decode("utf-8")
                    soup = BeautifulSoup(html, "lxml")
                    
                    # Determine home/visitor
                    filename = boxscore_url.split('/')[-1]
                    team_from_url = filename.replace('.htm', '')[-3:]
                    is_home = team_from_url.lower() == team.lower()
                    
                    # Find starters table
                    comments = soup.find_all(string=lambda t: isinstance(t, Comment))
                    table_id = "home_starters" if is_home else "vis_starters"
                    starters_html = None
                    
                    for comment in comments:
                        if table_id in comment:
                            starters_html = comment
                            break
                    
                    if not starters_html:
                        continue
                    
                    starters_df = pd.read_html(StringIO(starters_html), header=0, attrs={"id": table_id})[0]
                    soup_table = BeautifulSoup(starters_html, "lxml")
                    player_links = soup_table.select(f"table#{table_id} th[data-stat='player'] a")
                    
                    # Get skill position players
                    players = []
                    for i, link in enumerate(player_links):
                        if i >= len(starters_df):
                            break
                        
                        player_name = link.get_text(strip=True)
                        player_href = link["href"]
                        player_url = BASE_URL + player_href
                        
                        row = starters_df.iloc[i]
                        position = normalize_pos(str(row.get("Pos", "")))
                        
                        if position in SKILL_POSITIONS:
                            players.append({
                                "name": player_name,
                                "position": position,
                                "url": player_url,
                            })
                    
                    if len(players) < 4:
                        continue
                    
                    # Get college info for all players
                    quiz_players = []
                    all_valid = True
                    
                    for i, player in enumerate(players[:6]):
                        time.sleep(random.uniform(2, 4))
                        
                        try:
                            req = Request(player["url"], headers={"User-Agent": "Mozilla/5.0"})
                            html = urlopen(req).read().decode("utf-8")
                            soup = BeautifulSoup(html, "lxml")
                            
                            meta = soup.find(id="meta")
                            college = "Unknown"
                            
                            if meta:
                                label = meta.find("strong", string=lambda s: s and s.strip().startswith("College"))
                                if label:
                                    for node in label.next_siblings:
                                        if getattr(node, "name", None) == "br":
                                            break
                                        if getattr(node, "name", None) == "a":
                                            href = node.get("href", "")
                                            if href.startswith("/schools/") and "high_schools" not in href:
                                                college = node.get_text(strip=True)
                            
                            if college == "Unknown":
                                all_valid = False
                                break
                            
                            # Validate college
                            normalized = normalize_nfl_college_name(college)
                            if normalized in college_data:
                                matched_college = college_data[normalized]
                            else:
                                all_valid = False
                                break
                            
                            # AI avatar selection
                            avatar = get_ai_avatar_selection(player["name"], team.upper(), is_nba=False)
                            
                            quiz_players.append({
                                "name": player["name"],
                                "position": f"{player['position']}{i+1}",
                                "college": matched_college,
                                "player_url": player["url"],
                                "team_abbrev": team.upper(),
                                "avatar": avatar
                            })
                            
                            print(f"✅ {player['name']}: {matched_college}")
                            
                        except Exception as e:
                            print(f"⚠️ Error getting college for {player['name']}: {e}")
                            all_valid = False
                            break
                    
                    if not all_valid or len(quiz_players) < 4:
                        continue
                    
                    # Save quiz
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    quiz_data = {
                        "team": team.upper(),
                        "season": season,
                        "game_url": boxscore_url,
                        "generated_at": timestamp,
                        "players": quiz_players
                    }
                    
                    NFL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
                    fname = f"players_{timestamp}.json"
                    out_path = NFL_SAVE_DIR / fname
                    
                    with out_path.open("w", encoding="utf-8") as f:
                        json.dump(quiz_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Saved NFL quiz: {fname}")
                    generated += 1
                    
                    if generated >= count:
                        return generated
                    
                    break  # Move to next team/season
                    
                except Exception as e:
                    print(f"⚠️ Error with game {boxscore_url}: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error with {team} {season}: {e}")
            continue
    
    return generated


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Automated Quiz Generator")
    parser.add_argument("--game", choices=["nba", "nfl", "both"], default="both",
                       help="Type of quiz to generate")
    parser.add_argument("--count", type=int, default=1,
                       help="Number of quizzes to generate per game type")
    
    args = parser.parse_args()
    
    print(f"🚀 Automated Quiz Generator")
    print(f"   Game type: {args.game}")
    print(f"   Count: {args.count}")
    print(f"   AI Avatar Selection: {'Enabled' if os.environ.get('ANTHROPIC_API_KEY') else 'Disabled (random)'}")
    print()
    
    nba_generated = 0
    nfl_generated = 0
    
    if args.game in ["nba", "both"]:
        nba_generated = generate_nba_quiz(args.count)
        print(f"\n🏀 NBA: Generated {nba_generated}/{args.count} quizzes")
    
    if args.game in ["nfl", "both"]:
        nfl_generated = generate_nfl_quiz(args.count)
        print(f"\n🏈 NFL: Generated {nfl_generated}/{args.count} quizzes")
    
    print(f"\n✅ Generation complete!")
    print(f"   NBA: {nba_generated}")
    print(f"   NFL: {nfl_generated}")
    
    # Exit with error if nothing was generated
    if nba_generated == 0 and nfl_generated == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
