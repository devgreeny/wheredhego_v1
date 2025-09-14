#!/bin/bash
# PythonAnywhere Game Update Script
# This script calls the Flask CLI command to update games
# Use this in PythonAnywhere's scheduled tasks

# Set up environment
cd /home/devgreeny/wheredhego

# Activate virtual environment if needed (uncomment if using venv)
# source venv/bin/activate

# Set Flask app
export FLASK_APP=run:app

# Run the game update command
python3.10 -m flask update-games

# Log completion
echo "Game update task completed at $(date)" >> /home/devgreeny/logs/task_completions.log
