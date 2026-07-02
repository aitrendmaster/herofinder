from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .database import init_db
from .routers import admin, campaigns, deals, influencers, proposals, webhooks

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Hero Finder API 시작 — DB 초기화 완료")
    yield


app = FastAPI(title="Hero Finder API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(influencers.router)
app.include_router(campaigns.router)
app.include_router(proposals.router)
app.include_router(deals.router)
app.include_router(webhooks.router)
app.include_router(admin.router)

# 생성된 제안서/리스트업 다운로드 경로
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/health")
def health():
    return {"status": "ok", "service": "hero-finder-api"}
