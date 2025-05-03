# backend/app/api/stats.py
from fastapi import APIRouter
from datetime import datetime
from fastapi.responses import JSONResponse
from app.services.tracker import get_follower_stats

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/ping")
def ping():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# later we’ll add follower counts here
@router.get("/followers")
def followers():
    stats = get_follower_stats()
    return JSONResponse(stats)