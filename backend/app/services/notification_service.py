"""알림 서비스 — 이벤트 알림 + 미처리 업무 리마인드 스윕.

이벤트: 상태 전환 시 라우터에서 notify() 호출.
리마인드: run_reminder_sweep()이 미처리 업무를 탐지해 kind='reminder' 알림 생성.
main.py lifespan에서 6시간 주기 백그라운드 실행 + POST /api/admin/reminders/run 수동 트리거.
크리에이터 알림은 이메일 발송도 시도한다 (SendGrid 미설정 시 시뮬레이션 로그).
"""

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session
from ..models.orm_models import (
    Campaign,
    Contract,
    CreatorAccount,
    Deliverable,
    Notification,
    Quote,
    RfpDispatch,
    Settlement,
    Storyboard,
)
from .email_service import send_rfp_email

CLIENT = "client"
CREATOR = "creator"
REMINDER_DEDUP_HOURS = 24

_sweep_status: dict = {"last_run": None, "created": 0}


def get_sweep_status() -> dict:
    return _sweep_status


async def notify(
    db: AsyncSession,
    recipient_type: str,
    recipient_id: int,
    message: str,
    kind: str = "event",
    campaign_id: int | None = None,
    contract_id: int | None = None,
    send_email: bool = False,
) -> None:
    """알림 생성. commit은 호출자 트랜잭션에 맡긴다."""
    db.add(
        Notification(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            campaign_id=campaign_id,
            contract_id=contract_id,
            kind=kind,
            message=message,
        )
    )
    if send_email and recipient_type == CREATOR:
        try:
            account = (
                await db.execute(
                    select(CreatorAccount).where(CreatorAccount.influencer_id == recipient_id)
                )
            ).scalar_one_or_none()
            if account:
                await send_rfp_email(account.email, "[Hero Finder] 업무 알림", message)
        except Exception as e:
            logger.warning(f"알림 이메일 발송 실패 (creator={recipient_id}): {e}")


async def _reminder_exists(
    db: AsyncSession, recipient_type: str, recipient_id: int, message: str
) -> bool:
    """동일 대상·동일 사유 리마인드 24시간 내 중복 방지."""
    since = datetime.utcnow() - timedelta(hours=REMINDER_DEDUP_HOURS)
    row = (
        await db.execute(
            select(Notification.id)
            .where(
                Notification.recipient_type == recipient_type,
                Notification.recipient_id == recipient_id,
                Notification.kind == "reminder",
                Notification.message == message,
                Notification.created_at >= since,
            )
            .limit(1)
        )
    ).first()
    return row is not None


async def run_reminder_sweep() -> int:
    """미처리 업무 탐지 → 리마인드 알림 생성. 생성 건수 반환."""
    created = 0
    try:
        async with async_session() as db:
            campaigns = {
                c.id: c for c in (await db.execute(select(Campaign))).scalars().all()
            }

            async def remind(rtype: str, rid: int, msg: str, campaign_id=None, contract_id=None):
                nonlocal created
                if not await _reminder_exists(db, rtype, rid, msg):
                    await notify(
                        db, rtype, rid, msg,
                        kind="reminder", campaign_id=campaign_id, contract_id=contract_id,
                        send_email=(rtype == CREATOR),
                    )
                    created += 1

            # 1. 미회신 RFP → 크리에이터
            for d in (
                (await db.execute(select(RfpDispatch).where(RfpDispatch.status == "sent")))
                .scalars().all()
            ):
                name = campaigns[d.campaign_id].name if d.campaign_id in campaigns else f"#{d.campaign_id}"
                await remind(
                    CREATOR, d.influencer_id,
                    f"[리마인드] 캠페인 '{name}' RFP에 아직 회신하지 않았습니다. 포털에서 견적을 제출해 주세요.",
                    campaign_id=d.campaign_id,
                )

            # 2. 검토 대기 견적 → 클라이언트
            for q in (
                (await db.execute(select(Quote).where(Quote.status == "proposed")))
                .scalars().all()
            ):
                name = campaigns[q.campaign_id].name if q.campaign_id in campaigns else f"#{q.campaign_id}"
                await remind(
                    CLIENT, 0,
                    f"[리마인드] 캠페인 '{name}'에 검토 대기 중인 견적이 있습니다.",
                    campaign_id=q.campaign_id,
                )

            contracts = {
                c.id: c for c in (await db.execute(select(Contract))).scalars().all()
            }

            # 3. 검토 대기 스토리보드 → 클라이언트
            for sb in (
                (await db.execute(select(Storyboard).where(Storyboard.status.in_(["submitted", "reviewing"]))))
                .scalars().all()
            ):
                await remind(
                    CLIENT, 0,
                    f"[리마인드] 계약 #{sb.contract_id}의 스토리보드가 검토(내부 보고·법무 검토)를 기다리고 있습니다.",
                    contract_id=sb.contract_id,
                )

            # 4. 스토리보드 confirm 후 미납품 → 크리에이터
            confirmed_contract_ids = {
                sb.contract_id
                for sb in (
                    (await db.execute(select(Storyboard).where(Storyboard.status == "confirmed")))
                    .scalars().all()
                )
            }
            delivered_contract_ids = {
                d.contract_id
                for d in ((await db.execute(select(Deliverable))).scalars().all())
            }
            for cid in confirmed_contract_ids - delivered_contract_ids:
                contract = contracts.get(cid)
                if contract:
                    await remind(
                        CREATOR, contract.influencer_id,
                        f"[리마인드] 계약 #{cid}의 스토리보드가 확정되었습니다. 최종 콘텐츠를 납품일 전까지 제출해 주세요.",
                        contract_id=cid,
                    )

            # 5. 검수 대기 납품물 → 클라이언트
            for d in (
                (await db.execute(select(Deliverable).where(Deliverable.review_status == "pending")))
                .scalars().all()
            ):
                await remind(
                    CLIENT, 0,
                    f"[리마인드] 계약 #{d.contract_id}의 납품물이 검수를 기다리고 있습니다.",
                    contract_id=d.contract_id,
                )

            # 6. 미지급 정산 → 클라이언트
            for s in (
                (await db.execute(select(Settlement).where(Settlement.status == "pending")))
                .scalars().all()
            ):
                await remind(
                    CLIENT, 0,
                    f"[리마인드] 계약 #{s.contract_id}의 정산({s.amount:,}원)이 미지급 상태입니다.",
                    contract_id=s.contract_id,
                )

            await db.commit()
    except Exception as e:
        logger.error(f"리마인드 스윕 실패: {e}")

    _sweep_status["last_run"] = datetime.utcnow().isoformat()
    _sweep_status["created"] = created
    logger.info(f"리마인드 스윕 완료 — 생성 {created}건")
    return created
