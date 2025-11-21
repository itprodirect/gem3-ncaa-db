import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import date
from statistics import mean, pstdev
from typing import Optional, List


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;",
        (name,),
    )
    return cur.fetchone() is not None


def ensure_age_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fact_player_age_season (
            global_player_id     TEXT NOT NULL,
            season               INTEGER NOT NULL,
            age_season           REAL,
            age_zscore           REAL,
            is_young_for_level   INTEGER,
            is_old_for_level     INTEGER,
            created_at           TEXT DEFAULT (datetime('now')),
            updated_at           TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (global_player_id, season),
            FOREIGN KEY (global_player_id) REFERENCES dim_player_global(global_player_id)
        );
        """
    )
    conn.commit()


def get_seasons(conn: sqlite3.Connection, target_season: Optional[int]) -> List[int]:
    cur = conn.cursor()
    if target_season is not None:
        return [target_season]
    cur.execute("SELECT DISTINCT season FROM players ORDER BY season;")
    rows = cur.fetchall()
    return [int(r[0]) for r in rows if r[0] is not None]


def compute_age(birthdate_str: str, season: int) -> Optional[float]:
    """
    Compute age in years at a reference date for the season.
    Using July 1 of the season year as a simple reference point.
    """
    try:
        year, month, day = map(int, birthdate_str.split("-"))
        dob = date(year, month, day)
    except Exception:
        return None

    ref_date = date(season, 7, 1)
    days = (ref_date - dob).days
    return days / 365.25


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute age features by season into fact_player_age_season."
    )
    parser.add_argument(
        "--db-path",
        default="ncaa-analytics/db/ncaa_d1_master.db",
        help="Path to SQLite DB.",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="Specific season year to compute (e.g., 2025). If omitted, computes all.",
    )
    parser.add_argument(
        "--young-threshold",
        type=float,
        default=-0.75,
        help="Z-score at or below which a player is considered young for level.",
    )
    parser.add_argument(
        "--old-threshold",
        type=float,
        default=0.75,
        help="Z-score at or above which a player is considered old for level.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"[ERROR] DB not found at: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        if not table_exists(conn, "players"):
            print("[ERROR] Expected `players` table not found.")
            sys.exit(1)
        if not table_exists(conn, "dim_player_bio"):
            print("[ERROR] Expected `dim_player_bio` table not found.")
            sys.exit(1)

        ensure_age_table(conn)

        seasons = get_seasons(conn, args.season)
        if not seasons:
            print("[ERROR] No seasons found in players table.")
            sys.exit(1)

        cur = conn.cursor()

        for season in seasons:
            print(f"\n[INFO] Computing age features for season {season} ...")

            cur.execute(
                """
                SELECT DISTINCT
                    p.global_player_id,
                    p.season,
                    b.birthdate
                FROM players p
                JOIN dim_player_bio b
                  ON b.global_player_id = p.global_player_id
                WHERE p.season = ?
                  AND b.birthdate IS NOT NULL
                  AND b.birthdate != '';
                """,
                (season,),
            )
            rows = cur.fetchall()
            if not rows:
                print(
                    f"[WARN] No players with birthdate found for season {season}. Skipping.")
                continue

            ages = {}
            for global_player_id, _, birthdate_str in rows:
                age = compute_age(birthdate_str, season)
                if age is None:
                    continue
                ages[global_player_id] = age

            if not ages:
                print(
                    f"[WARN] Could not compute ages for any players in season {season}.")
                continue

            age_values = list(ages.values())
            mu = mean(age_values)
            sigma = pstdev(age_values) if len(age_values) > 1 else 0.0

            print(
                f"[INFO] Season {season}: N={len(age_values)}, "
                f"mean age={mu:.2f}, std={sigma:.2f}"
            )

            for global_player_id, age in ages.items():
                if sigma > 0:
                    z = (age - mu) / sigma
                else:
                    z = 0.0

                is_young = int(z <= args.young_threshold)
                is_old = int(z >= args.old_threshold)

                cur.execute(
                    """
                    INSERT INTO fact_player_age_season (
                        global_player_id,
                        season,
                        age_season,
                        age_zscore,
                        is_young_for_level,
                        is_old_for_level,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    ON CONFLICT(global_player_id, season) DO UPDATE SET
                        age_season = excluded.age_season,
                        age_zscore = excluded.age_zscore,
                        is_young_for_level = excluded.is_young_for_level,
                        is_old_for_level = excluded.is_old_for_level,
                        updated_at = datetime('now');
                    """,
                    (
                        global_player_id,
                        season,
                        age,
                        z,
                        is_young,
                        is_old,
                    ),
                )

            conn.commit()
            print(
                f"[INFO] Wrote age features for {len(ages)} players in season {season}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
