# backend/app/api/stats.py

from fastapi import APIRouter, HTTPException
from app.services.tracker import get_follower_stats, get_change_history

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/followers")
async def followers():
    try:
        return get_follower_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/new")
async def new_followers():
    try:
        # returns List[{"timestamp": "...", "new": X, "count": Y}, ...]
        return {"history": get_change_history("new")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lost")
async def lost_followers():
    try:
        # returns List[{"timestamp": "...", "lost": X, "count": Y}, ...]
        return {"history": get_change_history("lost")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
