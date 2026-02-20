# Automated Quiz Generation Setup

This document explains how to set up fully automated daily quiz generation for WheredHeGo.

## Overview

The system uses **GitHub Actions** to automatically generate new quizzes daily and **PythonAnywhere** to serve them. This is completely hands-off once configured.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Daily Flow (4:00 AM UTC)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   GitHub Actions                     PythonAnywhere              │
│   ─────────────────                  ──────────────              │
│                                                                  │
│   1. Generate new NBA quiz  ────────►  4:30 AM: Pull from GitHub │
│   2. Generate new NFL quiz            │                          │
│   3. AI selects avatars               5. Rotate daily quizzes    │
│   4. Commit & push to repo            6. Serve to users          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Setup Instructions

### Step 1: Set Up GitHub Repository

If you haven't already, push your code to GitHub:

```bash
cd wheredhego
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/wheredhego.git
git push -u origin main
```

### Step 2: Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secret:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude API key for AI avatar selection (optional) |

> **Note:** The AI avatar selection is optional. Without it, avatars will be randomly assigned.

### Step 3: Enable GitHub Actions

The workflow file is already created at `.github/workflows/daily-quiz-generation.yml`.

It will:
- Run daily at 4:00 AM UTC (midnight EST)
- Generate 1 new NBA quiz
- Generate 1 new NFL quiz  
- Use AI to select appropriate avatars (if API key provided)
- Commit and push new quizzes to the repo

You can also manually trigger it from the "Actions" tab.

### Step 4: Set Up PythonAnywhere Sync

1. **SSH into PythonAnywhere** or use the web console

2. **Clone your repository** (if not already):
   ```bash
   cd ~
   git clone https://github.com/YOUR_USERNAME/wheredhego.git
   ```

3. **Set up the scheduled task**:
   - Go to PythonAnywhere Dashboard → Tasks
   - Add a new scheduled task
   - Time: `04:30` (UTC) - 30 minutes after GitHub Action
   - Command:
     ```
     cd /home/YOUR_USERNAME/wheredhego && /usr/bin/python3 scripts/sync_from_github.py
     ```

4. **Test the sync**:
   ```bash
   cd ~/wheredhego
   python scripts/sync_from_github.py
   ```

## How It Works

### Quiz Generation (`scripts/auto_generate_quiz.py`)

1. **NBA Quiz Generation**:
   - Fetches random game from NBA API (seasons 2010-2024)
   - Gets starting 5 lineup
   - Validates all players attended college (in our database)
   - AI selects avatars based on player appearance
   - Saves to `quizzes/starting5/preloaded/`

2. **NFL Quiz Generation**:
   - Scrapes Pro Football Reference
   - Gets skill position players (QB, RB, WR, TE)
   - Validates colleges in our database
   - AI selects avatars
   - Saves to `quizzes/gridiron11/preloaded/`

### AI Avatar Selection

When `ANTHROPIC_API_KEY` is set, the system uses Claude to select appropriate avatars:

```python
# Example prompt sent to Claude:
"Based on your knowledge of what LeBron James looks like (skin tone, facial hair, hair style),
which avatar number (01-14) would be the best match?"
```

This ensures characters roughly match the real player's appearance.

### Quiz Rotation (`scripts/update_games.py`)

Runs daily to:
1. Archive yesterday's quiz
2. Move a new quiz from `preloaded/` to `current/`
3. Prepare bonus quiz (NBA only)

### GitHub Sync (`scripts/sync_from_github.py`)

Runs on PythonAnywhere to:
1. Pull latest changes from GitHub
2. Run quiz rotation
3. Log inventory levels

## Monitoring

### Check Quiz Inventory

```bash
# On PythonAnywhere
ls quizzes/starting5/preloaded/ | wc -l   # NBA quiz count
ls quizzes/gridiron11/preloaded/ | wc -l  # NFL quiz count
```

### View Sync Logs

```bash
cat logs/sync.log | tail -50
```

### Check GitHub Actions

Go to your repository → Actions tab to see workflow runs.

## Troubleshooting

### "No quizzes generated"

- **NBA**: The NBA API can be rate-limited. The script retries multiple seasons.
- **NFL**: Web scraping can fail if the site structure changes.

Check the GitHub Actions log for specific errors.

### "Git pull failed"

- Make sure PythonAnywhere has access to your repo
- Check if you need to set up SSH keys or use HTTPS with a token

### "Low quiz inventory"

The system warns when fewer than 5 quizzes remain. You can manually generate more:

```bash
# On your local machine with good API access
python scripts/auto_generate_quiz.py --game nba --count 10
python scripts/auto_generate_quiz.py --game nfl --count 10
git add quizzes/
git commit -m "Add more quizzes"
git push
```

## Configuration

### Change Schedule

Edit `.github/workflows/daily-quiz-generation.yml`:

```yaml
on:
  schedule:
    - cron: '0 4 * * *'  # 4:00 AM UTC
```

[Cron syntax reference](https://crontab.guru/)

### Generate More Quizzes

To increase quiz generation per run:

```yaml
- name: Generate NBA Quiz
  run: |
    python scripts/auto_generate_quiz.py --game nba --count 2
```

### Disable AI Avatars

Remove or don't set `ANTHROPIC_API_KEY` - avatars will be randomly assigned.

## Cost Estimate

| Service | Cost |
|---------|------|
| GitHub Actions | Free (2000 mins/month) |
| PythonAnywhere | Free tier or $5/month |
| Claude API (optional) | ~$0.01/day (10 players × $0.001/call) |

**Total: Free to ~$3/month**

## Files Reference

| File | Purpose |
|------|---------|
| `.github/workflows/daily-quiz-generation.yml` | GitHub Actions workflow |
| `scripts/auto_generate_quiz.py` | Automated quiz generator |
| `scripts/sync_from_github.py` | PythonAnywhere sync script |
| `scripts/update_games.py` | Quiz rotation script |
| `logs/sync.log` | Sync operation logs |
