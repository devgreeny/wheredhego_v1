#!/bin/bash
# PythonAnywhere Game Update Script
# This script calls the Flask CLI command to update games
# Use this in PythonAnywhere's scheduled tasks

# Set up environment and logging
echo "Task started at $(date)" >> /home/devgreeny/logs/task_debug.log

# Ensure logs directory exists
mkdir -p /home/devgreeny/logs

# Navigate to project directory
cd /home/devgreeny/wheredhego_v1
echo "Changed to directory: $(pwd)" >> /home/devgreeny/logs/task_debug.log

# Set Flask app environment variable
export FLASK_APP=run:app
export PYTHONPATH=/home/devgreeny/wheredhego_v1:$PYTHONPATH

# Log environment info
echo "FLASK_APP=$FLASK_APP" >> /home/devgreeny/logs/task_debug.log
echo "Python version: $(python3.10 --version)" >> /home/devgreeny/logs/task_debug.log

# Run the game update command with full output logging
python3.10 -m flask update-games >> /home/devgreeny/logs/task_debug.log 2>&1

# Log completion
echo "Task completed at $(date) with exit code: $?" >> /home/devgreeny/logs/task_debug.log
