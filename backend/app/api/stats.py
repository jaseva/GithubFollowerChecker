# app/api/stats.py
from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from app.services.tracker import (
    get_follower_stats,
    get_follower_trends,
    get_change_history,
)

router = APIRouter()

@router.get("/followers")
async def total_followers():
    try:
        stats = get_follower_stats()
        return JSONResponse(stats.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def trends():
    try:
        t = get_follower_trends()
        return JSONResponse(t.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{change_type}")
async def history(change_type: str):
    if change_type not in ("new", "lost"):
        raise HTTPException(status_code=400, detail="must be 'new' or 'lost'")
    try:
        changes = get_change_history(change_type)
        return JSONResponse([c.dict() for c in changes])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
