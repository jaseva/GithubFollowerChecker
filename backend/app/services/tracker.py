import os
import sqlite3
import requests
from datetime import datetime

# We'll write everything into this file (auto-created if missing)
DB_PATH = os.path.join(os.path.dirname(__file__), "followers.db")

def fetch_total_followers(username: str, token: str) -> int:
    headers = {"Authorization": f"token {token}"}
    r = requests.get(f"https://api.github.com/users/{username}", headers=headers)
    r.raise_for_status()
    return r.json().get("followers", 0)

def track_followers_paginated_job(username: str, token: str):
    """
    Every run, page through GitHub's /users/{username}/followers
    (100 per page), collect all IDs, then INSERT or IGNORE them
    into our `followers` table with the current timestamp.
    """
    all_ids = []
    page = 1
    headers = {"Authorization": f"token {token}"}

    while True:
        resp = requests.get(
            f"https://api.github.com/users/{username}/followers",
            params={"per_page": 100, "page": page},
            headers=headers,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break

        # collect each follower's unique GitHub numeric ID
        all_ids.extend(user["id"] for user in batch)
        page += 1

    # Persist into SQLite
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create table if it's the first run
    cur.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        follower_id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL
    )
    """)

    now = datetime.utcnow().isoformat()
    for fid in all_ids:
        # only insert new ones; ignore ones we already have
        cur.execute(
            "INSERT OR IGNORE INTO followers (follower_id, timestamp) VALUES (?, ?)",
            (fid, now),
        )

    conn.commit()
    conn.close()
