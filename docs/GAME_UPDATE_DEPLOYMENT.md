# Game Update Task Deployment Guide

## 🎯 Overview

The game update system provides **Flask CLI commands** for updating both **Starting5** (NBA Basketball) and **Gridiron11** (NFL Football) games. This system replaces the previous script-based approach with a more robust Flask-integrated solution.

## 🚀 Features

- **Flask CLI Integration**: Native Flask commands with proper app context
- **Dual Game Support**: Updates both Starting5 and Gridiron11 simultaneously
- **Smart Archiving**: Moves yesterday's quizzes to archive folders
- **Random Selection**: Picks random quizzes from preloaded pools
- **Bonus Quiz Management**: Prepares bonus quizzes for Starting5
- **Dry Run Mode**: Preview updates without making changes
- **Selective Updates**: Update individual games or both
- **Status Checking**: View current quiz status
- **Comprehensive Logging**: Detailed logs with timestamps and colors
- **Error Handling**: Graceful failure handling with detailed error messages
- **PythonAnywhere Compatible**: Designed specifically for PythonAnywhere's task system

## 📁 Directory Structure

```
wheredhego/
├── app/
│   └── tasks.py                       # Flask CLI commands
├── scripts/
│   ├── update_games.py               # Legacy script (backup)
│   ├── update_games_cli.sh           # Main PythonAnywhere task script
│   ├── update_starting5.sh           # Starting5 only
│   ├── update_gridiron11.sh          # Gridiron11 only
│   └── check_game_status.sh          # Status check
├── quizzes/                           # Organized quiz data
│   ├── starting5/
│   │   ├── current/                   # Active Starting5 quiz
│   │   ├── preloaded/                 # Starting5 quiz pool
│   │   ├── archive/                   # Old Starting5 quizzes
│   │   └── bonus/                     # Starting5 bonus quiz
│   └── gridiron11/
│       ├── current/                   # Active Gridiron11 quiz
│       ├── preloaded/                 # Gridiron11 quiz pool
│       └── archive/                   # Old Gridiron11 quizzes
└── logs/
    └── game_updates.log               # Update logs
```

## 🔧 PythonAnywhere Deployment

### 1. Available Commands

The new Flask CLI system provides several commands:

```bash
# Update both games
flask update-games

# Update individual games
flask update-starting5
flask update-gridiron11

# Preview changes (dry run)
flask update-games --dry-run
flask update-starting5 --dry-run

# Check current status
flask game-status

# Update specific games only
flask update-games --games=starting5
flask update-games --games=gridiron11
```

### 2. Setup Flask App Environment

```bash
# SSH into PythonAnywhere
ssh devgreeny@ssh.pythonanywhere.com

# Navigate to your project
cd ~/wheredhego

# Set Flask app environment variable
export FLASK_APP=run:app

# Test the commands
python3.10 -m flask game-status
python3.10 -m flask update-games --dry-run
```

### 3. PythonAnywhere Task Configuration

**For the Scheduled Tasks interface, use one of these commands:**

**Option 1: Main update script (recommended)**
```bash
/bin/bash /home/devgreeny/wheredhego/scripts/update_games_cli.sh
```

**Option 2: Direct Flask command**
```bash
python3.10 /home/devgreeny/wheredhego/scripts/update_games_cli.sh
```

**Option 3: Individual game updates**
```bash
# For Starting5 only
/bin/bash /home/devgreeny/wheredhego/scripts/update_starting5.sh

# For Gridiron11 only  
/bin/bash /home/devgreeny/wheredhego/scripts/update_gridiron11.sh
```

### 4. PythonAnywhere Task Settings

- **Frequency**: Daily
- **Time**: 22:20 (10:20 PM UTC = ~6:20 PM EDT / 5:20 PM EST)
- **Command**: `/bin/bash /home/devgreeny/wheredhego/scripts/update_games_cli.sh`
- **Description**: Update Games!

### 5. Manual Testing

```bash
# Test individual commands
cd ~/wheredhego
export FLASK_APP=run:app

# Check status
python3.10 -m flask game-status

# Test dry run
python3.10 -m flask update-games --dry-run

# Test actual update
python3.10 -m flask update-games

# Test individual game
python3.10 -m flask update-starting5
```

## 📊 Script Behavior

### Starting5 Updates
1. **Archive**: Moves current quiz to `archive_quizzes/`
2. **Update**: Selects random quiz from `preloaded_quizzes/`
3. **Bonus**: Prepares a different random quiz for bonus mode

### Gridiron11 Updates
1. **Archive**: Moves current quiz to `archive_quizzes/`
2. **Update**: Selects random quiz from `preloaded_quizzes/`
3. **Fallback**: Uses standalone directory if app version unavailable

## 🔍 Monitoring

