#!/usr/bin/env python3
"""
Flask CLI Commands for Game Updates - PythonAnywhere Compatible
Provides CLI commands for updating games that can be used with PythonAnywhere's task scheduler.

Commands:
    flask update-games          # Update both games
    flask update-starting5      # Update only Starting5
    flask update-gridiron11     # Update only Skill Positions (gridiron11)
    flask update-games --dry-run # Preview what would be updated

Usage in PythonAnywhere Tasks:
    python3.10 -m flask --app run:app update-games
"""

import os
import random
import shutil
import sys
import click
from datetime import datetime
from pathlib import Path
from flask import current_app
from flask.cli import with_appcontext


# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
def get_project_root():
    """Get the project root directory dynamically."""
    # When running as Flask CLI, we need to find the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from app/ to project root
    return os.path.dirname(current_dir)

def get_quiz_directories():
    """Get quiz directory paths."""
    project_root = get_project_root()
    
    return {
        'starting5': {
            'preloaded': os.path.join(project_root, "quizzes", "starting5", "preloaded"),
            'current': os.path.join(project_root, "quizzes", "starting5", "current"),
            'archive': os.path.join(project_root, "quizzes", "starting5", "archive"),
            'bonus': os.path.join(project_root, "quizzes", "starting5", "bonus")
        },
        'gridiron11': {
            'preloaded': os.path.join(project_root, "quizzes", "gridiron11", "preloaded"),
            'current': os.path.join(project_root, "quizzes", "gridiron11", "current"),
            'archive': os.path.join(project_root, "quizzes", "gridiron11", "archive")
        },
        'starting11': {
            'preloaded': os.path.join(project_root, "quizzes", "starting11", "preloaded"),
            'current': os.path.join(project_root, "quizzes", "starting11", "current"),
            'archive': os.path.join(project_root, "quizzes", "starting11", "archive")
        }
    }


