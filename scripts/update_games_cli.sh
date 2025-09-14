#!/bin/bash
# PythonAnywhere Game Update Script - Robust Environment Setup
# This script handles all PythonAnywhere task environment issues

# Set up logging first (absolute paths only)
LOG_FILE="/home/devgreeny/logs/game_update_task.log"
mkdir -p /home/devgreeny/logs

# Function to log with timestamp
log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_msg "=== GAME UPDATE TASK STARTED ==="
log_msg "Task PID: $$"
log_msg "User: $(whoami)"
log_msg "Initial working directory: $(pwd)"

# Navigate to project directory (absolute path)
PROJECT_DIR="/home/devgreeny/wheredhego_v1"
log_msg "Changing to project directory: $PROJECT_DIR"

if [ ! -d "$PROJECT_DIR" ]; then
    log_msg "ERROR: Project directory does not exist: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR" || {
    log_msg "ERROR: Failed to change to project directory"
    exit 1
}

log_msg "Current directory: $(pwd)"
log_msg "Directory contents: $(ls -la | head -5)"

# Check if virtualenv exists and activate it
VENV_PATH="/home/devgreeny/.virtualenvs/wheredhego"
if [ -d "$VENV_PATH" ]; then
    log_msg "Activating virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
    log_msg "Virtual environment activated. Python path: $(which python)"
    log_msg "Python version: $(python --version)"
else
    log_msg "No virtual environment found at $VENV_PATH, using system Python"
    log_msg "System Python version: $(python3.10 --version)"
fi

# Set environment variables (absolute paths)
export FLASK_APP="run:app"
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

log_msg "Environment variables set:"
log_msg "  FLASK_APP=$FLASK_APP"
log_msg "  PYTHONPATH=$PYTHONPATH"
log_msg "  PWD=$(pwd)"

# Check if Flask app can be imported
log_msg "Testing Flask app import..."
if python3.10 -c "from run import app; print('Flask app imported successfully')" 2>> "$LOG_FILE"; then
    log_msg "✅ Flask app import successful"
else
    log_msg "❌ Flask app import failed - check the error above"
    exit 1
fi

# Check if Flask CLI is working
log_msg "Testing Flask CLI..."
if python3.10 -m flask --help > /dev/null 2>> "$LOG_FILE"; then
    log_msg "✅ Flask CLI working"
else
    log_msg "❌ Flask CLI not working - check the error above"
    exit 1
fi

# Run the actual game update command
log_msg "Starting game update..."
if python3.10 -m flask update-games 2>> "$LOG_FILE"; then
    log_msg "✅ Game update completed successfully"
    EXIT_CODE=0
else
    log_msg "❌ Game update failed with exit code: $?"
    EXIT_CODE=1
fi

log_msg "=== GAME UPDATE TASK FINISHED (Exit Code: $EXIT_CODE) ==="
exit $EXIT_CODE
