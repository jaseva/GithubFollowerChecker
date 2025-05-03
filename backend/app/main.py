from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# 1) load .env (if you went that route)
load_dotenv()

# 2) pull in your GitHub credentials
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_USERNAME or not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN must be set in env")

app = FastAPI(title="GitHub Follower Checker API")

# allow Next.js on localhost:3000 to talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.stats import router as stats_router
app.include_router(stats_router)
