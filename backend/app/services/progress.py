"""캠페인 진행 단계 계산 — 프로세스 라인바의 데이터 소스.

V2+V3 전체 수명주기 10단계. DB의 실제 상태(dispatch/quote/contract/storyboard/
deliverable/settlement)로 판정하므로 별도 상태 필드 동기화가 필요 없다.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.orm_models import (
    Campaign,
    Contract,
    Deliverable,
    Quote,
    RfpDispatch,
    Settlement,
    Storyboard,
)
from ..models.schemas import StageOut

STAGES = [
    ("rfp", "RFP 등록"),
    ("recommend", "AI 추천"),
    ("dispatch", "RFP 송부"),
    ("reply", "크리에이터 회신"),
    ("quote", "견적 합의"),
    ("contract", "가계약"),
    ("storyboard", "스토리보드 확정"),
    ("delivery", "납품"),
    ("review", "검수/공개"),
    ("settlement", "정산 완료"),
]

NEXT_ACTIONS = {
    "rfp": "AI 추천을 실행하세요",
    "recommend": "추천 결과에서 대상 선택 후 RFP를 송부하세요",
    "dispatch": "크리에이터 회신 대기 중 — 리마인드 발송 가능",
    "reply": "크리에이터 견적을 확인·협의하세요",
    "quote": "합의된 견적으로 가계약을 생성하세요",
    "contract": "브랜드 가이드를 전달하고 스토리보드를 기다리세요",
    "storyboard": "크리에이터가 최종 콘텐츠 제작 중",
    "delivery": "납품물을 검수하고 공개 여부를 결정하세요",
    "review": "정산을 진행하세요",
    "settlement": "캠페인 완료",
}


async def compute_progress(db: AsyncSession, campaign: Campaign) -> tuple[list[StageOut], str]:
    """(stages, current_stage_key) 반환. done=완료, current=다음 진행 위치."""

    async def exists(query) -> bool:
        return (await db.execute(query.limit(1))).first() is not None

    dispatched = await exists(select(RfpDispatch.id).where(RfpDispatch.campaign_id == campaign.id))
    replied = await exists(
        select(RfpDispatch.id).where(
            RfpDispatch.campaign_id == campaign.id,
            RfpDispatch.status.in_(["replied", "accepted"]),
        )
    )
    quote_agreed = await exists(
        select(Quote.id).where(Quote.campaign_id == campaign.id, Quote.status == "agreed")
    )
    # 회신 판정 보강: 견적이 들어왔다면 회신한 것으로 간주
    quote_any = await exists(select(Quote.id).where(Quote.campaign_id == campaign.id))
    contract_ids = (
        (await db.execute(select(Contract.id).where(Contract.campaign_id == campaign.id)))
        .scalars()
        .all()
    )
    storyboard_confirmed = bool(contract_ids) and await exists(
        select(Storyboard.id).where(
            Storyboard.contract_id.in_(contract_ids), Storyboard.status == "confirmed"
        )
    )
    delivered = bool(contract_ids) and await exists(
        select(Deliverable.id).where(Deliverable.contract_id.in_(contract_ids))
    )
    reviewed = bool(contract_ids) and await exists(
        select(Deliverable.id).where(
            Deliverable.contract_id.in_(contract_ids),
            Deliverable.review_status == "approved",
        )
    )
    settled = bool(contract_ids) and await exists(
        select(Settlement.id).where(
            Settlement.contract_id.in_(contract_ids), Settlement.status == "paid"
        )
    )

    done_map = {
        "rfp": True,  # 캠페인이 존재하면 등록 완료
        "recommend": campaign.status in ("dispatched",) or dispatched or campaign.status == "recommended",
        "dispatch": dispatched,
        "reply": replied or quote_any,
        "quote": quote_agreed,
        "contract": bool(contract_ids),
        "storyboard": storyboard_confirmed,
        "delivery": delivered,
        "review": reviewed,
        "settlement": settled,
    }

    # current = 첫 미완료 단계
    current_key = STAGES[-1][0]
    for key, _ in STAGES:
        if not done_map[key]:
            current_key = key
            break

    stages = [
        StageOut(key=key, label=label, done=done_map[key], current=(key == current_key and not done_map[key]))
        for key, label in STAGES
    ]
    return stages, current_key
