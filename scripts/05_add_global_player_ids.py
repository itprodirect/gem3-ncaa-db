import argparse
import sqlite3
import sys
from pathlib import Path

# We try these in order and use the first one that exists.
CANDIDATE_PLAYER_TABLES = ["players", "dim_players", "dim_player"]


def find_player_table(conn: sqlite3.Connection) -> str | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    )
    tables = {row[0] for row in cur.fetchall()}

    for name in CANDIDATE_PLAYER_TABLES:
        if name in tables:
            print(f"[INFO] Using player table: {name}")
            return name

    print(
        f"[ERROR] None of the expected player tables found: {CANDIDATE_PLAYER_TABLES}")
    print(f"[INFO] Tables present: {', '.join(sorted(tables))}")
    return None


def get_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name});")
    rows = cur.fetchall()
    cols = [r[1] for r in rows]
    print(f"[INFO] Columns in {table_name}: {', '.join(cols)}")
    return cols


def add_global_player_id(conn: sqlite3.Connection, table_name: str, id_col: str) -> None:
    cols = get_columns(conn, table_name)
    cur = conn.cursor()

    if "global_player_id" not in cols:
        print(f"[INFO] Adding global_player_id column to {table_name} ...")
        cur.execute(
            f"ALTER TABLE {table_name} ADD COLUMN global_player_id TEXT;")
        conn.commit()
    else:
        print(
            f"[INFO] global_player_id column already exists on {table_name}.")

    print(f"[INFO] Populating global_player_id from {id_col} ...")
    cur.execute(
        f"""
        UPDATE {table_name}
        SET global_player_id = {id_col}
        WHERE global_player_id IS NULL OR global_player_id = '';
        """
    )
    conn.commit()
    print("[INFO] Done setting global_player_id.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add and populate global_player_id column for player table."
    )
    parser.add_argument(
        "--db-path",
        default="ncaa-analytics/db/ncaa.sqlite",
        help="Path to local NCAA SQLite database.",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    print(f"[INFO] Using DB: {db_path}")

    if not db_path.exists():
        print(f"[ERROR] SQLite DB not found at: {db_path}")
        print("        Run the main NCAA pipeline to build the DB first.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    try:
        table_name = find_player_table(conn)
        if not table_name:
            sys.exit(1)

        cols = get_columns(conn, table_name)
        if "player_id" in cols:
            id_col = "player_id"
        elif "id" in cols:
            id_col = "id"
        else:
            print(
                f"[ERROR] Could not find an id column on {table_name} (looked for player_id/id).")
            sys.exit(1)

        add_global_player_id(conn, table_name, id_col)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
