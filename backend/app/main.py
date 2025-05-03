import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api.stats import router as stats_router
from app.services.tracker import track_followers_job

# ensure these are set before startup
if "GITHUB_USERNAME" not in os.environ or "GITHUB_TOKEN" not in os.environ:
    raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN must be set in env")

scheduler = AsyncIOScheduler()
scheduler.add_job(
    lambda: track_followers_job(
        os.environ["GITHUB_USERNAME"],
        os.environ["GITHUB_TOKEN"]
    ),
    trigger="interval",
    hours=1,
    next_run_time=None  # don’t run immediately twice
)
scheduler.start()

app = FastAPI(title="GitHub Follower Checker API")
app.include_router(stats_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
async def ping():
    return {"status": "ok"}
