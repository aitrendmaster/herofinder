"""주간 수집 파이프라인 (Render Cron — 매주 월 04:00 KST).

[시드 로드] → [수집: YouTube 실데이터] → [정규화·중복제거(channel+channel_id upsert)]
  → [등급 자동 분류] → [활성도 스코어링(전주 대비)] → [주간 스냅샷 저장]

시드: app/data/seed_channels.json (PTK 리스트업 기반 실채널)
로컬/수동 트리거: POST /api/admin/pipeline/run
⚠️ contact_email은 수집하지 않는다 — 법무 검토(개인정보) 완료 전 미수집 방침.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from ..database import async_session
from ..models.orm_models import Category, Influencer, InfluencerSnapshot
from .collectors.youtube_collector import collect_channel_stats, collect_recent_video_stats
from .scoring import classify_tier, is_trending

SEED_FILE = Path(__file__).parent.parent / "data" / "seed_channels.json"

# 파이프라인 실행 상태 (인메모리 — 단일 프로세스 기준)
_pipeline_status: dict = {"last_run": None, "status": "idle", "results": {}}


def get_pipeline_status() -> dict:
    return _pipeline_status


def current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())  # 월요일


def load_seeds() -> list[dict]:
    if not SEED_FILE.exists():
        return []
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


async def run_weekly_pipeline() -> dict:
    """시드 채널 실수집 → 인플루언서 upsert + 주간 스냅샷 기록."""
    _pipeline_status["status"] = "running"
    _pipeline_status["last_run"] = datetime.utcnow().isoformat()
    week = current_week_start()
    created = updated = failed = 0

    try:
        seeds = load_seeds()
        yt_seeds = [s for s in seeds if s["channel"] == "youtube"]
        # TODO: instagram/tiktok 시드는 ScrapeCreators 수집기 연결 시 추가

        stats_map = {
            s["channel_id"]: s
            for s in await collect_channel_stats([s["channel_id"] for s in yt_seeds])
        }

        async with async_session() as db:
            # 카테고리 get-or-create
            cats = {c.name: c for c in (await db.execute(select(Category))).scalars().all()}

            async def get_category(name: str) -> Category:
                if name not in cats:
                    cat = Category(name=name, sort_order=len(cats))
                    db.add(cat)
                    await db.flush()
                    cats[name] = cat
                return cats[name]

            for seed in yt_seeds:
                stat = stats_map.get(seed["channel_id"])
                if not stat or stat["followers"] == 0:
                    failed += 1
                    logger.warning(f"수집 실패 스킵: {seed['name']}")
                    continue

                recent = await collect_recent_video_stats(seed["channel_id"])
                followers = stat["followers"]
                category = await get_category(seed["category"])

                # upsert 기준: channel + channel_id (중복 제거)
                inf = (
                    await db.execute(
                        select(Influencer).where(
                            Influencer.channel == seed["channel"],
                            Influencer.channel_id == seed["channel_id"],
                        )
                    )
                ).scalar_one_or_none()
                if inf is None:
                    inf = Influencer(
                        name=stat["name"] or seed["name"],
                        channel=seed["channel"],
                        channel_id=seed["channel_id"],
                        country=seed.get("country", "KR"),
                        category_id=category.id,
                        tier=classify_tier(followers),
                        contact_email=None,  # 법무 검토 전 미수집
                    )
                    db.add(inf)
                    await db.flush()
                    created += 1
                else:
                    inf.name = stat["name"] or inf.name
                    inf.category_id = category.id
                    inf.tier = classify_tier(followers)
                    updated += 1

                # 전주 스냅샷 대비 성장률
                prev = (
                    await db.execute(
                        select(InfluencerSnapshot)
                        .where(
                            InfluencerSnapshot.influencer_id == inf.id,
                            InfluencerSnapshot.week_start < week,
                        )
                        .order_by(InfluencerSnapshot.week_start.desc())
                        .limit(1)
                    )
                ).scalar_one_or_none()
                growth = (
                    round((followers - prev.followers) / prev.followers * 100, 2)
                    if prev and prev.followers
                    else 0.0
                )

                # 주간 스냅샷 upsert (동주차 재실행 시 갱신)
                snap = (
                    await db.execute(
                        select(InfluencerSnapshot).where(
                            InfluencerSnapshot.influencer_id == inf.id,
                            InfluencerSnapshot.week_start == week,
                        )
                    )
                ).scalar_one_or_none()
                if snap is None:
                    snap = InfluencerSnapshot(influencer_id=inf.id, week_start=week)
                    db.add(snap)
                snap.followers = followers
                snap.monthly_views = recent["monthly_views"]
                snap.engagement_rate = recent["engagement_rate"]
                snap.growth_rate = growth
                snap.is_trending = is_trending(growth, recent["engagement_rate"])

            await db.commit()

        _pipeline_status["status"] = "completed"
        _pipeline_status["results"] = {
            "week_start": week.isoformat(),
            "created": created,
            "updated": updated,
            "failed": failed,
            "seeds": len(yt_seeds),
        }
    except Exception as e:
        logger.error(f"주간 파이프라인 실패: {e}")
        _pipeline_status["status"] = "failed"
        _pipeline_status["results"] = {"error": str(e)}
    return _pipeline_status
