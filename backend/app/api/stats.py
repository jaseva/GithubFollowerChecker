from fastapi import APIRouter, HTTPException

from app.models import Change, Stats, Trends

from app.services.tracker import (
    get_follower_stats,
    get_follower_trends,
    get_change_history,
)

router = APIRouter()

@router.get("/followers", response_model=Stats)
async def total_followers() -> Stats:
    try:
        return get_follower_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=Trends)
async def trends() -> Trends:
    try:
        return get_follower_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{change_type}", response_model=list[Change])
async def history(change_type: str) -> list[Change]:
    if change_type not in ("new", "lost"):
        raise HTTPException(status_code=400, detail="must be 'new' or 'lost'")
    try:
        return get_change_history(change_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
