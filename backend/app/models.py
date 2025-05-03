from pydantic import BaseModel
from typing import List

class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int

class FollowerSnapshot(BaseModel):
    timestamp: str
    total_followers: int

class ChangeEntry(BaseModel):
    login: str
    avatar_url: str
    html_url: str
    timestamp: str
