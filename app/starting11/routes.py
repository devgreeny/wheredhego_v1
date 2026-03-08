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
from .models import Starting11Score

bp = Blueprint('starting11', __name__,
               template_folder='templates',
               static_folder='static')

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CURRENT_DIR = os.path.join(PROJECT_ROOT, "quizzes", "starting11", "current")
PRELOADED_DIR = os.path.join(PROJECT_ROOT, "quizzes", "starting11", "preloaded")
ARCHIVE_DIR = os.path.join(PROJECT_ROOT, "quizzes", "starting11", "archive")

# Countries from scraped World Cup data (1998-2022)
COUNTRIES = [
    "Algeria", "Angola", "Argentina", "Australia", "Austria", "Belgium",
    "Bosnia-Herzegovina", "Brazil", "Bulgaria", "Cameroon", "Canada", "Chile",
    "China", "Colombia", "Costa Rica", "Croatia", "Czech Republic", "Denmark",
    "Ecuador", "Egypt", "England", "France", "Germany", "Ghana", "Greece",
    "Honduras", "Iceland", "Iran", "Italy", "Ivory Coast", "Jamaica", "Japan",
    "Mexico", "Morocco", "Netherlands", "New Zealand", "Nigeria", "North Korea",
    "Norway", "Panama", "Paraguay", "Peru", "Poland", "Portugal", "Qatar",
    "Republic of Ireland", "Romania", "Russia", "Saudi Arabia", "Scotland",
    "Senegal", "Serbia", "Serbia and Montenegro", "Slovakia", "Slovenia",
    "South Africa", "South Korea", "Spain", "Sweden", "Switzerland", "Togo",
    "Trinidad and Tobago", "Tunisia", "Turkiye", "USA", "Ukraine", "Uruguay",
    "Wales", "Yugoslavia",
]

# Aliases for matching user guesses to correct answers
COUNTRY_ALIASES = {
    "united states": "usa",
    "united states of america": "usa",
    "america": "usa",
    "usa": "united states",
    "holland": "netherlands",
    "ivory coast": "cote d'ivoire",
    "cote d'ivoire": "ivory coast",
    "south korea": "korea republic",
    "korea": "south korea",
    "north korea": "korea dpr",
    "bosnia": "bosnia-herzegovina",
    "bosnia and herzegovina": "bosnia-herzegovina",
    "uae": "united arab emirates",
    "united arab emirates": "uae",
    "dr congo": "congo dr",
    "democratic republic of congo": "dr congo",
    "turkey": "turkiye",
    "turkiye": "turkey",
    "republic of ireland": "ireland",
    "ireland": "republic of ireland",
    "serbia and montenegro": "serbia",
}

