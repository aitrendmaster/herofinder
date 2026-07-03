"""ScrapeCreators 수집기 — Instagram (KR), TikTok (KR/US/SEA).

주간 수집 비용: Instagram 1크레딧/명 (프로필에 최근 12개 게시물 지표 포함),
TikTok 2크레딧/명 (프로필 + 최근 영상 10개).
TikTok은 TTCM Open API 파트너 승인 시 공식 API로 전환 예정.
SCRAPECREATORS_API_KEY 미설정 시 None 반환 (파이프라인은 해당 채널 스킵).
"""

import time
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger

from ...utils.config import get_settings

API_BASE = "https://api.scrapecreators.com"


async def _get(client: httpx.AsyncClient, path: str, **params) -> dict | None:
    settings = get_settings()
    if not settings.scrapecreators_api_key:
        logger.warning("SCRAPECREATORS_API_KEY 미설정 — 수집 건너뜀")
        return None
    try:
        resp = await client.get(
            f"{API_BASE}{path}",
            params=params,
            headers={"x-api-key": settings.scrapecreators_api_key},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"ScrapeCreators 호출 실패 {path} ({params}): {e}")
        return None


async def collect_instagram_stats(handle: str) -> dict | None:
    """프로필 1콜 — 팔로워 + 최근 12개 게시물 기반 30일 조회수·참여율."""
    async with httpx.AsyncClient(timeout=60) as client:
        d = await _get(client, "/v1/instagram/profile", handle=handle)
    if not d:
        return None
    user = (d.get("data") or {}).get("user") or {}
    followers = int((user.get("edge_followed_by") or {}).get("count") or 0)
    if followers == 0:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    edges = (user.get("edge_owner_to_timeline_media") or {}).get("edges") or []
    monthly_views = 0
    reactions = 0
    for e in edges:
        n = e.get("node") or {}
        likes = int(
            ((n.get("edge_liked_by") or {}).get("count"))
            or ((n.get("edge_media_preview_like") or {}).get("count"))
            or 0
        )
        comments = int((n.get("edge_media_to_comment") or {}).get("count") or 0)
        reactions += max(likes, 0) + comments
        ts = n.get("taken_at_timestamp")
        if n.get("is_video") and ts and datetime.fromtimestamp(ts, timezone.utc) >= cutoff:
            monthly_views += int(n.get("video_view_count") or 0)

    # IG 표준 참여율: 게시물당 평균 반응 / 팔로워 × 100
    engagement = round(reactions / len(edges) / followers * 100, 2) if edges else 0.0
    return {
        "name": user.get("full_name") or handle,
        "followers": followers,
        "monthly_views": monthly_views,
        "engagement_rate": engagement,
    }


async def collect_tiktok_stats(handle: str) -> dict | None:
    """프로필 + 최근 영상 10개 (2콜) — 팔로워 + 30일 재생수·참여율."""
    async with httpx.AsyncClient(timeout=60) as client:
        prof = await _get(client, "/v1/tiktok/profile", handle=handle)
        vids = await _get(client, "/v3/tiktok/profile/videos", handle=handle)
    if not prof:
        return None
    user = prof.get("user") or {}
    stats = prof.get("statsV2") or prof.get("stats") or {}
    followers = int(stats.get("followerCount") or 0)
    if followers == 0:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    monthly_views = total_plays = total_reactions = 0
    videos = (vids or {}).get("aweme_list") or []
    for v in videos:
        s = v.get("statistics") or {}
        plays = int(s.get("play_count") or 0)
        total_plays += plays
        total_reactions += (
            int(s.get("digg_count") or 0)
            + int(s.get("comment_count") or 0)
            + int(s.get("share_count") or 0)
        )
        ct = v.get("create_time")
        if ct and datetime.fromtimestamp(ct, timezone.utc) >= cutoff:
            monthly_views += plays

    engagement = round(total_reactions / total_plays * 100, 2) if total_plays else 0.0
    if monthly_views == 0 and videos:
        monthly_views = total_plays // len(videos)
    return {
        "name": user.get("nickname") or handle,
        "followers": followers,
        "monthly_views": monthly_views,
        "engagement_rate": engagement,
    }
