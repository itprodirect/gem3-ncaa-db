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
        description="Seed dim_player_bio from NCAA players table."
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
            print("[ERROR] Expected `dim_player_global` table not found.")
            sys.exit(1)
        if not table_exists(conn, "dim_player_bio"):
            print(
                "[ERROR] Expected `dim_player_bio` table not found. "
                "Run 08_apply_player_bio_schema.py first."
            )
            sys.exit(1)

        cur = conn.cursor()
        print("[INFO] Inserting/refreshing bio rows from players ...")

        # Simple refresh: clear and reinsert from players snapshot
        cur.execute("DELETE FROM dim_player_bio;")

        cur.execute(
            """
            INSERT INTO dim_player_bio (
                global_player_id,
                full_name,
                class_year,
                height,
                weight,
                primary_position
            )
            SELECT DISTINCT
                p.global_player_id,
                p.full_name,
                p.class_year,
                p.height,
                p.weight,
                p.pos
            FROM players p
            WHERE p.global_player_id IS NOT NULL
              AND p.global_player_id != '';
            """
        )
        conn.commit()
        inserted = cur.rowcount
        print(f"[INFO] Inserted {inserted} rows into dim_player_bio.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
