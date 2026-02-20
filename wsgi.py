#!/usr/bin/env python3.10

import sys
import os
import logging

# Add your project directory to the sys.path
path = '/home/yourusername/wheredhego'  # Replace 'yourusername' with your actual PythonAnywhere username
if path not in sys.path:
    sys.path.insert(0, path)

# Load environment variables from .env file if it exists
if os.path.exists('.env'):
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logging.info("Environment variables loaded from .env file")
    except ImportError:
        logging.warning("python-dotenv not installed, skipping .env file loading")

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
