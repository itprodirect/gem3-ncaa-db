import argparse
import sqlite3
import sys
from pathlib import Path


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;",
        (name,),
    )
    return cur.fetchone() is not None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap dim_player_global from NCAA players table."
    )
    parser.add_argument(
        "--db-path",
        default="ncaa-analytics/db/ncaa_d1_master.db",
        help="Path to SQLite DB.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    print(f"[INFO] Using DB: {db_path}")

    if not db_path.exists():
        print(f"[ERROR] DB not found at: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        if not table_exists(conn, "players"):
            print("[ERROR] Expected `players` table not found.")
            sys.exit(1)
        if not table_exists(conn, "dim_player_global"):
            print(
                "[ERROR] Expected `dim_player_global` table not found. "
                "Run 06_apply_nba_schema.py first."
            )
            sys.exit(1)

        cur = conn.cursor()
        print("[INFO] Inserting missing players into dim_player_global ...")
        cur.execute(
            """
            INSERT INTO dim_player_global (global_player_id, canonical_name)
            SELECT DISTINCT p.global_player_id, p.full_name
            FROM players p
            LEFT JOIN dim_player_global g
                ON g.global_player_id = p.global_player_id
            WHERE p.global_player_id IS NOT NULL
              AND p.global_player_id != ''
              AND g.global_player_id IS NULL;
            """
        )
        conn.commit()
        inserted = cur.rowcount
        print(f"[INFO] Inserted {inserted} new rows into dim_player_global.")

        cur.execute("SELECT COUNT(*) FROM dim_player_global;")
        total = cur.fetchone()[0]
        print(f"[INFO] dim_player_global now has {total} rows.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
