from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.orm_models import Category, Influencer, InfluencerSnapshot
from ..models.schemas import CategoryOut, InfluencerListOut, InfluencerOut, SnapshotOut

router = APIRouter(prefix="/api", tags=["influencers"])


def _to_out(inf: Influencer, snapshot: InfluencerSnapshot | None) -> InfluencerOut:
    return InfluencerOut(
        id=inf.id,
        name=inf.name,
        channel=inf.channel,
        country=inf.country,
        tier=inf.tier,
        category=inf.category.name if inf.category else None,
        cost_range_min=inf.cost_range_min,
        cost_range_max=inf.cost_range_max,
        followers=snapshot.followers if snapshot else 0,
        monthly_views=snapshot.monthly_views if snapshot else 0,
        engagement_rate=float(snapshot.engagement_rate) if snapshot else 0,
        growth_rate=float(snapshot.growth_rate) if snapshot else 0,
        is_trending=snapshot.is_trending if snapshot else False,
    )


async def _latest_snapshot(db: AsyncSession, influencer_id: int) -> InfluencerSnapshot | None:
    return (
        await db.execute(
            select(InfluencerSnapshot)
            .where(InfluencerSnapshot.influencer_id == influencer_id)
            .order_by(InfluencerSnapshot.week_start.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@router.get("/influencers", response_model=InfluencerListOut)
async def list_influencers(
    tier: str | None = None,
    channel: str | None = None,
    category: str | None = None,
    country: str | None = None,
    trending: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(Influencer).options(selectinload(Influencer.category))
    count_query = select(func.count(Influencer.id))

    if tier:
        query = query.where(Influencer.tier == tier)
        count_query = count_query.where(Influencer.tier == tier)
    if channel:
        query = query.where(Influencer.channel == channel)
        count_query = count_query.where(Influencer.channel == channel)
    if country:
        query = query.where(Influencer.country == country)
        count_query = count_query.where(Influencer.country == country)
    if category:
        query = query.join(Category, Influencer.category_id == Category.id).where(
            Category.name == category
        )
        count_query = count_query.join(
            Category, Influencer.category_id == Category.id
        ).where(Category.name == category)

    total = (await db.execute(count_query)).scalar_one()
    rows = (
        (await db.execute(query.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    items = []
    for inf in rows:
        snap = await _latest_snapshot(db, inf.id)
        out = _to_out(inf, snap)
        if trending is not None and out.is_trending != trending:
            continue
        items.append(out)

    return InfluencerListOut(total=total, page=page, page_size=page_size, items=items)


@router.get("/influencers/{influencer_id}", response_model=InfluencerOut)
async def get_influencer(influencer_id: int, db: AsyncSession = Depends(get_db)):
    inf = (
        await db.execute(
            select(Influencer)
            .options(selectinload(Influencer.category))
            .where(Influencer.id == influencer_id)
        )
    ).scalar_one_or_none()
    if not inf:
        raise HTTPException(status_code=404, detail="인플루언서를 찾을 수 없습니다.")
    snap = await _latest_snapshot(db, inf.id)
    return _to_out(inf, snap)


@router.get("/influencers/{influencer_id}/snapshots", response_model=list[SnapshotOut])
async def get_snapshots(influencer_id: int, db: AsyncSession = Depends(get_db)):
    rows = (
        (
            await db.execute(
                select(InfluencerSnapshot)
                .where(InfluencerSnapshot.influencer_id == influencer_id)
                .order_by(InfluencerSnapshot.week_start.asc())
            )
        )
        .scalars()
        .all()
    )
    return rows


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    rows = (
        (await db.execute(select(Category).order_by(Category.sort_order))).scalars().all()
    )
    return rows
