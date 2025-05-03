# backend/app/services/tracker.py

import sqlite3
from datetime import datetime, timedelta

import os
from datetime import datetime

DB_PATH = "follower_data.db"

def track_followers_job(username: str, token: str, db_path: str = DB_PATH):
    """
    Wrapper around existing track_followers logic that just
    fetches followers and writes to the database (no UI).
    """
    from app.services.tracker import create_table, insert_follower  # etc.

    # existing logic: fetch current_followers, compute unfollowers, write to DB
    # but in CLI context: skip UI parts and just write to SQLite.
    # You can copy-paste your track_followers() core, minus tkinter.

def get_follower_stats(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total followers (latest timestamp)
    cursor.execute("""
      SELECT COUNT(DISTINCT username)
      FROM followers
      WHERE timestamp = (
        SELECT MAX(timestamp) FROM followers
      )
    """)
    total = cursor.fetchone()[0] or 0

    # Followers 24h ago (approx)
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    cursor.execute("""
      SELECT COUNT(DISTINCT username)
      FROM followers
      WHERE DATE(timestamp) = ?
    """, (yesterday,))
    then = cursor.fetchone()[0] or 0

    # New in last 24h
    new = total - then

    # Unfollowers in last 24h
    cursor.execute("""
      SELECT COUNT(DISTINCT username)
      FROM unfollowers
      WHERE DATE(timestamp) = ?
    """, (yesterday,))
    unfollowers = cursor.fetchone()[0] or 0

    conn.close()
    return {
        "total_followers": total,
        "new_followers": new if new > 0 else 0,
        "unfollowers": unfollowers,
    }
