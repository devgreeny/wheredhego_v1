#!/usr/bin/env python3
"""
Batch scraper for World Cup matches from Transfermarkt.
Generates Starting11 quiz JSON files for each match.

Usage:
    python batch_scrape_wc.py [--tournament wc2022|wc2018|wc2014|wc2010|wc2006|all]

Supported Tournaments:
    - wc2022: FIFA World Cup Qatar 2022 (64 matches)
    - wc2018: FIFA World Cup Russia 2018 (16 knockout matches)
    - wc2014: FIFA World Cup Brazil 2014 (16 knockout matches)
    - wc2010: FIFA World Cup South Africa 2010 (16 knockout matches)
    - wc2006: FIFA World Cup Germany 2006 (16 knockout matches)

Validation:
    - Skips matches where any player is missing club data
    - Skips matches where positions can't be extracted for all 11 players
    - Logs skipped matches for review
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import argparse
from datetime import datetime

# =============================================================================
# Configuration
# =============================================================================

REQUEST_DELAY = 4  # Seconds between requests - be respectful!
BASE_URL = "https://www.transfermarkt.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.join(SCRIPT_DIR, "..", "quizzes", "starting11")

# =============================================================================
# World Cup Match Data
# Format: (match_id, stage, team1_name, team1_code, team2_name, team2_code, date)
# =============================================================================

WC2022_MATCHES = [
    # === FINAL ===
    ("3975879", "Final", "Argentina", "ARG", "France", "FRA", "2022-12-18"),
    # === 3RD PLACE ===
    ("3975878", "Third-Place", "Croatia", "CRO", "Morocco", "MAR", "2022-12-17"),
    # === SEMI-FINALS ===
    ("3974501", "Semi-Final", "Argentina", "ARG", "Croatia", "CRO", "2022-12-13"),
    ("3974586", "Semi-Final", "France", "FRA", "Morocco", "MAR", "2022-12-14"),
    # === QUARTER-FINALS ===
    ("3972833", "Quarter-Final", "Croatia", "CRO", "Brazil", "BRA", "2022-12-09"),
    ("3971598", "Quarter-Final", "Netherlands", "NED", "Argentina", "ARG", "2022-12-09"),
    ("3973427", "Quarter-Final", "Morocco", "MAR", "Portugal", "POR", "2022-12-10"),
    ("3972029", "Quarter-Final", "England", "ENG", "France", "FRA", "2022-12-10"),
    # === ROUND OF 16 ===
    ("3970160", "Round-of-16", "Netherlands", "NED", "USA", "USA", "2022-12-03"),
    ("3970579", "Round-of-16", "Argentina", "ARG", "Australia", "AUS", "2022-12-03"),
    ("3970580", "Round-of-16", "France", "FRA", "Poland", "POL", "2022-12-04"),
    ("3970161", "Round-of-16", "England", "ENG", "Senegal", "SEN", "2022-12-04"),
    ("3970790", "Round-of-16", "Japan", "JPN", "Croatia", "CRO", "2022-12-05"),
    ("3970993", "Round-of-16", "Brazil", "BRA", "South Korea", "KOR", "2022-12-05"),
    ("3970791", "Round-of-16", "Morocco", "MAR", "Spain", "ESP", "2022-12-06"),
    ("3970994", "Round-of-16", "Portugal", "POR", "Switzerland", "SUI", "2022-12-06"),
    # === GROUP A ===
    ("3788834", "Group-A", "Qatar", "QAT", "Ecuador", "ECU", "2022-11-20"),
    ("3788835", "Group-A", "Senegal", "SEN", "Netherlands", "NED", "2022-11-21"),
    ("3788859", "Group-A", "Qatar", "QAT", "Senegal", "SEN", "2022-11-25"),
    ("3788860", "Group-A", "Netherlands", "NED", "Ecuador", "ECU", "2022-11-25"),
    ("3788884", "Group-A", "Ecuador", "ECU", "Senegal", "SEN", "2022-11-29"),
    ("3788885", "Group-A", "Netherlands", "NED", "Qatar", "QAT", "2022-11-29"),
    # === GROUP B ===
    ("3788836", "Group-B", "England", "ENG", "Iran", "IRN", "2022-11-21"),
    ("3788837", "Group-B", "USA", "USA", "Wales", "WAL", "2022-11-21"),
    ("3788862", "Group-B", "Wales", "WAL", "Iran", "IRN", "2022-11-25"),
    ("3788861", "Group-B", "England", "ENG", "USA", "USA", "2022-11-25"),
    ("3788886", "Group-B", "Iran", "IRN", "USA", "USA", "2022-11-29"),
    ("3788887", "Group-B", "Wales", "WAL", "England", "ENG", "2022-11-29"),
    # === GROUP C ===
    ("3788838", "Group-C", "Argentina", "ARG", "Saudi Arabia", "KSA", "2022-11-22"),
    ("3788839", "Group-C", "Mexico", "MEX", "Poland", "POL", "2022-11-22"),
    ("3788864", "Group-C", "Poland", "POL", "Saudi Arabia", "KSA", "2022-11-26"),
    ("3788863", "Group-C", "Argentina", "ARG", "Mexico", "MEX", "2022-11-26"),
    ("3788888", "Group-C", "Saudi Arabia", "KSA", "Mexico", "MEX", "2022-11-30"),
    ("3788889", "Group-C", "Poland", "POL", "Argentina", "ARG", "2022-11-30"),
    # === GROUP D ===
    ("3788841", "Group-D", "Denmark", "DEN", "Tunisia", "TUN", "2022-11-22"),
    ("3788840", "Group-D", "France", "FRA", "Australia", "AUS", "2022-11-22"),
    ("3788866", "Group-D", "Tunisia", "TUN", "Australia", "AUS", "2022-11-26"),
    ("3788865", "Group-D", "France", "FRA", "Denmark", "DEN", "2022-11-26"),
    ("3788890", "Group-D", "Australia", "AUS", "Denmark", "DEN", "2022-11-30"),
    ("3788891", "Group-D", "Tunisia", "TUN", "France", "FRA", "2022-11-30"),
    # === GROUP E ===
    ("3788843", "Group-E", "Germany", "GER", "Japan", "JPN", "2022-11-23"),
    ("3788842", "Group-E", "Spain", "ESP", "Costa Rica", "CRC", "2022-11-23"),
    ("3788868", "Group-E", "Japan", "JPN", "Costa Rica", "CRC", "2022-11-27"),
    ("3788867", "Group-E", "Spain", "ESP", "Germany", "GER", "2022-11-27"),
    ("3788892", "Group-E", "Costa Rica", "CRC", "Germany", "GER", "2022-12-01"),
    ("3788893", "Group-E", "Japan", "JPN", "Spain", "ESP", "2022-12-01"),
    # === GROUP F ===
    ("3788845", "Group-F", "Morocco", "MAR", "Croatia", "CRO", "2022-11-23"),
    ("3788844", "Group-F", "Belgium", "BEL", "Canada", "CAN", "2022-11-23"),
    ("3788869", "Group-F", "Belgium", "BEL", "Morocco", "MAR", "2022-11-27"),
    ("3788870", "Group-F", "Croatia", "CRO", "Canada", "CAN", "2022-11-27"),
    ("3788894", "Group-F", "Canada", "CAN", "Morocco", "MAR", "2022-12-01"),
    ("3788895", "Group-F", "Croatia", "CRO", "Belgium", "BEL", "2022-12-01"),
    # === GROUP G ===
    ("3788847", "Group-G", "Switzerland", "SUI", "Cameroon", "CMR", "2022-11-24"),
    ("3788846", "Group-G", "Brazil", "BRA", "Serbia", "SRB", "2022-11-24"),
    ("3788872", "Group-G", "Cameroon", "CMR", "Serbia", "SRB", "2022-11-28"),
    ("3788871", "Group-G", "Brazil", "BRA", "Switzerland", "SUI", "2022-11-28"),
    ("3788896", "Group-G", "Serbia", "SRB", "Switzerland", "SUI", "2022-12-02"),
    ("3788897", "Group-G", "Cameroon", "CMR", "Brazil", "BRA", "2022-12-02"),
    # === GROUP H ===
    ("3788849", "Group-H", "Uruguay", "URU", "South Korea", "KOR", "2022-11-24"),
    ("3788848", "Group-H", "Portugal", "POR", "Ghana", "GHA", "2022-11-24"),
    ("3788874", "Group-H", "South Korea", "KOR", "Ghana", "GHA", "2022-11-28"),
    ("3788873", "Group-H", "Portugal", "POR", "Uruguay", "URU", "2022-11-28"),
    ("3788898", "Group-H", "Ghana", "GHA", "Uruguay", "URU", "2022-12-02"),
    ("3788899", "Group-H", "South Korea", "KOR", "Portugal", "POR", "2022-12-02"),
]

WC2018_MATCHES = [
    # === FINAL ===
    ("3072773", "Final", "France", "FRA", "Croatia", "CRO", "2018-07-15"),
    # === 3RD PLACE ===
    ("3072772", "Third-Place", "Belgium", "BEL", "England", "ENG", "2018-07-14"),
    # === SEMI-FINALS ===
    ("3072770", "Semi-Final", "France", "FRA", "Belgium", "BEL", "2018-07-10"),
    ("3072771", "Semi-Final", "Croatia", "CRO", "England", "ENG", "2018-07-11"),
    # === QUARTER-FINALS ===
    ("3072766", "Quarter-Final", "Uruguay", "URU", "France", "FRA", "2018-07-06"),
    ("3072767", "Quarter-Final", "Brazil", "BRA", "Belgium", "BEL", "2018-07-06"),
    ("3072768", "Quarter-Final", "Sweden", "SWE", "England", "ENG", "2018-07-07"),
    ("3072769", "Quarter-Final", "Russia", "RUS", "Croatia", "CRO", "2018-07-07"),
    # === ROUND OF 16 ===
    ("3072758", "Round-of-16", "France", "FRA", "Argentina", "ARG", "2018-06-30"),
    ("3072759", "Round-of-16", "Uruguay", "URU", "Portugal", "POR", "2018-06-30"),
    ("3072760", "Round-of-16", "Spain", "ESP", "Russia", "RUS", "2018-07-01"),
    ("3072761", "Round-of-16", "Croatia", "CRO", "Denmark", "DEN", "2018-07-01"),
    ("3072762", "Round-of-16", "Brazil", "BRA", "Mexico", "MEX", "2018-07-02"),
    ("3072763", "Round-of-16", "Belgium", "BEL", "Japan", "JPN", "2018-07-02"),
    ("3072764", "Round-of-16", "Sweden", "SWE", "Switzerland", "SUI", "2018-07-03"),
    ("3072765", "Round-of-16", "Colombia", "COL", "England", "ENG", "2018-07-03"),
    # === GROUP A ===
    ("3072710", "Group-A", "Russia", "RUS", "Saudi Arabia", "KSA", "2018-06-14"),
    ("3072711", "Group-A", "Egypt", "EGY", "Uruguay", "URU", "2018-06-15"),
    ("3072726", "Group-A", "Russia", "RUS", "Egypt", "EGY", "2018-06-19"),
    ("3072727", "Group-A", "Uruguay", "URU", "Saudi Arabia", "KSA", "2018-06-20"),
    ("3072742", "Group-A", "Uruguay", "URU", "Russia", "RUS", "2018-06-25"),
    ("3072743", "Group-A", "Saudi Arabia", "KSA", "Egypt", "EGY", "2018-06-25"),
    # === GROUP B ===
    ("3072712", "Group-B", "Morocco", "MAR", "Iran", "IRN", "2018-06-15"),
    ("3072713", "Group-B", "Portugal", "POR", "Spain", "ESP", "2018-06-15"),
    ("3072728", "Group-B", "Portugal", "POR", "Morocco", "MAR", "2018-06-20"),
    ("3072729", "Group-B", "Iran", "IRN", "Spain", "ESP", "2018-06-20"),
    ("3072744", "Group-B", "Iran", "IRN", "Portugal", "POR", "2018-06-25"),
    ("3072745", "Group-B", "Spain", "ESP", "Morocco", "MAR", "2018-06-25"),
    # === GROUP C ===
    ("3072714", "Group-C", "France", "FRA", "Australia", "AUS", "2018-06-16"),
    ("3072715", "Group-C", "Peru", "PER", "Denmark", "DEN", "2018-06-16"),
    ("3072730", "Group-C", "Denmark", "DEN", "Australia", "AUS", "2018-06-21"),
    ("3072731", "Group-C", "France", "FRA", "Peru", "PER", "2018-06-21"),
    ("3072746", "Group-C", "Denmark", "DEN", "France", "FRA", "2018-06-26"),
    ("3072747", "Group-C", "Australia", "AUS", "Peru", "PER", "2018-06-26"),
    # === GROUP D ===
    ("3072716", "Group-D", "Argentina", "ARG", "Iceland", "ISL", "2018-06-16"),
    ("3072717", "Group-D", "Croatia", "CRO", "Nigeria", "NGA", "2018-06-16"),
    ("3072732", "Group-D", "Argentina", "ARG", "Croatia", "CRO", "2018-06-21"),
    ("3072733", "Group-D", "Nigeria", "NGA", "Iceland", "ISL", "2018-06-22"),
    ("3072748", "Group-D", "Iceland", "ISL", "Croatia", "CRO", "2018-06-26"),
    ("3072749", "Group-D", "Nigeria", "NGA", "Argentina", "ARG", "2018-06-26"),
    # === GROUP E ===
    ("3072718", "Group-E", "Costa Rica", "CRC", "Serbia", "SRB", "2018-06-17"),
    ("3072719", "Group-E", "Brazil", "BRA", "Switzerland", "SUI", "2018-06-17"),
    ("3072734", "Group-E", "Brazil", "BRA", "Costa Rica", "CRC", "2018-06-22"),
    ("3072735", "Group-E", "Serbia", "SRB", "Switzerland", "SUI", "2018-06-22"),
    ("3072750", "Group-E", "Serbia", "SRB", "Brazil", "BRA", "2018-06-27"),
    ("3072751", "Group-E", "Switzerland", "SUI", "Costa Rica", "CRC", "2018-06-27"),
    # === GROUP F ===
    ("3072720", "Group-F", "Germany", "GER", "Mexico", "MEX", "2018-06-17"),
    ("3072721", "Group-F", "Sweden", "SWE", "South Korea", "KOR", "2018-06-18"),
    ("3072736", "Group-F", "South Korea", "KOR", "Mexico", "MEX", "2018-06-23"),
    ("3072737", "Group-F", "Germany", "GER", "Sweden", "SWE", "2018-06-23"),
    ("3072752", "Group-F", "South Korea", "KOR", "Germany", "GER", "2018-06-27"),
    ("3072753", "Group-F", "Mexico", "MEX", "Sweden", "SWE", "2018-06-27"),
    # === GROUP G ===
    ("3072722", "Group-G", "Belgium", "BEL", "Panama", "PAN", "2018-06-18"),
    ("3072723", "Group-G", "Tunisia", "TUN", "England", "ENG", "2018-06-18"),
    ("3072738", "Group-G", "Belgium", "BEL", "Tunisia", "TUN", "2018-06-23"),
    ("3072739", "Group-G", "England", "ENG", "Panama", "PAN", "2018-06-24"),
    ("3072754", "Group-G", "England", "ENG", "Belgium", "BEL", "2018-06-28"),
    ("3072755", "Group-G", "Panama", "PAN", "Tunisia", "TUN", "2018-06-28"),
    # === GROUP H ===
    ("3072724", "Group-H", "Colombia", "COL", "Japan", "JPN", "2018-06-19"),
    ("3072725", "Group-H", "Poland", "POL", "Senegal", "SEN", "2018-06-19"),
    ("3072740", "Group-H", "Japan", "JPN", "Senegal", "SEN", "2018-06-24"),
    ("3072741", "Group-H", "Poland", "POL", "Colombia", "COL", "2018-06-24"),
    ("3072756", "Group-H", "Japan", "JPN", "Poland", "POL", "2018-06-28"),
    ("3072757", "Group-H", "Senegal", "SEN", "Colombia", "COL", "2018-06-28"),
]

WC2014_MATCHES = [
    # === FINAL ===
    ("2464546", "Final", "Germany", "GER", "Argentina", "ARG", "2014-07-13"),
    # === 3RD PLACE ===
    ("2464547", "Third-Place", "Brazil", "BRA", "Netherlands", "NED", "2014-07-12"),
    # === SEMI-FINALS ===
    ("2464545", "Semi-Final", "Brazil", "BRA", "Germany", "GER", "2014-07-08"),
    ("2464544", "Semi-Final", "Netherlands", "NED", "Argentina", "ARG", "2014-07-09"),
    # === QUARTER-FINALS ===
    ("2464541", "Quarter-Final", "France", "FRA", "Germany", "GER", "2014-07-04"),
    ("2464540", "Quarter-Final", "Brazil", "BRA", "Colombia", "COL", "2014-07-04"),
    ("2464542", "Quarter-Final", "Argentina", "ARG", "Belgium", "BEL", "2014-07-05"),
    ("2464543", "Quarter-Final", "Netherlands", "NED", "Costa Rica", "CRC", "2014-07-05"),
    # === ROUND OF 16 ===
    ("2464533", "Round-of-16", "Brazil", "BRA", "Chile", "CHI", "2014-06-28"),
    ("2464534", "Round-of-16", "Colombia", "COL", "Uruguay", "URU", "2014-06-28"),
    ("2464535", "Round-of-16", "Netherlands", "NED", "Mexico", "MEX", "2014-06-29"),
    ("2464536", "Round-of-16", "Costa Rica", "CRC", "Greece", "GRE", "2014-06-29"),
    ("2464537", "Round-of-16", "France", "FRA", "Nigeria", "NGA", "2014-06-30"),
    ("2464538", "Round-of-16", "Germany", "GER", "Algeria", "ALG", "2014-06-30"),
    ("2464539", "Round-of-16", "Argentina", "ARG", "Switzerland", "SUI", "2014-07-01"),
    ("2464532", "Round-of-16", "Belgium", "BEL", "USA", "USA", "2014-07-01"),
]

WC2010_MATCHES = [
    # === FINAL ===
    ("1019156", "Final", "Netherlands", "NED", "Spain", "ESP", "2010-07-11"),
    # === 3RD PLACE ===
    ("1019155", "Third-Place", "Uruguay", "URU", "Germany", "GER", "2010-07-10"),
    # === SEMI-FINALS ===
    ("1019153", "Semi-Final", "Uruguay", "URU", "Netherlands", "NED", "2010-07-06"),
    ("1019154", "Semi-Final", "Germany", "GER", "Spain", "ESP", "2010-07-07"),
    # === QUARTER-FINALS ===
    ("1019149", "Quarter-Final", "Netherlands", "NED", "Brazil", "BRA", "2010-07-02"),
    ("1019150", "Quarter-Final", "Uruguay", "URU", "Ghana", "GHA", "2010-07-02"),
    ("1019151", "Quarter-Final", "Argentina", "ARG", "Germany", "GER", "2010-07-03"),
    ("1019152", "Quarter-Final", "Paraguay", "PAR", "Spain", "ESP", "2010-07-03"),
    # === ROUND OF 16 ===
    ("1019141", "Round-of-16", "Uruguay", "URU", "South Korea", "KOR", "2010-06-26"),
    ("1019142", "Round-of-16", "USA", "USA", "Ghana", "GHA", "2010-06-26"),
    ("1019143", "Round-of-16", "Germany", "GER", "England", "ENG", "2010-06-27"),
    ("1019144", "Round-of-16", "Argentina", "ARG", "Mexico", "MEX", "2010-06-27"),
    ("1019145", "Round-of-16", "Netherlands", "NED", "Slovakia", "SVK", "2010-06-28"),
    ("1019146", "Round-of-16", "Brazil", "BRA", "Chile", "CHI", "2010-06-28"),
    ("1019147", "Round-of-16", "Paraguay", "PAR", "Japan", "JPN", "2010-06-29"),
    ("1019148", "Round-of-16", "Spain", "ESP", "Portugal", "POR", "2010-06-29"),
]

WC2006_MATCHES = [
    # === FINAL ===
    ("236851", "Final", "Italy", "ITA", "France", "FRA", "2006-07-09"),
    # === 3RD PLACE ===
    ("236850", "Third-Place", "Germany", "GER", "Portugal", "POR", "2006-07-08"),
    # === SEMI-FINALS ===
    ("236848", "Semi-Final", "Germany", "GER", "Italy", "ITA", "2006-07-04"),
    ("236849", "Semi-Final", "Portugal", "POR", "France", "FRA", "2006-07-05"),
    # === QUARTER-FINALS ===
    ("236844", "Quarter-Final", "Germany", "GER", "Argentina", "ARG", "2006-06-30"),
    ("236845", "Quarter-Final", "Italy", "ITA", "Ukraine", "UKR", "2006-06-30"),
    ("236846", "Quarter-Final", "England", "ENG", "Portugal", "POR", "2006-07-01"),
    ("236847", "Quarter-Final", "Brazil", "BRA", "France", "FRA", "2006-07-01"),
    # === ROUND OF 16 ===
    ("236836", "Round-of-16", "Germany", "GER", "Sweden", "SWE", "2006-06-24"),
    ("236837", "Round-of-16", "Argentina", "ARG", "Mexico", "MEX", "2006-06-24"),
    ("236838", "Round-of-16", "England", "ENG", "Ecuador", "ECU", "2006-06-25"),
    ("236839", "Round-of-16", "Portugal", "POR", "Netherlands", "NED", "2006-06-25"),
    ("236840", "Round-of-16", "Italy", "ITA", "Australia", "AUS", "2006-06-26"),
    ("236841", "Round-of-16", "Switzerland", "SUI", "Ukraine", "UKR", "2006-06-26"),
    ("236842", "Round-of-16", "Brazil", "BRA", "Ghana", "GHA", "2006-06-27"),
    ("236843", "Round-of-16", "Spain", "ESP", "France", "FRA", "2006-06-27"),
]

# =============================================================================
# Scraper Functions
# =============================================================================

def fetch_page(url, delay=True):
    """Fetch a page with rate limiting and proper headers."""
    if delay:
        time.sleep(REQUEST_DELAY)
    
    full_url = url if url.startswith('http') else BASE_URL + url
    
    try:
        response = requests.get(full_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"      ❌ Fetch error: {e}")
        return None


def scrape_match(match_id, stage, team1_name, team1_code, team2_name, team2_code, date, tournament_code, skip_existing=False):
    """
    Scrape a single match and generate quiz files for both teams.
    Returns (success, reason) tuple.
    """
    print(f"\n  [{team1_name} vs {team2_name}] ({stage})")
    
    # Check if files already exist
    if skip_existing:
        output_dir = os.path.join(OUTPUT_BASE, tournament_code)
        stage_slug = stage.lower().replace(' ', '-').replace('/', '-')
        file1 = f"{stage_slug}_{team1_name.lower().replace(' ', '_')}.json"
        file2 = f"{stage_slug}_{team2_name.lower().replace(' ', '_')}.json"
        
        file1_exists = os.path.exists(os.path.join(output_dir, file1))
        file2_exists = os.path.exists(os.path.join(output_dir, file2))
        
        if file1_exists and file2_exists:
            print(f"    ⏭️  Skipped (files exist)")
            return True, "Skipped (existing)"
    
    # Build URLs
    slug = f"{team1_name.lower().replace(' ', '-')}_{team2_name.lower().replace(' ', '-')}"
    lineup_url = f"{BASE_URL}/{slug}/aufstellung/spielbericht/{match_id}"
    index_url = f"{BASE_URL}/{slug}/index/spielbericht/{match_id}"
    
    # === SCRAPE LINEUP PAGE ===
    print(f"    Fetching lineup...")
    soup = fetch_page(lineup_url, delay=True)
    if not soup:
        return False, "Failed to fetch lineup page"
    
    # Parse players
    players = []
    inline_tables = soup.find_all('table', class_='inline-table')
    
    for inline_table in inline_tables:
        outer_td = inline_table.find_parent('td')
        if not outer_td:
            continue
        outer_row = outer_td.find_parent('tr')
        if not outer_row:
            continue
            
        cells = outer_row.find_all('td', recursive=False)
        if len(cells) < 4:
            continue
        
        jersey_text = cells[0].get_text(strip=True)
        jersey = int(jersey_text) if jersey_text.isdigit() else None
        if jersey is None:
            continue
        
        player_link = cells[1].find('a', href=re.compile(r'/profil/spieler/\d+'))
        if not player_link:
            continue
            
        href = player_link.get('href', '')
        player_match = re.search(r'/([^/]+)/profil/spieler/(\d+)', href)
        if not player_match:
            continue
            
        player_slug = player_match.group(1)
        player_id = player_match.group(2)
        
        name_link = cells[1].find('a', href=re.compile(r'/leistungsdatendetails/'))
        player_name = name_link.get('title', '') if name_link else player_slug.replace('-', ' ').title()
        
        # CRITICAL: Club info must be present
        club_link = cells[3].find('a', href=re.compile(r'/startseite/verein/\d+'))
        if not club_link:
            continue  # Skip players without club data
            
        club_href = club_link.get('href', '')
        club_match = re.search(r'/([^/]+)/startseite/verein/(\d+)', club_href)
        if not club_match:
            continue
            
        club_id = club_match.group(2)
        club_name = club_link.get('title', '') or club_match.group(1).replace('-', ' ').title()
        
        if not club_name or not club_id:
            continue  # Skip if missing
        
        players.append({
            'jersey': jersey,
            'name': player_name,
            'player_id': player_id,
            'club_name': club_name,
            'club_id': club_id
        })
    
    print(f"    Found {len(players)} players with complete data")
    
    # Validate: need at least 22 players (11 per team)
    if len(players) < 22:
        return False, f"Not enough players ({len(players)}/22)"
    
    # === SCRAPE POSITIONS PAGE ===
    print(f"    Fetching positions...")
    soup = fetch_page(index_url, delay=True)
    if not soup:
        return False, "Failed to fetch index page"
    
    teams_positions = []
    lineup_boxes = soup.find_all('div', class_=re.compile(r'large-6.*columns|columns.*large-6'))
    
    for box in lineup_boxes:
        team_players = []
        all_divs = box.find_all('div', style=True)
        
        for elem in all_divs:
            style = elem.get('style', '')
            text = elem.get_text(strip=True)
            
            if not text or not re.match(r'^\d+[A-Za-z]', text):
                continue
            
            top_match = re.search(r'top\s*:\s*([\d.]+)%', style)
            left_match = re.search(r'left\s*:\s*([\d.]+)%', style)
            
            if top_match and left_match:
                top_pct = float(top_match.group(1))
                left_pct = float(left_match.group(1))
                
                jersey_match = re.match(r'(\d+)', text)
                if jersey_match:
                    jersey = int(jersey_match.group(1))
                    
                    if not any(p['jersey'] == jersey for p in team_players):
                        team_players.append({
                            'jersey': jersey,
                            'x': left_pct,
                            'y': top_pct
                        })
        
        if len(team_players) == 11:
            teams_positions.append(team_players)
    
    print(f"    Found positions for {len(teams_positions)} teams")
    
    if len(teams_positions) < 2:
        return False, f"Missing position data ({len(teams_positions)}/2 teams)"
    
    # === MERGE AND VALIDATE ===
    team1_players = players[:11]
    team2_players = players[11:22]
    team1_positions = teams_positions[0]
    team2_positions = teams_positions[1]
    
    # Validate all 11 players have positions
    team1_jerseys = {p['jersey'] for p in team1_players}
    team1_pos_jerseys = {p['jersey'] for p in team1_positions}
    team2_jerseys = {p['jersey'] for p in team2_players}
    team2_pos_jerseys = {p['jersey'] for p in team2_positions}
    
    if team1_jerseys != team1_pos_jerseys:
        missing = team1_jerseys - team1_pos_jerseys
        return False, f"{team1_name}: Missing positions for jerseys {missing}"
    
    if team2_jerseys != team2_pos_jerseys:
        missing = team2_jerseys - team2_pos_jerseys
        return False, f"{team2_name}: Missing positions for jerseys {missing}"
    
    # === MERGE DATA ===
    def merge_player_data(players_with_clubs, positions):
        pos_by_jersey = {p['jersey']: p for p in positions}
        merged = []
        
        x_values = [p['x'] for p in positions]
        avg_x = sum(x_values) / len(x_values) if x_values else 50
        x_offset = 50 - avg_x
        
        def scale_pos(val, padding=15):
            return padding + (val * (100 - 2 * padding) / 100)
        
        for player in players_with_clubs:
            jersey = player['jersey']
            pos = pos_by_jersey.get(jersey, {})
            
            raw_x = pos.get('x', 50) + x_offset
            raw_y = pos.get('y', 50)
            
            merged.append({
                'jersey': jersey,
                'name': player['name'],
                'player_id': player['player_id'],
                'club': {
                    'name': player['club_name'],
                    'club_id': player['club_id'],
                    'badge_url': f"https://tmssl.akamaized.net/images/wappen/head/{player['club_id']}.png"
                },
                'position': {
                    'x': scale_pos(raw_x),
                    'y': scale_pos(raw_y)
                }
            })
        
        return merged
    
    team1_merged = merge_player_data(team1_players, team1_positions)
    team2_merged = merge_player_data(team2_players, team2_positions)
    
    # === CREATE QUIZZES ===
    tournament_name = {
        "wc2022": "World Cup 2022",
        "wc2018": "World Cup 2018",
        "wc2014": "World Cup 2014",
        "wc2010": "World Cup 2010",
        "wc2006": "World Cup 2006",
    }.get(tournament_code, tournament_code)
    
    match_info = {
        "tournament": tournament_name,
        "stage": stage,
        "date": date,
    }
    
    quiz1 = {
        'answer': {'country': team1_name, 'country_code': team1_code},
        'match': {**match_info, 'opponent': team2_name},
        'players': team1_merged
    }
    
    quiz2 = {
        'answer': {'country': team2_name, 'country_code': team2_code},
        'match': {**match_info, 'opponent': team1_name},
        'players': team2_merged
    }
    
    # === SAVE FILES ===
    output_dir = os.path.join(OUTPUT_BASE, tournament_code)
    os.makedirs(output_dir, exist_ok=True)
    
    stage_slug = stage.lower().replace(' ', '-').replace('/', '-')
    file1 = f"{stage_slug}_{team1_name.lower().replace(' ', '_')}.json"
    file2 = f"{stage_slug}_{team2_name.lower().replace(' ', '_')}.json"
    
    with open(os.path.join(output_dir, file1), 'w') as f:
        json.dump(quiz1, f, indent=2)
    
    with open(os.path.join(output_dir, file2), 'w') as f:
        json.dump(quiz2, f, indent=2)
    
    print(f"    ✅ Saved: {file1}, {file2}")
    return True, "Success"


def run_batch(matches, tournament_code, skip_existing=False):
    """Run batch scraping for a list of matches."""
    print(f"\n{'='*60}")
    print(f"SCRAPING {tournament_code.upper()} ({len(matches)} matches)")
    if skip_existing:
        print("(Skipping existing files)")
    print(f"{'='*60}")
    
    success_count = 0
    skipped_count = 0
    failed = []
    
    for i, match_data in enumerate(matches, 1):
        match_id, stage, t1_name, t1_code, t2_name, t2_code, date = match_data
        
        print(f"\n[{i}/{len(matches)}]", end="")
        success, reason = scrape_match(
            match_id=match_id,
            stage=stage,
            team1_name=t1_name,
            team1_code=t1_code,
            team2_name=t2_name,
            team2_code=t2_code,
            date=date,
            tournament_code=tournament_code,
            skip_existing=skip_existing
        )
        
        if success:
            if reason == "Skipped (existing)":
                skipped_count += 1
            else:
                success_count += 1
        else:
            failed.append((f"{t1_name} vs {t2_name}", stage, reason))
            print(f"    ⚠️  SKIPPED: {reason}")
    
    return success_count, skipped_count, failed


def main():
    parser = argparse.ArgumentParser(description='Batch scrape World Cup matches')
    parser.add_argument('--tournament', '-t', 
                       choices=['wc2022', 'wc2018', 'wc2014', 'wc2010', 'wc2006', 'all'],
                       default='wc2022',
                       help='Which tournament to scrape')
    parser.add_argument('--skip-existing', '-s',
                       action='store_true',
                       help='Skip matches where quiz files already exist')
    args = parser.parse_args()
    
    tournaments = {
        'wc2022': WC2022_MATCHES,
        'wc2018': WC2018_MATCHES,
        'wc2014': WC2014_MATCHES,
        'wc2010': WC2010_MATCHES,
        'wc2006': WC2006_MATCHES,
    }
    
    if args.tournament == 'all':
        to_scrape = tournaments.items()
    else:
        to_scrape = [(args.tournament, tournaments[args.tournament])]
    
    total_matches = sum(len(m) for _, m in to_scrape)
    
    print("\n" + "="*60)
    print("STARTING11 BATCH SCRAPER")
    print("="*60)
    print(f"Tournaments: {', '.join(t for t, _ in to_scrape)}")
    print(f"Total matches: {total_matches}")
    if args.skip_existing:
        print("Mode: Skip existing files")
    else:
        print(f"Estimated time: ~{total_matches * 2 * REQUEST_DELAY / 60:.1f} minutes")
    print(f"Output: {OUTPUT_BASE}/")
    print("="*60)
    
    all_success = 0
    all_skipped = 0
    all_failed = []
    
    for tournament_code, matches in to_scrape:
        success, skipped, failed = run_batch(matches, tournament_code, skip_existing=args.skip_existing)
        all_success += success
        all_skipped += skipped
        all_failed.extend([(tournament_code, *f) for f in failed])
    
    # Summary
    print("\n" + "="*60)
    print("BATCH COMPLETE")
    print("="*60)
    print(f"✅ Scraped: {all_success} matches ({all_success * 2} quizzes)")
    if all_skipped > 0:
        print(f"⏭️  Skipped (existing): {all_skipped} matches")
    print(f"⚠️  Failed: {len(all_failed)} matches")
    
    if all_failed:
        print("\nFailed matches:")
        for tournament, match_name, stage, reason in all_failed:
            print(f"  - [{tournament}] {match_name} ({stage}): {reason}")
    
    print("="*60)


if __name__ == "__main__":
    main()
