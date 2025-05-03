import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.tracker import track_followers_paginated_job
from app.api.stats import router as stats_router
from dotenv import load_dotenv

# Load from a .env file if you prefer
load_dotenv()

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_USERNAME or not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN must be set in env")

# Kick off the hourly job (runs immediately on startup, then every hour)
scheduler = AsyncIOScheduler()
scheduler.add_job(
    lambda: track_followers_paginated_job(GITHUB_USERNAME, GITHUB_TOKEN),
    trigger="interval",
    hours=1,
    next_run_time=datetime.utcnow(),
)
scheduler.start()

app = FastAPI(title="GitHub Follower Checker API")

# CORS so your Next.js front-end on localhost:3000 can call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your stats endpoints live under /stats
app.include_router(stats_router, prefix="/stats")

@app.get("/ping")
async def ping():
    return {"status": "ok"}
