import os
import json
import random
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
)
from flask_login import current_user
from datetime import datetime
from app.starting5.models import db
from .models import StartingTeeScore

bp = Blueprint('startingtee', __name__,
               template_folder='templates',
               static_folder='static')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COURSES_FILE = os.path.join(PROJECT_ROOT, "quizzes", "startingtee", "us_open_courses.json")

# Cache courses data
_CACHED_COURSES = None

def load_courses():
    """Load courses from JSON file (cached)."""
    global _CACHED_COURSES
    if _CACHED_COURSES is not None:
        return _CACHED_COURSES
    
    with open(COURSES_FILE, encoding="utf-8") as f:
        data = json.load(f)
        _CACHED_COURSES = data.get('courses', [])
    return _CACHED_COURSES


def get_course_by_id(course_id):
    """Get a specific course by ID."""
    courses = load_courses()
    for course in courses:
        if course['id'] == course_id:
            return course
    return None


def performance_text(score, max_points):
    if score == 4:
        return "Perfect! No hints needed!"
    elif score == 3:
        return "Great job! Just one hint."
    elif score == 2:
        return "Nice work with two hints!"
    elif score == 1:
        return "Got it with all hints!"
    else:
        return "Better luck next time!"


@bp.route("/")
def home():
    return redirect(url_for("startingtee.show_quiz"))


@bp.route("/quiz", methods=["GET", "POST"])
def show_quiz():
    from app.utils.daily_limits import has_played_today, mark_played_today
    
    # TESTING MODE: Set to False for production
    TESTING_MODE = False  # Production: one play per day
    
    if request.method == "POST":
        if not TESTING_MODE:
            has_played, _ = has_played_today('startingtee')
            if has_played:
                return redirect(url_for("startingtee.show_quiz"))
        
        course_id = request.form.get("course_id", "")
        course = get_course_by_id(course_id)
        
        if not course:
            return redirect(url_for("startingtee.show_quiz"))
        
        time_taken = request.form.get("time_taken", type=int)
        hints_used = request.form.get("hints_used", type=int, default=0)
        
        guess = request.form.get("course_guess", "").strip().lower()
        correct_answer = course["name"].lower()
        
        # Flexible matching - check if guess contains key parts of course name
        course_name_parts = correct_answer.replace("golf club", "").replace("country club", "").replace("golf links", "").replace("golf course", "").strip()
        
        is_correct = (
            guess == correct_answer or
            course_name_parts in guess or
            guess in correct_answer or
            # Match main identifier (e.g., "augusta" matches "Augusta National Golf Club")
            course['id'].replace('_', ' ') in guess or
            guess.replace(' ', '_') == course['id']
        )
        
        # Score based on hints used: 4 pts (no hints), 3 pts (1 hint), 2 pts (2 hints), 1 pt (3 hints), 0 if wrong
        if is_correct:
            score = 4 - hints_used
        else:
            score = 0
        max_points = 4
        
        if current_user.is_authenticated:
            current_user.save_game_score(
                game_type='startingtee',
                quiz_id=course_id,
                score=score,
                max_points=max_points,
                time_taken=time_taken,
                metadata={'correct': is_correct, 'hints_used': hints_used}
            )
        
        score_entry = StartingTeeScore(
            quiz_id=course_id,
            user_id=int(current_user.id) if current_user.is_authenticated else None,
            score=score,
            max_points=max_points,
            time_taken=time_taken,
        )
        db.session.add(score_entry)
        db.session.commit()
        
        if not TESTING_MODE:
            mark_played_today('startingtee')
        
        scores = [s.score for s in StartingTeeScore.query.filter_by(quiz_id=course_id).all()]
        percentile = 0
        if scores:
            scores.sort()
            rank = sum(s <= score for s in scores)
            percentile = round(100 * rank / len(scores))
        
        perf_text = performance_text(score, max_points)
        
        date_str = datetime.utcnow().strftime("%B %-d, %Y")
        share_message = f"StartingTee – {date_str}\n"
        share_message += f"{'✅' if is_correct else '❌'} Score: {int(score)}/{int(max_points)}\n"
        share_message += f"Hints used: {hints_used}\n"
        share_message += f"\nPlay: wheredhego.com/startingtee"
        
        return render_template(
            "startingtee/results.html",
            course=course,
            is_correct=is_correct,
            score=score,
            max_points=max_points,
            hints_used=hints_used,
            percentile=percentile,
            performance_text=perf_text,
            share_message=share_message,
        )
    
    # GET request - show quiz
    has_played_today_flag = False if TESTING_MODE else has_played_today('startingtee')[0]
    
    courses = load_courses()
    if not courses:
        return "No courses available.", 500
    
    # Pick a random course
    course = random.choice(courses)
    
    # Get all course names for autocomplete
    all_course_names = sorted([c['name'] for c in courses])
    
    return render_template(
        "startingtee/quiz.html",
        course=course,
        all_courses=all_course_names,
        already_played=has_played_today_flag,
    )