# Confederation mapping for hint system
CONFEDERATIONS = {
    # UEFA (Europe)
    "Albania": "UEFA", "Andorra": "UEFA", "Armenia": "UEFA", "Austria": "UEFA", 
    "Azerbaijan": "UEFA", "Belarus": "UEFA", "Belgium": "UEFA", "Bosnia-Herzegovina": "UEFA",
    "Bulgaria": "UEFA", "Croatia": "UEFA", "Cyprus": "UEFA", "Czech Republic": "UEFA",
    "Czechoslovakia": "UEFA", "Denmark": "UEFA", "England": "UEFA", "Estonia": "UEFA",
    "Faroe Islands": "UEFA", "Finland": "UEFA", "France": "UEFA", "Georgia": "UEFA",
    "Germany": "UEFA", "Gibraltar": "UEFA", "Greece": "UEFA", "Hungary": "UEFA",
    "Iceland": "UEFA", "Ireland": "UEFA", "Israel": "UEFA", "Italy": "UEFA",
    "Kazakhstan": "UEFA", "Kosovo": "UEFA", "Latvia": "UEFA", "Liechtenstein": "UEFA",
    "Lithuania": "UEFA", "Luxembourg": "UEFA", "Malta": "UEFA", "Moldova": "UEFA",
    "Monaco": "UEFA", "Montenegro": "UEFA", "Netherlands": "UEFA", "North Macedonia": "UEFA",
    "Northern Ireland": "UEFA", "Norway": "UEFA", "Poland": "UEFA", "Portugal": "UEFA",
    "Romania": "UEFA", "Russia": "UEFA", "San Marino": "UEFA", "Scotland": "UEFA",
    "Republic of Ireland": "UEFA", "Serbia": "UEFA", "Serbia and Montenegro": "UEFA",
    "Slovakia": "UEFA", "Slovenia": "UEFA", "Soviet Union": "UEFA",
    "Spain": "UEFA", "Sweden": "UEFA", "Switzerland": "UEFA", "Turkey": "UEFA",
    "Turkiye": "UEFA", "Ukraine": "UEFA", "Wales": "UEFA", "Yugoslavia": "UEFA",
    # CONMEBOL (South America)
    "Argentina": "CONMEBOL", "Bolivia": "CONMEBOL", "Brazil": "CONMEBOL", 
    "Chile": "CONMEBOL", "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL",
    "Paraguay": "CONMEBOL", "Peru": "CONMEBOL", "Uruguay": "CONMEBOL", "Venezuela": "CONMEBOL",
    # CONCACAF (North/Central America & Caribbean)
    "Canada": "CONCACAF", "Costa Rica": "CONCACAF", "Cuba": "CONCACAF", 
    "El Salvador": "CONCACAF", "Guatemala": "CONCACAF", "Haiti": "CONCACAF",
    "Honduras": "CONCACAF", "Jamaica": "CONCACAF", "Mexico": "CONCACAF",
    "Nicaragua": "CONCACAF", "Panama": "CONCACAF", "Trinidad and Tobago": "CONCACAF", 
    "USA": "CONCACAF", "United States": "CONCACAF",
    # CAF (Africa)
    "Algeria": "CAF", "Angola": "CAF", "Benin": "CAF", "Burkina Faso": "CAF",
    "Burundi": "CAF", "Cameroon": "CAF", "Cape Verde": "CAF", "Central African Republic": "CAF",
    "Chad": "CAF", "Comoros": "CAF", "Congo": "CAF", "DR Congo": "CAF", 
    "Ivory Coast": "CAF", "Djibouti": "CAF", "Egypt": "CAF", "Equatorial Guinea": "CAF",
    "Eritrea": "CAF", "Eswatini": "CAF", "Ethiopia": "CAF", "Gabon": "CAF",
    "Gambia": "CAF", "Ghana": "CAF", "Guinea": "CAF", "Guinea-Bissau": "CAF",
    "Kenya": "CAF", "Lesotho": "CAF", "Liberia": "CAF", "Libya": "CAF",
    "Madagascar": "CAF", "Malawi": "CAF", "Mali": "CAF", "Mauritania": "CAF",
    "Mauritius": "CAF", "Morocco": "CAF", "Mozambique": "CAF", "Namibia": "CAF",
    "Niger": "CAF", "Nigeria": "CAF", "Rwanda": "CAF", "Senegal": "CAF",
    "Sierra Leone": "CAF", "Somalia": "CAF", "South Africa": "CAF", "South Sudan": "CAF",
    "Sudan": "CAF", "Tanzania": "CAF", "Togo": "CAF", "Tunisia": "CAF",
    "Uganda": "CAF", "Zambia": "CAF", "Zimbabwe": "CAF", "Zaire": "CAF",
    # AFC (Asia)
    "Afghanistan": "AFC", "Australia": "AFC", "Bahrain": "AFC", "Bangladesh": "AFC",
    "Bhutan": "AFC", "Brunei": "AFC", "Cambodia": "AFC", "China": "AFC",
    "Hong Kong": "AFC", "India": "AFC", "Indonesia": "AFC", "Iran": "AFC",
    "Iraq": "AFC", "Japan": "AFC", "Jordan": "AFC", "Kuwait": "AFC",
    "Kyrgyzstan": "AFC", "Laos": "AFC", "Lebanon": "AFC", "Macau": "AFC",
    "Malaysia": "AFC", "Maldives": "AFC", "Mongolia": "AFC", "Myanmar": "AFC",
    "Nepal": "AFC", "North Korea": "AFC", "Oman": "AFC", "Pakistan": "AFC",
    "Palestine": "AFC", "Philippines": "AFC", "Qatar": "AFC", "Saudi Arabia": "AFC",
    "Singapore": "AFC", "South Korea": "AFC", "Sri Lanka": "AFC", "Syria": "AFC",
    "Tajikistan": "AFC", "Thailand": "AFC", "Timor-Leste": "AFC", "Turkmenistan": "AFC",
    "UAE": "AFC", "Uzbekistan": "AFC", "Vietnam": "AFC", "Yemen": "AFC",
    # OFC (Oceania)
    "Fiji": "OFC", "New Caledonia": "OFC", "New Zealand": "OFC", 
    "Papua New Guinea": "OFC", "Samoa": "OFC", "Solomon Islands": "OFC",
    "Tahiti": "OFC", "Tonga": "OFC", "Vanuatu": "OFC",
}

def get_confederation(country):
    """Get confederation for a country, with fallback."""
    return CONFEDERATIONS.get(country, "Unknown")

def performance_text(score, max_points):
    if score == 3:
        return "Perfect! No hints needed!"
    elif score == 2:
        return "Great job! Just one hint."
    elif score == 1:
        return "Nice work figuring it out!"
    else:
        return "Better luck next time!"


@bp.route("/")
def home():
    return redirect(url_for("starting11.show_quiz"))


