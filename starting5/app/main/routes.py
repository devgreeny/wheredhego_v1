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
from flask_login import current_user, login_required
from datetime import datetime
from app.models import db, GuessLog, ScoreLog
from sqlalchemy import func

bp = Blueprint("main", __name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CURRENT_DIR  = os.path.join(PROJECT_ROOT, "app", "static", "current_quiz")
BONUS_DIR    = os.path.join(PROJECT_ROOT, "app", "static", "bonus_quiz")
ARCHIVE_DIR  = os.path.join(PROJECT_ROOT, "app", "static", "archive_quizzes")
PRELOADED_DIR = os.path.join(PROJECT_ROOT, "app", "static", "preloaded_quizzes")
CBB_CSV      = os.path.join(PROJECT_ROOT, "app", "static", "json", "cbb25.csv")

def load_confs():
    """Return a mapping of college names to conferences and a sorted list of names.

    The CSV may come in different shapes. If a header containing "common name"
    or "conference" exists, those columns are used. Otherwise we fall back to
    using the second column for the name and the last column for the conference.
    """

    import csv

    d = {}
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
    return d, sorted(d.keys())


def normalise_usc(p, confs):
    if p.get("school") == "Southern California":
        p["school"]     = "USC"
        p["conference"] = confs.get("USC", "P12")

def ensure_avatar_fields(p):
    """Ensure ``team_abbrev`` and ``avatar`` are present and normalised.

    Older quiz JSON files may contain an ``avatarPath`` with an absolute path or
    an ``avatar`` value like ``"BKN_11"``. This helper extracts the team
    abbreviation and zero padded avatar number while stripping any filesystem
    paths.
    """

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

def ordinal(n: int) -> str:
    """Return the ordinal suffix for a given day number."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def get_archive_list():
    items = []
    for fname in os.listdir(ARCHIVE_DIR):
        if not fname.lower().endswith(".json"):
            continue
        path = os.path.join(ARCHIVE_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            date_str = data.get("game_date")
            team = data.get("team_abbr", "")
            dt = None
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%b %d, %Y")
                except ValueError:
                    pass
            if dt:
                date_label = f"{dt.strftime('%b')} {ordinal(dt.day)}, {dt.year}"
            else:
                date_label = date_str or fname
            label = f"{date_label} -- {team} Starting 5"
            items.append((dt or datetime.min, fname, label))
        except Exception:
            continue
    items.sort(key=lambda x: x[0], reverse=True)
    return [{"id": f, "label": lbl} for _, f, lbl in items]

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

def get_leaderboard(quiz_id):
    """Return all results for a quiz, labeling guests sequentially."""
    from app.models import User  # local import to avoid circular deps

    q = (
        db.session.query(
            User.username,
            ScoreLog.score,
            ScoreLog.max_points,
            ScoreLog.time_taken,
            ScoreLog.user_id,
        )
        .outerjoin(User, User.id == ScoreLog.user_id)
        .filter(ScoreLog.quiz_id == quiz_id)
        .filter(ScoreLog.user_id.isnot(None))
        .order_by(ScoreLog.score.desc(), ScoreLog.time_taken.asc())
        .all()
    )

    guest_count = 1
    board = []
    for r in q:
        username = r.username
        if not username:
            username = f"Guest {guest_count}"
            guest_count += 1
        board.append(
            {
                "username": username,
                "score": round(r.score, 2),
                "max_points": round(r.max_points, 2) if r.max_points is not None else None,
                "time_taken": r.time_taken,
            }
        )
    return board

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
    return redirect(url_for("main.show_quiz"))


@bp.route("/archive")
@login_required
def archive_index():
    """Display available past quizzes for logged-in users."""
    quizzes = get_archive_list()
    return render_template("archive.html", quizzes=quizzes)


@bp.route("/archive/<quiz_id>", methods=["GET", "POST"])
@login_required
def play_archived_quiz(quiz_id):
    conf_map, colleges = load_confs()
    quiz_path = os.path.join(ARCHIVE_DIR, quiz_id)
    if not os.path.isfile(quiz_path):
        return redirect(url_for("main.archive_index"))

    quiz_key = os.path.basename(quiz_path)

    if request.method == "POST":
        qp = request.form.get("quiz_json_path", "")
        if not qp or not os.path.isfile(qp):
            return redirect(url_for("main.play_archived_quiz", quiz_id=quiz_id))

        quiz_key = os.path.basename(qp)

        with open(qp, encoding="utf-8") as f:
            data = json.load(f)
        for pl in data["players"]:
            normalise_usc(pl, conf_map)

        time_taken = request.form.get("time_taken", type=int)

        existing_score = ScoreLog.query.filter_by(user_id=current_user.id, quiz_id=quiz_key).first()

        results, correct_answers, share_statuses = [], [], []
        score, max_points = 0.0, 0.0

        for idx, p in enumerate(data["players"]):
            name        = p["name"]
            school_type = p["school_type"]
            team_name   = p["school"]
            country     = p["country"]
            guess       = request.form.get(name, "").strip()
            used_hint   = request.form.get(f"hint_used_{idx}", "0") == "1"

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

            if not existing_score:
                guess_log = GuessLog(
                    user_id=current_user.id,
                    player_name=name,
                    school=team_name,
                    guess=guess,
                    is_correct=is_correct,
                    used_hint=used_hint,
                    quiz_id=quiz_key,
                )
                current_app.logger.debug(
                    f"[DBG] Adding GuessLog(user={current_user.id}, player={name!r}, quiz_key={quiz_key!r}, is_correct={is_correct})"
                )
                db.session.add(guess_log)

        if not existing_score:
            score_entry = ScoreLog(
                quiz_id=quiz_key,
                user_id=current_user.id,
                score=score,
                max_points=max_points,
                time_taken=time_taken,
            )
            db.session.add(score_entry)
            db.session.commit()
        else:
            score = existing_score.score
            max_points = existing_score.max_points
            time_taken = existing_score.time_taken

        streak = calc_streak(current_user.id)

        scores = [s.score for s in ScoreLog.query.filter_by(quiz_id=quiz_key).all()]
        percentile = 0
        if scores:
            scores.sort()
            rank = sum(s <= score for s in scores)
            percentile = round(100 * rank / len(scores))

        leaderboard = get_leaderboard(quiz_key)
        show_leaderboard = bool(leaderboard)

        perf_text = performance_text(score, max_points)

        date_str = datetime.utcnow().strftime("%B %-d, %Y")
        share_lines = [
            f"\U0001F3C0 Starting5 Puzzle – {date_str}",
            f"\U0001F4C8 Score: {round(score,2)}/{round(max_points,2)}",
            "",
        ]
        for pl, status in zip(data["players"], share_statuses):
            share_lines.append(f"\uD83D\uDD39 {pl['position']}: {status}")
        share_lines += ["", perf_text, "Play now: www.starting5.us"]
        share_message = "\n".join(share_lines)

        return render_template(
            "results.html",
            data=data,
            colleges=colleges,
            college_confs=conf_map,
            results=results,
            correct_answers=correct_answers,
            score=round(score, 2),
            max_points=round(max_points, 2),
            quiz_json_path=qp,
            quiz_id=quiz_key,
            percentile=percentile,
            streak=streak,
            share_message=share_message,
            performance_text=perf_text,
            leaderboard=leaderboard,
            show_leaderboard=show_leaderboard,
            show_share=False,
            already_played=False,
            archive_quizzes=get_archive_list(),
        )

    # GET mode
    with open(quiz_path, encoding="utf-8") as f:
        data = json.load(f)
    for pl in data["players"]:
        normalise_usc(pl, conf_map)

    already_played = bool(
        ScoreLog.query.filter_by(user_id=current_user.id, quiz_id=quiz_key).first()
    )

    streak = calc_streak(current_user.id)
    leaderboard = get_leaderboard(quiz_key)

    return render_template(
        "quiz.html",
        data=data,
        colleges=colleges,
        college_confs=conf_map,
        results=None,
        correct_answers=[],
        score=None,
        max_points=None,
        quiz_json_path=quiz_path,
        quiz_id=quiz_key,
        streak=streak,
        share_message=None,
        performance_text=None,
        leaderboard=leaderboard,
        show_leaderboard=False,
        show_share=False,
        already_played=already_played,
        archive_quizzes=get_archive_list(),
    )


@bp.route("/quiz", methods=["GET", "POST"])
def show_quiz():
    conf_map, colleges = load_confs()
    quiz_key = None
    is_bonus_quiz = False

    if request.method == "POST":
        # (Unchanged) read quiz_json_path from the form and grade it
        qp = request.form.get("quiz_json_path", "")
        if not qp or not os.path.isfile(qp):
            return redirect(url_for("main.show_quiz"))

        with open(qp, encoding="utf-8") as f:
            data = json.load(f)
        for pl in data["players"]:
            normalise_usc(pl, conf_map)

        quiz_key = os.path.basename(qp)
        is_bonus_quiz = qp.startswith(BONUS_DIR)
        time_taken = request.form.get("time_taken", type=int)

        existing_score = None
        if current_user.is_authenticated:
            existing_score = (
                ScoreLog.query.filter(
                    ScoreLog.user_id == current_user.id,
                    ScoreLog.quiz_id == quiz_key,
                )
                .first()
            )
        else:
            sid_key = f"guest_score_{quiz_key}"
            sid = session.get(sid_key)
            if sid:
                existing_score = (
                    ScoreLog.query.filter(
                        ScoreLog.id == sid,
                        ScoreLog.quiz_id == quiz_key,
                    )
                    .first()
                )

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

             # Log the guess only for authenticated users
            if current_user.is_authenticated and not existing_score:
                guess_log = GuessLog(
                    user_id=current_user.id,
                    player_name=name,
                    school=team_name,
                    guess=guess,
                    is_correct=is_correct,
                    used_hint=used_hint,
                    quiz_id=quiz_key,
                )
                current_app.logger.debug(
                    f"[DBG] Adding GuessLog(user={current_user.id}, player={name!r}, quiz_key={quiz_key!r}, is_correct={is_correct})"
                )
                db.session.add(guess_log)

        if not existing_score:
            score_entry = ScoreLog(
                quiz_id=quiz_key,
                user_id=current_user.id if current_user.is_authenticated else None,
                score=score,
                max_points=max_points,
                time_taken=time_taken,
            )
            db.session.add(score_entry)
            db.session.commit()
            if not current_user.is_authenticated:
                session[f"guest_score_{quiz_key}"] = score_entry.id
        else:
            score = existing_score.score
            max_points = existing_score.max_points
            time_taken = existing_score.time_taken
        
        streak = 0
        if current_user.is_authenticated:
            logs = (
                ScoreLog.query.filter_by(user_id=current_user.id)
                .order_by(ScoreLog.timestamp.desc())
                .all()
            )
            if logs:
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

        scores = [s.score for s in ScoreLog.query.filter_by(quiz_id=quiz_key).all()]
        percentile = 0
        if scores:
            scores.sort()
            rank = sum(s <= score for s in scores)
            percentile = round(100 * rank / len(scores))

        leaderboard = get_leaderboard(quiz_key)
        show_leaderboard = bool(leaderboard) or not current_user.is_authenticated
        
        perf_text = performance_text(score, max_points)

        date_str = datetime.utcnow().strftime("%B %-d, %Y")
        share_lines = [
            f"\U0001F3C0 Starting5 Puzzle – {date_str}",
            f"\U0001F4C8 Score: {round(score,2)}/{round(max_points,2)}",
            "",
        ]
        for pl, status in zip(data["players"], share_statuses):
            share_lines.append(f"\uD83D\uDD39 {pl['position']}: {status}")
        share_lines += ["", perf_text, "Play now: www.starting5.us"]
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
        leaderboard     = leaderboard,
        show_leaderboard= show_leaderboard,
            show_share      = not is_bonus_quiz,
        already_played  = False,
        archive_quizzes = get_archive_list(),
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # GET: serve whatever JSON is in CURRENT_DIR (there should be exactly one file)
    # ─────────────────────────────────────────────────────────────────────────────
    bonus_mode = request.args.get("bonus") == "1"
    if bonus_mode:
        if not session.get("bonus_unlocked"):
            return redirect(url_for("main.show_quiz"))
        os.makedirs(BONUS_DIR, exist_ok=True)
        bonus_files = [f for f in os.listdir(BONUS_DIR) if f.lower().endswith(".json")]
        if not bonus_files:
            return "❌ No bonus quiz available.", 500
        quiz_filename = random.choice(bonus_files)
        quiz_path = os.path.join(BONUS_DIR, quiz_filename)
        is_bonus_quiz = True
    else:
        # Ensure current_quiz folder exists (if not, create it)
        os.makedirs(CURRENT_DIR, exist_ok=True)

        # Look for any .json in CURRENT_DIR
        current_files = [f for f in os.listdir(CURRENT_DIR) if f.lower().endswith(".json")]
        if not current_files:
            return "❌ No current quiz loaded. Please run the updater script.", 500

        # We assume only ONE file should be there at a time
        quiz_filename = current_files[0]
        quiz_path = os.path.join(CURRENT_DIR, quiz_filename)

    quiz_key = os.path.basename(quiz_path)



    with open(quiz_path, encoding="utf-8") as f:
        data = json.load(f)
    for pl in data["players"]:
        normalise_usc(pl, conf_map)

    streak = 0
    if current_user.is_authenticated:
        logs = (
            ScoreLog.query.filter_by(user_id=current_user.id)
            .order_by(ScoreLog.timestamp.desc())
            .all()
        )
        if logs:
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

    leaderboard = get_leaderboard(quiz_key)
    show_leaderboard = False
    
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
        leaderboard = leaderboard,
        show_leaderboard= show_leaderboard,
        show_share      = not bonus_mode,
        already_played  = False,
        archive_quizzes = get_archive_list(),

    )



@bp.route("/player_accuracy/<player_name>")
def player_accuracy(player_name):
    """Return accuracy for a single player within a specific quiz."""
    safe_name = unquote(player_name)
    quiz_id = request.args.get("quiz_id")
    if not quiz_id:
        return jsonify({"error": "quiz_id is required"}), 400

    total = GuessLog.query.filter_by(player_name=safe_name, quiz_id=quiz_id).count()
    correct = GuessLog.query.filter_by(
        player_name=safe_name, quiz_id=quiz_id, is_correct=True
    ).count()

    percent = round(100 * correct / total, 1) if total else 0
    resp = jsonify({"player": safe_name, "accuracy": percent})
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return make_response(resp)



@bp.route("/record_share", methods=["POST"])
def record_share():
    session["bonus_unlocked"] = True
    return jsonify({"status": "ok"})
