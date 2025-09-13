import os, json, random
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    make_response,
    session,
    current_app,
)
# Removed authentication requirements
from datetime import datetime
from .models import db, GuessLog, ScoreLog
from sqlalchemy import func

bp = Blueprint('starting5', __name__, 
              template_folder='templates',
              static_folder='static',
              static_url_path='/starting5/static')

# Paths for quiz data (using new organized quiz folder structure)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CURRENT_DIR  = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "current")
BONUS_DIR    = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "bonus")
ARCHIVE_DIR  = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "archive")
PRELOADED_DIR = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "preloaded")
CBB_CSV      = os.path.join(PROJECT_ROOT, "app", "starting5", "static", "json", "cbb25.csv")

def load_confs():
    """Return a mapping of college names to conferences and a sorted list of names."""
    import csv
    d = {}
    try:
        with open(CBB_CSV, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)

            # Determine which columns hold the team name and conference
            name_idx = None
            conf_idx = None
            for i, col in enumerate(header):
                lc = col.strip().lower()
                if lc in {"common name", "common_name"}:
                    name_idx = i
                if lc == "conference":
                    conf_idx = i

            if name_idx is None:
                name_idx = 1 if len(header) > 1 else 0
            if conf_idx is None:
                conf_idx = len(header) - 1

            for row in reader:
                if not row:
                    continue
                # Ensure indices exist
                if name_idx >= len(row) or conf_idx >= len(row):
                    continue

                name = row[name_idx].strip()
                conf = row[conf_idx].strip() or "Other"
                if name:
                    d[name] = conf
    except FileNotFoundError:
        current_app.logger.warning(f"CSV file not found: {CBB_CSV}")
        
    return d, sorted(d.keys())

def normalise_usc(p, confs):
    if p.get("school") == "Southern California":
        p["school"]     = "USC"
        p["conference"] = confs.get("USC", "P12")

def ensure_avatar_fields(p):
    """Ensure team_abbrev and avatar are present and normalised."""
    team = p.get("team_abbrev") or p.get("team_abbr")
    avatar = p.get("avatar")
    path = p.get("avatarPath")

    if path:
        fname = os.path.basename(path)
        base = os.path.splitext(fname)[0]
        parts = base.split("_")
        if len(parts) == 2:
            team = team or parts[0]
            avatar = parts[1]
        elif parts:
            avatar = parts[-1]

    if isinstance(avatar, str) and "_" in avatar:
        # handle values like "BKN_11"
        avatar_parts = avatar.split("_")
        if len(avatar_parts) == 2:
            if not team:
                team = avatar_parts[0]
            avatar = avatar_parts[1]

    if avatar is not None:
        try:
            avatar = str(int(avatar)).zfill(2)
        except ValueError:
            avatar = str(avatar).zfill(2)

    if team:
        p["team_abbrev"] = team
    if avatar:
        p["avatar"] = avatar

    # Remove obsolete key if present
    if "avatarPath" in p:
        p.pop("avatarPath", None)

def performance_text(score, max_points):
    if score >= max_points:
        return "\U0001F410 Perfect game!"  # 🐐
    elif score >= 4:
        return "\U0001F525 You crushed it today!"
    elif score >= 3:
        return "\U0001F9E0 Solid effort, keep going!"
    elif score >= 2:
        return "\U0001F913 Not bad, study those rosters!"
    else:
        return "\U0001F9CA Cold start – better luck tomorrow!"

def calc_streak(user_id):
    """Return the user's current daily streak."""
    logs = (
        ScoreLog.query.filter_by(user_id=user_id)
        .order_by(ScoreLog.timestamp.desc())
        .all()
    )
    if not logs:
        return 0
    streak = 1
    prev = logs[0].timestamp.date()
    for log in logs[1:]:
        d = log.timestamp.date()
        if d == prev:
            continue
        if (prev - d).days == 1:
            streak += 1
            prev = d
        else:
            break
    return streak

@bp.route("/")
def home():
    return redirect(url_for("starting5.show_quiz"))

