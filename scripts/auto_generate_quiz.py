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
# TEAM ABBREVIATION MAPPINGS
# Maps NBA API abbreviations to your avatar directory names
# Handles relocated teams, renamed teams, and alternate abbreviations
# ═══════════════════════════════════════════════════════════════════════════════

TEAM_ABBREV_MAP = {
    # ═══════════════════════════════════════════════════════════════════════════
    # NBA TEAM ABBREVIATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    # New Orleans variations → NOH (your directory)
    "NOP": "NOH",   # New Orleans Pelicans (2013-present)
    "NOK": "NOH",   # New Orleans/Oklahoma City Hornets (2005-07 Katrina)
    
    # Phoenix variations → PHO (your directory)
    "PHX": "PHO",   # Common alternate
    
    # Utah variations → UTH (your directory)
    "UTA": "UTH",   # Common alternate
    
    # Brooklyn/New Jersey → BKN (your directory)
    "NJN": "BKN",   # New Jersey Nets (pre-2012)
    "BRK": "BKN",   # Alternate
    
    # Charlotte variations → CHA (your directory)
    "CHH": "CHA",   # Charlotte Hornets (original, 1988-2002)
    "CHO": "CHA",   # Alternate
    
    # Relocated teams with no current equivalent
    "SEA": "OKC",   # Seattle SuperSonics → OKC (pre-2008)
    "VAN": "MEM",   # Vancouver Grizzlies → Memphis (pre-2001)
    
    # Washington variations
    "WSB": "WAS",   # Washington Bullets (pre-1997)
    "WSH": "WAS",   # Alternate
    
    # Other common alternates
    "GS": "GSW",    # Golden State
    "SA": "SAS",    # San Antonio
    "NY": "NYK",    # New York
    "UTAH": "UTH",  # Full name variant
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NFL TEAM ABBREVIATIONS (Pro Football Reference → Your directory)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Green Bay
    "GB": "GNB",
    "GBP": "GNB",
    
    # Kansas City
    "KC": "KAN",
    "KCC": "KAN",
    
    # LA Rams
    "LA": "LAR",
    "RAM": "LAR",
    "STL": "LAR",   # St. Louis Rams (pre-2016)
    
    # Las Vegas/Oakland Raiders
    "LV": "LVR",
    "OAK": "LVR",   # Oakland Raiders (pre-2020)
    
    # New Orleans Saints
    "NO": "NOR",
    
    # New England
    "NE": "NWE",
    "NEP": "NWE",
    
    # San Francisco
    "SF": "SFO",
    
    # Tampa Bay
    "TB": "TAM",
    "TBB": "TAM",
    
    # San Diego → LA Chargers
    "SD": "LAC",
    "SDC": "LAC",
}


def normalize_team_abbrev(abbrev: str) -> str:
    """Convert NBA API team abbreviation to your avatar directory name."""
    return TEAM_ABBREV_MAP.get(abbrev.upper(), abbrev.upper())


# ═══════════════════════════════════════════════════════════════════════════════
# PRIORITY PLAYER AVATAR MAPPINGS
# These players get their designated avatar guaranteed (avatars designed after them)
# ═══════════════════════════════════════════════════════════════════════════════

