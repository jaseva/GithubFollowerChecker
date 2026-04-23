# app/services/tracker.py
import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

from app.models import Stats, Trends, Change

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_PATH = os.path.join(BASE_DIR, "followers.db")
API_URL = "https://api.github.com"
USERNAME = os.getenv("GITHUB_USERNAME")
TOKEN    = os.getenv("GITHUB_TOKEN")
HEADERS  = {"Authorization": f"token {TOKEN}"}

def init_db():
    """Ensure all needed tables exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            count INTEGER,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS new_followers (
            username TEXT,
            timestamp TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lost_followers (
            username TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

# Run our initializer on import
init_db()


def get_follower_stats() -> Stats:
    # 1) fetch the current follower count from GitHub
    r = requests.get(f"{API_URL}/users/{USERNAME}", headers=HEADERS)
    r.raise_for_status()
    total = r.json()["followers"]

    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # insert snapshot
    c.execute(
        "INSERT INTO followers (count, timestamp) VALUES (?, ?)",
        (total, now),
    )

    # compute 24h ago count
    since = (datetime.utcnow() - timedelta(days=1)).isoformat()
    c.execute("SELECT count FROM followers WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT 1", (since,))
    row = c.fetchone()

    if row:
        prior = row[0]
        delta = total - prior
        new = max(delta, 0)
        lost = max(-delta, 0)
    else:
        new, lost = 0, 0

    conn.commit()
    conn.close()

    return Stats(
        total_followers=total,
        new_followers=new,
        unfollowers=lost,
    )


def get_follower_trends() -> Trends:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, count FROM followers ORDER BY timestamp")
    rows = c.fetchall()
    conn.close()

    labels = [datetime.fromisoformat(ts) for ts, _ in rows]
    history = [count for _, count in rows]
    return Trends(labels=labels, history=history)


def get_change_history(change_type: str) -> list[Change]:
    table = "new_followers" if change_type == "new" else "lost_followers"
    since = (datetime.utcnow() - timedelta(days=1)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        f"SELECT username, timestamp FROM {table} WHERE timestamp >= ? ORDER BY timestamp",
        (since,),
    )
    rows = c.fetchall()
    conn.close()

    return [Change(username=u, timestamp=datetime.fromisoformat(ts)) for u, ts in rows]
