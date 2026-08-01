"""OAuth PKCE state 쿠키용 단기 JWT (python-jose / SECRET_KEY)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

_OAUTH_STATE_TYP = "oauth_state"


def create_oauth_state(*, code_verifier: str, provider: str, frontend_redirect: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "cv": code_verifier,
        "provider": provider,
        "redirect": frontend_redirect,
        "nonce": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "typ": _OAUTH_STATE_TYP,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_oauth_state(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("typ") != _OAUTH_STATE_TYP:
        raise JWTError("invalid oauth state type")
    return payload
