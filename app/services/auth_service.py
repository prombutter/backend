"""로컬 users / user_identities / workspaces / user_sessions 연동."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.crypto import encrypt_token
from app.security.tokens import (
    create_access_token,
    hash_token,
    new_refresh_token,
    refresh_expires_at,
)


@dataclass
class AuthSessionResult:
    user_id: UUID
    email: str
    name: str
    role: str
    workspace_id: UUID | None
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    is_new_user: bool
    onboarding_completed: bool


async def upsert_google_user_and_session(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    provider_user_id: str,
    provider_access_token: str | None,
    provider_refresh_token: str | None,
    device_info: str | None = None,
) -> AuthSessionResult:
    """
    Google(Supabase OAuth) 로그인:
    - (GOOGLE, provider_user_id) 로 기존 연결 조회
    - 없으면 email 로 users 조회 후 identity 연결 (계정 링크)
    - 둘 다 없으면 users + identity + workspace 생성
    - user_sessions 발급
    """
    enc_at = encrypt_token(provider_access_token)
    enc_rt = encrypt_token(provider_refresh_token)

    row = (
        await session.execute(
            text(
                """
                SELECT u.id, u.email, u.name, u.role::text AS role,
                       u.onboarding_completed_at, i.id AS identity_id
                FROM public.user_identities i
                JOIN public.users u ON u.id = i.user_id
                WHERE i.provider = 'GOOGLE' AND i.provider_user_id = :pid
                """
            ),
            {"pid": provider_user_id},
        )
    ).mappings().first()

    is_new_user = False
    identity_id: UUID | None = None

    if row:
        user_id = row["id"]
        email = str(row["email"])
        name = str(row["name"])
        role = str(row["role"])
        onboarding_completed = row["onboarding_completed_at"] is not None
        identity_id = row["identity_id"]
        await session.execute(
            text(
                """
                UPDATE public.user_identities
                SET access_token = :at, refresh_token = :rt
                WHERE id = :id
                """
            ),
            {"at": enc_at, "rt": enc_rt, "id": identity_id},
        )
        await session.execute(
            text(
                """
                UPDATE public.users
                SET failed_login_count = 0, last_failed_login_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {"id": user_id},
        )
    else:
        existing = (
            await session.execute(
                text(
                    """
                    SELECT id, email, name, role::text AS role, onboarding_completed_at
                    FROM public.users
                    WHERE email = :email
                    """
                ),
                {"email": email},
            )
        ).mappings().first()

        if existing:
            user_id = existing["id"]
            email = str(existing["email"])
            name = str(existing["name"])
            role = str(existing["role"])
            onboarding_completed = existing["onboarding_completed_at"] is not None
            await session.execute(
                text(
                    """
                    INSERT INTO public.user_identities
                        (user_id, provider, provider_user_id, access_token, refresh_token)
                    VALUES
                        (:uid, 'GOOGLE', :pid, :at, :rt)
                    """
                ),
                {"uid": user_id, "pid": provider_user_id, "at": enc_at, "rt": enc_rt},
            )
            await session.execute(
                text(
                    """
                    UPDATE public.users
                    SET email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP),
                        failed_login_count = 0,
                        last_failed_login_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": user_id},
            )
        else:
            is_new_user = True
            onboarding_completed = False
            created = (
                await session.execute(
                    text(
                        """
                        INSERT INTO public.users
                            (email, name, password_hash, role, email_verified_at)
                        VALUES
                            (:email, :name, NULL, 'USER', CURRENT_TIMESTAMP)
                        RETURNING id, email, name, role::text AS role
                        """
                    ),
                    {"email": email, "name": name},
                )
            ).mappings().one()
            user_id = created["id"]
            email = str(created["email"])
            name = str(created["name"])
            role = str(created["role"])
            await session.execute(
                text(
                    """
                    INSERT INTO public.user_identities
                        (user_id, provider, provider_user_id, access_token, refresh_token)
                    VALUES
                        (:uid, 'GOOGLE', :pid, :at, :rt)
                    """
                ),
                {"uid": user_id, "pid": provider_user_id, "at": enc_at, "rt": enc_rt},
            )
    workspace_id = await _workspace_id_for_user(session, user_id)
    if workspace_id is None:
        await session.execute(
            text(
                """
                INSERT INTO public.workspaces (owner_id, name)
                SELECT :uid, '내 워크스페이스'
                WHERE NOT EXISTS (
                    SELECT 1 FROM public.workspaces WHERE owner_id = :uid
                )
                """
            ),
            {"uid": user_id},
        )
        workspace_id = await _workspace_id_for_user(session, user_id)

    raw_refresh = new_refresh_token()
    refresh_hash = hash_token(raw_refresh)
    expires_at = refresh_expires_at()
    sess = (
        await session.execute(
            text(
                """
                INSERT INTO public.user_sessions
                    (user_id, refresh_token_hash, device_info, expires_at)
                VALUES
                    (:uid, :hash, :device, :exp)
                RETURNING id
                """
            ),
            {
                "uid": user_id,
                "hash": refresh_hash,
                "device": device_info,
                "exp": expires_at,
            },
        )
    ).mappings().one()
    session_id = sess["id"]

    access_token, access_exp = create_access_token(
        user_id=user_id,
        email=email,
        role=role,
        session_id=session_id,
    )
    await session.commit()

    return AuthSessionResult(
        user_id=user_id,
        email=email,
        name=name,
        role=role,
        workspace_id=workspace_id,
        access_token=access_token,
        refresh_token=raw_refresh,
        access_token_expires_at=access_exp,
        refresh_token_expires_at=expires_at,
        is_new_user=is_new_user,
        onboarding_completed=onboarding_completed,
    )


async def refresh_session(
    session: AsyncSession,
    *,
    raw_refresh_token: str,
    device_info: str | None = None,
) -> AuthSessionResult:
    token_hash = hash_token(raw_refresh_token)
    row = (
        await session.execute(
            text(
                """
                SELECT s.id AS session_id, s.expires_at, s.revoked_at,
                       u.id AS user_id, u.email, u.name, u.role::text AS role,
                       u.onboarding_completed_at
                FROM public.user_sessions s
                JOIN public.users u ON u.id = s.user_id
                WHERE s.refresh_token_hash = :hash
                """
            ),
            {"hash": token_hash},
        )
    ).mappings().first()
    if not row:
        raise ValueError("Invalid refresh token.")
    if row["revoked_at"] is not None:
        raise ValueError("Refresh token has been revoked.")
    exp = row["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    if exp <= datetime.now(UTC):
        raise ValueError("Refresh token expired.")

    # rotation
    await session.execute(
        text(
            """
            UPDATE public.user_sessions
            SET revoked_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
        ),
        {"id": row["session_id"]},
    )

    user_id = row["user_id"]
    email = str(row["email"])
    name = str(row["name"])
    role = str(row["role"])
    onboarding_completed = row["onboarding_completed_at"] is not None
    workspace_id = await _workspace_id_for_user(session, user_id)

    new_raw = new_refresh_token()
    new_hash = hash_token(new_raw)
    new_exp = refresh_expires_at()
    sess = (
        await session.execute(
            text(
                """
                INSERT INTO public.user_sessions
                    (user_id, refresh_token_hash, device_info, expires_at)
                VALUES
                    (:uid, :hash, :device, :exp)
                RETURNING id
                """
            ),
            {
                "uid": user_id,
                "hash": new_hash,
                "device": device_info,
                "exp": new_exp,
            },
        )
    ).mappings().one()
    access_token, access_exp = create_access_token(
        user_id=user_id,
        email=email,
        role=role,
        session_id=sess["id"],
    )
    await session.commit()
    return AuthSessionResult(
        user_id=user_id,
        email=email,
        name=name,
        role=role,
        workspace_id=workspace_id,
        access_token=access_token,
        refresh_token=new_raw,
        access_token_expires_at=access_exp,
        refresh_token_expires_at=new_exp,
        is_new_user=False,
        onboarding_completed=onboarding_completed,
    )


