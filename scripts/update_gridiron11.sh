#!/bin/bash
# Update only Gridiron11 game
cd /home/devgreeny/wheredhego_v1
export FLASK_APP=run:app
python3.10 -m flask update-gridiron11
