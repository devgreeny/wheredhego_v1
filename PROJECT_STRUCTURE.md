# 📁 Project Structure

This document explains the organized folder structure of the WheredHeGo application.

## 🏗️ Root Directory Structure

```
wheredhego_v1/
├── 🚀 run.py                    # Main Flask application entry point
├── 🌐 wsgi.py                   # WSGI configuration for production
├── 📱 app/                      # Main Flask application
├── 🎮 quizzes/                  # Organized quiz data for all games
├── 📜 scripts/                  # Utility and maintenance scripts
├── 📚 docs/                     # Documentation files
├── ⚙️ config/                   # Configuration files
├── 🚀 deployment/               # Deployment-specific files
├── 📦 legacy/                   # Legacy standalone applications
└── 🐍 venv/                     # Python virtual environment
```

## 📱 Main Application (`app/`)

The core Flask application with all integrated features:

```
app/
├── __init__.py                  # Flask app factory
├── landing.py                   # Landing page routes
├── wheredhego.db               # SQLite database (development)
├── templates/                   # Shared templates
│   ├── index.html              # Main landing page
│   └── auth/                   # Authentication templates
├── creatorpoll/                # College Football Creator Poll
│   ├── models.py               # Poll database models
│   ├── routes.py               # Poll routes and logic
│   ├── mysql_*.py              # MySQL-specific files
│   ├── static/                 # Poll assets and team logos
│   └── templates/              # Poll HTML templates
├── starting5/                  # NBA Basketball Quiz Game
│   ├── models.py               # NBA game models
│   ├── routes.py               # NBA game routes
│   ├── static/                 # NBA assets and team images
│   └── templates/              # NBA game templates
└── gridiron11/                 # NFL Football Quiz Game
    ├── routes.py               # NFL game routes
    ├── static/                 # NFL assets and images
    └── templates/              # NFL game templates
```

## 🎮 Quiz Data (`quizzes/`)

Organized quiz data for all games with clean separation:

```
quizzes/
├── starting5/                  # NBA Basketball Quiz Data
│   ├── preloaded/              # Pool of available NBA quizzes
│   ├── current/                # Currently active NBA quiz
│   ├── archive/                # Previously used NBA quizzes
│   └── bonus/                  # NBA bonus quiz data
└── gridiron11/                 # NFL Football Quiz Data
    ├── preloaded/              # Pool of available NFL quizzes
    ├── current/                # Currently active NFL quiz
    └── archive/                # Previously used NFL quizzes
```

## 📜 Scripts (`scripts/`)

Utility scripts for maintenance and quiz generation:

```
scripts/
├── 🔄 update_games.py          # Daily quiz update automation (PRODUCTION)
├── 🏀 generate_quiz_enhanced.py # NBA/NFL quiz generation tool
├── 🏈 generate_nfl_quiz.py     # NFL-specific quiz generator
├── 📊 ballot_storage.py        # Poll data management utilities
├── 🔐 creator_auth_system.py   # Authentication system utilities
├── 🗄️ mysql_creator_migration.py # Database migration scripts
└── 📝 create_sample_poll.py    # Sample data creation
```

## 📚 Documentation (`docs/`)

All project documentation and guides:

```
docs/
├── 📖 README.md                # Main project documentation
├── 🚀 DEPLOYMENT.md            # General deployment guide
├── 🐍 PRODUCTION_DEPLOYMENT.md # PythonAnywhere deployment
├── ⏰ GAME_UPDATE_DEPLOYMENT.md # Automated quiz updates
├── 🎮 QUIZ_GENERATION_GUIDE.md # Manual quiz generation
└── 🌐 PYTHONANYWHERE_DEPLOYMENT.md # Legacy deployment guide
```

## ⚙️ Configuration (`config/`)

Environment and dependency configuration:

```
config/
├── 🔒 production.env           # Production environment variables
├── 📦 requirements.txt         # Python dependencies
└── 📦 requirements_complete.txt # Complete dependency list
```

## 📦 Legacy (`legacy/`)

Original standalone applications (kept for reference):

```
legacy/
├── starting5/                  # Original NBA app
│   ├── app/                   # Flask structure
│   ├── generate_quiz.py       # Original quiz generator
│   └── update_quiz.py         # Original update script
└── gridiron11/                # Original NFL app
    ├── app.py                 # Standalone Flask app
    ├── Script to Pull NFL Players.ipynb # Jupyter notebook
    └── static/                # Original assets
```

## 🚀 Key Files

### Production Files
- **`run.py`** - Start the Flask development server
- **`wsgi.py`** - Production WSGI entry point
- **`scripts/update_games.py`** - Automated daily quiz updates (runs at 4 UTC)

### Development Files
- **`scripts/generate_quiz_enhanced.py`** - Generate new NBA/NFL quizzes manually
- **`config/production.env`** - Production environment variables
- **`docs/`** - All documentation and deployment guides

## 🎯 Quick Commands

### Start Development Server
```bash
source venv/bin/activate
python run.py
```

### Generate New Quizzes
```bash
# Interactive mode
python scripts/generate_quiz_enhanced.py

# NBA with manual avatars
python scripts/generate_quiz_enhanced.py --game nba --manual-avatars

# NFL quiz
python scripts/generate_quiz_enhanced.py --game nfl --count 1
```

### Deploy to Production
See `docs/PRODUCTION_DEPLOYMENT.md` for complete deployment instructions.

## 📝 Notes

- **Main App**: All active features are in the `app/` directory
- **Scripts**: Utility scripts are organized in `scripts/`
- **Documentation**: All guides and docs are in `docs/`
- **Legacy**: Old standalone apps preserved in `legacy/`
- **Clean Structure**: No more scattered files in the root directory!

This organization makes it much easier to:
- 🔍 Find specific functionality
- 📚 Access documentation
- 🛠️ Run maintenance scripts
- 🚀 Deploy to production
- 🧹 Keep the project clean and organized
