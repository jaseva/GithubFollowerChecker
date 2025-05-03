from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GitHub Follower Checker API")

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],  # tighten later
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

@app.get("/ping")
async def ping():
    return {"status": "ok"}