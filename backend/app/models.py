# app/models.py

from pydantic import BaseModel
from datetime import datetime

class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int

class FollowerSnapshot(BaseModel):
    timestamp: datetime
    total_followers: int
