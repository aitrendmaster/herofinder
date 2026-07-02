"""클라이언트 대시보드 — 전체 캠페인 진행 현황(프로세스 라인바) + 알림."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.orm_models import Campaign, Notification
from ..models.schemas import (
    CampaignProgressOut,
    DashboardItemOut,
    DashboardOut,
    NotificationOut,
)
from ..services.progress import NEXT_ACTIONS, compute_progress

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    campaigns = (
        (await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))).scalars().all()
    )
    items = []
    for c in campaigns:
        stages, current = await compute_progress(db, c)
        items.append(
            DashboardItemOut(
                campaign_id=c.id,
                campaign_name=c.name,
                status=c.status,
                stages=stages,
                current_stage=current,
                created_at=c.created_at,
                next_action=NEXT_ACTIONS.get(current, ""),
            )
        )
    unread = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.recipient_type == "client", Notification.is_read.is_(False)
            )
        )
    ).scalar_one()
    return DashboardOut(campaigns=items, unread_notifications=unread)


@router.get("/campaigns/{campaign_id}/progress", response_model=CampaignProgressOut)
async def get_campaign_progress(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다.")
    stages, current = await compute_progress(db, campaign)
    return CampaignProgressOut(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        status=campaign.status,
        stages=stages,
        current_stage=current,
    )


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False, db: AsyncSession = Depends(get_db)
):
    """클라이언트(운영 계정) 알림 목록."""
    query = (
        select(Notification)
        .where(Notification.recipient_type == "client")
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    rows = (await db.execute(query)).scalars().all()
    return rows


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def read_notification(notification_id: int, db: AsyncSession = Depends(get_db)):
    n = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.recipient_type == "client"
            )
        )
    ).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    n.is_read = True
    await db.commit()
    await db.refresh(n)
    return n
