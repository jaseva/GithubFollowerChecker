import os
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import List
from app.models import Stats, FollowerSnapshot, ChangeEntry

DB_PATH = os.path.join(os.path.dirname(__file__), "followers.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _fetch_github_total() -> int:
    """Fetch the real follower count from GitHub’s REST API."""
    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME")
    if not token or not username:
        raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN must be set in env")
    resp = requests.get(
        f"https://api.github.com/users/{username}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json().get("followers", 0)

def get_follower_stats() -> Stats:
    conn = _get_conn()
    cur = conn.cursor()

    # ← now pulled from GitHub, not from your local DB
    total = _fetch_github_total()

    # count of *newly tracked* followers in the last 24h
    cutoff = (datetime.utcnow() - timedelta(days=1)).timestamp()
    cur.execute("SELECT COUNT(*) AS cnt FROM followers WHERE timestamp >= ?", (cutoff,))
    new = cur.fetchone()["cnt"] or 0

    # unfollowers still stubbed (you’d track them in a separate table)
    lost = 0

    return Stats(
        total_followers=total,
        new_followers=new,
        unfollowers=lost,
    )

def get_follower_trends() -> List[FollowerSnapshot]:
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT timestamp, COUNT(*) OVER (ORDER BY timestamp) AS total_followers
        FROM followers
        ORDER BY timestamp
    """)
    rows = cur.fetchall()
    return [
        FollowerSnapshot(
            timestamp=str(row["timestamp"]),
            total_followers=row["total_followers"],
        )
        for row in rows
    ]

def get_change_history(kind: str) -> List[ChangeEntry]:
    conn = _get_conn()
    cur = conn.cursor()

    if kind == "new":
        cutoff = (datetime.utcnow() - timedelta(days=1)).timestamp()
        cur.execute("""
            SELECT login, avatar_url, html_url, timestamp
            FROM followers
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (cutoff,))
    else:
        # no unfollow tracking yet
        return []

    rows = cur.fetchall()
    return [
        ChangeEntry(
            login=row["login"],
            avatar_url=row["avatar_url"],
            html_url=row["html_url"],
            timestamp=str(row["timestamp"]),
        )
        for row in rows
    ]
