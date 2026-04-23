from fastapi import APIRouter, HTTPException, Query

from app.models import Change, DashboardData, GitHubProfile, Stats, Trends

from app.services.tracker import (
    get_dashboard_data,
    get_github_profile,
    get_follower_stats,
    get_follower_trends,
    get_change_history,
)

router = APIRouter()

@router.get("/dashboard", response_model=DashboardData)
async def dashboard(refresh: bool = Query(default=False)) -> DashboardData:
    try:
        return get_dashboard_data(refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile", response_model=GitHubProfile)
async def profile(refresh: bool = Query(default=False)) -> GitHubProfile:
    try:
        return get_github_profile(refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/followers", response_model=Stats)
async def total_followers(refresh: bool = Query(default=False)) -> Stats:
    try:
        return get_follower_stats(refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends", response_model=Trends)
async def trends(refresh: bool = Query(default=False)) -> Trends:
    try:
        return get_follower_trends(refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{change_type}", response_model=list[Change])
async def history(change_type: str, days: int = Query(default=30, ge=1, le=365), refresh: bool = Query(default=False)) -> list[Change]:
    if change_type not in ("new", "lost"):
        raise HTTPException(status_code=400, detail="must be 'new' or 'lost'")
    try:
        return get_change_history(change_type, days=days, refresh=refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
