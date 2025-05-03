from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stats

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