from pydantic import BaseModel
from datetime import datetime

class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int

class Trends(BaseModel):
    labels: list[datetime]
    history: list[int]

class Change(BaseModel):
    username: str
    timestamp: datetime
