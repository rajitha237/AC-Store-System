from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.ipv4_resolver import (
    build_neon_async_creator,
)

settings = get_settings()

async_creator = build_neon_async_creator(
    settings.database_url,
)

engine_options = {
    "echo": (
        settings.debug
        and not settings.is_production
    ),
    "pool_pre_ping": True,
}

if async_creator is not None:
    engine_options[
        "async_creator"
    ] = async_creator

engine = create_async_engine(
    settings.database_url,
    **engine_options,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
