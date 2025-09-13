# Wheredhego.com

A retro-style sports trivia platform featuring the Starting5 basketball guessing game.

## 🏀 Features

- **Starting5**: Basketball trivia game where you guess college players from silhouettes
- **Guest Mode**: Play without creating an account - scores tracked per session
- **Clean Interface**: Retro arcade-style design
- **Score Competition**: Compare your performance with other players

## 🚀 Quick Start (Local Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/wheredhego.git
cd wheredhego

# Install dependencies
pip install -r requirements.txt

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
