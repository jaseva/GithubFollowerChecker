# backend/app/api/ping.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def ping():
    """
    Simple health‐check endpoint for the frontend.
    Returns a static “ok” status that your client
    will display as “Server status: ok”.
    """
    return {"time": "ok"}