async def revoke_session(
    session: AsyncSession,
    *,
    session_id: UUID | None = None,
    raw_refresh_token: str | None = None,
) -> None:
    if session_id is not None:
        await session.execute(
            text(
                """
                UPDATE public.user_sessions
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE id = :id AND revoked_at IS NULL
                """
            ),
            {"id": session_id},
        )
    elif raw_refresh_token:
        await session.execute(
            text(
                """
                UPDATE public.user_sessions
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE refresh_token_hash = :hash AND revoked_at IS NULL
                """
            ),
            {"hash": hash_token(raw_refresh_token)},
        )
    await session.commit()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, email, name, role::text AS role,
                       onboarding_completed_at, created_at
                FROM public.users
                WHERE id = :id
                """
            ),
            {"id": user_id},
        )
    ).mappings().first()
    if not row:
        return None
    workspace_id = await _workspace_id_for_user(session, user_id)
    return {
        "id": row["id"],
        "email": str(row["email"]),
        "name": str(row["name"]),
        "role": str(row["role"]),
        "onboarding_completed": row["onboarding_completed_at"] is not None,
        "workspace_id": workspace_id,
        "created_at": row["created_at"],
    }


async def _workspace_id_for_user(session: AsyncSession, user_id: UUID) -> UUID | None:
    row = (
        await session.execute(
            text("SELECT id FROM public.workspaces WHERE owner_id = :uid LIMIT 1"),
            {"uid": user_id},
        )
    ).first()
    return row[0] if row else None
