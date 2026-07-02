"""RFP 이메일 발송 서비스 (SendGrid).

SENDGRID_API_KEY 미설정 시 실제 발송 없이 로그만 남긴다 (개발 모드).
"""

import httpx
from loguru import logger

from ..utils.config import get_settings

SENDGRID_SEND_URL = "https://api.sendgrid.com/v3/mail/send"
FROM_EMAIL = "rfp@herofinder.example.com"  # SendGrid 도메인 인증 후 실제 주소로 교체


def mask_email(email: str) -> str:
    """개인정보 보호 — 응답에는 마스킹된 이메일만 노출."""
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


async def send_rfp_email(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.sendgrid_api_key:
        logger.info(f"[DEV] SendGrid 미설정 — 발송 시뮬레이션: {mask_email(to_email)} / {subject}")
        return True
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                SENDGRID_SEND_URL,
                headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": FROM_EMAIL},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
            )
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"SendGrid 발송 실패 ({mask_email(to_email)}): {e}")
        return False
