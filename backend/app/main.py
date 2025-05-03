from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stats
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.tracker import track_followers_job  # we’ll define this
from datetime import datetime
import os

# Scheduler setup
scheduler = AsyncIOScheduler()
scheduler.add_job(
    lambda: track_followers_job(
        os.environ["GITHUB_USERNAME"],
        os.environ["GITHUB_TOKEN"]
    ),
    "interval",
    hours=1,
    next_run_time=datetime.utcnow()  # run immediately on startup
)
scheduler.start()

app = FastAPI(title="GitHub Follower Checker API")
app.include_router(stats.router)

app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:3000"],  # tighten later
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

@app.get("/ping")
async def ping():
    return {"status": "ok"}

app.include_router(stats.router)