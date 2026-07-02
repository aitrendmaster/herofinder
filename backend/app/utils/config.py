from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./herofinder.db"

    youtube_api_key: str = ""
    scrapecreators_api_key: str = ""
    tiktok_ttcm_client_id: str = ""
    tiktok_ttcm_client_secret: str = ""
    sendgrid_api_key: str = ""
    anthropic_api_key: str = ""
    jwt_secret: str = "change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