PRIORITY_PLAYER_AVATARS = {
    # Avatar 01 - Steph Curry
    "stephen curry": "01",
    "steph curry": "01",
    
    # Avatar 02 - Hugo Gonzalez
    "hugo gonzalez": "02",
    
    # Avatar 03 - Kawhi Leonard
    "kawhi leonard": "03",
    
    # Avatar 04 - James Harden / PJ Tucker
    "james harden": "04",
    "pj tucker": "04",
    "p.j. tucker": "04",
    
    # Avatar 05 - Jayson Tatum
    "jayson tatum": "05",
    
    # Avatar 06 - Brian Scalabrine
    "brian scalabrine": "06",
    "scalabrine": "06",
    
    # Avatar 07 - Russell Westbrook
    "russell westbrook": "07",
    "russ westbrook": "07",
    
    # Avatar 08 - Jason Terry
    "jason terry": "08",
    
    # Avatar 09 - Kelly Olynyk
    "kelly olynyk": "09",
    
    # Avatar 10 - Alex Caruso
    "alex caruso": "10",
    
    # Avatar 11 - Luka Doncic
    "luka doncic": "11",
    
    # Avatar 12 - Wendell Carter Jr.
    "wendell carter jr.": "12",
    "wendell carter": "12",
    
    # Avatar 13 - Chris Paul
    "chris paul": "13",
    
    # Avatar 14 - Nikola Jokic
    "nikola jokic": "14",
    "jokic": "14",
}


def get_priority_avatar(player_name: str) -> str | None:
    """Check if a player has a priority avatar assignment."""
    name_lower = player_name.lower().strip()
    return PRIORITY_PLAYER_AVATARS.get(name_lower)


# ═══════════════════════════════════════════════════════════════════════════════
# AI AVATAR SELECTION WITH VISION
# ═══════════════════════════════════════════════════════════════════════════════

def get_nba_headshot_url(player_id: int) -> str:
    """Get NBA player headshot URL."""
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"


def get_nfl_headshot_url(player_profile_url: str) -> str | None:
    """Extract NFL player headshot URL from their Pro Football Reference profile page."""
    try:
        from urllib.request import Request, urlopen
        from bs4 import BeautifulSoup
        
        req = Request(player_profile_url, headers={"User-Agent": "Mozilla/5.0"})
        html = urlopen(req, timeout=10).read().decode("utf-8")
        soup = BeautifulSoup(html, "lxml")
        
        # Find the player headshot in the media-item div
        media_item = soup.select_one("#meta .media-item img")
        if media_item and media_item.get("src"):
            return media_item["src"]
        
        # Fallback: look for any image in the meta section
        meta_img = soup.select_one("#meta img")
        if meta_img and meta_img.get("src"):
            return meta_img["src"]
            
    except Exception as e:
        print(f"⚠️ Could not get headshot URL: {e}")
    
    return None


def load_avatar_images_as_base64(team_abbr: str, is_nba: bool = True) -> dict:
    """Load avatar images and convert to base64 for vision API."""
    import base64
    
    avatars = {}
    
    if is_nba:
        avatar_dir = PROJECT_ROOT / "app" / "starting5" / "static" / team_abbr / "images"
        for i in range(1, 15):  # Avatars 01-14
            avatar_num = f"{i:02d}"
            avatar_path = avatar_dir / f"{team_abbr}_{avatar_num}.gif"
            if avatar_path.exists():
                with open(avatar_path, "rb") as f:
                    avatars[avatar_num] = base64.standard_b64encode(f.read()).decode("utf-8")
    else:
        avatar_dir = PROJECT_ROOT / "app" / "gridiron11" / "Sprites" / team_abbr / "images"
        for i in range(1, 11):  # Avatars 01-10
            avatar_num = f"{i:02d}"
            avatar_path = avatar_dir / f"{team_abbr.lower()}_{avatar_num}.png"
            if avatar_path.exists():
                with open(avatar_path, "rb") as f:
                    avatars[avatar_num] = base64.standard_b64encode(f.read()).decode("utf-8")
    
    return avatars


