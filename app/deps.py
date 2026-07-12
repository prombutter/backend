"""
FastAPI 의존성 — PB-67 / PB-72

get_current_user: 보호된 엔드포인트(me, workspaces 등) 앞에 두는 인증 검문소.
access 토큰을 HttpOnly 쿠키에서 읽어 검증 → User 반환. 실패 시 401.
get_current_workspace: 현재 유저의 워크스페이스(1:1) 반환. 프롬프트 등 스코프 기준.

위치: app/deps.py
"""

import uuid

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import ACCESS_COOKIE
from app.core.errors import AppError
from app.core.security import ACCESS, decode_token
from app.db import get_session
from app.models import User, Workspace

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise _UNAUTHORIZED
    try:
        payload = decode_token(token)  # 서명/만료 검증, 실패 시 JWTError
    except JWTError:
        raise _UNAUTHORIZED
    if payload.get("type") != ACCESS:  # refresh 토큰으로 API 호출 차단
        raise _UNAUTHORIZED
    sub = payload.get("sub")
    if not sub:
        raise _UNAUTHORIZED
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise _UNAUTHORIZED
    user = await session.get(User, user_id)
    if user is None:
        raise _UNAUTHORIZED
    return user


async def get_current_workspace(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workspace:
    """현재 유저의 워크스페이스(가입 시 자동 생성, 1:1). 프롬프트 스코프 기준."""
    ws = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if ws is None:  # 정상 흐름에선 발생 안 함(가입 시 자동 생성)
        raise AppError(
            status.HTTP_404_NOT_FOUND, "ERR-WORKSPACE-NOT-FOUND", "워크스페이스를 찾을 수 없어요."
        )
    return ws
