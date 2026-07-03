import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .database import init_db
from .routers import admin, campaigns, creator, dashboard, deals, influencers, proposals, webhooks
from .services.notification_service import run_reminder_sweep

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REMINDER_INTERVAL_SECONDS = 6 * 3600  # 미처리 업무 리마인드 주기


async def _reminder_loop():
    while True:
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
        try:
            await run_reminder_sweep()
        except Exception as e:
            logger.error(f"리마인드 루프 오류: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Hero Finder API 시작 — DB 초기화 완료")
    reminder_task = asyncio.create_task(_reminder_loop())
    yield
    reminder_task.cancel()


app = FastAPI(title="Hero Finder API", version="0.1.0", lifespan=lifespan)

from .utils.config import get_settings

_settings = get_settings()
_allowed_origins = list({
    "http://localhost:3000",
    "http://localhost:5173",
    _settings.frontend_base_url.rstrip("/"),
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    # Vercel 프리뷰 배포(*-*.vercel.app)도 허용
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(influencers.router)
app.include_router(campaigns.router)
app.include_router(proposals.router)
app.include_router(deals.router)
app.include_router(dashboard.router)
app.include_router(creator.router)
app.include_router(webhooks.router)
app.include_router(admin.router)

# 생성된 제안서/리스트업 다운로드 경로
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/health")
def health():
    return {"status": "ok", "service": "hero-finder-api"}
