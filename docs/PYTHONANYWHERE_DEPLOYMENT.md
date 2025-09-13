# PythonAnywhere Deployment Instructions for wheredhego.com

## Current Status
✅ Code pushed to GitHub: https://github.com/devgreeny/wheredhego.git
✅ WSGI file updated with logging and error handling

## Next Steps for PythonAnywhere:

### 1. Create Web App
1. Log into PythonAnywhere
2. Go to **Web** tab
3. Click **"Add a new web app"**
4. Choose **"Manual configuration"**
5. Select **Python 3.10**

### 2. Set Up Code
In **Bash console**:
```bash
cd ~
git clone https://github.com/devgreeny/wheredhego.git
cd wheredhego
pip3.10 install --user -r requirements.txt
```

### 3. Configure Web App
In the **Web** tab, **Code** section:
- **Source code**: `/home/yourusername/wheredhego`
- **WSGI configuration file**: Click to edit and replace ALL content with:

```python
#!/usr/bin/env python3.10

import sys
import os
import logging

# Add your project directory to the sys.path
path = '/home/yourusername/wheredhego'  # Replace 'yourusername' with your actual username
if path not in sys.path:
    sys.path.insert(0, path)

# Set up logging
logging.basicConfig(level=logging.INFO)

try:
    from app import create_app
    application = create_app()
    logging.info("Wheredhego application loaded successfully")
except Exception as e:
    logging.error(f"Error loading application: {e}")
    raise

if __name__ == "__main__":
    application.run()
```

### 4. Configure Static Files
In **Static files** section, add entries for:

**Starting5 Game:**
- **URL**: `/starting5/static/`
- **Directory**: `/home/yourusername/wheredhego/app/starting5/static/`

**Gridiron11 Game:**
- **URL**: `/gridiron11/static/`
- **Directory**: `/home/yourusername/wheredhego/app/gridiron11/static/`

### 5. Environment Variables (Optional)
Create `.env` file in `/home/yourusername/wheredhego/`:
```
SECRET_KEY=your-production-secret-key-here
DATABASE_URL=sqlite:///wheredhego.db
FLASK_ENV=production
```

### 6. Custom Domain Setup
1. In **Web** tab, find **"Custom domains"** section
2. Add **wheredhego.com**
3. Configure DNS at your domain registrar:
   - Add CNAME record: `www` → `yourusername.pythonanywhere.com`
   - Add A record: `@` → PythonAnywhere IP (they'll provide this)

### 7. SSL Certificate
- PythonAnywhere will automatically provide SSL for custom domains
- Your site will be accessible at both `http://wheredhego.com` and `https://wheredhego.com`

### 8. Test Deployment
Visit these URLs to test:
- `https://wheredhego.com/` - Homepage
- `https://wheredhego.com/starting5/` - Basketball game
- `https://wheredhego.com/gridiron11/` - Football game
- `https://wheredhego.com/healthz` - Health check

## Troubleshooting
- Check **Error logs** in Web tab if issues occur
- Make sure to replace `yourusername` with your actual PythonAnywhere username in all paths
- Database will be created automatically at `/home/yourusername/wheredhego/app/wheredhego.db`
