from fastapi import APIRouter, HTTPException
from app.services.tracker import (
    get_follower_stats,
    get_follower_trends,
    get_change_history,
)
from app.models import Stats, Trends, Change

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/followers", response_model=Stats)
def followers():
    try:
        return get_follower_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=Trends)
def trends():
    try:
        return get_follower_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{change_type}", response_model=list[Change])
def history(change_type: str):
    if change_type not in ("new", "lost"):
        raise HTTPException(status_code=400, detail="Invalid change type")
    try:
        return get_change_history(change_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
