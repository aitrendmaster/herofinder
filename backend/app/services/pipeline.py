"""주간 수집 파이프라인 (Render Cron — 매주 월 04:00 KST).

[수집] → [정규화·중복제거] → [등급 분류] → [활성도 스코어링] → [스냅샷 저장]
로컬에서는 POST /api/admin/pipeline/run 으로 수동 트리거.
"""

from datetime import date, datetime, timedelta

from loguru import logger
from sqlalchemy import select

from ..database import async_session
from ..models.orm_models import Influencer, InfluencerSnapshot
from .scoring import classify_tier, is_trending

# 파이프라인 실행 상태 (인메모리 — 단일 프로세스 기준)
_pipeline_status: dict = {"last_run": None, "status": "idle", "results": {}}


def get_pipeline_status() -> dict:
    return _pipeline_status


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())  # 월요일


async def run_weekly_pipeline() -> dict:
    """주간 파이프라인 실행. 현재는 등록된 인플루언서의 최신 스냅샷 재계산만 수행.

    TODO: youtube_collector / scrapecreators_collector 연동해 실제 수치 갱신.
    """
    _pipeline_status["status"] = "running"
    _pipeline_status["last_run"] = datetime.utcnow().isoformat()
    week = current_week_start()
    updated = 0
    try:
        async with async_session() as db:
            influencers = (await db.execute(select(Influencer))).scalars().all()
            for inf in influencers:
                latest = (
                    await db.execute(
                        select(InfluencerSnapshot)
                        .where(InfluencerSnapshot.influencer_id == inf.id)
                        .order_by(InfluencerSnapshot.week_start.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                if not latest:
                    continue
                inf.tier = classify_tier(latest.followers)
                latest.is_trending = is_trending(
                    float(latest.growth_rate), float(latest.engagement_rate)
                )
                updated += 1
            await db.commit()
        _pipeline_status["status"] = "completed"
        _pipeline_status["results"] = {"week_start": week.isoformat(), "updated": updated}
    except Exception as e:
        logger.error(f"주간 파이프라인 실패: {e}")
        _pipeline_status["status"] = "failed"
        _pipeline_status["results"] = {"error": str(e)}
    return _pipeline_status
