"""계약 파이프라인 — 견적(Quote) → 가계약/본계약(Contract) → 브랜드 가이드 →
스토리보드 검토 → 납품/검수 → 정산 (V3 §11-3 ~ §11-5)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.orm_models import (
    BrandGuideline,
    Campaign,
    Contract,
    Deliverable,
    GuidelineAccessLog,
    Quote,
    Settlement,
    Storyboard,
)
from ..services.notification_service import CLIENT, CREATOR, notify
from ..models.schemas import (
    ContractCreate,
    ContractOut,
    ContractUpdate,
    DeliverableCreate,
    DeliverableOut,
    DeliverableUpdate,
    GuidelineCreate,
    GuidelineOut,
    QuoteCreate,
    QuoteOut,
    QuoteUpdate,
    SettlementCreate,
    SettlementOut,
    StoryboardCreate,
    StoryboardOut,
    StoryboardUpdate,
)

router = APIRouter(prefix="/api", tags=["deals"])


async def _get_or_404(db: AsyncSession, model, obj_id: int, label: str):
    obj = (await db.execute(select(model).where(model.id == obj_id))).scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail=f"{label}을(를) 찾을 수 없습니다.")
    return obj


# ---------- 견적 (1차 견적: 기획 방향 + 업무범위 기준 금액) ----------

@router.post("/campaigns/{campaign_id}/quotes", response_model=QuoteOut)
async def create_quote(campaign_id: int, payload: QuoteCreate, db: AsyncSession = Depends(get_db)):
    await _get_or_404(db, Campaign, campaign_id, "캠페인")
    quote = Quote(campaign_id=campaign_id, **payload.model_dump())
    db.add(quote)
    await notify(
        db, CLIENT, 0,
        f"캠페인 #{campaign_id}에 새 견적이 등록되었습니다"
        + (f" ({payload.amount:,}원)." if payload.amount else "."),
        campaign_id=campaign_id,
    )
    await db.commit()
    await db.refresh(quote)
    return quote


@router.get("/campaigns/{campaign_id}/quotes", response_model=list[QuoteOut])
async def list_quotes(campaign_id: int, db: AsyncSession = Depends(get_db)):
    rows = (
        (await db.execute(select(Quote).where(Quote.campaign_id == campaign_id))).scalars().all()
    )
    return rows


@router.patch("/quotes/{quote_id}", response_model=QuoteOut)
async def update_quote(quote_id: int, payload: QuoteUpdate, db: AsyncSession = Depends(get_db)):
    quote = await _get_or_404(db, Quote, quote_id, "견적")
    quote.status = payload.status
    status_msg = {
        "agreed": "합의되었습니다. 가계약 진행이 가능합니다.",
        "negotiating": "협의 중으로 변경되었습니다.",
        "rejected": "반려되었습니다.",
    }.get(payload.status)
    if status_msg:
        await notify(
            db, CREATOR, quote.influencer_id,
            f"캠페인 #{quote.campaign_id} 견적이 {status_msg}",
            campaign_id=quote.campaign_id, send_email=True,
        )
    await db.commit()
    await db.refresh(quote)
    return quote


# ---------- 계약 (합의 → 가계약 provisional → 본계약 active) ----------

@router.post("/campaigns/{campaign_id}/contracts", response_model=ContractOut)
async def create_contract(
    campaign_id: int, payload: ContractCreate, db: AsyncSession = Depends(get_db)
):
    await _get_or_404(db, Campaign, campaign_id, "캠페인")
    if payload.quote_id:
        quote = await _get_or_404(db, Quote, payload.quote_id, "견적")
        if quote.status != "agreed":
            raise HTTPException(status_code=400, detail="합의(agreed)된 견적만 계약으로 전환할 수 있습니다.")
    contract = Contract(campaign_id=campaign_id, **payload.model_dump())
    db.add(contract)
    await db.flush()
    await notify(
        db, CREATOR, contract.influencer_id,
        f"캠페인 #{campaign_id} 가계약이 성립되었습니다. 브랜드 가이드 수령 후 스토리보드를 준비해 주세요.",
        campaign_id=campaign_id, contract_id=contract.id, send_email=True,
    )
    await notify(
        db, CLIENT, 0,
        f"캠페인 #{campaign_id} 가계약 생성 — 브랜드 가이드(톤앤매너·Do&Don't)를 전달하세요.",
        campaign_id=campaign_id, contract_id=contract.id,
    )
    await db.commit()
    await db.refresh(contract)
    return contract


@router.patch("/contracts/{contract_id}", response_model=ContractOut)
async def update_contract(
    contract_id: int, payload: ContractUpdate, db: AsyncSession = Depends(get_db)
):
    contract = await _get_or_404(db, Contract, contract_id, "계약")
    contract.status = payload.status
    if payload.status == "active" and contract.signed_at is None:
        contract.signed_at = datetime.utcnow()
        await notify(
            db, CREATOR, contract.influencer_id,
            f"계약 #{contract.id}이 본계약(active)으로 전환되었습니다.",
            contract_id=contract.id, send_email=True,
        )
    await db.commit()
    await db.refresh(contract)
    return contract


# ---------- 브랜드 가이드 (기밀 옵션 + 열람 로그) ----------

@router.post("/contracts/{contract_id}/guidelines", response_model=GuidelineOut)
async def create_guideline(
    contract_id: int, payload: GuidelineCreate, db: AsyncSession = Depends(get_db)
):
    contract = await _get_or_404(db, Contract, contract_id, "계약")
    guideline = BrandGuideline(contract_id=contract_id, **payload.model_dump())
    db.add(guideline)
    await notify(
        db, CREATOR, contract.influencer_id,
        f"브랜드 가이드 '{payload.title}'이(가) 전달되었습니다"
        + (" (기밀 — 외부 공유 금지)." if payload.is_confidential else "."),
        contract_id=contract_id, send_email=True,
    )
    await db.commit()
    await db.refresh(guideline)
    return guideline


@router.get("/contracts/{contract_id}/guidelines", response_model=list[GuidelineOut])
async def list_guidelines(
    contract_id: int,
    accessor: str = Query("unknown", description="열람 주체 식별자 — 기밀 가이드 열람 로그에 기록"),
    db: AsyncSession = Depends(get_db),
):
    await _get_or_404(db, Contract, contract_id, "계약")
    rows = (
        (
            await db.execute(
                select(BrandGuideline).where(BrandGuideline.contract_id == contract_id)
            )
        )
        .scalars()
        .all()
    )
    # 기밀 가이드는 열람 로그를 남긴다 (보안 옵션)
    for g in rows:
        if g.is_confidential:
            db.add(GuidelineAccessLog(guideline_id=g.id, accessor=accessor))
            logger.info(f"기밀 가이드 열람: guideline={g.id}, accessor={accessor}")
    await db.commit()
    return rows


# ---------- 스토리보드 (기획안/레퍼런스/가안 → 내부보고·법무검토 → confirm) ----------

@router.post("/contracts/{contract_id}/storyboards", response_model=StoryboardOut)
async def create_storyboard(
    contract_id: int, payload: StoryboardCreate, db: AsyncSession = Depends(get_db)
):
    await _get_or_404(db, Contract, contract_id, "계약")
    sb = Storyboard(contract_id=contract_id, **payload.model_dump())
    db.add(sb)
    await notify(
        db, CLIENT, 0,
        f"계약 #{contract_id}에 스토리보드/기획안({payload.kind})이 제출되었습니다 — 내부 보고·법무 검토를 진행하세요.",
        contract_id=contract_id,
    )
    await db.commit()
    await db.refresh(sb)
    return sb


@router.get("/contracts/{contract_id}/storyboards", response_model=list[StoryboardOut])
async def list_storyboards(contract_id: int, db: AsyncSession = Depends(get_db)):
    rows = (
        (await db.execute(select(Storyboard).where(Storyboard.contract_id == contract_id)))
        .scalars()
        .all()
    )
    return rows


@router.patch("/storyboards/{storyboard_id}", response_model=StoryboardOut)
async def review_storyboard(
    storyboard_id: int, payload: StoryboardUpdate, db: AsyncSession = Depends(get_db)
):
    sb = await _get_or_404(db, Storyboard, storyboard_id, "스토리보드")
    sb.status = payload.status
    if payload.client_feedback is not None:
        sb.client_feedback = payload.client_feedback
    contract = await _get_or_404(db, Contract, sb.contract_id, "계약")
    status_msg = {
        "confirmed": "확정(confirm)되었습니다. 최종 콘텐츠 제작을 진행해 주세요.",
        "rejected": f"반려되었습니다. 피드백: {payload.client_feedback or '-'}",
        "reviewing": "검토 중으로 변경되었습니다.",
    }.get(payload.status)
    if status_msg:
        await notify(
            db, CREATOR, contract.influencer_id,
            f"계약 #{sb.contract_id} 스토리보드가 {status_msg}",
            contract_id=sb.contract_id, send_email=True,
        )
    await db.commit()
    await db.refresh(sb)
    return sb


# ---------- 납품/검수 (unlisted·private URL → 검수 → public) ----------

@router.post("/contracts/{contract_id}/deliverables", response_model=DeliverableOut)
async def create_deliverable(
    contract_id: int, payload: DeliverableCreate, db: AsyncSession = Depends(get_db)
):
    contract = await _get_or_404(db, Contract, contract_id, "계약")
    # confirmed 스토리보드가 있어야 최종안 납품 가능
    confirmed = (
        await db.execute(
            select(Storyboard).where(
                Storyboard.contract_id == contract_id, Storyboard.status == "confirmed"
            )
        )
    ).first()
    if not confirmed:
        raise HTTPException(
            status_code=400, detail="클라이언트가 confirm한 스토리보드/기획안이 있어야 납품할 수 있습니다."
        )
    if payload.visibility == "public":
        raise HTTPException(status_code=400, detail="납품은 일부공개(unlisted) 또는 비공개(private) URL만 허용됩니다.")
    deliverable = Deliverable(contract_id=contract_id, **payload.model_dump())
    db.add(deliverable)
    await notify(
        db, CLIENT, 0,
        f"계약 #{contract_id}의 최종 콘텐츠가 납품되었습니다 ({payload.visibility} URL) — 검수를 진행하세요.",
        contract_id=contract_id,
    )
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


@router.patch("/deliverables/{deliverable_id}", response_model=DeliverableOut)
async def review_deliverable(
    deliverable_id: int, payload: DeliverableUpdate, db: AsyncSession = Depends(get_db)
):
    d = await _get_or_404(db, Deliverable, deliverable_id, "납품물")
    d.review_status = payload.review_status
    if payload.review_note is not None:
        d.review_note = payload.review_note
    published = False
    if payload.review_status == "approved" and payload.publish:
        d.visibility = "public"
        d.published_at = datetime.utcnow()
        published = True
    contract = await _get_or_404(db, Contract, d.contract_id, "계약")
    msg = (
        "검수 승인 및 public 공개되었습니다."
        if published
        else f"검수 결과: {payload.review_status}"
        + (f" — {payload.review_note}" if payload.review_note else "")
    )
    await notify(
        db, CREATOR, contract.influencer_id,
        f"계약 #{d.contract_id} 납품물 {msg}",
        contract_id=d.contract_id, send_email=True,
    )
    await db.commit()
    await db.refresh(d)
    return d


# ---------- 정산 (세금계산서/현금입금/플랫폼 간편정산) ----------

@router.post("/contracts/{contract_id}/settlements", response_model=SettlementOut)
async def create_settlement(
    contract_id: int, payload: SettlementCreate, db: AsyncSession = Depends(get_db)
):
    await _get_or_404(db, Contract, contract_id, "계약")
    approved = (
        await db.execute(
            select(Deliverable).where(
                Deliverable.contract_id == contract_id, Deliverable.review_status == "approved"
            )
        )
    ).first()
    if not approved:
        raise HTTPException(status_code=400, detail="검수 승인(approved)된 납품물이 있어야 정산할 수 있습니다.")
    settlement = Settlement(contract_id=contract_id, **payload.model_dump())
    db.add(settlement)
    contract = await _get_or_404(db, Contract, contract_id, "계약")
    method_label = {"tax_invoice": "세금계산서", "cash_transfer": "현금입금", "platform": "플랫폼 간편정산"}.get(payload.method, payload.method)
    await notify(
        db, CREATOR, contract.influencer_id,
        f"계약 #{contract_id} 정산이 생성되었습니다 ({payload.amount:,}원 · {method_label}).",
        contract_id=contract_id, send_email=True,
    )
    await db.commit()
    await db.refresh(settlement)
    return settlement


@router.patch("/settlements/{settlement_id}/paid", response_model=SettlementOut)
async def mark_settlement_paid(settlement_id: int, db: AsyncSession = Depends(get_db)):
    s = await _get_or_404(db, Settlement, settlement_id, "정산")
    s.status = "paid"
    s.paid_at = datetime.utcnow()
    contract = await _get_or_404(db, Contract, s.contract_id, "계약")
    await notify(
        db, CREATOR, contract.influencer_id,
        f"계약 #{s.contract_id} 정산({s.amount:,}원)이 지급 완료되었습니다.",
        contract_id=s.contract_id, send_email=True,
    )
    await notify(
        db, CLIENT, 0,
        f"계약 #{s.contract_id} 정산 지급 완료 — 캠페인 수명주기가 종료되었습니다.",
        contract_id=s.contract_id,
    )
    await db.commit()
    await db.refresh(s)
    return s
