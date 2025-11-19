import pandas as pd
import sqlite3
import os
import json

# --- PATHS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, 'ncaa-analytics',
                       'db', 'ncaa_d1_master.db')
INTER_DIR = os.path.join(PROJECT_ROOT, 'ncaa-analytics', 'data_intermediate')
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'configs', 'd1_teams_master.json')

YEARS = [2021, 2022, 2023, 2024, 2025]


def init_schema(conn):
    """Creates the Normalized Tables (Teams, Players, Stats) matching reference style."""
    cur = conn.cursor()

    # 1. Teams Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        team_id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_slug TEXT NOT NULL UNIQUE,
        team_name TEXT,
        conference TEXT,
        is_d1 INTEGER DEFAULT 1
    );
    """)

    # 2. Players Table (Unique by Name + Team + Season to track transfers/years)
    # Note: The reference code uses Name+Team+Season as unique.
    # In a 5-year DB, a player changes seasons.
    # We will create a 'master' player entry per season per team.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        team_id INTEGER NOT NULL,
        season INTEGER NOT NULL,
        class_year TEXT,
        height TEXT,
        weight TEXT,
        pos TEXT,
        FOREIGN KEY (team_id) REFERENCES teams(team_id),
        UNIQUE (full_name, team_id, season)
    );
    """)

    # 3. Stats Table (Linked to Player ID)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fact_player_stats (
        stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        season INTEGER NOT NULL,
        g INTEGER,
        gs INTEGER,
        mp REAL,
        pts REAL,
        trb REAL,
        ast REAL,
        stl REAL,
        blk REAL,
        fg_pct REAL,
        three_p_pct REAL,
        ft_pct REAL,
        ts_pct REAL,
        FOREIGN KEY (player_id) REFERENCES players(player_id)
    );
    """)
    conn.commit()


def load_data():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_schema(conn)

    # 1. Load Teams from Config
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            teams_data = json.load(f)

        print(f"Loading {len(teams_data)} teams...")
        cur = conn.cursor()
        for team in teams_data:
            cur.execute("INSERT OR IGNORE INTO teams (team_slug, team_name) VALUES (?, ?)",
                        (team['slug'], team['name']))
        conn.commit()

    # 2. Load Stats & Rosters by Year
    for year in YEARS:
        stats_path = os.path.join(INTER_DIR, str(
            year), f'per_game_all_d1_{year}.csv')
        roster_path = os.path.join(INTER_DIR, str(
            year), f'rosters_all_d1_{year}.csv')

        if not os.path.exists(stats_path):
            print(f"Skipping {year} (No data)")
            continue

        print(f"Processing {year}...")
        df_stats = pd.read_csv(stats_path)

        # Clean Column Names
        df_stats.columns = [c.replace('%', '_pct').replace(
            '3', 'three_').replace('2', 'two_') for c in df_stats.columns]

        # Load Roster if available for enrichment
        df_roster = pd.DataFrame()
        if os.path.exists(roster_path):
            df_roster = pd.read_csv(roster_path)

        cur = conn.cursor()

        # --- INSERT PLAYERS AND STATS ---
        # This mimics the reference logic: Join stats to teams, then insert players

        for _, row in df_stats.iterrows():
            slug = row['team_slug']
            name = row['Player']

            # Get Team ID
            cur.execute(
                "SELECT team_id FROM teams WHERE team_slug = ?", (slug,))
            res = cur.fetchone()
            if not res:
                continue  # Skip if team not in DB
            team_id = res[0]

            # Try to find roster info for this player
            r_info = df_roster[(df_roster['team_slug'] == slug) & (
                df_roster['Player'] == name)] if not df_roster.empty else pd.DataFrame()

            cls = r_info['Class'].values[0] if not r_info.empty and 'Class' in r_info else None
            ht = r_info['Ht'].values[0] if not r_info.empty and 'Ht' in r_info else None
            wt = r_info['Wt'].values[0] if not r_info.empty and 'Wt' in r_info else None
            pos = r_info['Pos'].values[0] if not r_info.empty and 'Pos' in r_info else None

            # Insert Player (Or Ignore if exists)
            cur.execute("""
                INSERT OR IGNORE INTO players (full_name, team_id, season, class_year, height, weight, pos)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, team_id, year, cls, ht, wt, pos))

            # Get Player ID
            cur.execute(
                "SELECT player_id FROM players WHERE full_name = ? AND team_id = ? AND season = ?", (name, team_id, year))
            pid = cur.fetchone()[0]

            # Insert Stats
            # Calculate TS% (Points / (2 * (FGA + 0.44 * FTA)))
            pts = row.get('PTS', 0)
            fga = row.get('FGA', 0)
            fta = row.get('FTA', 0)
            ts_pct = 0
            if (fga + 0.44 * fta) > 0:
                ts_pct = pts / (2 * (fga + 0.44 * fta))

            cur.execute("""
                INSERT INTO fact_player_stats (player_id, season, g, gs, mp, pts, trb, ast, stl, blk, fg_pct, three_p_pct, ft_pct, ts_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid, year, row.get('G'), row.get('GS'), row.get('MP'),
                pts, row.get('TRB'), row.get(
                    'AST'), row.get('STL'), row.get('BLK'),
                row.get('FG_pct'), row.get(
                    'three_P_pct'), row.get('FT_pct'), ts_pct
            ))

        conn.commit()
        print(f"  Loaded {year} complete.")

    conn.close()
    print("Database Load Complete.")


if __name__ == "__main__":
    load_data()
