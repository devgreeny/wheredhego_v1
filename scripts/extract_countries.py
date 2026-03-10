#!/usr/bin/env python3
"""
Extract unique country names from all scraped Starting11 quiz files.
Run this after batch_scrape_wc.py to get the definitive list of country names.

Usage:
    python extract_countries.py
"""

import os
import json
from collections import defaultdict

QUIZ_BASE = os.path.join(os.path.dirname(__file__), "..", "quizzes", "starting11")

def extract_countries():
    """Extract all unique country names from quiz files."""
    countries = defaultdict(set)  # country_name -> set of tournaments
    
    tournaments = ["wc2022", "wc2018", "wc2014", "wc2010", "wc2006"]
    
    for tournament in tournaments:
        tournament_dir = os.path.join(QUIZ_BASE, tournament)
        if not os.path.exists(tournament_dir):
            continue
            
        for filename in os.listdir(tournament_dir):
            if not filename.endswith(".json"):
                continue
                
            filepath = os.path.join(tournament_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    country = data.get("answer", {}).get("country", "")
                    if country:
                        countries[country].add(tournament)
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    
    # Sort and display
    print("\n" + "="*60)
    print("UNIQUE COUNTRIES FROM SCRAPED QUIZZES")
    print("="*60)
    
    sorted_countries = sorted(countries.keys())
    print(f"\nTotal unique countries: {len(sorted_countries)}\n")
    
    # Python list format for copy-paste into routes.py
    print("# Country names from Transfermarkt (for routes.py):")
    print("SCRAPED_COUNTRIES = [")
    for country in sorted_countries:
        tournaments_str = ", ".join(sorted(countries[country]))
        print(f'    "{country}",  # {tournaments_str}')
    print("]")
    
    print("\n" + "="*60)
    
    return sorted_countries


if __name__ == "__main__":
    extract_countries()
