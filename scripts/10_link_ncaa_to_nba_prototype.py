import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path


def check_players_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(players);")
        rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        print("[ERROR] Could not read `players` table:", e)
        return

    if not rows:
        print("[WARN] No `players` table found in the database.")
        return

    cols = [r[1] for r in rows]
    print(f"[INFO] Found `players` table with {len(cols)} columns:")
    print("       " + ", ".join(cols))


def load_nba_csv(nba_csv_path: Path) -> int:
    if not nba_csv_path.exists():
        print(f"[WARN] NBA CSV not found at: {nba_csv_path}")
        print("       Download a players CSV (e.g. from Basketball-Reference) "
              "and save it here, then rerun this script.")
        return 0

    with nba_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"[INFO] Loaded {len(rows)} NBA rows from {nba_csv_path}")
    sample_cols = list(reader.fieldnames or [])
    print(f"[INFO] Columns in NBA CSV: {', '.join(sample_cols)}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prototype NCAA ↔ NBA player linker (no writes yet)."
    )
    parser.add_argument(
        "--db-path",
        default="ncaa-analytics/db/ncaa.sqlite",
        help="Path to local NCAA SQLite database.",
    )
    parser.add_argument(
        "--nba-csv",
        default="data_external/nba/bref_players_2023_24.csv",
        help="Path to NBA players CSV export.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    nba_csv_path = Path(args.nba_csv)

    print(f"[INFO] Using DB: {db_path}")
    print(f"[INFO] Using NBA CSV: {nba_csv_path}")

    if not db_path.exists():
        print(f"[ERROR] SQLite DB not found at: {db_path}")
        print("        Run the NCAA pipeline scripts first to build the DB.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        check_players_table(conn)
    finally:
        conn.close()

    load_nba_csv(nba_csv_path)

    print("\n[TODO] Next steps for this script:")
    print("  - Implement name + college + DOB matching between NCAA and NBA.")
    print("  - Create / populate dim_player_global and fact_nba_season tables.")
    print("  - Add simple reports: NCAA→NBA hit rate, archetype outcomes, etc.")


if __name__ == "__main__":
    main()
