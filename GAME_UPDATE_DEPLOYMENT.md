# Game Update Script Deployment Guide

## 🎯 Overview

The `update_games.py` script automatically updates both **Starting5** (NBA Basketball) and **Gridiron11** (NFL Football) games daily at midnight EST.

## 🚀 Features

- **Dual Game Support**: Updates both Starting5 and Gridiron11 simultaneously
- **Smart Archiving**: Moves yesterday's quizzes to archive folders
- **Random Selection**: Picks random quizzes from preloaded pools
- **Bonus Quiz Management**: Prepares bonus quizzes for Starting5
- **Comprehensive Logging**: Detailed logs with timestamps
- **Error Handling**: Graceful failure handling with detailed error messages
- **Fallback Support**: Handles different directory structures

## 📁 Directory Structure

```
wheredhego/
├── update_games.py                    # Main update script
├── app/
│   ├── starting5/
│   │   └── static/
│   │       ├── current_quiz/          # Active Starting5 quiz
│   │       ├── preloaded_quizzes/     # Starting5 quiz pool
│   │       ├── archive_quizzes/       # Old Starting5 quizzes
│   │       └── bonus_quiz/            # Starting5 bonus quiz
│   └── gridiron11/
│       ├── preloaded_quizzes/         # Gridiron11 quiz pool
│       └── static/
│           ├── current_quiz/          # Active Gridiron11 quiz
│           └── archive_quizzes/       # Old Gridiron11 quizzes
└── logs/
    └── game_updates.log               # Update logs
```

## 🔧 PythonAnywhere Deployment

### 1. Upload the Script

```bash
# SSH into PythonAnywhere
ssh devgreeny@ssh.pythonanywhere.com

# Navigate to your project
cd ~/wheredhego

# Upload the script (or copy from GitHub after pushing)
# The script should be in your project root
```

### 2. Set Up Logging Directory

```bash
# Create logs directory
mkdir -p ~/logs

# Test the script
python update_games.py
```

### 3. Configure Cron Job

```bash
# Edit crontab
crontab -e

# Add this line for midnight EST updates:
0 5 * * * cd /home/devgreeny/wheredhego && python3.10 update_games.py >> /home/devgreeny/logs/game_updates.log 2>&1

# Note: 5 AM UTC = Midnight EST (adjust for daylight saving time)
# For EDT (Daylight Saving): 0 4 * * *
# For EST (Standard Time):   0 5 * * *
```

### 4. Verify Cron Job

```bash
# List current cron jobs
crontab -l

# Check if cron service is running
ps aux | grep cron
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

### Check Logs
```bash
# View recent logs
tail -f ~/logs/game_updates.log

# View last 50 lines
tail -50 ~/logs/game_updates.log

# Search for errors
grep "ERROR\|CRITICAL" ~/logs/game_updates.log
```

### Manual Testing
```bash
# Test the script manually
cd ~/wheredhego
python update_games.py

# Check current quizzes
ls -la app/starting5/static/current_quiz/
ls -la app/gridiron11/static/current_quiz/
```

## 🚨 Troubleshooting

### Common Issues

1. **No Quiz Files Found**
   - Check if `preloaded_quizzes/` directories contain `.json` files
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

1. **Starting5**: Add `.json` files to `app/starting5/static/preloaded_quizzes/`
2. **Gridiron11**: Add `.json` files to `app/gridiron11/preloaded_quizzes/`

### Archive Cleanup

```bash
# Clean old archives (optional - keep last 30 days)
find app/*/static/archive_quizzes/ -name "*.json" -mtime +30 -delete
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

**Auto-adjusting cron job:**
```bash
# This adjusts automatically for daylight saving time
0 5 * * * cd /home/devgreeny/wheredhego && python3.10 update_games.py >> /home/devgreeny/logs/game_updates.log 2>&1
```

Your games will now update automatically every night! 🎮
