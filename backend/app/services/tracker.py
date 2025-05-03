import os
import sqlite3
from datetime import datetime, timedelta
from typing import List
from app.models import Stats, FollowerSnapshot, ChangeEntry

DB_PATH = os.path.join(os.path.dirname(__file__), "followers.db")

def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_follower_stats() -> Stats:
    conn = _get_conn()
    cur = conn.cursor()

    # total so far
    cur.execute("SELECT COUNT(*) AS cnt FROM followers")
    total = cur.fetchone()["cnt"]

    # new in last 24h
    cutoff = (datetime.utcnow() - timedelta(days=1)).timestamp()
    cur.execute("SELECT COUNT(*) AS cnt FROM followers WHERE timestamp >= ?", (cutoff,))
    new = cur.fetchone()["cnt"]

    # unfollowers: we'd track deletions in a separate table; stub to 0 for now
    lost = 0

    return Stats(
        total_followers=total,
        new_followers=new,
        unfollowers=lost,
    )

def get_follower_trends() -> List[FollowerSnapshot]:
    conn = _get_conn()
    cur = conn.cursor()

    # you’d normally record snapshots in a separate table; for now mirror total count on each distinct timestamp
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
        # you’d track unfollows in a separate table — for now, return empty list
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
