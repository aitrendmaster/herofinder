"""YouTube Data API v3 수집기 (KR).

시드 채널 리스트 기반 주간 스냅샷 수집. 일 쿼터 10,000 유닛 — channels.list는 1유닛/호출.
YOUTUBE_API_KEY 미설정 시 빈 결과 반환 (파이프라인은 계속 진행).
"""

import httpx
from loguru import logger

from ...utils.config import get_settings

API_BASE = "https://www.googleapis.com/youtube/v3"


async def collect_recent_video_stats(channel_id: str) -> dict:
    """최근 업로드 10개 기반 지표 — 최근 30일 조회수 합계 + 참여율.

    uploads 재생목록 ID는 UC→UU 치환으로 조회 (추가 쿼터 소모 없음).
    반환: {"monthly_views": int, "engagement_rate": float}  (실패 시 0)
    """
    from datetime import datetime, timedelta, timezone

    settings = get_settings()
    empty = {"monthly_views": 0, "engagement_rate": 0.0}
    if not settings.youtube_api_key or not channel_id.startswith("UC"):
        return empty
    uploads_playlist = "UU" + channel_id[2:]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{API_BASE}/playlistItems",
                params={
                    "part": "contentDetails",
                    "playlistId": uploads_playlist,
                    "maxResults": 10,
                    "key": settings.youtube_api_key,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            video_ids = [i["contentDetails"]["videoId"] for i in items]
            if not video_ids:
                return empty

            resp = await client.get(
                f"{API_BASE}/videos",
                params={
                    "part": "statistics,snippet",
                    "id": ",".join(video_ids),
                    "key": settings.youtube_api_key,
                },
            )
            resp.raise_for_status()
            videos = resp.json().get("items", [])

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        monthly_views = 0
        total_views = total_reactions = 0
        for v in videos:
            stats = v.get("statistics", {})
            views = int(stats.get("viewCount", 0))
            published = datetime.fromisoformat(
                v["snippet"]["publishedAt"].replace("Z", "+00:00")
            )
            if published >= cutoff:
                monthly_views += views
            total_views += views
            total_reactions += int(stats.get("likeCount", 0)) + int(stats.get("commentCount", 0))

        engagement = round(total_reactions / total_views * 100, 2) if total_views else 0.0
        # 최근 30일 업로드가 없으면 최근작 평균으로 근사
        if monthly_views == 0 and videos:
            monthly_views = total_views // len(videos)
        return {"monthly_views": monthly_views, "engagement_rate": engagement}
    except Exception as e:
        logger.warning(f"YouTube 최근 영상 지표 수집 실패 ({channel_id}): {e}")
        return empty


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
