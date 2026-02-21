#!/bin/bash
# Local Daily Quiz Generator
# This script generates quizzes and pushes to GitHub
# Run this on your Mac to avoid API blocks

cd /Users/noah/Downloads/wheredhego_v1-main

echo "$(date): Starting daily quiz generation..."

# Generate 1 NBA quiz
python scripts/auto_generate_quiz.py --game nba --count 1

# Generate 1 NFL quiz  
python scripts/auto_generate_quiz.py --game nfl --count 1

# Push to GitHub
git add quizzes/
git commit -m "🎮 Auto-generated quizzes - $(date +'%Y-%m-%d')"
git push origin main

echo "$(date): Done!"