def get_ai_avatar_selection_with_vision(player_name: str, team_abbr: str, is_nba: bool = True, 
                                        player_id: int = None, headshot_url: str = None,
                                        used_avatars: set = None) -> str:
    """
    Use Claude Vision to compare player headshot with avatar options.
    Avoids reusing avatars unless necessary.
    
    Args:
        player_name: Player's name
        team_abbr: Team abbreviation (normalized)
        is_nba: True for NBA, False for NFL
        player_id: NBA player ID (for NBA headshots)
        headshot_url: Direct URL to player headshot (for NFL)
        used_avatars: Set of already-used avatar numbers
    """
    if used_avatars is None:
        used_avatars = set()
    try:
        import anthropic
        import base64
        import urllib.request
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"⚠️ No ANTHROPIC_API_KEY, using random avatar for {player_name}")
            max_avatar = 14 if is_nba else 10
            return f"{random.randint(1, max_avatar):02d}"
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Load avatar images
        all_avatars = load_avatar_images_as_base64(team_abbr, is_nba)
        if not all_avatars:
            print(f"⚠️ No avatars found for {team_abbr}, using random")
            max_avatar = 14 if is_nba else 10
            return f"{random.randint(1, max_avatar):02d}"
        
        # Filter out already-used avatars (unless we've used them all)
        available_avatars = {k: v for k, v in all_avatars.items() if k not in used_avatars}
        if not available_avatars:
            # All avatars used, allow reuse
            print(f"ℹ️ All avatars used, allowing reuse for {player_name}")
            available_avatars = all_avatars
        
        avatars = available_avatars
        
        # Get player headshot URL
        if is_nba and player_id:
            fetch_url = get_nba_headshot_url(player_id)
            media_type = "image/png"
        elif headshot_url:
            fetch_url = headshot_url
            # Determine media type from URL
            media_type = "image/jpeg" if headshot_url.lower().endswith(".jpg") else "image/png"
        else:
            print(f"⚠️ No headshot source for {player_name}, using random")
            return random.choice(list(avatars.keys()))
        
        # Fetch player headshot
        try:
            req = urllib.request.Request(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                player_image_data = base64.standard_b64encode(response.read()).decode("utf-8")
        except Exception as e:
            print(f"⚠️ Could not fetch headshot for {player_name}: {e}, using random")
            return random.choice(list(avatars.keys()))
        
        league = "NBA" if is_nba else "NFL"
        avatar_media_type = "image/gif" if is_nba else "image/png"
        
        # Build message with images
        content = [
            {
                "type": "text",
                "text": f"I need you to match this {league} player ({player_name}) to the best pixel art avatar based on their appearance (skin tone, facial hair, hair style, etc.).\n\nHere is the player's photo:"
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": player_image_data
                }
            },
            {
                "type": "text",
                "text": "Here are the available avatar options:"
            }
        ]
        
        # Add avatar images
        for avatar_num, avatar_data in sorted(avatars.items()):
            content.append({
                "type": "text",
                "text": f"Avatar #{avatar_num}:"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": avatar_media_type,
                    "data": avatar_data
                }
            })
        
        # Build available avatar list for prompt
        available_nums = sorted(avatars.keys())
        available_list = ", ".join(available_nums)
        
        content.append({
            "type": "text",
            "text": f"Which avatar best matches {player_name}'s appearance? Consider skin tone, hair style, and facial hair.\n\nAVAILABLE OPTIONS: {available_list}\n\nIMPORTANT: Respond with ONLY a two-digit number from the available options. No explanation, no words, just the number."
        })
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=5,
            messages=[{"role": "user", "content": content}]
        )
        
        response = message.content[0].text.strip()
        
        # Try to extract any number from the response
        match = re.search(r'(\d{1,2})', response)
        if match:
            num = match.group(1).zfill(2)
            if num in avatars:
                print(f"👁️ Vision AI matched {player_name} → Avatar {num}")
                return num
        
        # Check if response is directly a valid avatar
        if response in avatars:
            print(f"👁️ Vision AI matched {player_name} → Avatar {response}")
            return response
        
        print(f"⚠️ Could not parse vision response '{response[:50]}...', using random for {player_name}")
        
    except Exception as e:
        print(f"⚠️ Vision AI error for {player_name}: {e}, using random")
    
    # Fallback to random
    max_avatar = 14 if is_nba else 10
    return f"{random.randint(1, max_avatar):02d}"


