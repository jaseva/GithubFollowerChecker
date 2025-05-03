# backend/app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ping import router as ping_router
from app.api.stats import router as stats_router

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_USERNAME or not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN must be set in env")

app = FastAPI(
    title="GitHub Follower Checker API",
    version="0.1.0",
)

# Allow our Next.js front-end on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ping_router)
app.include_router(stats_router)
