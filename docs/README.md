# WheredHeGo v1.0

A comprehensive sports gaming platform featuring NBA basketball quizzes, NFL football games, and college football creator polls.

## 📁 Project Organization

This project has been reorganized into a clean folder structure. See `PROJECT_STRUCTURE.md` in the root directory for detailed information about the new organization.

## 🎮 Features

- **Starting5**: NBA basketball quiz game with player silhouettes and stats
- **Gridiron11**: NFL football quiz game with player data
- **Creator Poll**: College football weekly ranking polls with team logos
- **Guest Mode**: Play without creating an account - scores tracked per session
- **Automated Updates**: Daily quiz updates via scheduled scripts
- **Clean Interface**: Retro arcade-style design
- **Score Competition**: Compare your performance with other players

## 🚀 Quick Start (Local Development)

```bash
# Clone the repository
git clone https://github.com/devgreeny/wheredhego_v1.git
cd wheredhego_v1

# Install dependencies
pip install -r config/requirements.txt

# Run the app
python run.py
```

Visit `http://localhost:8080` to play!

## 🌐 Deployment

This app is designed to be deployed on PythonAnywhere. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Quick Deploy Steps:
1. Create GitHub repository
2. Push code to GitHub
3. Clone to PythonAnywhere
4. Configure WSGI and static files
5. Launch!

## 🎮 Game Structure

- **Homepage**: Clean landing page at `/`
- **Starting5 Game**: Basketball trivia at `/starting5`
- **Guest Mode**: Session-based scoring without user accounts
- **Mobile Friendly**: Responsive design for all devices

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (guest scores)
- **Frontend**: HTML, CSS, JavaScript
- **Hosting**: PythonAnywhere ready

## 📁 Project Structure

```
wheredhego/
├── app/
│   ├── __init__.py          # Main Flask app
│   ├── starting5/           # Starting5 game
│   │   ├── models.py        # Database models
│   │   ├── routes.py        # Game logic
│   │   ├── templates/       # Game templates
│   │   └── static/          # Game assets (images, CSS, JS)
│   └── templates/
│       └── index.html       # Homepage
├── run.py                   # Development server
├── wsgi.py                  # Production WSGI config
├── requirements.txt         # Python dependencies
└── DEPLOYMENT.md           # Deployment guide
```

## 🎯 Features Coming Soon

- The Gridiron (NFL trivia game)
- More sports games
- Enhanced scoring system
- Leaderboards

## 📝 License

Personal project - see repository for details.

---

**Play now at wheredhego.com!** 🏀
