from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models import Stats
from app.services.tracker import get_follower_stats

router = APIRouter(prefix="/stats")

@router.get("/followers", response_model=Stats)
async def followers():
    stats = get_follower_stats()
    # return Pydantic model as JSON
    return JSONResponse(content=stats.dict())
