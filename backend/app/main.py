import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.stats import router as stats_router

app = FastAPI(
    title="GitHub Follower Checker API",
    version="0.1.0",
)

# CORS so your Next.js frontend (http://localhost:3000) can talk here
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount our stats routes under /stats
app.include_router(stats_router, prefix="/stats", tags=["stats"])


@app.get("/ping")
def ping():
    return {"status": "ok"}
