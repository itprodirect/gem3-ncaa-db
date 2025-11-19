# GEM3 NCAA Database

## How to run

1. Install requirements:
   `pip install -r requirements.txt`

2. Get the team list:
   `python scripts/00_fetch_team_slugs.py`

3. Scrape Data (This takes hours):
   `python scripts/01_scrape_all_d1.py`

4. Build Database:
   `python scripts/02_parse_stats_and_roster.py`
   `python scripts/03_load_sqlite_master.py`

5. Run Analytics:
   `python scripts/04_create_analytics_views.py`

