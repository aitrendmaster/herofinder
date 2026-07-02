"""제안 리스트/제안서 생성 — 비동기 Job 패턴."""

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session, get_db
from ..models.orm_models import Campaign
from ..services.proposal_service import generate_proposal_package
from ..services.recommendation import build_recommendations

router = APIRouter(prefix="/api", tags=["proposals"])

_jobs: dict[str, dict] = {}  # 인메모리 Job 저장소


@router.post("/campaigns/{campaign_id}/proposal")
async def create_proposal_job(
    campaign_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다.")

    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"job_id": job_id, "campaign_id": campaign_id, "status": "pending"}
    background_tasks.add_task(_process_proposal, job_id, campaign_id)
    return {"job_id": job_id, "status": "pending"}


async def _process_proposal(job_id: str, campaign_id: int):
    job = _jobs[job_id]
    job["status"] = "processing"
    try:
        async with async_session() as db:
            campaign = (
                await db.execute(select(Campaign).where(Campaign.id == campaign_id))
            ).scalar_one()
            recs = await build_recommendations(db, campaign, limit=16)
        files = generate_proposal_package(campaign, recs)
        job.update(files)
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.error(f"제안서 생성 Job 실패 ({job_id}): {e}")
        job["status"] = "failed"
        job["error"] = str(e)


@router.get("/proposal-jobs/{job_id}")
def get_proposal_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job을 찾을 수 없습니다.")
    return job
