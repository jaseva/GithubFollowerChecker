# app/api/stats.py

from typing import List
from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from app.services.tracker import get_follower_stats, get_follower_trends
from app.models import Stats, FollowerSnapshot

router = APIRouter()

@router.get("/stats/followers", response_model=Stats)
def followers():
    """
    Returns the latest follower stats (total / new / unfollowers).
    """
    stats = get_follower_stats()
    return JSONResponse(stats)

@router.get("/stats/trends", response_model=List[FollowerSnapshot])
def trends():
    """
    Returns the full time-series of total-followers snapshots.
    """
    try:
        return get_follower_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
