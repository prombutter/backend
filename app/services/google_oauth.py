"""Google(Supabase OAuth) 로그인 → ORM users / user_identities / workspaces 업서트."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthProvider, User, UserIdentity, Workspace
from app.security.crypto import encrypt_token


async def upsert_google_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    provider_user_id: str,
    provider_access_token: str | None = None,
    provider_refresh_token: str | None = None,
) -> tuple[User, bool]:
    """
    Returns (user, is_new_user).
    - GOOGLE identity 있으면 토큰 갱신
    - 동일 email 있으면 GOOGLE identity 연결
    - 없으면 users + identity + workspace 생성
    """
    enc_at = encrypt_token(provider_access_token)
    enc_rt = encrypt_token(provider_refresh_token)
    now = datetime.now(timezone.utc)

    identity = await session.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == AuthProvider.GOOGLE,
            UserIdentity.provider_user_id == provider_user_id,
        )
    )
    if identity is not None:
        user = await session.get(User, identity.user_id)
        if user is None:
            raise RuntimeError("user_identities.user_id orphan")
        identity.access_token = enc_at
        identity.refresh_token = enc_rt
        user.failed_login_count = 0
        user.last_failed_login_at = None
        user.updated_at = now
        await _ensure_workspace(session, user)
        await session.flush()
        return user, False

    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        session.add(
            UserIdentity(
                user_id=existing.id,
                provider=AuthProvider.GOOGLE,
                provider_user_id=provider_user_id,
                access_token=enc_at,
                refresh_token=enc_rt,
            )
        )
        if existing.email_verified_at is None:
            existing.email_verified_at = now
        existing.failed_login_count = 0
        existing.last_failed_login_at = None
        existing.updated_at = now
        await _ensure_workspace(session, existing)
        await session.flush()
        return existing, False

    user = User(
        email=email,
        name=name,
        password_hash=None,
        email_verified_at=now,
    )
    session.add(user)
    await session.flush()
    session.add(
        UserIdentity(
            user_id=user.id,
            provider=AuthProvider.GOOGLE,
            provider_user_id=provider_user_id,
            access_token=enc_at,
            refresh_token=enc_rt,
        )
    )
    session.add(Workspace(owner_id=user.id, name="내 워크스페이스"))
    await session.flush()
    return user, True


async def _ensure_workspace(session: AsyncSession, user: User) -> None:
    ws = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if ws is None:
        session.add(Workspace(owner_id=user.id, name="내 워크스페이스"))
