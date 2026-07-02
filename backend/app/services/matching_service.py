"""AI 매칭/추천 서비스.

현재: 규칙 기반 matchScore (프로토타입 산식 유지 — 폴백 로직으로 계속 사용).
추후: Claude API 기반 매칭 사유 생성으로 고도화 (ANTHROPIC_API_KEY 설정 시 활성화).
"""

from loguru import logger

from ..models.orm_models import Campaign
from ..utils.config import get_settings

MATCH_SCORE_CAP = 98


def rule_based_match_score(engagement_rate: float, growth_rate: float, is_trending: bool) -> int:
    """프로토타입 산식: 60 + engagement*2 + growth*0.5 + (trending ? 8 : 0), 상한 98."""
    score = 60 + engagement_rate * 2 + growth_rate * 0.5 + (8 if is_trending else 0)
    return min(MATCH_SCORE_CAP, round(score))


def estimate_kpi(followers: int, monthly_views: int, engagement_rate: float) -> dict:
    """예상 KPI 시뮬레이션 (규칙 기반)."""
    reach = round(followers * 0.35 + monthly_views * 0.1)
    clicks = round(reach * 0.02)
    conversions = round(clicks * 0.05)
    return {
        "expected_reach": reach,
        "expected_clicks": clicks,
        "expected_conversions": conversions,
        "expected_engagement_rate": engagement_rate,
    }


async def generate_match_reason(campaign: Campaign, influencer_name: str, score: int) -> str:
    """매칭 사유 생성. Claude API 사용 가능 시 AI 생성, 실패/미설정 시 템플릿 폴백."""
    settings = get_settings()
    fallback = (
        f"{influencer_name}은(는) 캠페인 '{campaign.name}'의 타깃과 활동 지표(참여율·성장률) "
        f"기준으로 매칭 점수 {score}점을 기록했습니다."
    )
    if not settings.anthropic_api_key:
        return fallback
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"B2B 인플루언서 매칭 플랫폼입니다. 캠페인 '{campaign.name}' "
                        f"(광고 타입: {campaign.ad_type}, 내용: {campaign.content_detail or '미입력'})에 "
                        f"인플루언서 '{influencer_name}'이 매칭 점수 {score}점으로 추천된 이유를 "
                        f"한국어 1~2문장으로 작성하세요."
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Claude API 매칭 사유 생성 실패: {e}")
        return fallback
