#!/usr/bin/env python3
"""
Enhanced Midnight Game Updater for wheredhego.com
Updates both Starting5 (NBA) and Gridiron11 (NFL) games daily at midnight EST

This script:
1. Archives yesterday's quizzes for both games
2. Selects new random quizzes from preloaded pools
3. Prepares bonus quizzes for Starting5
4. Logs all operations for monitoring

Usage:
    python update_games.py
    
For cron job (runs at midnight EST):
    0 0 * * * cd /home/devgreeny/wheredhego && python update_games.py >> /home/devgreeny/logs/game_updates.log 2>&1
"""

import os
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
# Project root - adjust this path for your deployment (script is in scripts/ folder)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Starting5 (NBA Basketball) directories (using new organized quiz folder structure)
STARTING5_PRELOADED = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "preloaded")
STARTING5_CURRENT = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "current")
STARTING5_ARCHIVE = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "archive")
STARTING5_BONUS = os.path.join(PROJECT_ROOT, "quizzes", "starting5", "bonus")

# Gridiron11 (NFL Football) directories (using new organized quiz folder structure)
GRIDIRON11_PRELOADED = os.path.join(PROJECT_ROOT, "quizzes", "gridiron11", "preloaded")
GRIDIRON11_CURRENT = os.path.join(PROJECT_ROOT, "quizzes", "gridiron11", "current")
GRIDIRON11_ARCHIVE = os.path.join(PROJECT_ROOT, "quizzes", "gridiron11", "archive")

# Fallback: Check legacy gridiron11 directory if app version doesn't exist
GRIDIRON11_FALLBACK_ROOT = os.path.join(PROJECT_ROOT, "legacy", "gridiron11")
GRIDIRON11_FALLBACK_CURRENT = os.path.join(GRIDIRON11_FALLBACK_ROOT, "static", "current_quiz")
# ────────────────────────────────────────────────────────────────────────────────