# ─── UTILITY FUNCTIONS ─────────────────────────────────────────────────────────
def log_message(message: str, level: str = "INFO"):
    """Log a message with timestamp and level."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {level}: {message}"
    
    # Print to console
    if level == "ERROR" or level == "CRITICAL":
        click.echo(click.style(formatted_message, fg='red'), err=True)
    elif level == "WARNING":
        click.echo(click.style(formatted_message, fg='yellow'))
    elif level == "SUCCESS":
        click.echo(click.style(formatted_message, fg='green'))
    else:
        click.echo(formatted_message)
    
    # Also log to Flask logger if available
    if current_app:
        if level == "ERROR" or level == "CRITICAL":
            current_app.logger.error(message)
        elif level == "WARNING":
            current_app.logger.warning(message)
        else:
            current_app.logger.info(message)

def ensure_directories(*dirs):
    """Ensure all specified directories exist."""
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)

def get_json_files(directory: str) -> list:
    """Get all JSON files from a directory."""
    if not os.path.exists(directory):
        return []
    return [f for f in os.listdir(directory) if f.lower().endswith(".json")]

def archive_quiz_files(current_dir: str, archive_dir: str, game_name: str, dry_run: bool = False):
    """Archive existing quiz files from current to archive directory."""
    ensure_directories(current_dir, archive_dir)
    
    existing_files = get_json_files(current_dir)
    if not existing_files:
        log_message(f"No existing {game_name} quiz files to archive")
        return
    
    for old_file in existing_files:
        old_path = os.path.join(current_dir, old_file)
        archive_path = os.path.join(archive_dir, old_file)
        
        if dry_run:
            log_message(f"[DRY RUN] Would archive {game_name} quiz: {old_file}")
            continue
        
        try:
            shutil.move(old_path, archive_path)
            log_message(f"📦 Archived {game_name} quiz: {old_file}", "SUCCESS")
        except Exception as e:
            log_message(f"⚠️ Could not archive {game_name} quiz '{old_file}': {e}", "ERROR")

def update_quiz_files(preloaded_dir: str, current_dir: str, game_name: str, dry_run: bool = False) -> str:
    """Select and move a random quiz from preloaded to current directory."""
    ensure_directories(preloaded_dir, current_dir)
    
    available_quizzes = get_json_files(preloaded_dir)
    if not available_quizzes:
        log_message(f"❌ No {game_name} quizzes found in preloaded directory", "ERROR")
        return None
    
    chosen_quiz = random.choice(available_quizzes)
    src_path = os.path.join(preloaded_dir, chosen_quiz)
    dest_path = os.path.join(current_dir, chosen_quiz)
    
    if dry_run:
        log_message(f"[DRY RUN] Would update {game_name} quiz: {chosen_quiz}")
        return chosen_quiz
    
    try:
        shutil.move(src_path, dest_path)
        log_message(f"✅ Updated {game_name} quiz: {chosen_quiz}", "SUCCESS")
        return chosen_quiz
    except Exception as e:
        log_message(f"❌ Failed to update {game_name} quiz '{chosen_quiz}': {e}", "ERROR")
        return None

def prepare_bonus_quiz(preloaded_dir: str, bonus_dir: str, exclude_file: str = None, dry_run: bool = False):
    """Prepare a bonus quiz for Starting5."""
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
    
    if dry_run:
        log_message(f"[DRY RUN] Would prepare bonus quiz: {chosen_bonus}")
        return
    
    try:
        shutil.copy(src_path, dest_path)
        log_message(f"✅ Prepared bonus quiz: {chosen_bonus}", "SUCCESS")
    except Exception as e:
        log_message(f"⚠️ Failed to prepare bonus quiz '{chosen_bonus}': {e}", "ERROR")


# ─── GAME UPDATE FUNCTIONS ─────────────────────────────────────────────────────
def update_starting5_game(dry_run: bool = False):
    """Update Starting5 basketball game."""
    log_message("🏀 Starting Starting5 update...")
    
    dirs = get_quiz_directories()['starting5']
    
    # Archive yesterday's quiz
    archive_quiz_files(dirs['current'], dirs['archive'], "Starting5", dry_run)
    
    # Update current quiz
    chosen_quiz = update_quiz_files(dirs['preloaded'], dirs['current'], "Starting5", dry_run)
    
    # Prepare bonus quiz
    if chosen_quiz:
        prepare_bonus_quiz(dirs['preloaded'], dirs['bonus'], chosen_quiz, dry_run)
    
    log_message("🏀 Starting5 update completed", "SUCCESS")
    return chosen_quiz

def update_gridiron11_game(dry_run: bool = False):
    """Update Skill Positions NFL game (gridiron11)."""
    log_message("🏈 Starting Skill Positions update...")
    
    dirs = get_quiz_directories()['gridiron11']
    
    # Check if preloaded directory has quiz files
    if not get_json_files(dirs['preloaded']):
        log_message("⚠️ No Skill Positions quiz files found in preloaded directory", "WARNING")
        log_message("🏈 Skill Positions update skipped - no quiz files available")
        return None
    
    # Archive yesterday's quiz
    archive_quiz_files(dirs['current'], dirs['archive'], "Skill Positions", dry_run)
    
    # Update current quiz
    chosen_quiz = update_quiz_files(dirs['preloaded'], dirs['current'], "Skill Positions", dry_run)
    
    log_message("🏈 Skill Positions update completed", "SUCCESS")
    return chosen_quiz

def update_starting11_game(dry_run: bool = False):
    """Update Starting11 soccer/football game."""
    log_message("⚽ Starting Starting11 update...")
    
    dirs = get_quiz_directories()['starting11']
    
    # Check if preloaded directory has quiz files
    if not get_json_files(dirs['preloaded']):
        log_message("⚠️ No Starting11 quiz files found in preloaded directory", "WARNING")
        log_message("⚽ Starting11 update skipped - no quiz files available")
        return None
    
    # Archive yesterday's quiz
    archive_quiz_files(dirs['current'], dirs['archive'], "Starting11", dry_run)
    
    # Update current quiz
    chosen_quiz = update_quiz_files(dirs['preloaded'], dirs['current'], "Starting11", dry_run)
    
    log_message("⚽ Starting11 update completed", "SUCCESS")
    return chosen_quiz


# ─── CLI COMMANDS ─────────────────────────────────────────────────────────────
@click.command('update-games')
@click.option('--dry-run', is_flag=True, help='Preview what would be updated without making changes')
@click.option('--games', default='all', type=click.Choice(['all', 'starting5', 'gridiron11', 'starting11']), 
              help='Which games to update')
@with_appcontext
def update_games_command(dry_run, games):
    """Update game quizzes (all games by default)."""
    if dry_run:
        log_message("🔍 DRY RUN MODE - No changes will be made")
    
    log_message("🚀 Starting game updates...")
    log_message(f"Project root: {get_project_root()}")
    
    starting5_quiz = None
    gridiron11_quiz = None
    starting11_quiz = None
    
    # Update games based on selection
    if games in ['all', 'starting5']:
        starting5_quiz = update_starting5_game(dry_run)
    
    if games in ['all', 'gridiron11']:
        gridiron11_quiz = update_gridiron11_game(dry_run)
    
    if games in ['all', 'starting11']:
        starting11_quiz = update_starting11_game(dry_run)
    
    # Summary
    log_message("📊 Update Summary:")
    if games in ['all', 'starting5']:
        status = '✅ ' + starting5_quiz if starting5_quiz else '❌ Failed'
        if dry_run and starting5_quiz:
            status = f'🔍 Would update: {starting5_quiz}'
        log_message(f"  🏀 Starting5: {status}")
    
    if games in ['all', 'gridiron11']:
        status = '✅ ' + gridiron11_quiz if gridiron11_quiz else '❌ Failed or Skipped'
        if dry_run and gridiron11_quiz:
            status = f'🔍 Would update: {gridiron11_quiz}'
        log_message(f"  🏈 Skill Positions: {status}")
    
    if games in ['all', 'starting11']:
        status = '✅ ' + starting11_quiz if starting11_quiz else '❌ Failed or Skipped'
        if dry_run and starting11_quiz:
            status = f'🔍 Would update: {starting11_quiz}'
        log_message(f"  ⚽ Starting11: {status}")
    
    action = "preview completed" if dry_run else "updates completed"
    log_message(f"🎯 Game {action}!", "SUCCESS")

@click.command('update-starting5')
@click.option('--dry-run', is_flag=True, help='Preview what would be updated without making changes')
@with_appcontext
def update_starting5_command(dry_run):
    """Update only the Starting5 basketball game."""
    if dry_run:
        log_message("🔍 DRY RUN MODE - No changes will be made")
    
    quiz = update_starting5_game(dry_run)
    action = "preview" if dry_run else "update"
    status = "completed" if quiz else "failed"
    log_message(f"🏀 Starting5 {action} {status}!", "SUCCESS" if quiz else "ERROR")

@click.command('update-gridiron11')
@click.option('--dry-run', is_flag=True, help='Preview what would be updated without making changes')
@with_appcontext
def update_gridiron11_command(dry_run):
    """Update only the Skill Positions NFL game."""
    if dry_run:
        log_message("🔍 DRY RUN MODE - No changes will be made")
    
    quiz = update_gridiron11_game(dry_run)
    action = "preview" if dry_run else "update"
    status = "completed" if quiz else "failed"
    log_message(f"🏈 Skill Positions {action} {status}!", "SUCCESS" if quiz else "ERROR")

@click.command('update-starting11')
@click.option('--dry-run', is_flag=True, help='Preview what would be updated without making changes')
@with_appcontext
def update_starting11_command(dry_run):
    """Update only the Starting11 soccer game."""
    if dry_run:
        log_message("🔍 DRY RUN MODE - No changes will be made")
    
    quiz = update_starting11_game(dry_run)
    action = "preview" if dry_run else "update"
    status = "completed" if quiz else "failed"
    log_message(f"⚽ Starting11 {action} {status}!", "SUCCESS" if quiz else "ERROR")

@click.command('game-status')
@with_appcontext
def game_status_command():
    """Check the current status of game quizzes."""
    log_message("📊 Game Status Report")
    
    dirs = get_quiz_directories()
    
    # Starting5 status
    log_message("🏀 Starting5 Status:")
    current_s5 = get_json_files(dirs['starting5']['current'])
    preloaded_s5 = get_json_files(dirs['starting5']['preloaded'])
    bonus_s5 = get_json_files(dirs['starting5']['bonus'])
    
    log_message(f"  Current quiz: {current_s5[0] if current_s5 else 'None'}")
    log_message(f"  Preloaded quizzes: {len(preloaded_s5)} available")
    log_message(f"  Bonus quiz: {bonus_s5[0] if bonus_s5 else 'None'}")
    
    # Skill Positions status
    log_message("🏈 Skill Positions Status:")
    current_g11 = get_json_files(dirs['gridiron11']['current'])
    preloaded_g11 = get_json_files(dirs['gridiron11']['preloaded'])
    
    log_message(f"  Current quiz: {current_g11[0] if current_g11 else 'None'}")
    log_message(f"  Preloaded quizzes: {len(preloaded_g11)} available")
    
    # Starting11 status
    log_message("⚽ Starting11 Status:")
    current_s11 = get_json_files(dirs['starting11']['current'])
    preloaded_s11 = get_json_files(dirs['starting11']['preloaded'])
    
    log_message(f"  Current quiz: {current_s11[0] if current_s11 else 'None'}")
    log_message(f"  Preloaded quizzes: {len(preloaded_s11)} available")


# ─── REGISTRATION FUNCTION ─────────────────────────────────────────────────────
def register_cli_commands(app):
    """Register all CLI commands with the Flask app."""
    app.cli.add_command(update_games_command)
    app.cli.add_command(update_starting5_command)
    app.cli.add_command(update_gridiron11_command)
    app.cli.add_command(update_starting11_command)
    app.cli.add_command(game_status_command)
    
    app.logger.info("Game update CLI commands registered successfully")


# ─── STANDALONE EXECUTION ─────────────────────────────────────────────────────
if __name__ == "__main__":
    # This allows the script to be run standalone for testing
    import sys
    
    # Simple command line interface for testing
    if len(sys.argv) > 1:
        command = sys.argv[1]
        dry_run = '--dry-run' in sys.argv
        
        if command == 'update-games':
            starting5_quiz = update_starting5_game(dry_run)
            gridiron11_quiz = update_gridiron11_game(dry_run)
            starting11_quiz = update_starting11_game(dry_run)
            
            log_message("📊 Update Summary:")
            log_message(f"  🏀 Starting5: {'✅ ' + starting5_quiz if starting5_quiz else '❌ Failed'}")
            log_message(f"  🏈 Skill Positions: {'✅ ' + gridiron11_quiz if gridiron11_quiz else '❌ Failed or Skipped'}")
            log_message(f"  ⚽ Starting11: {'✅ ' + starting11_quiz if starting11_quiz else '❌ Failed or Skipped'}")
            
        elif command == 'update-starting5':
            quiz = update_starting5_game(dry_run)
            log_message(f"🏀 Starting5: {'✅ ' + quiz if quiz else '❌ Failed'}")
            
        elif command == 'update-gridiron11':
            quiz = update_gridiron11_game(dry_run)
            log_message(f"🏈 Skill Positions: {'✅ ' + quiz if quiz else '❌ Failed'}")
            
        elif command == 'update-starting11':
            quiz = update_starting11_game(dry_run)
            log_message(f"⚽ Starting11: {'✅ ' + quiz if quiz else '❌ Failed'}")
            
        else:
            log_message(f"Unknown command: {command}", "ERROR")
            log_message("Available commands: update-games, update-starting5, update-gridiron11, update-starting11")
    else:
        log_message("Usage: python tasks.py [command] [--dry-run]")
        log_message("Commands: update-games, update-starting5, update-gridiron11, update-starting11")
