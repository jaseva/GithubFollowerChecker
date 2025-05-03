import os
import sqlite3
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models import Stats

router = APIRouter()
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "services", "followers.db")

@router.get("/followers", response_model=Stats)
def get_follower_stats():
    """
    Return:
      - total_followers: how many unique IDs we've ever seen
      - new_followers: how many first-seen in the last 24h
      - unfollowers: how many *weren't* seen in the last 24h
    """
    if not os.path.exists(DB_PATH):
        raise HTTPException(500, detail="No followers database found")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) total distinct followers
    cur.execute("SELECT COUNT(*) FROM followers")
    total = cur.fetchone()[0]

    # 2) new in last 24h
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    cur.execute("SELECT COUNT(*) FROM followers WHERE timestamp > ?", (cutoff,))
    new = cur.fetchone()[0]

    # 3) “unfollowers” = total - new
    unfollowers = max(0, total - new)

    conn.close()

    payload = Stats(
        total_followers=total,
        new_followers=new,
        unfollowers=unfollowers,
    ).dict()

    return JSONResponse(payload)