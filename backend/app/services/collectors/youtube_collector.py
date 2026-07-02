"""YouTube Data API v3 수집기 (KR).

시드 채널 리스트 기반 주간 스냅샷 수집. 일 쿼터 10,000 유닛 — channels.list는 1유닛/호출.
YOUTUBE_API_KEY 미설정 시 빈 결과 반환 (파이프라인은 계속 진행).
"""

import httpx
from loguru import logger

from ...utils.config import get_settings

API_BASE = "https://www.googleapis.com/youtube/v3"


async def collect_channel_stats(channel_ids: list[str]) -> list[dict]:
    settings = get_settings()
    if not settings.youtube_api_key:
        logger.warning("YOUTUBE_API_KEY 미설정 — YouTube 수집 건너뜀")
        return []

    results: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # channels.list는 한 번에 최대 50개 ID 지원
            for i in range(0, len(channel_ids), 50):
                batch = channel_ids[i : i + 50]
                resp = await client.get(
                    f"{API_BASE}/channels",
                    params={
                        "part": "statistics,snippet",
                        "id": ",".join(batch),
                        "key": settings.youtube_api_key,
                    },
                )
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    stats = item.get("statistics", {})
                    results.append(
                        {
                            "channel": "youtube",
                            "channel_id": item["id"],
                            "name": item.get("snippet", {}).get("title", ""),
                            "country": "KR",
                            "followers": int(stats.get("subscriberCount", 0)),
                            "total_views": int(stats.get("viewCount", 0)),
                        }
                    )
    except Exception as e:
        logger.warning(f"YouTube 수집 실패: {e}")
    return results
