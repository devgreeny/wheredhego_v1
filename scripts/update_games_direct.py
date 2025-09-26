#!/usr/bin/env python3.10
"""
Direct Python script for PythonAnywhere tasks
This bypasses Flask CLI and calls the update functions directly
"""

import os
import sys
from datetime import datetime

# Add the project root to Python path
project_root = '/home/devgreeny/wheredhego_v1'
sys.path.insert(0, project_root)

# Change to project directory
os.chdir(project_root)

def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    
    # Log to file
    os.makedirs('/home/devgreeny/logs', exist_ok=True)
    with open('/home/devgreeny/logs/direct_task.log', 'a') as f:
        f.write(log_line)
    
    # Also print to stdout
    print(log_line.strip())

try:
    log_message("🚀 Starting direct game update...")
    
    # Import Flask app to get context
    from run import app
    
    # Import the update functions
    from app.tasks import update_starting5_game, update_gridiron11_game
    
    # Run updates within Flask app context
    with app.app_context():
        log_message("🏀 Updating Starting5...")
        starting5_result = update_starting5_game()
        
        log_message("🏈 Updating Gridiron11...")
        gridiron11_result = update_gridiron11_game()
        
        # Log results
        log_message("📊 Update Summary:")
        log_message(f"  🏀 Starting5: {'✅ ' + starting5_result if starting5_result else '❌ Failed'}")
        log_message(f"  🏈 Gridiron11: {'✅ ' + gridiron11_result if gridiron11_result else '❌ Failed or Skipped'}")
        
        log_message("🎯 Direct game update completed successfully!")

except Exception as e:
    log_message(f"❌ Error during update: {str(e)}")
    import traceback
    log_message(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)
