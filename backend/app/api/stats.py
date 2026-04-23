import logging
from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query

from app.models import Change, DashboardData, GitHubProfile, Stats, Trends
from app.services.tracker import (
    get_change_history,
    get_dashboard_data,
    get_follower_stats,
    get_follower_trends,
    get_github_profile,
)

router = APIRouter()
logger = logging.getLogger(__name__)
SERVER_ERROR_DETAIL = "Unable to load follower data."


def _raise_service_error(message: str, exc: Exception) -> NoReturn:
    logger.exception(message)
    raise HTTPException(status_code=500, detail=SERVER_ERROR_DETAIL) from exc


@router.get("/dashboard", response_model=DashboardData)
def dashboard(refresh: bool = Query(default=False)) -> DashboardData:
    try:
        return get_dashboard_data(refresh=refresh)
    except Exception as exc:
        _raise_service_error("Failed to build dashboard data.", exc)


@router.get("/profile", response_model=GitHubProfile)
def profile(refresh: bool = Query(default=False)) -> GitHubProfile:
    try:
        return get_github_profile(refresh=refresh)
    except Exception as exc:
        _raise_service_error("Failed to load GitHub profile.", exc)


@router.get("/followers", response_model=Stats)
def total_followers(refresh: bool = Query(default=False)) -> Stats:
    try:
        return get_follower_stats(refresh=refresh)
    except Exception as exc:
        _raise_service_error("Failed to load follower stats.", exc)


@router.get("/trends", response_model=Trends)
def trends(refresh: bool = Query(default=False)) -> Trends:
    try:
        return get_follower_trends(refresh=refresh)
    except Exception as exc:
        _raise_service_error("Failed to load follower trends.", exc)


@router.get("/history/{change_type}", response_model=list[Change])
def history(
    change_type: str,
    days: int = Query(default=30, ge=1, le=365),
    refresh: bool = Query(default=False),
) -> list[Change]:
    if change_type not in ("new", "lost"):
        raise HTTPException(status_code=400, detail="must be 'new' or 'lost'")
    try:
        return get_change_history(change_type, days=days, refresh=refresh)
    except Exception as exc:
        _raise_service_error("Failed to load follower history.", exc)
