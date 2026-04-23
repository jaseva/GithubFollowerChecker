# app/models.py
from pydantic import BaseModel
from datetime import datetime
from typing import List

class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int

class GitHubProfile(BaseModel):
    username: str
    name: str | None = None
    avatar_url: str | None = None
    html_url: str
    bio: str | None = None
    public_repos: int
    following: int
    followers: int

class Trends(BaseModel):
    labels: List[datetime]
    history: List[int]

class Change(BaseModel):
    username: str
    timestamp: datetime
