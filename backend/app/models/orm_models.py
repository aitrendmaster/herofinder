from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

CHANNELS = ("youtube", "instagram", "tiktok")
TIERS = ("mega", "power", "micro", "nano")
AD_TYPES = ("ppl", "branded")
DISPATCH_STATUSES = ("sent", "opened", "replied", "accepted", "declined")
MESSAGE_DIRECTIONS = ("inbound", "outbound")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Influencer(Base):
    __tablename__ = "influencers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(20))  # youtube | instagram | tiktok
    channel_id: Mapped[str] = mapped_column(String(100))  # 플랫폼 고유 ID
    country: Mapped[str] = mapped_column(String(2), default="KR")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    tier: Mapped[str] = mapped_column(String(10))  # 최신 스냅샷 기준 자동 갱신
    # ⚠️ 개인정보 — 목록 API 응답에서 제외, RFP 송부 시점에만 서버 측 사용
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cost_range_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_range_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["Category | None"] = relationship()
    snapshots: Mapped[list["InfluencerSnapshot"]] = relationship(back_populates="influencer")


class InfluencerSnapshot(Base):
    __tablename__ = "influencer_snapshots"
    __table_args__ = (UniqueConstraint("influencer_id", "week_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    influencer_id: Mapped[int] = mapped_column(ForeignKey("influencers.id"))
    week_start: Mapped[date] = mapped_column(Date)
    followers: Mapped[int] = mapped_column(Integer, default=0)
    monthly_views: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    growth_rate: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False)

    influencer: Mapped["Influencer"] = relationship(back_populates="snapshots")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(100))
    contact_email: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    budget_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    content_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ad_type: Mapped[str] = mapped_column(String(20), default="ppl")  # ppl | branded
    include_offline: Mapped[bool] = mapped_column(Boolean, default=False)
    need_ip_license: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    expectation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # V3 확장 — 콘텐츠 규격 (업무 범위 → 크리에이터 견적 산정 기준)
    content_format: Mapped[str | None] = mapped_column(String(20), nullable=True)  # shortform | longform | package
    longform_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 5 | 10 | 15 | 20(이상)
    shortform_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 | 2 | 3
    additional_rewards: Mapped[str | None] = mapped_column(Text, nullable=True)  # 추가 보상 (크레딧, 티어별 리워드 등)
    provided_resources: Mapped[str | None] = mapped_column(Text, nullable=True)  # 클라이언트 제공 재원·소재
    must_include: Mapped[str | None] = mapped_column(Text, nullable=True)  # 필수 포함 내용 (해시태그·멘션·워터마크 등)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dispatches: Mapped[list["RfpDispatch"]] = relationship(back_populates="campaign")


class RfpDispatch(Base):
    __tablename__ = "rfp_dispatches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    influencer_id: Mapped[int] = mapped_column(ForeignKey("influencers.id"))
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="sent")
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_kpi: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="dispatches")
    influencer: Mapped["Influencer"] = relationship()


class Quote(Base):
    """크리에이터 1차 견적 — 콘텐츠 기획 방향 + 업무범위 기준 금액."""

    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    influencer_id: Mapped[int] = mapped_column(ForeignKey("influencers.id"))
    content_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # 기획 방향·형식
    content_format: Mapped[str | None] = mapped_column(String(20), nullable=True)  # shortform | longform | package
    length_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 원 단위
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed | negotiating | agreed | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    influencer: Mapped["Influencer"] = relationship()


class Contract(Base):
    """견적·스콥 합의 → 가계약(provisional) → 실질 계약(active)."""

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    influencer_id: Mapped[int] = mapped_column(ForeignKey("influencers.id"))
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="provisional")  # provisional | active | completed | terminated
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    influencer: Mapped["Influencer"] = relationship()


class BrandGuideline(Base):
    """클라이언트 → 크리에이터 브랜드 가이드 (톤앤매너·정책·Do&Don't). 기밀 옵션."""

    __tablename__ = "brand_guidelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)  # 기밀 — 열람 로그 남김
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GuidelineAccessLog(Base):
    """기밀 가이드 열람 로그 (보안 옵션)."""

    __tablename__ = "guideline_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guideline_id: Mapped[int] = mapped_column(ForeignKey("brand_guidelines.id"))
    accessor: Mapped[str] = mapped_column(String(100))  # 열람 주체 식별자
    accessed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Storyboard(Base):
    """크리에이터 기획안·스토리보드·레퍼런스·가안 영상 제출 → 클라이언트 confirm."""

    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    kind: Mapped[str] = mapped_column(String(20), default="storyboard")  # storyboard | reference | draft_video
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # 기획안 본문
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 레퍼런스/가안 영상 URL
    status: Mapped[str] = mapped_column(String(20), default="submitted")  # submitted | reviewing | confirmed | rejected
    client_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Deliverable(Base):
    """최종 콘텐츠 납품 (일부공개/비공개 URL) → 검수 → public 공개."""

    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    url: Mapped[str] = mapped_column(String(500))  # unlisted/private URL
    visibility: Mapped[str] = mapped_column(String(20), default="unlisted")  # unlisted | private | public
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Settlement(Base):
    """클라이언트-크리에이터 정산. Hero Finder 간편정산은 method=platform."""

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"))
    amount: Mapped[int] = mapped_column(Integer)  # 원 단위
    method: Mapped[str] = mapped_column(String(20), default="tax_invoice")  # tax_invoice | cash_transfer | platform
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | paid | disputed
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BlacklistEntry(Base):
    """직거래 우회 등 위반 시 블랙 처리 — 크리에이터는 추천 제외/강등, 클라이언트는 과금·제약."""

    __tablename__ = "blacklist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # creator | client
    entity_id: Mapped[int] = mapped_column(Integer)  # influencer.id 또는 client.id
    reason: Mapped[str] = mapped_column(String(50))  # direct_contract | direct_settlement | rule_violation
    penalty: Mapped[str] = mapped_column(String(20), default="deprioritize")  # exclude | deprioritize | surcharge | block
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    influencer_id: Mapped[int] = mapped_column(ForeignKey("influencers.id"))
    direction: Mapped[str] = mapped_column(String(10))  # inbound | outbound
    body: Mapped[str] = mapped_column(Text)
    email_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 이메일 스레딩용
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    influencer: Mapped["Influencer"] = relationship()
