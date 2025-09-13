# Deploying Wheredhego to PythonAnywhere

## Step 1: Push to GitHub (RECOMMENDED)
1. Create a new repository on GitHub called `wheredhego`
2. Push your local repository:
   ```bash
   git remote add origin https://github.com/yourusername/wheredhego.git
   git branch -M main
   git push -u origin main
   ```

## Step 2: Clone from GitHub to PythonAnywhere
1. Log into your PythonAnywhere account
2. Go to **Tasks** → **Bash console**
3. Clone your repository:
   ```bash
   cd ~
   git clone https://github.com/yourusername/wheredhego.git
   ```

## Step 3: Install Dependencies
1. Go to **Tasks** → **Bash console**
2. Run these commands:
```bash
cd wheredhego
pip3.10 install --user -r requirements.txt
```

## Step 4: Configure Web App
1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration**
4. Choose **Python 3.10**
5. In the **Code** section:
   - **Source code**: `/home/yourusername/wheredhego`
   - **WSGI configuration file**: Click to edit, then replace content with:

```python
#!/usr/bin/env python3.10

import sys
import os

# Add your project directory to the sys.path
path = '/home/yourusername/wheredhego'  # Replace 'yourusername' with your actual username
if path not in sys.path:
    sys.path.insert(0, path)

from app import create_app

application = create_app()
```

## Step 5: Configure Static Files
In the **Static files** section, add:
- **URL**: `/starting5/starting5/static/`
- **Directory**: `/home/yourusername/wheredhego/app/starting5/static/`

## Step 6: Set Domain
- Your app will be available at: `yourusername.pythonanywhere.com`
- Or configure custom domain: `wheredhego.com`

## Step 7: Reload and Test
1. Click **Reload yourusername.pythonanywhere.com**
2. Visit your site
3. Test:
   - Homepage should show "WHEREDHEGO"
   - Basketball button should go to Starting5 game
   - Game should work in guest mode

## Environment Variables (Optional)
In **Files** tab, create `.env` file in `/home/yourusername/wheredhego/`:
```
SECRET_KEY=your-production-secret-key-here
DATABASE_URL=sqlite:///wheredhego.db
```

## Database
- SQLite database will be created automatically
- Located at: `/home/yourusername/wheredhego/app/wheredhego.db`
- Guest scores are stored with user_id=NULL

## Troubleshooting
- Check **Error logs** in Web tab if issues occur
- Ensure all file paths use your actual username
- Make sure static files are properly configured
