# backend/app/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.stats import router as stats_router
from app.api.ping import router as ping_router

# read GitHub creds early, so app won’t start without them
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_USERNAME or not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN must be set in env")

app = FastAPI(
    title="GitHub Follower Checker API",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# CORS: allow your frontend on localhost:3000 to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# mount your routers
app.include_router(ping_router, prefix="")
app.include_router(stats_router, prefix="/stats")


@app.get("/")
def root():
    return JSONResponse({"message": "Welcome to the GitHub Follower Checker API"})
