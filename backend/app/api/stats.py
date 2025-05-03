from typing import List
from fastapi import APIRouter
from app.models import Stats, FollowerSnapshot, ChangeEntry
from app.services.tracker import (
    get_follower_stats,
    get_follower_trends,
    get_change_history,
)

router = APIRouter()

@router.get("/followers", response_model=Stats)
def followers():
    return get_follower_stats()

@router.get("/trends", response_model=List[FollowerSnapshot])
def trends():
    return get_follower_trends()

@router.get("/new", response_model=List[ChangeEntry])
def new_followers():
    return get_change_history("new")

@router.get("/lost", response_model=List[ChangeEntry])
def lost_followers():
    return get_change_history("lost")
