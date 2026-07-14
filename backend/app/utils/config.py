import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./herofinder.db"
    # 프론트엔드 도메인 — CORS 허용 + RFP 이메일의 크리에이터 포털 링크에 사용
    frontend_base_url: str = "http://localhost:3000"

    youtube_api_key: str = ""
    scrapecreators_api_key: str = ""
    tiktok_ttcm_client_id: str = ""
    tiktok_ttcm_client_secret: str = ""
    sendgrid_api_key: str = ""
    anthropic_api_key: str = ""
    # 프로덕션은 반드시 JWT_SECRET env 로 고정값 지정(재시작 간 토큰 유지).
    # 미지정 시 프로세스마다 랜덤 — 공개 리포에 고정 시크릿을 두지 않기 위함(구 "change-me" 제거).
    jwt_secret: str = Field(default_factory=lambda: secrets.token_hex(32))
    # 관리자 API 토큰. 설정 시 /api/admin/* 는 X-Admin-Token 헤더 일치 요구.
    # 프로덕션 배포 전 반드시 설정할 것(미설정 시 개발 편의로 통과).
    admin_api_token: str = ""
    google_client_id: str = ""  # 크리에이터 구글 로그인 (GIS ID 토큰 검증용)


@lru_cache
def get_settings() -> Settings:
    return Settings()
