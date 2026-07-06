"""크리에이터 포털 API — 본인 계정 로그인, 받은 RFP 조회, 견적 제출, 메시지 커뮤니케이션.

인증: RFP 송부 시 자동 발급된 access_code를 X-Creator-Token 헤더로 전달.
(정식 JWT 인증은 Phase 2-4에서 도입 예정)
"""

import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..utils.config import get_settings

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
    CreatorSettingsIn,
    CreatorSettingsOut,
    CreatorSignupIn,
    CreatorSignupOut,
    GoogleLoginIn,
    GoogleLoginOut,
    MessageOut,
    NotificationOut,
    QuoteOut,
)
from ..models.orm_models import Influencer
from ..services.scoring import classify_tier
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


def _session_of(account: CreatorAccount) -> CreatorSessionOut:
    influencer = account.influencer
    return CreatorSessionOut(
        token=account.access_code,
        influencer_id=account.influencer_id,
        name=influencer.name if influencer else "",
        channel=influencer.channel if influencer else "",
    )


@router.post("/auth/creator/signup", response_model=CreatorSignupOut)
async def creator_signup(payload: CreatorSignupIn, db: AsyncSession = Depends(get_db)):
    """셀프 가입 — 기존 인플루언서(channel+handle)가 있으면 자동 연결(claim), 없으면 신규 등록."""
    channel = payload.channel.lower().strip()
    handle = payload.handle.lstrip("@").strip()
    email = payload.email.strip().lower()
    if channel not in ("youtube", "instagram", "tiktok"):
        raise HTTPException(status_code=400, detail="channel은 youtube/instagram/tiktok 중 하나여야 합니다.")
    if not handle or not email or not payload.name.strip():
        raise HTTPException(status_code=400, detail="이름, 이메일, 핸들을 모두 입력하세요.")

    dup = (
        await db.execute(select(CreatorAccount).where(CreatorAccount.email == email))
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다. 로그인해 주세요.")

    # claim: 파이프라인이 수집해 둔 기존 프로필과 연결 (IG/TT는 channel_id가 곧 핸들)
    inf = (
        await db.execute(
            select(Influencer).where(
                Influencer.channel == channel, Influencer.channel_id == handle
            )
        )
    ).scalar_one_or_none()
    claimed = inf is not None
    if inf is None:
        inf = Influencer(
            name=payload.name.strip(),
            channel=channel,
            channel_id=handle,
            country="KR",
            tier=classify_tier(0),
            contact_email=email,  # 본인 제공 동의 기반
        )
        db.add(inf)
        await db.flush()
    else:
        existing_account = (
            await db.execute(
                select(CreatorAccount).where(CreatorAccount.influencer_id == inf.id)
            )
        ).scalar_one_or_none()
        if existing_account:
            raise HTTPException(status_code=409, detail="이 채널은 이미 다른 계정에 연결되어 있습니다.")
        inf.contact_email = email  # 크리에이터 연결 시 컨택 이메일 등록

    account = CreatorAccount(
        influencer_id=inf.id,
        email=email,
        access_code=uuid.uuid4().hex,
        google_sub=payload.google_sub,
        last_login_at=datetime.utcnow(),
    )
    db.add(account)
    await db.commit()
    account = (
        await db.execute(
            select(CreatorAccount)
            .options(selectinload(CreatorAccount.influencer))
            .where(CreatorAccount.id == account.id)
        )
    ).scalar_one()
    return CreatorSignupOut(
        session=_session_of(account), access_code=account.access_code, claimed_existing=claimed
    )


@router.post("/auth/creator/google", response_model=GoogleLoginOut)
async def creator_google_login(payload: GoogleLoginIn, db: AsyncSession = Depends(get_db)):
    """구글 로그인 — GIS ID 토큰 검증 후 계정 매칭. 미가입이면 needs_signup 반환."""
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="구글 로그인이 아직 설정되지 않았습니다 (GOOGLE_CLIENT_ID).")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo", params={"id_token": payload.id_token}
            )
            resp.raise_for_status()
            info = resp.json()
    except Exception as e:
        logger.warning(f"구글 토큰 검증 실패: {e}")
        raise HTTPException(status_code=401, detail="구글 토큰 검증에 실패했습니다.")

    if info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=401, detail="토큰 대상(aud)이 일치하지 않습니다.")
    sub = info.get("sub")
    email = (info.get("email") or "").lower()

    account = (
        await db.execute(
            select(CreatorAccount)
            .options(selectinload(CreatorAccount.influencer))
            .where(CreatorAccount.google_sub == sub)
        )
    ).scalar_one_or_none()
    if account is None and email:
        account = (
            await db.execute(
                select(CreatorAccount)
                .options(selectinload(CreatorAccount.influencer))
                .where(CreatorAccount.email == email)
            )
        ).scalar_one_or_none()
        if account:
            account.google_sub = sub  # 기존 이메일 계정에 구글 연동

    if account is None:
        return GoogleLoginOut(status="needs_signup", email=email, google_sub=sub)

    account.last_login_at = datetime.utcnow()
    await db.commit()
    return GoogleLoginOut(status="ok", session=_session_of(account))


@router.get("/creator/settings", response_model=CreatorSettingsOut)
async def get_creator_settings(account: CreatorAccount = Depends(get_current_creator)):
    inf = account.influencer
    return CreatorSettingsOut(
        name=inf.name if inf else "",
        channel=inf.channel if inf else "",
        handle=inf.channel_id if inf else "",
        contact_email=inf.contact_email if inf else None,
        bio=account.bio,
        preferred_format=account.preferred_format,
        preferred_length_minutes=account.preferred_length_minutes,
        cost_range_min=inf.cost_range_min if inf else None,
        cost_range_max=inf.cost_range_max if inf else None,
        available=account.available if account.available is not None else True,
    )


@router.put("/creator/settings", response_model=CreatorSettingsOut)
async def update_creator_settings(
    payload: CreatorSettingsIn,
    account: CreatorAccount = Depends(get_current_creator),
    db: AsyncSession = Depends(get_db),
):
    """기획 설정 저장 — 컨택 이메일·콘텐츠 형식·길이·희망 단가·소개·협업 가능 여부."""
    inf = (
        await db.execute(select(Influencer).where(Influencer.id == account.influencer_id))
    ).scalar_one()
    acc = (
        await db.execute(select(CreatorAccount).where(CreatorAccount.id == account.id))
    ).scalar_one()

    if payload.contact_email is not None:
        inf.contact_email = payload.contact_email.strip().lower() or None
    if payload.cost_range_min is not None:
        inf.cost_range_min = payload.cost_range_min
    if payload.cost_range_max is not None:
        inf.cost_range_max = payload.cost_range_max
    if payload.bio is not None:
        acc.bio = payload.bio
    if payload.preferred_format is not None:
        acc.preferred_format = payload.preferred_format or None
    if payload.preferred_length_minutes is not None:
        acc.preferred_length_minutes = payload.preferred_length_minutes
    if payload.available is not None:
        acc.available = payload.available
    await db.commit()

    return CreatorSettingsOut(
        name=inf.name,
        channel=inf.channel,
        handle=inf.channel_id,
        contact_email=inf.contact_email,
        bio=acc.bio,
        preferred_format=acc.preferred_format,
        preferred_length_minutes=acc.preferred_length_minutes,
        cost_range_min=inf.cost_range_min,
        cost_range_max=inf.cost_range_max,
        available=acc.available if acc.available is not None else True,
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
