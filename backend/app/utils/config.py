from functools import lru_cache

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
    jwt_secret: str = "change-me"
    google_client_id: str = ""  # 크리에이터 구글 로그인 (GIS ID 토큰 검증용)


@lru_cache
def get_settings() -> Settings:
    return Settings()
