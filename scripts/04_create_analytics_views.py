import pandas as pd
from sqlalchemy import create_engine, text
import numpy as np
import os

# --- PATH CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, 'ncaa-analytics',
                       'db', 'ncaa_d1_master.db')
# Handle Windows paths for SQLite
DB_CONNECTION_STR = f'sqlite:///{DB_PATH}'


def create_views():
    engine = create_engine(DB_CONNECTION_STR)

    print("Creating Views...")
    with engine.connect() as con:
        # 1. Create a Master View that joins Teams, Players, and Stats
        # This makes querying easy (like a flat Excel sheet)
        con.execute(text("DROP VIEW IF EXISTS view_player_profiles;"))

        sql_view = """
        CREATE VIEW view_player_profiles AS
        SELECT 
            p.player_id,
            p.full_name,
            t.team_slug,
            t.team_name,
            t.conference,
            p.season,
            p.class_year,
            p.height,
            p.weight,
            p.pos,
            s.g,
            s.gs,
            s.mp,
            s.pts,
            s.trb,
            s.ast,
            s.stl,
            s.blk,
            s.fg_pct,
            s.three_p_pct,
            s.ft_pct,
            s.ts_pct
        FROM fact_player_stats s
        JOIN players p ON s.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id;
        """
        con.execute(text(sql_view))
        print("View 'view_player_profiles' created successfully.")


def run_similarity_search(target_season=2025):
    print(f"\n--- Computing Similarity for {target_season} ---")
    engine = create_engine(DB_CONNECTION_STR)

    # Load data using the View we just made
    try:
        df = pd.read_sql(
            f"SELECT * FROM view_player_profiles WHERE g > 0", engine)
        if df.empty:
            print("No stats found in DB.")
            return
    except Exception as e:
        print(f"Database Error: {e}")
        return

    # 1. Select Features for Similarity
    features = ['pts', 'trb', 'ast', 'stl',
                'blk', 'fg_pct', 'three_p_pct', 'ts_pct']

    # 2. Normalize Data (Z-Score) across the ENTIRE dataset (all years)
    # This lets us compare a 2025 player to a 2021 player
    for f in features:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0)
        if df[f].std() != 0:
            df[f'{f}_z'] = (df[f] - df[f].mean()) / df[f].std()
        else:
            df[f'{f}_z'] = 0

    # 3. Filter for current target players (e.g., 2025 roster)
    current_players = df[df['season'] == target_season].copy()

    if current_players.empty:
        print(
            f"No players found for season {target_season}. (Did you run the parser?)")
        return

    print(
        f"Analyzing {len(current_players)} players from {target_season} against {len(df)} historical records...")

    # 4. Find Similar Players (Example: Top 5 Scorers)
    top_scorers = current_players.sort_values('pts', ascending=False).head(5)

    for idx, target in top_scorers.iterrows():
        # Calculate Euclidean Distance
        dist_sq = 0
        for f in features:
            dist_sq += (df[f'{f}_z'] - target[f'{f}_z']) ** 2

        # Calculate distance for ALL players in DB
        df['distance'] = np.sqrt(dist_sq)

        # Find top 3 matches (excluding the player themselves)
        # We allow matches from previous years (historical comps)
        matches = df[
            (df['player_id'] != target['player_id'])  # Don't match self
        ].sort_values('distance').head(3)

        print(f"\nPLAYER: {target['full_name']} ({target['team_slug']})")
        print(
            f"STATS:  {target['pts']} PPG, {target['trb']} RPG, {target['ts_pct']:.3f} TS%")
        print("-" * 40)
        for i, match in matches.iterrows():
            print(
                f"  MATCH: {match['full_name']} ({match['team_slug']} '{match['season']})")
            print(
                f"         Dist: {match['distance']:.2f} | Stats: {match['pts']} PPG, {match['ts_pct']:.3f} TS%")


if __name__ == "__main__":
    create_views()
    run_similarity_search(2025)
