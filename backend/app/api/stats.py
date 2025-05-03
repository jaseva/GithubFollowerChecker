# backend/app/api/stats.py
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/ping")
def ping():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# later we’ll add follower counts here
