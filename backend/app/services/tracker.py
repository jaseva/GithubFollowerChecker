# backend/app/services/tracker.py

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Literal, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "followers.db")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_follower_stats() -> Dict[str, int]:
    """
    Returns {"total_followers": int, "new_followers": int, "unfollowers": int}
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # latest snapshot
    cur.execute("SELECT count FROM followers ORDER BY timestamp DESC LIMIT 1")
    row = cur.fetchone()
    total = row[0] if row else 0

    # 24h ago snapshot
    cutoff = datetime.utcnow() - timedelta(days=1)
    cur.execute(
        "SELECT count FROM followers WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
        (cutoff.timestamp(),)
    )
    row = cur.fetchone()
    previous = row[0] if row else total

    new = max(0, total - previous)
    lost = max(0, previous - total)

    conn.close()
    return {
        "total_followers": total,
        "new_followers": new,
        "unfollowers": lost,
    }

def get_change_history(kind: Literal["new", "lost"]) -> List[Dict]:
    """
    Returns a list of records for the last 7 days:
    [
      {"timestamp": ISO8601, kind: int, "count": int},
      ...
    ]
    """
    conn = get_db_connection()
    cur = conn.cursor()

    since = datetime.utcnow() - timedelta(days=7)
    cur.execute(
        "SELECT timestamp, count FROM followers WHERE timestamp >= ? ORDER BY timestamp",
        (since.timestamp(),)
    )
    rows = cur.fetchall()
    history = []
    prev_count = None

    for ts, cnt in rows:
        dt = datetime.utcfromtimestamp(ts).isoformat()
        if prev_count is None:
            delta = 0
        else:
            if kind == "new":
                delta = max(0, cnt - prev_count)
            else:
                delta = max(0, prev_count - cnt)
        history.append({"timestamp": dt, kind: delta, "count": cnt})
        prev_count = cnt

    conn.close()
    return history
