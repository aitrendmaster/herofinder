from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.orm_models import Influencer, Message, RfpDispatch
from ..models.schemas import InboundEmailWebhook
from ..services.notification_service import CLIENT, notify

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/email-inbound")
async def email_inbound(payload: InboundEmailWebhook, db: AsyncSession = Depends(get_db)):
    """인플루언서 회신 수신 (SendGrid Inbound Parse).

    campaign_id/influencer_id가 없으면 발신 이메일로 인플루언서를 역추적한다.
    """
    influencer_id = payload.influencer_id
    campaign_id = payload.campaign_id

    if influencer_id is None:
        inf = (
            await db.execute(
                select(Influencer).where(Influencer.contact_email == payload.from_email)
            )
        ).scalar_one_or_none()
        if inf:
            influencer_id = inf.id

    if influencer_id is None:
        logger.warning(f"인바운드 이메일 매칭 실패: {payload.from_email}")
        return {"status": "unmatched"}

    if campaign_id is None:
        dispatch = (
            await db.execute(
                select(RfpDispatch)
                .where(RfpDispatch.influencer_id == influencer_id)
                .order_by(RfpDispatch.sent_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if dispatch:
            campaign_id = dispatch.campaign_id
            dispatch.status = "replied"

    if campaign_id is None:
        logger.warning(f"인바운드 이메일 캠페인 매칭 실패: influencer={influencer_id}")
        return {"status": "unmatched"}

    db.add(
        Message(
            campaign_id=campaign_id,
            influencer_id=influencer_id,
            direction="inbound",
            body=payload.text or payload.subject,
        )
    )
    await notify(
        db, CLIENT, 0,
        f"크리에이터 #{influencer_id}의 이메일 회신이 도착했습니다 (캠페인 #{campaign_id}).",
        campaign_id=campaign_id,
    )
    await db.commit()
    return {"status": "received", "campaign_id": campaign_id, "influencer_id": influencer_id}
