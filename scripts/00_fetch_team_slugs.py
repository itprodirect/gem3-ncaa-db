import requests
from bs4 import BeautifulSoup
import json
import os
import time

# CONFIG
OUTPUT_FILE = 'configs/d1_teams_master.json'
# CHANGED URL: Target the 2025 stats page (contains all active D1 teams)
URL = "https://www.sports-reference.com/cbb/seasons/men/2025-school-stats.html"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}


def get_d1_slugs():
    print(f"Fetching D1 team list from {URL}...")

    try:
        # Sleep briefly to cool down if you just ran the script
        time.sleep(2)

        resp = requests.get(URL, headers=HEADERS)

        if resp.status_code != 200:
            print(
                f"Error: Failed to fetch page. Status Code: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.content, 'html.parser')

        # The ID for the stats table on this page is 'basic_school_stats'
        table = soup.find('table', {'id': 'basic_school_stats'})

        if table is None:
            print("Error: Could not find the 'basic_school_stats' table.")
            if "banned" in resp.text.lower():
                print("!! YOU ARE CURRENTLY RATE LIMITED/BANNED !!")
                print("Wait 1 hour before trying again.")
            return

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')

        teams = []
        seen_slugs = set()

        print(f"Parsing rows...")

        for row in rows:
            # Skip header rows that repeat in the table
            if row.get('class') and 'thead' in row.get('class'):
                continue

            school_col = row.find('td', {'data-stat': 'school_name'})
            if not school_col:
                continue

            link = school_col.find('a')
            if link:
                # href looks like: /cbb/schools/duke/2025.html
                # Split: ['', 'cbb', 'schools', 'duke', '2025.html']
                # We want index 3 ('duke')
                href_parts = link['href'].split('/')
                if len(href_parts) > 3:
                    slug = href_parts[3]
                    name = link.text

                    if slug not in seen_slugs:
                        teams.append({"slug": slug, "name": name})
                        seen_slugs.add(slug)

        print(f"Found {len(teams)} active D1 teams.")

        os.makedirs('configs', exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(teams, f, indent=2)
        print(f"Saved master team list to {OUTPUT_FILE}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    get_d1_slugs()
