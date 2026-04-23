# app/models.py
from pydantic import BaseModel
from datetime import datetime
from typing import List

class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int

class Trends(BaseModel):
    labels: List[datetime]
    history: List[int]

class Change(BaseModel):
    username: str
    timestamp: datetime