@bp.route("/quiz", methods=["GET", "POST"])
def show_quiz():
    conf_map, colleges = load_confs()
    quiz_key = None
    is_bonus_quiz = False

    if request.method == "POST":
        # read quiz_json_path from the form and grade it
        qp = request.form.get("quiz_json_path", "")
        if not qp or not os.path.isfile(qp):
            return redirect(url_for("starting5.show_quiz"))

        with open(qp, encoding="utf-8") as f:
            data = json.load(f)
        for pl in data["players"]:
            normalise_usc(pl, conf_map)

        quiz_key = os.path.basename(qp)
        is_bonus_quiz = qp.startswith(BONUS_DIR)
        time_taken = request.form.get("time_taken", type=int)

        # Check if already played (guest mode using session)
        sid_key = f"guest_score_{quiz_key}"
        sid = session.get(sid_key)
        existing_score = None
        if sid:
            existing_score = ScoreLog.query.filter(
                ScoreLog.id == sid,
                ScoreLog.quiz_id == quiz_key,
            ).first()

        results, correct_answers, share_statuses = [], [], []
        score, max_points = 0.0, 0.0

        for idx, p in enumerate(data["players"]):
            name         = p["name"]
            school_type  = p["school_type"]
            team_name    = p["school"]
            country      = p["country"]
            guess        = request.form.get(name, "").strip()
            used_hint    = request.form.get(f"hint_used_{idx}", "0") == "1"

            is_correct = False
            pts = 0.0

            if school_type == "College":
                max_points += 1.0
                if guess.lower() == team_name.lower():
                    pts = 0.75 if used_hint else 1.0
                    is_correct = True
                score += pts
                results.append("✅" if is_correct else "❌")
                share_statuses.append("🟨 -- Used Hint" if (is_correct and used_hint) else ("✅ -- Correct" if is_correct else "❌ -- Missed"))
                correct_answers.append(f"I played for {team_name}")

            else:
                max_points += 1.0
                if guess.lower() == team_name.lower():
                    pts = 1.0
                    is_correct = True
                elif guess.lower() == country.lower():
                    pts = 0.75
                    is_correct = True
                score += pts
                results.append("✅" if is_correct else "❌")
                share_statuses.append("🟨 -- Used Hint" if (is_correct and used_hint) else ("✅ -- Correct" if is_correct else "❌ -- Missed"))
                correct_answers.append(f"I am from {country} and played for {team_name}")

        # Save score to database (guest mode with no user_id)
        if not existing_score:
            score_entry = ScoreLog(
                quiz_id=quiz_key,
                user_id=None,  # Guest mode
                score=score,
                max_points=max_points,
                time_taken=time_taken,
            )
            db.session.add(score_entry)
            db.session.commit()
            session[sid_key] = score_entry.id
        else:
            # Already played, use existing score
            score = existing_score.score
            max_points = existing_score.max_points
            time_taken = existing_score.time_taken
        
        streak = 0  # No streak tracking in guest mode

        # Calculate percentile based on all scores for this quiz
        scores = [s.score for s in ScoreLog.query.filter_by(quiz_id=quiz_key).all()]
        percentile = 0
        if scores:
            scores.sort()
            rank = sum(s <= score for s in scores)
            percentile = round(100 * rank / len(scores))
        
        perf_text = performance_text(score, max_points)

        date_str = datetime.utcnow().strftime("%B %-d, %Y")
        share_lines = [
            f"\U0001F3C0 Starting5 Puzzle – {date_str}",
            f"\U0001F4C8 Score: {round(score,2)}/{round(max_points,2)}",
            "",
        ]
        for pl, status in zip(data["players"], share_statuses):
            share_lines.append(f"\uD83D\uDD39 {pl['position']}: {status}")
        share_lines += ["", perf_text, "Play now: wheredhego.com/starting5"]
        share_message = "\n".join(share_lines)

        if is_bonus_quiz:
            session.pop("bonus_unlocked", None)

        return render_template(
            "results.html",
            data            = data,
            colleges        = colleges,
            college_confs   = conf_map,
            results         = results,
            correct_answers = correct_answers,
            score           = round(score, 2),
            max_points      = round(max_points, 2),
            quiz_json_path  = qp,
            quiz_id        = quiz_key,
            percentile     = percentile,
            streak          = streak,
        share_message   = share_message,
        performance_text= perf_text,
        leaderboard     = [],
        show_leaderboard= False,
            show_share      = not is_bonus_quiz,
        already_played  = False,
        archive_quizzes = [],
        )

    # GET: serve whatever JSON is in CURRENT_DIR (there should be exactly one file)
    # Ensure current_quiz folder exists (if not, create it)
    os.makedirs(CURRENT_DIR, exist_ok=True)

    # Look for any .json in CURRENT_DIR
    current_files = [f for f in os.listdir(CURRENT_DIR) if f.lower().endswith(".json")]
    if not current_files:
        # Fall back to preloaded quizzes
        os.makedirs(PRELOADED_DIR, exist_ok=True)
        preloaded_files = [f for f in os.listdir(PRELOADED_DIR) if f.lower().endswith(".json")]
        if not preloaded_files:
            return "❌ No quiz loaded. Please add quiz files.", 500
        
        # Pick a random preloaded quiz
        quiz_filename = random.choice(preloaded_files)
        quiz_path = os.path.join(PRELOADED_DIR, quiz_filename)
    else:
        # We assume only ONE file should be there at a time
        quiz_filename = current_files[0]
        quiz_path = os.path.join(CURRENT_DIR, quiz_filename)

    quiz_key = os.path.basename(quiz_path)

    with open(quiz_path, encoding="utf-8") as f:
        data = json.load(f)
    for pl in data["players"]:
        normalise_usc(pl, conf_map)
        ensure_avatar_fields(pl)

    streak = 0  # No streak tracking in guest mode
    
    return render_template(
        "quiz.html",
        data            = data,
        colleges        = colleges,
        college_confs   = conf_map,
        results         = None,
        correct_answers = [],
        score           = None,
        max_points      = None,
        quiz_json_path  = quiz_path,
        quiz_id        = quiz_key,
        streak         = streak,
        share_message  = None,
        performance_text = None,
        leaderboard = [],
        show_leaderboard= False,
        show_share      = True,
        already_played  = False,
        archive_quizzes = [],
    )
