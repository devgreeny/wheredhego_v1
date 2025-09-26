# Production Deployment Guide - wheredhego.com

## 🚀 Ready for Production!

Your CFB Creator Poll system is ready to deploy with the following features:
- ✅ **Week 3 Placeholder Rankings** with official team logos
- ✅ **Sunday 3pm → Thursday 3pm** voting cycle
- ✅ **Automatic week progression** (Week 3 → 4 → 5...)
- ✅ **No login required** - public voting
- ✅ **MySQL database** configured for production
- ✅ **Data persistence** - all polls and votes saved permanently

## 📊 Database Configuration

**Production Database:** `devgreeny$default`
- **Host:** `devgreeny.mysql.pythonanywhere-services.com`
- **User:** `devgreeny`
- **Password:** `lebron69`
- **Database:** `devgreeny$default`

## 🔧 Deployment Steps

### 1. Environment Setup on PythonAnywhere

Create `.env` file in your project root:
```bash
# Copy from production.env file
MYSQL_HOST=devgreeny.mysql.pythonanywhere-services.com
MYSQL_USER=devgreeny
MYSQL_PASSWORD=lebron69
MYSQL_DATABASE=devgreeny$default
SECRET_KEY=prod-secret-key-wheredhego-cfb-poll-2025
FLASK_ENV=production
```

### 2. Database Tables Creation

The app will automatically create these tables on first run:
- `poll` - Weekly polls (Week 3, 4, 5...)
- `vote` - Individual team votes
- `user_ballot` - Complete user ballots (JSON)
- `user` - User sessions (for guest tracking)

### 3. Static Files Configuration

Add these static file mappings in PythonAnywhere Web tab:

**Creator Poll Assets:**
- **URL:** `/creatorpoll/static/`
- **Directory:** `/home/yourusername/wheredhego/app/creatorpoll/static/`

**Team Logos:**
- **URL:** `/creatorpoll/logo/`
- **Directory:** `/home/yourusername/wheredhego/app/creatorpoll/static/Teams for Polls/logos/`

### 4. WSGI Configuration

Your `wsgi.py` is already configured - just update the path:
```python
path = '/home/devgreeny/wheredhego'  # Update with your username
```

## 📅 Current Poll Status

**Week 3 Poll (Active):**
- **Status:** Locked until Sunday, September 14 at 3:00 PM EST
- **Placeholder Rankings:** Ohio State, Penn State, LSU, Oregon, Miami... (Top 25)
- **Auto-opens:** Sunday 3pm EST for voting
- **Auto-locks:** Thursday 3pm EST
- **Auto-advances:** To Week 4 on next Sunday

## 🎯 What Happens After Deployment

1. **Immediate:** Users see Week 3 placeholder rankings with official logos
2. **Sunday 3pm EST:** Voting opens automatically, placeholders disappear
3. **Live Updates:** Real community rankings appear as votes come in
4. **Thursday 3pm EST:** Voting locks, results frozen
5. **Next Sunday 3pm EST:** Week 4 poll auto-creates and opens

## 🔍 Testing Checklist

After deployment, test these URLs:
- ✅ `https://wheredhego.com/creatorpoll/` - Homepage with Week 3 placeholder
- ✅ `https://wheredhego.com/creatorpoll/results/3` - Full Top 25 placeholder
- ✅ `https://wheredhego.com/creatorpoll/vote/3` - Should redirect (poll locked)
- ✅ `https://wheredhego.com/creatorpoll/logo/194.png` - Ohio State logo
- ✅ `https://wheredhego.com/healthz` - Health check

## 📊 Data Persistence

**What's Saved:**
- Every individual vote (team, rank, user, timestamp)
- Complete ballots (full Top 25 as JSON)
- Poll metadata (start/end times, week numbers)
- Historical data (all previous weeks preserved)

**Guest Voting:**
- No login required
- Tracked by IP address or session ID
- One ballot per user per poll
- Can update ballot during voting window

## 🚨 Important Notes

1. **Database Migration:** SQLite data won't transfer - production starts fresh
2. **Time Zone:** All times are EST (Eastern Standard Time)
3. **Logo Assets:** 453 team logos included (2KB each, ~1MB total)
4. **Auto-Management:** Polls create/lock/advance automatically
5. **No Manual Intervention:** System runs itself once deployed

## 🎉 You're Ready!

The system is production-ready with:
- Professional-looking placeholder rankings
- Automatic weekly cycle management
- Robust data persistence
- Public access (no login barriers)
- Official team logos and branding

Deploy and watch your CFB Creator Poll come to life! 🏈
