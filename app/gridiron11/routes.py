from __future__ import annotations
from flask import Blueprint, render_template, jsonify, url_for, request, send_from_directory, redirect
from flask_login import current_user
import json, os, pathlib, typing as t, random, glob, csv

bp = Blueprint('gridiron11', __name__, 
              template_folder='templates',
              static_folder='static',
              static_url_path='/gridiron11/static')

# Get the project root directory (two levels up from this module)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Quiz files directory (using new organized quiz folder structure)
CURRENT_QUIZ_DIR = os.path.join(PROJECT_ROOT, "quizzes", "gridiron11", "current")
PRELOADED_QUIZ_DIR = os.path.join(PROJECT_ROOT, "quizzes", "gridiron11", "preloaded")
ARCHIVE_QUIZ_DIR = os.path.join(PROJECT_ROOT, "quizzes", "gridiron11", "archive")
CFB_DATA_FILE = os.path.join(PROJECT_ROOT, "app", "gridiron11", "CFB", "cbb25.csv")

# Skill positions for the new game (6 players total)
SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]

# Legacy positions for old Gridiron11 game (now called Skill Positions)
LEGACY_FIXED_POSITIONS = ["QB", "RB", "C", "LT", "LG", "RG", "RT"]
LEGACY_SKILL_POSITIONS = ["WR", "TE", "FB"]

# All offensive positions (filter out defensive players)
OFFENSIVE_POSITIONS = set(LEGACY_FIXED_POSITIONS + LEGACY_SKILL_POSITIONS)

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
    
    # Strip numbers from positions (WR1 -> WR, TE2 -> TE, FB1 -> FB)
    import re
    p = re.sub(r'\d+$', '', p)
    
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

def get_skill_positions_payload() -> dict:
    """Get payload for the new Skill Positions game with 6 players."""
    try:
        quiz_file = get_current_quiz_file()
        
        with open(quiz_file, 'r') as f:
            data = json.load(f)
        
        # Filter to only skill positions (handle numbered positions like QB1, WR1, etc.)
        skill_players = []
        team_abbrev = data.get("team", "").upper()
        
        for i, player in enumerate(data.get("players", [])):
            position = player.get("position", "")
            # Extract base position (QB1 -> QB, WR2 -> WR, etc.)
            base_position = ''.join([c for c in position if c.isalpha()])
            if base_position in SKILL_POSITIONS:
                # Assign avatar/sprite based on player index (1-10)
                avatar_num = str(i + 1).zfill(2)  # 01, 02, 03, etc.
                
                skill_players.append({
                    "name": player["name"],
                    "position": player["position"],
                    "college": player["college"],
                    "team_abbrev": team_abbrev,
                    "avatar": avatar_num
                })
        
        # Ensure we have exactly 6 players (or close to it)
        if len(skill_players) < 4:
            print(f"⚠️ Only found {len(skill_players)} skill players, need at least 4")
        
        # Limit to 6 players max
        skill_players = skill_players[:6]
        
        return {
            "players": skill_players,
            "quiz_file": os.path.basename(quiz_file),
            "game_info": data.get("game_info", "NFL Skill Positions Quiz"),
            "total_players": len(skill_players)
        }
        
    except Exception as e:
        print(f"Error loading skill positions data: {e}")
        return {
            "players": [],
            "quiz_file": "error",
            "game_info": "Error loading game",
            "total_players": 0
        }

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
    """New Skill Positions quiz page"""
    from app.utils.daily_limits import has_played_today
    
    # Check if user already played today
    has_played_today_flag, _ = has_played_today('skill_positions')
    
    payload = get_skill_positions_payload()
    college_data = load_college_data()
    return render_template("skill_positions.html",
                           game_data=payload,
                           colleges=college_data["colleges"],
                           already_played_today=has_played_today_flag)

@bp.route("/results")
def show_results():
    """Show Skill Positions results with animated cards"""
    # Get results from URL parameters
    results_data = request.args.get('data')
    if results_data:
        try:
            import json
            import base64
            # Decode the base64 encoded JSON data
            decoded_data = base64.b64decode(results_data).decode('utf-8')
            data = json.loads(decoded_data)
            
            return render_template("skill_positions_results.html",
                                 players=data['players'],
                                 results=data['results'], 
                                 score=data['score'],
                                 total_players=data['total_players'])
        except Exception as e:
            print(f"Error decoding results data: {e}")
    
    # If no valid data, redirect to quiz
    return redirect(url_for('gridiron11.show_quiz'))