### Check Flask CLI Status
```bash
cd ~/wheredhego
export FLASK_APP=run:app

# Check current game status
python3.10 -m flask game-status

# Preview what would be updated
python3.10 -m flask update-games --dry-run
```

### Check Logs
```bash
# View recent task logs
tail -f ~/logs/game_updates.log
tail -f ~/logs/task_completions.log

# View last 50 lines
tail -50 ~/logs/game_updates.log

# Search for errors
grep "ERROR\|CRITICAL" ~/logs/game_updates.log
```

### Manual Testing
```bash
# Test Flask commands manually
cd ~/wheredhego
export FLASK_APP=run:app

# Check status first
python3.10 -m flask game-status

# Test with dry run
python3.10 -m flask update-games --dry-run

# Run actual update
python3.10 -m flask update-games

# Check current quizzes
ls -la quizzes/starting5/current/
ls -la quizzes/gridiron11/current/
```

## 🚨 Troubleshooting

### Common Issues

1. **No Quiz Files Found**
   - Check if `quizzes/*/preloaded/` directories contain `.json` files
   - Verify file permissions

2. **Permission Errors**
   ```bash
   chmod +x update_games.py
   chmod -R 755 app/*/static/
   ```

3. **Cron Job Not Running**
   - Check cron logs: `grep CRON /var/log/syslog`
   - Verify timezone settings
   - Test with a temporary frequent schedule

4. **Path Issues**
   - Ensure the script uses absolute paths
   - Check `PROJECT_ROOT` variable in script

### Log Analysis

**Successful Update:**
```
[2025-09-12 05:00:01] INFO: 🚀 Starting daily game updates...
[2025-09-12 05:00:01] INFO: ✅ Updated Starting5 quiz: 2023-24_0022300548_CHI.json
[2025-09-12 05:00:01] INFO: ✅ Updated Gridiron11 quiz: players_20250816_213147.json
[2025-09-12 05:00:01] INFO: 🎯 Daily game updates completed!
```

**Error Example:**
```
[2025-09-12 05:00:01] ERROR: ❌ No Starting5 quizzes found in preloaded directory
[2025-09-12 05:00:01] CRITICAL: 💥 Critical error during update: No quiz files available
```

## 📈 Maintenance

### Adding New Quiz Files

1. **Starting5**: Add `.json` files to `quizzes/starting5/preloaded/`
2. **Gridiron11**: Add `.json` files to `quizzes/gridiron11/preloaded/`

### Archive Cleanup

```bash
# Clean old archives (optional - keep last 30 days)
find quizzes/*/archive/ -name "*.json" -mtime +30 -delete
```

### Log Rotation

```bash
# Rotate logs monthly (optional)
mv ~/logs/game_updates.log ~/logs/game_updates_$(date +%Y%m).log
touch ~/logs/game_updates.log
```

## 🎯 Production Schedule

- **Frequency**: Daily at midnight EST
- **Duration**: ~1-2 seconds per update
- **Impact**: Zero downtime (files updated atomically)
- **Monitoring**: Check logs daily for any issues

## 🔄 Timezone Considerations

**EST/EDT Conversion for Cron:**
- **EST (Nov-Mar)**: `0 5 * * *` (5 AM UTC = Midnight EST)
- **EDT (Mar-Nov)**: `0 4 * * *` (4 AM UTC = Midnight EDT)

**Current recommended cron job:**
```bash
# Set for 4 AM UTC (midnight EDT) - most of the year
0 4 * * * cd /home/devgreeny/wheredhego && python3.10 scripts/update_games.py >> /home/devgreeny/logs/game_updates.log 2>&1
```

## 🎯 Quick Setup Summary

### For PythonAnywhere Tasks Interface:

1. **Command to use**: `/bin/bash /home/devgreeny/wheredhego/scripts/update_games_cli.sh`
2. **Frequency**: Daily  
3. **Time**: 22:20 UTC (6:20 PM EDT)
4. **Description**: Update Games!

### Available Flask Commands:

```bash
# Main commands (with FLASK_APP=run:app)
python3.10 -m flask update-games           # Update both games
python3.10 -m flask update-starting5       # Update Starting5 only  
python3.10 -m flask update-gridiron11      # Update Gridiron11 only
python3.10 -m flask game-status            # Check current status

# With options
python3.10 -m flask update-games --dry-run                    # Preview changes
python3.10 -m flask update-games --games=starting5           # Update specific game
```

### Benefits of New System:

- ✅ **Flask Integration**: Proper app context and database access
- ✅ **Dry Run Mode**: Test changes before applying
- ✅ **Selective Updates**: Update individual games
- ✅ **Better Logging**: Colored output and structured logging  
- ✅ **Status Checking**: View current quiz status anytime
- ✅ **Error Handling**: More robust error handling and recovery
- ✅ **PythonAnywhere Ready**: Designed specifically for PA's task system

Your games will now update automatically every night with improved reliability! 🎮
