import os
import sqlite3
import requests
from datetime import datetime, timedelta

# bring in your Pydantic models for type annotations
from app.models import Stats, Trends, Change

# path to your SQLite DB
DB_PATH = os.path.join(os.path.dirname(__file__), "../followers.db")

API_URL = "https://api.github.com"
USERNAME = os.getenv("GITHUB_USERNAME")
TOKEN    = os.getenv("GITHUB_TOKEN")
HEADERS  = {"Authorization": f"token {TOKEN}"}

def get_follower_stats() -> Stats:
    # 1) fetch the current follower count from GitHub
    r = requests.get(f"{API_URL}/users/{USERNAME}", headers=HEADERS)
    r.raise_for_status()
    total = r.json()["followers"]

    # 2) open DB, append snapshot
    now = datetime.utcnow()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO followers (count, timestamp) VALUES (?, ?)",
        (total, now.isoformat()),
    )
    conn.commit()

    # 3) compute changes over the last 24h
    since = (now - timedelta(days=1)).isoformat()
    c.execute("SELECT count FROM followers WHERE timestamp >= ?", (since,))
    rows = [r[0] for r in c.fetchall()]
    conn.close()

    if rows:
        delta = total - rows[0]
        new   = delta if delta > 0 else 0
        lost  = -delta if delta < 0 else 0
    else:
        new, lost = 0, 0

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

    labels  = [datetime.fromisoformat(r[0]) for r in rows]
    history = [r[1] for r in rows]
    return Trends(labels=labels, history=history)

def get_change_history(change_type: str) -> list[Change]:
    table = "new_followers" if change_type == "new" else "lost_followers"
    since = (datetime.utcnow() - timedelta(days=1)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        f"SELECT username, timestamp FROM {table} WHERE timestamp >= ?",
        (since,),
    )
    rows = c.fetchall()
    conn.close()

    return [
        Change(username=r[0], timestamp=datetime.fromisoformat(r[1]))
        for r in rows
    ]
