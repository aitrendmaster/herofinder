"""활성도 스코어링 — 주간 파이프라인의 등급 분류 및 활성(trending) 판정."""

TIER_THRESHOLDS = [
    ("mega", 1_000_000),
    ("power", 100_000),
    ("micro", 10_000),
    ("nano", 2_000),
]

# 활성 판정 임계값 (초기값 — 데이터 축적 후 조정)
TRENDING_GROWTH_RATE = 3.0  # 주간 성장률 %
TRENDING_ENGAGEMENT_RATE = 5.0  # 참여율 %


def classify_tier(followers: int) -> str:
    for tier, threshold in TIER_THRESHOLDS:
        if followers >= threshold:
            return tier
    return "nano"


def is_trending(growth_rate: float, engagement_rate: float) -> bool:
    return growth_rate >= TRENDING_GROWTH_RATE or engagement_rate >= TRENDING_ENGAGEMENT_RATE
