#!/bin/bash
# Update only Starting5 game
cd /home/devgreeny/wheredhego_v1
export FLASK_APP=run:app
python3.10 -m flask update-starting5
