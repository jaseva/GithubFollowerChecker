# app/api/ping.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"status": "ok"}
