import os
import time
import json
import requests
import random
from tqdm import tqdm

# --- CONFIG ---
TEST_MODE = False  # <--- Set to False for the full run
YEARS = [2021, 2022, 2023, 2024, 2025]

# --- ROBUST PATH SETUP ---
# Get the location of this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the project root
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Define paths relative to the project root
TEAM_LIST_PATH = os.path.join(PROJECT_ROOT, 'configs', 'd1_teams_master.json')
RAW_DIR = os.path.join(PROJECT_ROOT, 'ncaa-analytics', 'data_raw')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}


def scrape_season(year, teams):
    year_dir = os.path.join(RAW_DIR, str(year))
    os.makedirs(year_dir, exist_ok=True)

    print(f"\n--- Scraping Season: {year} ---")

    # If in test mode, slice the list to just the first 3 teams
    current_batch = teams[:3] if TEST_MODE else teams

    # Randomize order to behave less like a bot (only if full run)
    if not TEST_MODE:
        random.shuffle(current_batch)

    # Use tqdm for a nice progress bar
    for team in tqdm(current_batch):
        slug = team['slug']
        filename = f"{slug}_{year}.html"
        filepath = os.path.join(year_dir, filename)

        # Skip if already downloaded
        if os.path.exists(filepath):
            continue

        url = f"https://www.sports-reference.com/cbb/schools/{slug}/{year}.html"

        try:
            # VITAL: Rate limiting.
            # Sleep 3.5 to 4.5 seconds (~15 requests/min) to stay safe.
            time.sleep(random.uniform(3.5, 4.5))

            resp = requests.get(url, headers=HEADERS)

            if resp.status_code == 200:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(resp.text)
            elif resp.status_code == 404:
                # Team might not have existed or played D1 that year
                pass
            elif resp.status_code == 429:
                print(f"\nHIT RATE LIMIT (429). Sleeping for 2 minutes...")
                time.sleep(120)
            else:
                print(f"Error {resp.status_code} for {slug}")

        except Exception as e:
            print(f"Failed {slug}: {e}")


if __name__ == "__main__":
    print(f"Looking for config at: {TEAM_LIST_PATH}")

    if not os.path.exists(TEAM_LIST_PATH):
        print(f"Error: Config file not found at {TEAM_LIST_PATH}")
        print("Did you run script 00_fetch_team_slugs.py?")
    else:
        with open(TEAM_LIST_PATH, 'r') as f:
            d1_teams = json.load(f)

        print(f"Loaded {len(d1_teams)} teams.")
        if TEST_MODE:
            print("!!! RUNNING IN TEST MODE (First 3 teams only) !!!")
        else:
            print("!!! RUNNING FULL SCRAPE (This will take hours) !!!")

        for year in YEARS:
            scrape_season(year, d1_teams)
