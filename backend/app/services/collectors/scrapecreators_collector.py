"""ScrapeCreators 수집기 — Instagram (KR), TikTok (KR/US/SEA).

TikTok은 TTCM Open API 파트너 승인 시 공식 API로 전환 예정.
SCRAPECREATORS_API_KEY 미설정 시 빈 결과 반환 (파이프라인은 계속 진행).
"""

import httpx
from loguru import logger

from ...utils.config import get_settings

API_BASE = "https://api.scrapecreators.com"


async def collect_instagram_profile(handle: str) -> dict | None:
    return await _fetch_profile("instagram", f"{API_BASE}/v1/instagram/profile", {"handle": handle})


async def collect_tiktok_profile(handle: str) -> dict | None:
    return await _fetch_profile("tiktok", f"{API_BASE}/v1/tiktok/profile", {"handle": handle})


async def _fetch_profile(channel: str, url: str, params: dict) -> dict | None:
    settings = get_settings()
    if not settings.scrapecreators_api_key:
        logger.warning("SCRAPECREATORS_API_KEY 미설정 — 수집 건너뜀")
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"x-api-key": settings.scrapecreators_api_key},
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "channel": channel,
            "channel_id": str(data.get("id", params.get("handle", ""))),
            "name": data.get("full_name") or data.get("nickname") or params.get("handle", ""),
            "followers": int(data.get("follower_count") or data.get("followers") or 0),
            "raw": data,
        }
    except Exception as e:
        logger.warning(f"ScrapeCreators {channel} 수집 실패 ({params}): {e}")
        return None
