from pydantic import BaseModel

class Stats(BaseModel):
    total_followers: int
    new_followers: int
    unfollowers: int