@bp.route("/quiz", methods=["GET", "POST"])
def show_quiz():
    from app.utils.daily_limits import has_played_today, mark_played_today
    
    # TESTING MODE: Set to False for production
    TESTING_MODE = False
    
    quiz_key = None
    
    if request.method == "POST":
        if not TESTING_MODE:
            has_played, _ = has_played_today('starting11')
            if has_played:
                return redirect(url_for("starting11.show_quiz"))
        
        qp = request.form.get("quiz_json_path", "")
        if not qp or not os.path.isfile(qp):
            return redirect(url_for("starting11.show_quiz"))
        
        with open(qp, encoding="utf-8") as f:
            data = json.load(f)
        
        quiz_key = os.path.basename(qp)
        time_taken = request.form.get("time_taken", type=int)
        hints_used = request.form.get("hints_used", type=int, default=0)
        
        guess = request.form.get("country_guess", "").strip().lower()
        correct_answer = data["answer"]["country"].lower()
        
        # Normalize guess using aliases
        normalized_guess = COUNTRY_ALIASES.get(guess, guess)
        normalized_answer = COUNTRY_ALIASES.get(correct_answer, correct_answer)
        
        # Check for match (exact, alias, or substring)
        is_correct = (
            normalized_guess == normalized_answer or
            guess == correct_answer or
            normalized_guess == correct_answer or
            guess == normalized_answer
        )
        
        # Score based on hints used: 3 pts (no hints), 2 pts (1 hint), 1 pt (2 hints), 0 if wrong
        if is_correct:
            score = 3 - hints_used
        else:
            score = 0
        max_points = 3
        
        if current_user.is_authenticated:
            current_user.save_game_score(
                game_type='starting11',
                quiz_id=quiz_key,
                score=score,
                max_points=max_points,
                time_taken=time_taken,
                metadata={'correct': is_correct, 'hints_used': hints_used}
            )
        
        score_entry = Starting11Score(
            quiz_id=quiz_key,
            user_id=int(current_user.id) if current_user.is_authenticated else None,
            score=score,
            max_points=max_points,
            time_taken=time_taken,
        )
        db.session.add(score_entry)
        db.session.commit()
        
        if not TESTING_MODE:
            mark_played_today('starting11')
        
        scores = [s.score for s in Starting11Score.query.filter_by(quiz_id=quiz_key).all()]
        percentile = 0
        if scores:
            scores.sort()
            rank = sum(s <= score for s in scores)
            percentile = round(100 * rank / len(scores))
        
        perf_text = performance_text(score, max_points)
        
        date_str = datetime.utcnow().strftime("%B %-d, %Y")
        share_message = f"Starting XI – {date_str}\n"
        share_message += f"{'✅' if is_correct else '❌'} {data['answer']['country']}\n"
        share_message += f"Score: {int(score)}/{int(max_points)} (Hints: {hints_used})\n"
        share_message += f"\nPlay: wheredhego.com/starting11"
        
        return render_template(
            "starting11/results.html",
            data=data,
            is_correct=is_correct,
            score=score,
            max_points=max_points,
            hints_used=hints_used,
            percentile=percentile,
            performance_text=perf_text,
            share_message=share_message,
            quiz_json_path=qp,
        )
    
    has_played_today_flag = False if TESTING_MODE else has_played_today('starting11')[0]
    
    os.makedirs(CURRENT_DIR, exist_ok=True)
    os.makedirs(PRELOADED_DIR, exist_ok=True)
    
    # Collect all available quizzes from multiple sources
    all_quiz_paths = []
    
    # 1. Check current directory (for daily scheduled quiz)
    current_files = [f for f in os.listdir(CURRENT_DIR) if f.endswith(".json")]
    if current_files and not TESTING_MODE:
        # In production, use the scheduled daily quiz
        quiz_path = os.path.join(CURRENT_DIR, current_files[0])
    else:
        # In testing mode or no current quiz, pool from all sources
        
        # Add preloaded quizzes
        if os.path.exists(PRELOADED_DIR):
            for f in os.listdir(PRELOADED_DIR):
                if f.endswith(".json"):
                    all_quiz_paths.append(os.path.join(PRELOADED_DIR, f))
        
        # Add all World Cup quizzes (1998-2022)
        for tournament in ["wc2022", "wc2018", "wc2014", "wc2010", "wc2006", "wc2002", "wc1998"]:
            tournament_dir = os.path.join(PROJECT_ROOT, "quizzes", "starting11", tournament)
            if os.path.exists(tournament_dir):
                for f in os.listdir(tournament_dir):
                    if f.endswith(".json"):
                        all_quiz_paths.append(os.path.join(tournament_dir, f))
        
        if not all_quiz_paths:
            return "No quizzes available.", 500
        
        quiz_path = random.choice(all_quiz_paths)
    
    quiz_key = os.path.basename(quiz_path)
    
    with open(quiz_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # Get hints data
    country = data.get('answer', {}).get('country', '')
    confederation = get_confederation(country)
    first_letter = country[0].upper() if country else '?'
    
    return render_template(
        "starting11/quiz.html",
        data=data,
        countries=sorted(COUNTRIES),
        quiz_json_path=quiz_path,
        quiz_id=quiz_key,
        already_played=has_played_today_flag,
        confederation=confederation,
        first_letter=first_letter,
    )
