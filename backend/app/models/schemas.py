from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week_start: date
    followers: int
    monthly_views: int
    engagement_rate: float
    growth_rate: float
    is_trending: bool


class InfluencerOut(BaseModel):
    """목록/상세 공용 응답. contact_email은 개인정보 — 절대 포함하지 않는다."""

    id: int
    name: str
    channel: str
    country: str
    tier: str
    category: str | None = None
    cost_range_min: int | None = None
    cost_range_max: int | None = None
    # 최신 스냅샷 지표 (프로토타입 INFLUENCERS 목업 배열 형태 유지)
    followers: int = 0
    monthly_views: int = 0
    engagement_rate: float = 0
    growth_rate: float = 0
    is_trending: bool = False


class InfluencerListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[InfluencerOut]


class CampaignCreate(BaseModel):
    name: str
    budget_range: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    content_detail: str | None = None
    ad_type: str = "ppl"  # ppl | branded
    include_offline: bool = False
    need_ip_license: bool = False
    deadline: date | None = None
    expectation: str | None = None
    # V3 — 콘텐츠 규격·추가 보상 (업무 범위에 따라 크리에이터 견적이 달라짐)
    content_format: str | None = None  # shortform | longform | package
    longform_minutes: int | None = None  # 5 | 10 | 15 | 20(이상)
    shortform_minutes: int | None = None  # 1 | 2 | 3
    additional_rewards: str | None = None
    provided_resources: str | None = None
    must_include: str | None = None


class CampaignOut(CampaignCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime


class RecommendationOut(BaseModel):
    influencer: InfluencerOut
    match_score: int
    match_reason: str
    estimated_kpi: dict


class DispatchRequest(BaseModel):
    influencer_ids: list[int]


class DispatchOut(BaseModel):
    campaign_id: int
    dispatched: int
    recipients: list[str]  # 마스킹된 이메일 목록


class MessageCreate(BaseModel):
    influencer_id: int
    body: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    influencer_id: int
    direction: str
    body: str
    created_at: datetime


class CreatorQuoteIn(BaseModel):
    """크리에이터 포털 견적 제출 — influencer_id는 토큰에서 결정."""

    content_plan: str | None = None
    content_format: str | None = None
    length_minutes: int | None = None
    amount: int | None = None


class QuoteCreate(CreatorQuoteIn):
    influencer_id: int


class QuoteOut(QuoteCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    status: str
    created_at: datetime


class QuoteUpdate(BaseModel):
    status: str  # proposed | negotiating | agreed | rejected


class ContractCreate(BaseModel):
    influencer_id: int
    quote_id: int | None = None


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    influencer_id: int
    quote_id: int | None
    status: str
    signed_at: datetime | None
    created_at: datetime


class ContractUpdate(BaseModel):
    status: str  # provisional | active | completed | terminated


class GuidelineCreate(BaseModel):
    title: str
    body: str
    is_confidential: bool = False


class GuidelineOut(GuidelineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    created_at: datetime


class StoryboardCreate(BaseModel):
    kind: str = "storyboard"  # storyboard | reference | draft_video
    content: str | None = None
    url: str | None = None


class StoryboardOut(StoryboardCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    status: str
    client_feedback: str | None
    created_at: datetime


class StoryboardUpdate(BaseModel):
    status: str  # reviewing | confirmed | rejected
    client_feedback: str | None = None


class DeliverableCreate(BaseModel):
    url: str
    visibility: str = "unlisted"  # unlisted | private


class DeliverableOut(DeliverableCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    review_status: str
    review_note: str | None
    delivered_at: datetime
    published_at: datetime | None


class DeliverableUpdate(BaseModel):
    review_status: str  # approved | rejected
    review_note: str | None = None
    publish: bool = False  # approved + publish → public 전환


class SettlementCreate(BaseModel):
    amount: int
    method: str = "tax_invoice"  # tax_invoice | cash_transfer | platform


class SettlementOut(SettlementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    status: str
    paid_at: datetime | None
    created_at: datetime


class BlacklistCreate(BaseModel):
    entity_type: str  # creator | client
    entity_id: int
    reason: str  # direct_contract | direct_settlement | rule_violation
    penalty: str = "deprioritize"  # exclude | deprioritize | surcharge | block
    note: str | None = None


class BlacklistOut(BlacklistCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CreatorLoginIn(BaseModel):
    email: str
    access_code: str


class CreatorSessionOut(BaseModel):
    token: str  # access_code 그대로 — X-Creator-Token 헤더로 전달
    influencer_id: int
    name: str
    channel: str


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_type: str
    recipient_id: int
    campaign_id: int | None
    contract_id: int | None
    kind: str
    message: str
    is_read: bool
    created_at: datetime


class StageOut(BaseModel):
    key: str
    label: str
    done: bool
    current: bool


class CampaignProgressOut(BaseModel):
    campaign_id: int
    campaign_name: str
    status: str
    stages: list[StageOut]
    current_stage: str


class DashboardItemOut(CampaignProgressOut):
    created_at: datetime
    next_action: str


class DashboardOut(BaseModel):
    campaigns: list[DashboardItemOut]
    unread_notifications: int


class CreatorRfpOut(BaseModel):
    """크리에이터에게 보여주는 RFP.

    ⚠️ 전체 캠페인 예산(budget_range)은 절대 포함하지 않는다 —
    인플루언서별 단가가 제각각이라 공유 금지 정보. 크리에이터는 본인 견적만 제시한다.
    """

    campaign_id: int
    campaign_name: str
    ad_type: str
    content_format: str | None
    longform_minutes: int | None
    shortform_minutes: int | None
    additional_rewards: str | None
    provided_resources: str | None
    must_include: str | None
    deadline: date | None
    dispatch_status: str
    sent_at: datetime
    stages: list[StageOut]
    current_stage: str


class InboundEmailWebhook(BaseModel):
    """SendGrid Inbound Parse 페이로드 (핵심 필드만)."""

    from_email: str
    subject: str = ""
    text: str = ""
    campaign_id: int | None = None
    influencer_id: int | None = None
