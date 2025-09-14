#!/bin/bash
# Check current game status
cd /home/devgreeny/wheredhego
export FLASK_APP=run:app
python3.10 -m flask game-status
