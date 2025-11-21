import argparse
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.sports-reference.com"
SEARCH_URL = f"{BASE_URL}/cbb/search/search.fcgi"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; gem3-ncaa-db/0.1; +https://github.com/itprodirect)",
}


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?;",
        (name,),
    )
    return cur.fetchone() is not None


def get_latest_season(conn: sqlite3.Connection) -> int:
    cur = conn.cursor
    cur = conn.cursor()
    cur.execute("SELECT MAX(season) FROM players;")
    row = cur.fetchone()
    if not row or row[0] is None:
        raise RuntimeError("No seasons found in players table.")
    return int(row[0])


def search_player_url(name: str) -> Optional[str]:
    """Search Sports-Reference for a player and return the first /cbb/players/*.html URL."""
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"search": name},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] Search request failed for '{name}': {e}")
        return None

    # If Sports-Reference redirects straight to a player page, use that.
    if resp.url.startswith(f"{BASE_URL}/cbb/players/") and resp.url.endswith(".html"):
        print(f"[INFO] Direct player page for '{name}': {resp.url}")
        return resp.url

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try to find a player link in the search results table first.
    link = None
    selectors = [
        "div.search-results table tbody tr th a[href^='/cbb/players/'][href$='.html']",
        "div.search-results a[href^='/cbb/players/'][href$='.html']",
        "a[href^='/cbb/players/'][href$='.html']",
    ]
    for sel in selectors:
        link = soup.select_one(sel)
        if link and link.get("href"):
            break

    if not link or not link.get("href"):
        print(f"[WARN] No specific player link found for '{name}'. "
              f"Search page URL: {resp.url}")
        return None

    href = link["href"]
    if not href.startswith("/"):
        href = "/" + href
    url = BASE_URL + href
    print(f"[INFO] Search match for '{name}': {url}")
    return url


def fetch_birthdate(player_url: str) -> Optional[str]:
    """Fetch player page and extract birthdate in YYYY-MM-DD from data-birth attr."""
    try:
        resp = requests.get(player_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] Failed to fetch player page {player_url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    span = soup.find("span", attrs={"itemprop": "birthDate"})
    if span:
        data_birth = span.get("data-birth")
        if data_birth:
            print(f"[INFO] Parsed birthdate {data_birth} from {player_url}")
            return data_birth.strip()

    print(f"[WARN] Could not find structured birthdate on page: {player_url}")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape player DOBs from Sports-Reference and update dim_player_bio.birthdate."
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
        help="Season year to process (e.g., 2025). If omitted, uses latest season in DB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Max number of players to process in this run.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="Seconds to sleep between player requests (rate limiting).",
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

        cur = conn.cursor()

        season = args.season
        if season is None:
            season = get_latest_season(conn)
            print(f"[INFO] Using latest season from DB: {season}")

        # Get players for this season with missing DOB
        cur.execute(
            """
            SELECT DISTINCT
                pb.global_player_id,
                pb.full_name
            FROM dim_player_bio pb
            JOIN players p
              ON p.global_player_id = pb.global_player_id
            WHERE p.season = ?
              AND (pb.birthdate IS NULL OR pb.birthdate = '')
            ORDER BY pb.full_name
            LIMIT ?;
            """,
            (season, args.limit),
        )
        rows = cur.fetchall()

        if not rows:
            print(
                f"[INFO] No players with missing DOB found for season {season}.")
            return

        print(
            f"[INFO] Found {len(rows)} players with missing DOB for season {season}.")

        updated = 0
        for idx, (global_player_id, full_name) in enumerate(rows, start=1):
            print(
                f"\n[PLAYER {idx}/{len(rows)}] {full_name} ({global_player_id})")

            player_url = search_player_url(full_name)
            if not player_url:
                continue

            dob = fetch_birthdate(player_url)
            if not dob:
                continue

            cur.execute(
                """
                UPDATE dim_player_bio
                SET birthdate = ?, updated_at = datetime('now')
                WHERE global_player_id = ?;
                """,
                (dob, global_player_id),
            )
            conn.commit()
            updated += 1

            print(
                f"[INFO] Updated {full_name} ({global_player_id}) with DOB {dob}.")
            if args.sleep > 0:
                time.sleep(args.sleep)

        print(
            f"\n[RESULT] Updated {updated} players with DOBs for season {season}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
