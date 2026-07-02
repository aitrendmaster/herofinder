"""크리에이터 포털 API — 본인 계정 로그인, 받은 RFP 조회, 견적 제출, 메시지 커뮤니케이션.

인증: RFP 송부 시 자동 발급된 access_code를 X-Creator-Token 헤더로 전달.
(정식 JWT 인증은 Phase 2-4에서 도입 예정)
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.orm_models import (
    Campaign,
    CreatorAccount,
    Message,
    Notification,
    Quote,
    RfpDispatch,
)
from ..models.schemas import (
    CreatorLoginIn,
    CreatorQuoteIn,
    CreatorRfpOut,
    CreatorSessionOut,
    MessageOut,
    NotificationOut,
    QuoteOut,
)
from ..services.notification_service import CLIENT, notify
from ..services.progress import compute_progress

router = APIRouter(prefix="/api", tags=["creator"])


async def get_current_creator(
    x_creator_token: str = Header(..., description="크리에이터 접속 코드"),
    db: AsyncSession = Depends(get_db),
) -> CreatorAccount:
    account = (
        await db.execute(
            select(CreatorAccount)
            .options(selectinload(CreatorAccount.influencer))
            .where(CreatorAccount.access_code == x_creator_token)
        )
    ).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=401, detail="유효하지 않은 접속 코드입니다.")
    return account


@router.post("/auth/creator/login", response_model=CreatorSessionOut)
async def creator_login(payload: CreatorLoginIn, db: AsyncSession = Depends(get_db)):
    account = (
        await db.execute(
            select(CreatorAccount)
            .options(selectinload(CreatorAccount.influencer))
            .where(
                CreatorAccount.email == payload.email,
                CreatorAccount.access_code == payload.access_code,
            )
        )
    ).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=401, detail="이메일 또는 접속 코드가 올바르지 않습니다.")
    account.last_login_at = datetime.utcnow()
    await db.commit()

    influencer = account.influencer if account.influencer else None
    return CreatorSessionOut(
        token=account.access_code,
        influencer_id=account.influencer_id,
        name=influencer.name if influencer else "",
        channel=influencer.channel if influencer else "",
    )


@router.get("/creator/me", response_model=CreatorSessionOut)
async def creator_me(account: CreatorAccount = Depends(get_current_creator)):
    influencer = account.influencer
    return CreatorSessionOut(
        token=account.access_code,
        influencer_id=account.influencer_id,
        name=influencer.name if influencer else "",
        channel=influencer.channel if influencer else "",
    )


@router.get("/creator/rfps", response_model=list[CreatorRfpOut])
async def creator_rfps(
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    """본인에게 송부된 RFP 목록 — 캠페인 조건·규격·보상·필수 포함 내용 + 진행 단계."""
    dispatches = (
        (
            await db.execute(
                select(RfpDispatch)
                .where(RfpDispatch.influencer_id == account.influencer_id)
                .order_by(RfpDispatch.sent_at.desc())
            )
        )
        .scalars()
        .all()
    )
    results = []
    for d in dispatches:
        campaign = (
            await db.execute(select(Campaign).where(Campaign.id == d.campaign_id))
        ).scalar_one_or_none()
        if not campaign:
            continue
        stages, current = await compute_progress(db, campaign)
        results.append(
            CreatorRfpOut(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                ad_type=campaign.ad_type,
                budget_range=campaign.budget_range,
                content_format=campaign.content_format,
                longform_minutes=campaign.longform_minutes,
                shortform_minutes=campaign.shortform_minutes,
                additional_rewards=campaign.additional_rewards,
                provided_resources=campaign.provided_resources,
                must_include=campaign.must_include,
                deadline=campaign.deadline,
                dispatch_status=d.status,
                sent_at=d.sent_at,
                stages=stages,
                current_stage=current,
            )
        )
    return results


@router.post("/creator/campaigns/{campaign_id}/quotes", response_model=QuoteOut)
async def creator_submit_quote(
    campaign_id: int,
    payload: CreatorQuoteIn,
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    """크리에이터 1차 견적 제출 — influencer_id는 토큰 기준으로 강제."""
    dispatched = (
        await db.execute(
            select(RfpDispatch.id).where(
                RfpDispatch.campaign_id == campaign_id,
                RfpDispatch.influencer_id == account.influencer_id,
            ).limit(1)
        )
    ).first()
    if not dispatched:
        raise HTTPException(status_code=403, detail="이 캠페인의 RFP를 받은 크리에이터만 견적을 제출할 수 있습니다.")

    data = payload.model_dump()
    data["influencer_id"] = account.influencer_id
    quote = Quote(campaign_id=campaign_id, **data)
    db.add(quote)

    # 회신으로 간주 — dispatch 상태 갱신
    dispatch = (
        await db.execute(
            select(RfpDispatch).where(
                RfpDispatch.campaign_id == campaign_id,
                RfpDispatch.influencer_id == account.influencer_id,
            )
        )
    ).scalars().first()
    if dispatch and dispatch.status == "sent":
        dispatch.status = "replied"

    influencer_name = account.influencer.name if account.influencer else f"#{account.influencer_id}"
    await notify(
        db, CLIENT, 0,
        f"'{influencer_name}' 크리에이터가 캠페인 #{campaign_id}에 견적을 제출했습니다"
        + (f" ({payload.amount:,}원)." if payload.amount else "."),
        campaign_id=campaign_id,
    )
    await db.commit()
    await db.refresh(quote)
    return quote


@router.get("/creator/campaigns/{campaign_id}/messages", response_model=list[MessageOut])
async def creator_messages(
    campaign_id: int,
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (
            await db.execute(
                select(Message)
                .where(
                    Message.campaign_id == campaign_id,
                    Message.influencer_id == account.influencer_id,
                )
                .order_by(Message.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return rows


@router.post("/creator/campaigns/{campaign_id}/messages", response_model=MessageOut)
async def creator_send_message(
    campaign_id: int,
    payload: dict,
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="메시지 내용을 입력하세요.")
    message = Message(
        campaign_id=campaign_id,
        influencer_id=account.influencer_id,
        direction="inbound",  # 크리에이터 → 클라이언트
        body=body,
    )
    db.add(message)

    influencer_name = account.influencer.name if account.influencer else f"#{account.influencer_id}"
    await notify(
        db, CLIENT, 0,
        f"'{influencer_name}' 크리에이터의 새 메시지: {body[:50]}",
        campaign_id=campaign_id,
    )
    await db.commit()
    await db.refresh(message)
    return message


@router.get("/creator/notifications", response_model=list[NotificationOut])
async def creator_notifications(
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        (
            await db.execute(
                select(Notification)
                .where(
                    Notification.recipient_type == "creator",
                    Notification.recipient_id == account.influencer_id,
                )
                .order_by(Notification.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return rows


@router.patch("/creator/notifications/{notification_id}/read", response_model=NotificationOut)
async def creator_read_notification(
    notification_id: int,
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    n = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_type == "creator",
                Notification.recipient_id == account.influencer_id,
            )
        )
    ).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    n.is_read = True
    await db.commit()
    await db.refresh(n)
    return n
