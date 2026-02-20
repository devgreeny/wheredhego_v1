#!/usr/bin/env python3
"""
GitHub Sync Script for PythonAnywhere
Pulls the latest quiz updates from GitHub repository.

This script should be run as a scheduled task on PythonAnywhere:
1. Go to the "Tasks" tab in PythonAnywhere dashboard
2. Add a new scheduled task
3. Set it to run at 4:30 UTC (30 minutes after GitHub Action)
4. Command: cd /home/YOUR_USERNAME/wheredhego && python scripts/sync_from_github.py

The script will:
1. Pull latest changes from GitHub (including new quizzes)
2. Run the update_games.py script to rotate quizzes
3. Log all operations

Usage:
    python sync_from_github.py
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "sync.log"


def log(message: str, level: str = "INFO"):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {level}: {message}"
    print(log_line)
    
    # Also write to log file
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")


def run_command(cmd: list, cwd: Path = None) -> tuple:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def main():
    log("🚀 Starting GitHub sync...")
    log(f"   Project root: {PROJECT_ROOT}")
    
    # Step 1: Pull from GitHub
    log("📥 Pulling latest changes from GitHub...")
    success, output = run_command(["git", "pull", "origin", "main"])
    
    if not success:
        # Try with 'master' branch
        success, output = run_command(["git", "pull", "origin", "master"])
    
    if success:
        log(f"✅ Git pull successful")
        if "Already up to date" in output:
            log("   No new changes")
        else:
            log(f"   Changes pulled")
    else:
        log(f"❌ Git pull failed: {output}", "ERROR")
        # Continue anyway - maybe just run update_games
    
    # Step 2: Run quiz rotation
    log("🔄 Running quiz rotation...")
    success, output = run_command([sys.executable, "scripts/update_games.py"])
    
    if success:
        log("✅ Quiz rotation complete")
    else:
        log(f"⚠️ Quiz rotation had issues: {output}", "WARNING")
    
    # Step 3: Check quiz counts
    log("📊 Checking quiz inventory...")
    
    nba_preloaded = PROJECT_ROOT / "quizzes" / "starting5" / "preloaded"
    nfl_preloaded = PROJECT_ROOT / "quizzes" / "gridiron11" / "preloaded"
    
    nba_count = len(list(nba_preloaded.glob("*.json"))) if nba_preloaded.exists() else 0
    nfl_count = len(list(nfl_preloaded.glob("*.json"))) if nfl_preloaded.exists() else 0
    
    log(f"   NBA quizzes available: {nba_count}")
    log(f"   NFL quizzes available: {nfl_count}")
    
    if nba_count < 5:
        log("⚠️ Low NBA quiz inventory!", "WARNING")
    if nfl_count < 5:
        log("⚠️ Low NFL quiz inventory!", "WARNING")
    
    log("✅ Sync complete!")


if __name__ == "__main__":
    main()
