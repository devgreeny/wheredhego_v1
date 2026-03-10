#!/usr/bin/env python3
"""
Cron job script to set the daily StartingTee course.
Run this at midnight to set the next day's course.

Usage:
    python scripts/set_daily_startingtee.py          # Set random course for tomorrow
    python scripts/set_daily_startingtee.py --today  # Set random course for today
    python scripts/set_daily_startingtee.py --course pebble_beach_golf_links  # Set specific course

Cron example (run at 11:59 PM daily):
    59 23 * * * cd /path/to/wheredhego_v1 && python scripts/set_daily_startingtee.py
"""

import os
import sys
import json
import random
import argparse
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSES_FILE = os.path.join(PROJECT_ROOT, "quizzes", "startingtee", "us_open_courses.json")
DAILY_COURSE_FILE = os.path.join(PROJECT_ROOT, "quizzes", "startingtee", "daily_course.json")
HISTORY_FILE = os.path.join(PROJECT_ROOT, "quizzes", "startingtee", "course_history.json")


def load_courses():
    """Load all available courses."""
    with open(COURSES_FILE, encoding="utf-8") as f:
        data = json.load(f)
        return data.get('courses', [])


def load_history():
    """Load recently used courses to avoid repeats."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"recent_courses": []}


def save_history(history):
    """Save course history."""
    with open(HISTORY_FILE, 'w', encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def select_course(courses, history, specific_course_id=None):
    """Select a course, avoiding recent ones unless specified."""
    if specific_course_id:
        for course in courses:
            if course['id'] == specific_course_id:
                return course
        print(f"Warning: Course '{specific_course_id}' not found, selecting random.")
    
    # Get courses not used in last 14 days
    recent_ids = set(history.get('recent_courses', [])[-14:])
    available = [c for c in courses if c['id'] not in recent_ids]
    
    # If all courses used recently, just pick from all
    if not available:
        available = courses
    
    return random.choice(available)


def set_daily_course(course, target_date):
    """Set the daily course file."""
    daily_data = {
        'date': target_date.isoformat(),
        'course_id': course['id'],
        'course_name': course['name'],
        'set_at': date.today().isoformat()
    }
    
    with open(DAILY_COURSE_FILE, 'w', encoding="utf-8") as f:
        json.dump(daily_data, f, indent=2)
    
    return daily_data


def main():
    parser = argparse.ArgumentParser(description='Set daily StartingTee course')
    parser.add_argument('--today', action='store_true', help='Set course for today instead of tomorrow')
    parser.add_argument('--course', type=str, help='Specific course ID to set')
    parser.add_argument('--list', action='store_true', help='List all available courses')
    args = parser.parse_args()
    
    courses = load_courses()
    
    if args.list:
        print(f"\nAvailable courses ({len(courses)} total):\n")
        for c in sorted(courses, key=lambda x: x['name']):
            print(f"  {c['id']}: {c['name']}")
        return
    
    history = load_history()
    target_date = date.today() if args.today else date.today() + timedelta(days=1)
    
    course = select_course(courses, history, args.course)
    daily_data = set_daily_course(course, target_date)
    
    # Update history
    history['recent_courses'] = history.get('recent_courses', [])
    history['recent_courses'].append(course['id'])
    # Keep last 30 entries
    history['recent_courses'] = history['recent_courses'][-30:]
    save_history(history)
    
    print(f"✅ Set daily course for {target_date}:")
    print(f"   Course: {course['name']}")
    print(f"   ID: {course['id']}")
    if course.get('city') or course.get('state'):
        print(f"   Location: {course.get('city', '')}, {course.get('state', '')}")


if __name__ == "__main__":
    main()
