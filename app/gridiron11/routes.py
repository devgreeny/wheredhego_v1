from __future__ import annotations
from flask import Blueprint, render_template, jsonify, url_for
import json, os, pathlib, typing as t, random, glob, csv

bp = Blueprint('gridiron11', __name__, 
              template_folder='templates',
              static_folder='static',
              static_url_path='/gridiron11/static')

# Get the directory where this module is located
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Quiz files directory (relative to this module)
CURRENT_QUIZ_DIR = os.path.join(PROJECT_ROOT, "static", "current_quiz")
PRELOADED_QUIZ_DIR = os.path.join(PROJECT_ROOT, "preloaded_quizzes")
CFB_DATA_FILE = os.path.join(PROJECT_ROOT, "CFB", "cbb25.csv")

# Fixed positions that are always present (7 players)
FIXED_POSITIONS = ["QB", "RB", "C", "LT", "LG", "RG", "RT"]

# Skill positions that vary by formation (4 players total)
SKILL_POSITIONS = ["WR", "TE", "FB"]

# All offensive positions (filter out defensive players)
OFFENSIVE_POSITIONS = set(FIXED_POSITIONS + SKILL_POSITIONS)

def load_college_data() -> dict:
    """Load college data from CSV file and return structured data."""
    colleges = []
    conferences = {}
    
    try:
        with open(CFB_DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                common_name = row.get('Common name', '').strip()
                conference = row.get('Primary', '').strip()
                
                if common_name and conference:
                    college_data = {
                        'name': common_name,
                        'conference': conference,
                        'school': row.get('School', '').strip(),
                        'nickname': row.get('Nickname', '').strip(),
                        'subdivision': row.get('Subdivision', '').strip()
                    }
                    colleges.append(college_data)
                    
                    # Group by conference
                    if conference not in conferences:
                        conferences[conference] = []
                    conferences[conference].append(common_name)
        
        # Sort colleges alphabetically
        colleges.sort(key=lambda x: x['name'])
        
        # Sort conferences
        for conf_teams in conferences.values():
            conf_teams.sort()
            
        print(f"📚 Loaded {len(colleges)} colleges from {len(conferences)} conferences")
        return {
            'colleges': colleges,
            'conferences': conferences,
            'names': [c['name'] for c in colleges]
        }
        
    except Exception as e:
        print(f"Error loading college data: {e}")
        return {'colleges': [], 'conferences': {}, 'names': []}

def get_current_quiz_file() -> str:
    """Get the active quiz file from current_quiz directory, fallback to random preloaded quiz."""
    # First, try to get a quiz from current_quiz directory
    current_quiz_pattern = os.path.join(CURRENT_QUIZ_DIR, "*.json")
    current_quiz_files = glob.glob(current_quiz_pattern)
    
    if current_quiz_files:
        # Use the first (and presumably only) quiz in current_quiz
        selected_file = current_quiz_files[0]
        print(f"Using current quiz file: {os.path.basename(selected_file)}")
        return selected_file
    
    # Fallback: randomly select from preloaded quizzes
    preloaded_quiz_pattern = os.path.join(PRELOADED_QUIZ_DIR, "*.json")
    preloaded_quiz_files = glob.glob(preloaded_quiz_pattern)
    
    if not preloaded_quiz_files:
        raise FileNotFoundError(f"No JSON files found in either {CURRENT_QUIZ_DIR} or {PRELOADED_QUIZ_DIR}")
    
    selected_file = random.choice(preloaded_quiz_files)
    print(f"No current quiz found, using random preloaded quiz: {os.path.basename(selected_file)}")
    return selected_file

def normalize_pos(p: str) -> str:
    if not p: return ""
    p = p.strip().upper().replace(".", "")
    synonyms = {
        "HB":"RB","TB":"RB","HALFBACK":"RB","TAILBACK":"RB",
        "OC":"C","CENTER":"C",
        "LEFT TACKLE":"LT","RIGHT TACKLE":"RT",
        "LEFT GUARD":"LG","RIGHT GUARD":"RG",
        "WIDE RECEIVER":"WR","SPLIT END":"WR","FLANKER":"WR",
        "TIGHT END":"TE","FULLBACK":"FB","QUARTERBACK":"QB",
    }
    return synonyms.get(p, p)

def load_players(path: str) -> t.List[dict]:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Lineup JSON not found at: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("players","data","items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        if all(isinstance(v, dict) for v in data.values()):
            return list(data.values())
        raise ValueError("JSON structure not recognized. Expect a list of player objects.")
    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of player objects.")
    return data

def build_lineup(players: t.List[dict]) -> dict:
    """Build a flexible 11-player formation from available players."""
    
    # Group players by position (only offensive positions)
    buckets: dict[str, list] = {
        "WR": [], "TE": [], "RB": [], "FB": [], "QB": [], 
        "LT": [], "LG": [], "C": [], "RG": [], "RT": []
    }
    
    # Filter for offensive players only
    offensive_players = []
    for pl in players:
        pos = normalize_pos(pl.get("position", ""))
        if pos in OFFENSIVE_POSITIONS:
            offensive_players.append(pl)
            buckets[pos].append(pl)
    
    print(f"📊 Found {len(offensive_players)} offensive players out of {len(players)} total")
    
    lineup: dict[str, dict] = {}
    formation_order = []
    
    # Step 1: Assign fixed positions (7 players) - these are always present
    for pos in FIXED_POSITIONS:
        if buckets[pos]:
            lineup[pos] = buckets[pos][0]
            formation_order.append(pos)
        else:
            print(f"⚠️  Warning: No {pos} found in lineup")
    
    # Step 2: Assign skill positions (4 players) - flexible based on available players
    skill_slots_filled = 0
    target_skill_slots = 4
    
    # Priority order for skill positions (WR first, then TE, then FB)
    skill_priority = [
        ("WR", buckets["WR"]),
        ("TE", buckets["TE"]), 
        ("FB", buckets["FB"])
    ]
    
    # Assign skill positions until we have 4 or run out of players
    for pos_type, available_players in skill_priority:
        for i, player in enumerate(available_players):
            if skill_slots_filled >= target_skill_slots:
                break
                
            # Create numbered position (WR1, WR2, TE1, TE2, etc.)
            position_name = f"{pos_type}{i + 1}"
            lineup[position_name] = player
            formation_order.append(position_name)
            skill_slots_filled += 1
    
    # Log formation summary
    total_players = len(lineup)
    wr_count = len([p for p in formation_order if p.startswith("WR")])
    te_count = len([p for p in formation_order if p.startswith("TE")])
    fb_count = len([p for p in formation_order if p.startswith("FB")])
    fixed_count = len([p for p in formation_order if p in FIXED_POSITIONS])
    
    print(f"🏈 Formation: {total_players} players - {wr_count}WR, {te_count}TE, {fb_count}FB + {fixed_count} fixed positions")
    
    if total_players < 11:
        print(f"⚠️  Incomplete lineup: {11 - total_players} players missing")
        missing_fixed = [pos for pos in FIXED_POSITIONS if pos not in lineup]
        if missing_fixed:
            print(f"   Missing fixed positions: {missing_fixed}")
    
    return {"order": formation_order, "by_pos": lineup}

def get_lineup_payload() -> dict:
    # Use environment variable if set, otherwise get current quiz file
    json_path = os.environ.get("GRIDIRON_JSON")
    if not json_path:
        json_path = get_current_quiz_file()
    
    players = load_players(json_path)
    lineup = build_lineup(players)
    answers = {pos: lineup["by_pos"][pos].get("college","").strip() for pos in lineup["order"]}
    
    # Extract team info from filename (e.g., "players_20250816_204444.json")
    filename = os.path.basename(json_path)
    
    return {
        "lineup": lineup, 
        "answers": answers, 
        "quiz_file": filename
    }

@bp.route("/")
def home():
    """Redirect to the main quiz"""
    from flask import redirect
    return redirect(url_for("gridiron11.show_quiz"))

@bp.route("/quiz")
def show_quiz():
    """Main quiz page"""
    payload = get_lineup_payload()
    college_data = load_college_data()
    return render_template("game.html",
                           lineup_by_pos=payload["lineup"]["by_pos"],
                           order=payload["lineup"]["order"],
                           answers=payload["answers"],
                           quiz_file=payload["quiz_file"],
                           colleges=college_data["names"],
                           conferences=college_data["conferences"])

@bp.route("/api/lineup")
def api_lineup():
    """API endpoint for lineup data"""
    return jsonify(get_lineup_payload())