def get_ai_avatar_selection(player_name: str, team: str, is_nba: bool = True, player_id: int = None, 
                            headshot_url: str = None, used_avatars: set = None) -> str:
    """
    Use Claude AI to select the most appropriate avatar for a player.
    If player_id or headshot_url is provided, uses vision API for better matching.
    Falls back to random selection if AI is unavailable.
    Tracks used_avatars to avoid duplicates when possible.
    """
    if used_avatars is None:
        used_avatars = set()
    
    # Use vision-based selection if we have image source
    if player_id or headshot_url:
        return get_ai_avatar_selection_with_vision(
            player_name, team, is_nba, 
            player_id=player_id, 
            headshot_url=headshot_url,
            used_avatars=used_avatars
        )
    
    # Fallback to text-based selection
    try:
        import anthropic
        
        max_avatar = 14 if is_nba else 10
        all_options = [f"{i:02d}" for i in range(1, max_avatar + 1)]
        
        # Filter out used avatars
        available_options = [opt for opt in all_options if opt not in used_avatars]
        if not available_options:
            print(f"ℹ️ All avatars used, allowing reuse for {player_name}")
            available_options = all_options
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"⚠️ No ANTHROPIC_API_KEY, using random avatar for {player_name}")
            return random.choice(available_options)
        
        client = anthropic.Anthropic(api_key=api_key)
        
        available_list = ", ".join(available_options)
        
        prompt = f"""You are helping select an 8-bit pixel art avatar for an {'NBA' if is_nba else 'NFL'} player.

Player: {player_name}
Team: {team}

Based on your knowledge of what {player_name} looks like (skin tone, facial hair, hair style), 
pick from these AVAILABLE options: {available_list}

General guide:
- 01-04: Darker skin tones with various hair/beard styles
- 05-08: Medium skin tones
- 09-12: Various styles
- 13-14: Light skin tones

Reply with ONLY the two-digit number (e.g., "07"). Nothing else."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = message.content[0].text.strip()
        
        # Validate response is from available options
        match = re.search(r'(\d{1,2})', response)
        if match:
            result = f"{int(match.group(1)):02d}"
            if result in available_options:
                print(f"🤖 AI selected avatar {result} for {player_name}")
                return result
        
        print(f"⚠️ Invalid AI response '{response}', using random for {player_name}")
        return random.choice(available_options)
        
    except Exception as e:
        print(f"⚠️ AI error for {player_name}: {e}, using random")
    
    # Fallback to random from available options
    max_avatar = 14 if is_nba else 10
    all_opts = [f"{i:02d}" for i in range(1, max_avatar + 1)]
    available = [o for o in all_opts if o not in used_avatars] or all_opts
    return random.choice(available)


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
                    home_abbr_raw = df[df["TEAM_ID"] == home_id]["TEAM_ABBREVIATION"].iloc[0]
                    away_abbr_raw = df[df["TEAM_ID"] == away_id]["TEAM_ABBREVIATION"].iloc[0]
                    
                    # Normalize team abbreviations to match avatar directories
                    home_abbr = normalize_team_abbrev(home_abbr_raw)
                    away_abbr = normalize_team_abbrev(away_abbr_raw)
                    
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
                        
                        team_abbr_raw = team_starters["TEAM_ABBREVIATION"].iloc[0]
                        team_abbr = normalize_team_abbrev(team_abbr_raw)
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
                        
                        used_avatars = set()  # Track used avatars to avoid duplicates
                        player_avatars = {}   # Store avatar assignments
                        
                        # PHASE 1: Assign priority players their guaranteed avatars first
                        for pr in player_rows:
                            name = pr["name"]
                            priority_avatar = get_priority_avatar(name)
                            if priority_avatar and priority_avatar not in used_avatars:
                                player_avatars[name] = priority_avatar
                                used_avatars.add(priority_avatar)
                                print(f"⭐ Priority match: {name} → Avatar {priority_avatar}")
                        
                        # PHASE 2: AI selection for remaining players
                        for pr in player_rows:
                            row = pr["row"]
                            name = pr["name"]
                            
                            # Check if already assigned in priority phase
                            if name in player_avatars:
                                avatar = player_avatars[name]
                            else:
                                # AI avatar selection with vision (avoids duplicates)
                                avatar = get_ai_avatar_selection(name, team_abbr, is_nba=True, player_id=pr["player_id"], used_avatars=used_avatars)
                                used_avatars.add(avatar)  # Mark as used
                            
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
                        
                        generated += 1
                        progress = f"[{generated}/{count}]"
                        bar_filled = int((generated / count) * 20)
                        bar = "█" * bar_filled + "░" * (20 - bar_filled)
                        print(f"✅ {progress} {bar} Saved: {fname}")
                        
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

# Realistic browser headers to avoid bot detection
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


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
            req = Request(url, headers=BROWSER_HEADERS)
            time.sleep(random.uniform(1, 2))  # Be respectful
            html = urlopen(req, timeout=15).read().decode("utf-8")
            soup = BeautifulSoup(html, "lxml")
            
            boxscore_links = soup.select("table#games a[href*='/boxscores/']")
            if not boxscore_links:
                continue
            
            boxscore_urls = [BASE_URL + link["href"] for link in boxscore_links]
            random.shuffle(boxscore_urls)
            
            for boxscore_url in boxscore_urls[:5]:  # Try up to 5 games
                time.sleep(random.uniform(2, 4))
                
                try:
                    req = Request(boxscore_url, headers=BROWSER_HEADERS)
                    html = urlopen(req, timeout=15).read().decode("utf-8")
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
                    used_avatars = set()  # Track used avatars to avoid duplicates
                    
                    for i, player in enumerate(players[:6]):
                        time.sleep(random.uniform(2, 4))
                        
                        try:
                            req = Request(player["url"], headers=BROWSER_HEADERS)
                            html = urlopen(req, timeout=15).read().decode("utf-8")
                            soup = BeautifulSoup(html, "lxml")
                            
                            meta = soup.find(id="meta")
                            college = "Unknown"
                            headshot_url = None
                            
                            if meta:
                                # Get college
                                label = meta.find("strong", string=lambda s: s and s.strip().startswith("College"))
                                if label:
                                    for node in label.next_siblings:
                                        if getattr(node, "name", None) == "br":
                                            break
                                        if getattr(node, "name", None) == "a":
                                            href = node.get("href", "")
                                            if href.startswith("/schools/") and "high_schools" not in href:
                                                college = node.get_text(strip=True)
                                
                                # Get headshot image
                                media_item = meta.select_one(".media-item img")
                                if media_item and media_item.get("src"):
                                    headshot_url = media_item["src"]
                            
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
                            
                            # AI avatar selection with vision
                            team_normalized = normalize_team_abbrev(team.upper())
                            avatar = get_ai_avatar_selection(
                                player["name"], team_normalized, is_nba=False,
                                headshot_url=headshot_url, used_avatars=used_avatars
                            )
                            used_avatars.add(avatar)  # Mark as used
                            
                            quiz_players.append({
                                "name": player["name"],
                                "position": f"{player['position']}{i+1}",
                                "college": matched_college,
                                "player_url": player["url"],
                                "team_abbrev": team_normalized,
                                "avatar": avatar
                            })
                            
                            print(f"✅ {player['name']}: {matched_college} (Avatar {avatar})")
                            
                        except Exception as e:
                            print(f"⚠️ Error getting college for {player['name']}: {e}")
                            all_valid = False
                            break
                    
                    if not all_valid or len(quiz_players) < 4:
                        continue
                    
                    # Save quiz
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    team_normalized = normalize_team_abbrev(team.upper())
                    quiz_data = {
                        "team": team_normalized,
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
