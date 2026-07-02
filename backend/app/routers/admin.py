from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.orm_models import BlacklistEntry
from ..models.schemas import BlacklistCreate, BlacklistOut
from ..services.pipeline import get_pipeline_status, run_weekly_pipeline

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/pipeline/run")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """수동 수집 트리거 — 파이프라인을 백그라운드로 실행."""
    background_tasks.add_task(run_weekly_pipeline)
    return {"status": "started"}


@router.get("/pipeline/status")
def pipeline_status():
    """플랫폼별 수집 상태/성공률."""
    return get_pipeline_status()


@router.post("/blacklist", response_model=BlacklistOut)
async def add_blacklist(payload: BlacklistCreate, db: AsyncSession = Depends(get_db)):
    """직거래 우회 등 위반 시 블랙 처리.

    creator: AI 추천 제외(exclude/block) 또는 최후순위 강등(deprioritize)
    client: 추가 과금(surcharge), find 제약·재계약 차단(block)
    """
    entry = BlacklistEntry(**payload.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/blacklist", response_model=list[BlacklistOut])
async def list_blacklist(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(BlacklistEntry))).scalars().all()
    return rows
