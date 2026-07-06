from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .utils.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


# create_all은 기존 테이블에 컬럼을 추가하지 못하므로, 추가된 컬럼은 여기서 보정한다.
# (정식 Alembic 마이그레이션 도입 전의 경량 방식 — 컬럼별 try/except로 멱등)
_LIGHT_MIGRATIONS = [
    "ALTER TABLE creator_accounts ADD COLUMN google_sub VARCHAR(64)",
    "ALTER TABLE creator_accounts ADD COLUMN bio TEXT",
    "ALTER TABLE creator_accounts ADD COLUMN preferred_format VARCHAR(20)",
    "ALTER TABLE creator_accounts ADD COLUMN preferred_length_minutes INTEGER",
    "ALTER TABLE creator_accounts ADD COLUMN available BOOLEAN DEFAULT TRUE",
]


async def init_db() -> None:
    from sqlalchemy import text

    from .models import orm_models  # noqa: F401 — 테이블 등록

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    for stmt in _LIGHT_MIGRATIONS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception:
            pass  # 이미 존재하는 컬럼
