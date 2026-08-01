from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy.pool import StaticPool
from app.core.config import settings

connect_args = {}
engine_kwargs = {}
if "sqlite" not in settings.DATABASE_URL:
    connect_args["statement_cache_size"] = 0
elif ":memory:" in settings.DATABASE_URL:
    engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
    **engine_kwargs,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
