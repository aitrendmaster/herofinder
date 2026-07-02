from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from ..database import get_db
from ..models.orm_models import Campaign, CreatorAccount, Influencer, Message, RfpDispatch
from ..models.schemas import (
    CampaignCreate,
    CampaignOut,
    DispatchOut,
    DispatchRequest,
    InfluencerOut,
    MessageCreate,
    MessageOut,
    RecommendationOut,
)
from ..routers.influencers import _latest_snapshot
from ..services.email_service import mask_email, send_rfp_email
from ..services.matching_service import estimate_kpi, rule_based_match_score
from ..services.notification_service import CREATOR, notify
from ..services.recommendation import build_recommendations

CREATOR_PORTAL_URL = "http://localhost:3000/creator"  # 배포 시 실제 도메인으로 교체


async def _ensure_creator_account(db: AsyncSession, inf: Influencer) -> CreatorAccount:
    """RFP 송부 시 크리에이터 계정 자동 발급 (이미 있으면 재사용)."""
    account = (
        await db.execute(
            select(CreatorAccount).where(CreatorAccount.influencer_id == inf.id)
        )
    ).scalar_one_or_none()
    if not account:
        account = CreatorAccount(
            influencer_id=inf.id,
            email=inf.contact_email or "",
            access_code=uuid.uuid4().hex,
        )
        db.add(account)
        await db.flush()
    return account

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


async def _get_campaign(db: AsyncSession, campaign_id: int) -> Campaign:
    campaign = (
        await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    ).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다.")
    return campaign


@router.post("", response_model=CampaignOut)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**payload.model_dump(), status="registered")
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_campaign(db, campaign_id)


@router.post("/{campaign_id}/ai-recommend", response_model=list[RecommendationOut])
async def ai_recommend(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """AI 맞춤 인플루언서 추천 — 매칭 점수 + 예상 KPI. 상위 10명 반환.

    블랙리스트 크리에이터는 제외(exclude/block)되거나 최후순위(deprioritize)로 밀린다.
    """
    campaign = await _get_campaign(db, campaign_id)
    recs = await build_recommendations(db, campaign, limit=10)
    return [
        RecommendationOut(
            influencer=InfluencerOut(**{k: r[k] for k in InfluencerOut.model_fields}),
            match_score=r["match_score"],
            match_reason=r["match_reason"],
            estimated_kpi=r["estimated_kpi"],
        )
        for r in recs
    ]


@router.post("/{campaign_id}/dispatch", response_model=DispatchOut)
async def dispatch_rfp(
    campaign_id: int, payload: DispatchRequest, db: AsyncSession = Depends(get_db)
):
    """선택된 인플루언서의 contact mail로 RFP 자동 송부."""
    campaign = await _get_campaign(db, campaign_id)

    recipients: list[str] = []
    dispatched = 0
    for influencer_id in payload.influencer_ids:
        inf = (
            await db.execute(select(Influencer).where(Influencer.id == influencer_id))
        ).scalar_one_or_none()
        if not inf:
            continue

        snap = await _latest_snapshot(db, inf.id)
        score = (
            rule_based_match_score(
                float(snap.engagement_rate), float(snap.growth_rate), snap.is_trending
            )
            if snap
            else None
        )

        # 크리에이터 계정 자동 발급 — 포털 접속 코드가 RFP 이메일에 포함됨
        account = await _ensure_creator_account(db, inf)

        # contact_email은 서버 측에서만 사용 — 응답에는 마스킹된 값만 노출
        if inf.contact_email:
            # ⚠️ 전체 캠페인 예산은 크리에이터 비노출 (인플루언서별 단가 상이 — 공유 금지)
            body = (
                f"[Hero Finder] 캠페인 제안: {campaign.name}\n\n"
                f"광고 타입: {campaign.ad_type}\n"
                f"내용: {campaign.content_detail or '-'}\n"
                f"납품 기한: {campaign.deadline or '협의'}\n"
                f"보수: 크리에이터님의 견적 제안을 받아 개별 협의합니다\n\n"
                f"▶ Hero Finder 크리에이터 포털에서 견적 제출·메시지 소통이 가능합니다.\n"
                f"   포털: {CREATOR_PORTAL_URL}\n"
                f"   로그인 이메일: {inf.contact_email}\n"
                f"   접속 코드: {account.access_code}\n"
            )
            await send_rfp_email(inf.contact_email, f"[RFP] {campaign.name}", body)
            recipients.append(mask_email(inf.contact_email))

        await notify(
            db, CREATOR, inf.id,
            f"새 캠페인 제안(RFP)이 도착했습니다: '{campaign.name}' — 포털에서 견적을 제출해 주세요.",
            campaign_id=campaign.id,
        )

        db.add(
            RfpDispatch(
                campaign_id=campaign.id,
                influencer_id=inf.id,
                status="sent",
                match_score=score,
                estimated_kpi=estimate_kpi(
                    snap.followers, snap.monthly_views, float(snap.engagement_rate)
                )
                if snap
                else None,
            )
        )
        dispatched += 1

    campaign.status = "dispatched"
    await db.commit()
    return DispatchOut(campaign_id=campaign.id, dispatched=dispatched, recipients=recipients)


@router.get("/{campaign_id}/messages", response_model=list[MessageOut])
async def list_messages(campaign_id: int, db: AsyncSession = Depends(get_db)):
    await _get_campaign(db, campaign_id)
    rows = (
        (
            await db.execute(
                select(Message)
                .where(Message.campaign_id == campaign_id)
                .order_by(Message.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return rows


@router.post("/{campaign_id}/messages", response_model=MessageOut)
async def send_message(
    campaign_id: int, payload: MessageCreate, db: AsyncSession = Depends(get_db)
):
    """아웃바운드 메시지 — 인플루언서 이메일로 발송 후 저장."""
    await _get_campaign(db, campaign_id)
    inf = (
        await db.execute(select(Influencer).where(Influencer.id == payload.influencer_id))
    ).scalar_one_or_none()
    if not inf:
        raise HTTPException(status_code=404, detail="인플루언서를 찾을 수 없습니다.")

    if inf.contact_email:
        await send_rfp_email(inf.contact_email, "[Hero Finder] 새 메시지", payload.body)

    message = Message(
        campaign_id=campaign_id,
        influencer_id=payload.influencer_id,
        direction="outbound",
        body=payload.body,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
