#!/usr/bin/env python3.10

import sys
import os
import logging

# Add your project directory to the sys.path
path = '/home/devgreeny/wheredhego'
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
