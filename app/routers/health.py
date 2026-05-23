from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db-ping")
async def db_ping(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    result = await session.execute(text("SELECT 1 AS value"))
    return {"db": "ok", "value": result.scalar_one()}
