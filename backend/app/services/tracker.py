# app/services/tracker.py

import os
import sqlite3
import requests
from datetime import datetime
from typing import Dict

# path to your SQLite DB file
DB_PATH = os.path.join(os.path.dirname(__file__), "followers.db")

def track_followers_job(username: str, token: str) -> Dict[str,int]:
    """
    Fetches current followers from GitHub, diffs against
    our stored set, writes a new count snapshot, and returns
    stats for this run.
    """
    # ensure tables exist
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            login TEXT PRIMARY KEY,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follower_counts (
            timestamp TEXT PRIMARY KEY,
            count INTEGER
        )
    """)

    # fetch current followers
    resp = requests.get(
        f"https://api.github.com/users/{username}/followers",
        auth=(username, token)
    )
    resp.raise_for_status()
    current = [f["login"] for f in resp.json()]

    now = datetime.utcnow().isoformat()
    # record the total count
    cursor.execute(
        "INSERT OR REPLACE INTO follower_counts (timestamp, count) VALUES (?,?)",
        (now, len(current))
    )

    # load previous set
    cursor.execute("SELECT login FROM followers")
    prev = {row[0] for row in cursor.fetchall()}

    new_followers = set(current) - prev
    unfollowers   = prev - set(current)

    # refresh the followers table
    cursor.execute("DELETE FROM followers")
    cursor.executemany(
        "INSERT INTO followers (login, timestamp) VALUES (?,?)",
        [(login, now) for login in current]
    )

    conn.commit()
    conn.close()

    return {
        "total_followers": len(current),
        "new_followers":   len(new_followers),
        "unfollowers":     len(unfollowers),
    }

def get_follower_stats() -> Dict[str,int]:
    """
    Reads the most recent snapshot and the snapshot from ~24h ago
    to compute total, new, and unfollower counts.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # latest total
    cursor.execute(
        "SELECT count FROM follower_counts ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    total = row[0] if row else 0

    # count from 24h ago (or fall back to latest)
    cursor.execute("""
        SELECT count
        FROM follower_counts
        WHERE timestamp <= datetime('now','-1 day')
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    prev = row[0] if row else total

    conn.close()

    new = max(total - prev, 0)
    unfollowers = max(prev - total, 0)

    return {
        "total_followers": total,
        "new_followers":   new,
        "unfollowers":     unfollowers,
    }

def get_follower_trends():
    """
    Returns every saved snapshot, ordered by time,
    as a list of { timestamp, total_followers }.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, count FROM follower_counts ORDER BY timestamp"
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {"timestamp": row[0], "total_followers": row[1]}
        for row in rows
    ]
