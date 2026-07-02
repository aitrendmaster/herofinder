"""AI 추천 빌더 — 매칭 점수 + reason why + 블랙리스트 페널티 적용.

블랙리스트 정책 (V3 §11-6):
- penalty가 exclude/block인 크리에이터는 추천에서 제외
- penalty가 deprioritize인 크리에이터는 최후순위로 강등
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.orm_models import BlacklistEntry, Campaign, Influencer, InfluencerSnapshot
from .matching_service import estimate_kpi, generate_match_reason, rule_based_match_score

CHANNEL_URL_TEMPLATES = {
    "youtube": "https://www.youtube.com/{cid}",
    "instagram": "https://www.instagram.com/{cid}",
    "tiktok": "https://www.tiktok.com/@{cid}",
}


async def get_creator_blacklist(db: AsyncSession) -> dict[int, str]:
    """influencer_id → penalty 맵."""
    rows = (
        (
            await db.execute(
                select(BlacklistEntry).where(BlacklistEntry.entity_type == "creator")
            )
        )
        .scalars()
        .all()
    )
    return {r.entity_id: r.penalty for r in rows}


async def build_recommendations(
    db: AsyncSession, campaign: Campaign, limit: int = 10, with_reason: bool = True
) -> list[dict]:
    blacklist = await get_creator_blacklist(db)

    influencers = (
        (await db.execute(select(Influencer).options(selectinload(Influencer.category))))
        .scalars()
        .all()
    )

    scored: list[tuple[int, bool, Influencer, InfluencerSnapshot]] = []
    for inf in influencers:
        penalty = blacklist.get(inf.id)
        if penalty in ("exclude", "block"):
            continue  # 추천 제외
        snap = (
            await db.execute(
                select(InfluencerSnapshot)
                .where(InfluencerSnapshot.influencer_id == inf.id)
                .order_by(InfluencerSnapshot.week_start.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not snap:
            continue
        score = rule_based_match_score(
            float(snap.engagement_rate), float(snap.growth_rate), snap.is_trending
        )
        deprioritized = penalty == "deprioritize"
        scored.append((score, deprioritized, inf, snap))

    # 강등되지 않은 크리에이터 우선, 그 안에서 점수 내림차순
    scored.sort(key=lambda x: (x[1], -x[0]))

    results = []
    for score, deprioritized, inf, snap in scored[:limit]:
        reason = (
            await generate_match_reason(campaign, inf.name, score) if with_reason else ""
        )
        url_tpl = CHANNEL_URL_TEMPLATES.get(inf.channel, "{cid}")
        results.append(
            {
                "id": inf.id,
                "name": inf.name,
                "channel": inf.channel,
                "country": inf.country,
                "tier": inf.tier,
                "category": inf.category.name if inf.category else None,
                "cost_range_min": inf.cost_range_min,
                "cost_range_max": inf.cost_range_max,
                "followers": snap.followers,
                "monthly_views": snap.monthly_views,
                "engagement_rate": float(snap.engagement_rate),
                "growth_rate": float(snap.growth_rate),
                "is_trending": snap.is_trending,
                "match_score": score,
                "match_reason": reason,
                "deprioritized": deprioritized,
                "url": url_tpl.format(cid=inf.channel_id),
                "estimated_kpi": estimate_kpi(
                    snap.followers, snap.monthly_views, float(snap.engagement_rate)
                ),
            }
        )
    return results
