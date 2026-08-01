"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.security.tokens import decode_access_token
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc
    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = UUID(str(payload["sub"]))
    session_id = UUID(str(payload["sid"]))
    user = await auth_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # 세션 폐기 여부 확인
    from sqlalchemy import text

    row = (
        await session.execute(
            text(
                """
                SELECT revoked_at, expires_at
                FROM public.user_sessions
                WHERE id = :id AND user_id = :uid
                """
            ),
            {"id": session_id, "uid": user_id},
        )
    ).mappings().first()
    if not row or row["revoked_at"] is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")

    user["session_id"] = session_id
    return user


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