@bp.route("/legacy")
def show_legacy_quiz():
    """Legacy Skill Positions quiz page (formerly Gridiron11)"""
    payload = get_lineup_payload()
    college_data = load_college_data()
    return render_template("game.html",
                           lineup_by_pos=payload["lineup"]["by_pos"],
                           order=payload["lineup"]["order"],
                           answers=payload["answers"],
                           quiz_file=payload["quiz_file"],
                           colleges=college_data["names"],
                           conferences=college_data["conferences"])

@bp.route("/sprites/<team>/<path:filename>")
def serve_sprites(team, filename):
    """Serve team sprite images"""
    sprites_dir = os.path.join(PROJECT_ROOT, "app", "gridiron11", "Sprites", team.upper())
    return send_from_directory(sprites_dir, filename)

@bp.route("/api/lineup")
def api_lineup():
    """API endpoint for lineup data"""
    return jsonify(get_lineup_payload())

@bp.route("/api/submit_skill_positions_score", methods=['POST'])
def submit_skill_positions_score():
    """API endpoint to submit Skill Positions game score"""
    from app.utils.daily_limits import has_played_today, mark_played_today
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check daily limit
    has_played, _ = has_played_today('skill_positions')
    if has_played:
        return jsonify({
            'error': 'You have already played Skill Positions today. Come back tomorrow for a new challenge!',
            'already_played': True
        }), 429
    
    score = data.get('score', 0)
    total = data.get('total', 5)
    quiz_file = data.get('quiz_file', 'unknown')
    time_taken = data.get('time_taken')
    player_results = data.get('player_results', [])
    
    # Save score if user is logged in
    if current_user.is_authenticated:
        try:
            current_user.save_game_score(
                game_type='skill_positions',
                quiz_id=quiz_file,
                score=score,
                max_points=total,
                time_taken=time_taken,
                metadata={
                    'correct_answers': score,
                    'total_questions': total,
                    'percentage': round((score / total) * 100, 1) if total > 0 else 0,
                    'quiz_type': 'skill_positions',
                    'player_results': player_results
                }
            )
            # Mark as played today
            mark_played_today('skill_positions')
            return jsonify({'success': True, 'message': 'Score saved successfully'})
        except Exception as e:
            return jsonify({'error': f'Failed to save score: {str(e)}'}), 500
    else:
        # Mark as played today even for guests
        mark_played_today('skill_positions')
        return jsonify({'success': True, 'message': 'Game completed! Login to save your scores.'})

@bp.route("/api/submit_score", methods=['POST'])
def submit_score():
    """API endpoint to submit legacy game score"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    score = data.get('score', 0)
    total = data.get('total', 11)
    quiz_file = data.get('quiz_file', 'unknown')
    time_taken = data.get('time_taken')
    
    # Save score if user is logged in
    if current_user.is_authenticated:
        try:
            current_user.save_game_score(
                game_type='gridiron11',
                quiz_id=quiz_file,
                score=score,
                max_points=total,
                time_taken=time_taken,
                metadata={
                    'correct_answers': score,
                    'total_questions': total,
                    'percentage': round((score / total) * 100, 1) if total > 0 else 0,
                    'quiz_type': 'formation'
                }
            )
            return jsonify({'success': True, 'message': 'Score saved successfully'})
        except Exception as e:
            return jsonify({'error': f'Failed to save score: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Login required to save scores'})

@bp.route("/api/user_stats")
def user_stats():
    """API endpoint to get user's Skill Positions stats"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401
    
    try:
        scores = current_user.get_game_scores(game_type='gridiron11', limit=50)
        
        if not scores:
            return jsonify({
                'total_games': 0,
                'avg_score': 0,
                'best_score': 0,
                'total_points': 0,
                'recent_scores': []
            })
        
        total_games = len(scores)
        avg_score = sum(s['score'] for s in scores) / total_games
        best_score = max(s['score'] for s in scores)
        total_points = sum(s['score'] for s in scores)
        
        return jsonify({
            'total_games': total_games,
            'avg_score': round(avg_score, 2),
            'best_score': best_score,
            'total_points': total_points,
            'recent_scores': scores[:10]  # Last 10 games
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500