def log_message(message: str, level: str = "INFO"):
    """Log a message with timestamp and level."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def ensure_directories(*dirs):
    """Ensure all specified directories exist."""
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)

def get_json_files(directory: str) -> list:
    """Get all JSON files from a directory."""
    if not os.path.exists(directory):
        return []
    return [f for f in os.listdir(directory) if f.lower().endswith(".json")]

def archive_quiz_files(current_dir: str, archive_dir: str, game_name: str):
    """Archive existing quiz files from current to archive directory."""
    ensure_directories(current_dir, archive_dir)
    
    existing_files = get_json_files(current_dir)
    if not existing_files:
        log_message(f"No existing {game_name} quiz files to archive")
        return
    
    for old_file in existing_files:
        old_path = os.path.join(current_dir, old_file)
        archive_path = os.path.join(archive_dir, old_file)
        
        try:
            shutil.move(old_path, archive_path)
            log_message(f"📦 Archived {game_name} quiz: {old_file}")
        except Exception as e:
            log_message(f"⚠️ Could not archive {game_name} quiz '{old_file}': {e}", "ERROR")

def update_quiz_files(preloaded_dir: str, current_dir: str, game_name: str) -> str:
    """Select and move a random quiz from preloaded to current directory."""
    ensure_directories(preloaded_dir, current_dir)
    
    available_quizzes = get_json_files(preloaded_dir)
    if not available_quizzes:
        log_message(f"❌ No {game_name} quizzes found in preloaded directory", "ERROR")
        return None
    
    chosen_quiz = random.choice(available_quizzes)
    src_path = os.path.join(preloaded_dir, chosen_quiz)
    dest_path = os.path.join(current_dir, chosen_quiz)
    
    try:
        shutil.move(src_path, dest_path)
        log_message(f"✅ Updated {game_name} quiz: {chosen_quiz}")
        return chosen_quiz
    except Exception as e:
        log_message(f"❌ Failed to update {game_name} quiz '{chosen_quiz}': {e}", "ERROR")
        return None

def prepare_bonus_quiz(preloaded_dir: str, bonus_dir: str, exclude_file: str = None):
    """Prepare a bonus quiz for Starting5 (if needed)."""
    ensure_directories(bonus_dir)
    
    # Check if bonus quiz already exists
    existing_bonus = get_json_files(bonus_dir)
    if existing_bonus:
        log_message("Bonus quiz already exists, skipping preparation")
        return
    
    # Get available quizzes (excluding the one we just used)
    available_quizzes = get_json_files(preloaded_dir)
    if exclude_file and exclude_file in available_quizzes:
        available_quizzes.remove(exclude_file)
    
    if not available_quizzes:
        log_message("⚠️ No quizzes available for bonus quiz preparation", "WARNING")
        return
    
    chosen_bonus = random.choice(available_quizzes)
    src_path = os.path.join(preloaded_dir, chosen_bonus)
    dest_path = os.path.join(bonus_dir, chosen_bonus)
    
    try:
        shutil.copy(src_path, dest_path)
        log_message(f"✅ Prepared bonus quiz: {chosen_bonus}")
    except Exception as e:
        log_message(f"⚠️ Failed to prepare bonus quiz '{chosen_bonus}': {e}", "ERROR")

def update_starting5():
    """Update Starting5 basketball game."""
    log_message("🏀 Starting Starting5 update...")
    
    # Archive yesterday's quiz
    archive_quiz_files(STARTING5_CURRENT, STARTING5_ARCHIVE, "Starting5")
    
    # Update current quiz
    chosen_quiz = update_quiz_files(STARTING5_PRELOADED, STARTING5_CURRENT, "Starting5")
    
    # Prepare bonus quiz
    if chosen_quiz:
        prepare_bonus_quiz(STARTING5_PRELOADED, STARTING5_BONUS, chosen_quiz)
    
    log_message("🏀 Starting5 update completed")
    return chosen_quiz

def update_gridiron11():
    """Update Gridiron11 NFL game."""
    log_message("🏈 Starting Gridiron11 update...")
    
    # Determine which directories to use (app version or fallback)
    preloaded_dir = GRIDIRON11_PRELOADED
    current_dir = GRIDIRON11_CURRENT
    archive_dir = GRIDIRON11_ARCHIVE
    
    # Check if we need to use fallback directories
    if not os.path.exists(preloaded_dir) and os.path.exists(GRIDIRON11_FALLBACK_CURRENT):
        log_message("Using fallback Gridiron11 directories")
        # For fallback, we'll just work with the current directory
        current_dir = GRIDIRON11_FALLBACK_CURRENT
        # Check if there are quiz files in the fallback location
        fallback_files = get_json_files(current_dir)
        if fallback_files:
            log_message(f"Found {len(fallback_files)} quiz files in fallback location")
            log_message("🏈 Gridiron11 using existing quiz files")
            return fallback_files[0] if fallback_files else None
    
    # Check if preloaded directory has quiz files
    if not get_json_files(preloaded_dir):
        log_message("⚠️ No Gridiron11 quiz files found in preloaded directory", "WARNING")
        log_message("🏈 Gridiron11 update skipped - no quiz files available")
        return None
    
    # Archive yesterday's quiz
    archive_quiz_files(current_dir, archive_dir, "Gridiron11")
    
    # Update current quiz
    chosen_quiz = update_quiz_files(preloaded_dir, current_dir, "Gridiron11")
    
    log_message("🏈 Gridiron11 update completed")
    return chosen_quiz

def main():
    """Main function to update both games."""
    log_message("🚀 Starting daily game updates...")
    log_message(f"Project root: {PROJECT_ROOT}")
    
    # Update both games
    starting5_quiz = update_starting5()
    gridiron11_quiz = update_gridiron11()
    
    # Summary
    log_message("📊 Update Summary:")
    log_message(f"  🏀 Starting5: {'✅ ' + starting5_quiz if starting5_quiz else '❌ Failed'}")
    log_message(f"  🏈 Gridiron11: {'✅ ' + gridiron11_quiz if gridiron11_quiz else '❌ Failed or Skipped'}")
    
    log_message("🎯 Daily game updates completed!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_message(f"💥 Critical error during update: {e}", "CRITICAL")
        sys.exit(1)
