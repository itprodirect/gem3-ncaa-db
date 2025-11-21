import argparse
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply player bio schema SQL file to the NCAA SQLite database."
    )
    parser.add_argument(
        "--db-path",
        default="ncaa-analytics/db/ncaa_d1_master.db",
        help="Path to SQLite DB.",
    )
    parser.add_argument(
        "--schema-path",
        default="schema/player_bio_schema.sql",
        help="Path to player bio schema SQL file.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    schema_path = Path(args.schema_path)

    print(f"[INFO] Using DB: {db_path}")
    print(f"[INFO] Using schema: {schema_path}")

    if not db_path.exists():
        print(f"[ERROR] DB not found at: {db_path}")
        sys.exit(1)
    if not schema_path.exists():
        print(f"[ERROR] Schema file not found at: {schema_path}")
        sys.exit(1)

    sql = schema_path.read_text(encoding="utf-8")

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
        print("[INFO] Player bio schema applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
