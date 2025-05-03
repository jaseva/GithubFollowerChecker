import os
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import List
from app.models import Stats

DB_PATH = os.path.join(os.path.dirname(__file__), "followers.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS followers (
            login TEXT PRIMARY KEY,
            timestamp DATETIME
        )
        """
    )
    conn.commit()
    conn.close()

def track_followers_job(username: str, token: str):
    """
    Fetches current GitHub followers, upserts them into the DB (with a timestamp),
    and deletes any logins that have unfollowed since last run.
    """
    init_db()
    url = f"https://api.github.com/users/{username}/followers"
    resp = requests.get(url, auth=(username, token))
    resp.raise_for_status()
    current: List[str] = [f["login"] for f in resp.json()]
    now = datetime.utcnow()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert any new followers
    for login in current:
        cursor.execute(
            "INSERT OR IGNORE INTO followers (login, timestamp) VALUES (?, ?)",
            (login, now),
        )

    # Find unfollowers & remove them
    cursor.execute("SELECT login FROM followers")
    all_stored = {row[0] for row in cursor.fetchall()}
    unfollowers = all_stored - set(current)
    for login in unfollowers:
        cursor.execute("DELETE FROM followers WHERE login = ?", (login,))

    conn.commit()
    conn.close()

def get_follower_stats() -> Stats:
    """
    Returns a Stats object:
      - total_followers: count of rows in followers
      - new_followers: rows with timestamp in last 24h
      - unfollowers: number removed in last 24h
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # total
    cursor.execute("SELECT COUNT(*) FROM followers")
    total = cursor.fetchone()[0]

    # new in 24h
    since = datetime.utcnow() - timedelta(hours=24)
    cursor.execute(
        "SELECT COUNT(*) FROM followers WHERE timestamp >= ?", (since,)
    )
    new = cursor.fetchone()[0]

    # we don’t track deletes by timestamp here, so as a simple placeholder:
    # unfollowers is always 0 (unless you build a history table)
    unfollowers = 0

    conn.close()
    return Stats(
        total_followers=total,
        new_followers=new,
        unfollowers=unfollowers,
    )
