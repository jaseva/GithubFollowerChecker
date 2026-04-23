# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ping import router as ping_router
from app.api.stats import router as stats_router

app = FastAPI(
    title="GitHub Follower Checker API",
    version="0.1.0"
)

# Enable CORS for local Next.js dev servers. Next automatically falls back to
# 3001 when 3000 is already occupied.
to_allow = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=to_allow,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ping_router)
app.include_router(stats_router, prefix="/stats", tags=["stats"])
