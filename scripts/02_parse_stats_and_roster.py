import os
import pandas as pd
import glob
from io import StringIO
import re

# --- PATHS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RAW_DIR = os.path.join(PROJECT_ROOT, 'ncaa-analytics', 'data_raw')
INTER_DIR = os.path.join(PROJECT_ROOT, 'ncaa-analytics', 'data_intermediate')

YEARS = [2021, 2022, 2023, 2024, 2025]


def clean_html(html_content):
    """
    Strip HTML comments to expose hidden tables.
    """
    return html_content.replace('<!--', '').replace('-->', '')


def find_per_game_table(tables):
    """
    Heuristic: Find the table that looks like per-game stats.
    Logic borrowed from reference: Look for 'Player' and 'G' columns.
    """
    for df in tables:
        # Normalize columns to strings and check content
        cols = [str(c) for c in df.columns]
        if "Player" in cols and "G" in cols and "PTS" in cols:
            return df
    return None


def parse_html_for_year(year):
    year_path = os.path.join(RAW_DIR, str(year))
    print(f"\n--- Processing Year: {year} ---")

    if not os.path.exists(year_path):
        print(f"No data found for {year}")
        return

    html_files = glob.glob(os.path.join(year_path, "*.html"))

    all_stats = []
    all_rosters = []

    for filepath in html_files:
        file_name = os.path.basename(filepath)
        team_slug = file_name.split('_')[0]

        with open(filepath, 'r', encoding='utf-8') as f:
            raw_html = f.read()
            # 1. Strip comments to see hidden tables
            html_content = clean_html(raw_html)

        try:
            # Read ALL tables from the HTML
            tables = pd.read_html(StringIO(html_content))
        except ValueError:
            print(f"  No tables found in {file_name}")
            continue

        # --- 1. Find Stats Table (Heuristic Approach) ---
        df_stats = find_per_game_table(tables)

        if df_stats is not None:
            # Clean up standard SR footer rows (Team Totals, etc)
            df_stats = df_stats[df_stats['Player'].notna()]
            bad_labels = {"Team", "Team Totals", "Opponents", "Opponent"}
            df_stats = df_stats[~df_stats["Player"].isin(bad_labels)]

            # Add Metadata
            df_stats.insert(0, 'team_slug', team_slug)
            df_stats.insert(1, 'season', year)

            all_stats.append(df_stats)
        else:
            print(f"  Warning: No 'Per Game' table found for {team_slug}")

        # --- 2. Find Roster Table (Heuristic Approach) ---
        # Look for 'Player' and 'Class' or 'Pos'
        df_roster = None
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            if "player" in cols and ("class" in cols or "pos" in cols or "hgt" in cols):
                df_roster = df
                break

        if df_roster is not None:
            df_roster.insert(0, 'team_slug', team_slug)
            df_roster.insert(1, 'season', year)
            all_rosters.append(df_roster)

    # --- SAVE CSVs ---
    out_dir = os.path.join(INTER_DIR, str(year))
    os.makedirs(out_dir, exist_ok=True)

    if all_stats:
        master_stats = pd.concat(all_stats, ignore_index=True)
        outfile = os.path.join(out_dir, f'per_game_all_d1_{year}.csv')
        master_stats.to_csv(outfile, index=False)
        print(f"SUCCESS: Saved {len(master_stats)} stat rows to {outfile}")
    else:
        print(f"FAILURE: No stats found for {year}.")

    if all_rosters:
        master_roster = pd.concat(all_rosters, ignore_index=True)
        outfile = os.path.join(out_dir, f'rosters_all_d1_{year}.csv')
        master_roster.to_csv(outfile, index=False)
        print(f"SUCCESS: Saved {len(master_roster)} roster rows to {outfile}")


if __name__ == "__main__":
    for year in YEARS:
        parse_html_for_year(year)
