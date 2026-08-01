"""Supabase Auth (GoTrue) — Google OAuth PKCE / user 조회."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings


class SupabaseAuthError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


def _require_supabase() -> None:
    if not settings.supabase_oauth_ready:
        raise SupabaseAuthError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set for OAuth.",
            status_code=503,
        )


def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorize_url(
    *,
    provider: str,
    redirect_to: str,
    code_challenge: str,
    scopes: str | None = None,
) -> str:
    _require_supabase()
    params: dict[str, str] = {
        "provider": provider,
        "redirect_to": redirect_to,
        "code_challenge": code_challenge,
        "code_challenge_method": "s256",
    }
    if scopes:
        params["scopes"] = scopes
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/auth/v1/authorize?{urlencode(params)}"


def _headers() -> dict[str, str]:
    key = settings.SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def exchange_code_for_session(*, auth_code: str, code_verifier: str) -> dict[str, Any]:
    _require_supabase()
    base = settings.SUPABASE_URL.rstrip("/")
    url = f"{base}/auth/v1/token?grant_type=pkce"
    payload = {"auth_code": auth_code, "code_verifier": code_verifier}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, headers=_headers(), json=payload)
    if resp.status_code >= 400:
        raise SupabaseAuthError(
            "Failed to exchange OAuth code with Supabase.",
            status_code=resp.status_code,
            detail=_safe_json(resp),
        )
    data = resp.json()
    if not data.get("access_token"):
        raise SupabaseAuthError("Supabase token response missing access_token.", detail=data)
    return data


async def get_user(access_token: str) -> dict[str, Any]:
    _require_supabase()
    base = settings.SUPABASE_URL.rstrip("/")
    url = f"{base}/auth/v1/user"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code >= 400:
        raise SupabaseAuthError(
            "Invalid or expired Supabase access token.",
            status_code=resp.status_code,
            detail=_safe_json(resp),
        )
    return resp.json()


def extract_google_profile(supabase_user: dict[str, Any]) -> dict[str, str]:
    email = (supabase_user.get("email") or "").strip().lower()
    meta = supabase_user.get("user_metadata") or {}
    name = (meta.get("full_name") or meta.get("name") or meta.get("preferred_username") or "").strip()
    if not name and email:
        name = email.split("@", 1)[0]
    if not name:
        name = "User"

    google_identity = None
    for identity in supabase_user.get("identities") or []:
        if identity.get("provider") == "google":
            google_identity = identity
            break
    if google_identity is None:
        if (supabase_user.get("app_metadata") or {}).get("provider") != "google":
            raise SupabaseAuthError(
                "Supabase user is not linked to Google. Use Google OAuth provider.",
                status_code=400,
            )

    provider_user_id = str(supabase_user.get("id") or "")
    if google_identity is not None:
        data = google_identity.get("identity_data") or {}
        provider_user_id = str(data.get("sub") or google_identity.get("id") or provider_user_id)
        if not email:
            email = (data.get("email") or "").strip().lower()
        if name == "User":
            name = (data.get("full_name") or data.get("name") or name).strip() or name

    if not email:
        raise SupabaseAuthError(
            "OAuth user has no email; enable email scope for Google.",
            status_code=400,
        )
    if not provider_user_id:
        raise SupabaseAuthError("OAuth user missing provider id.", status_code=400)

    return {
        "email": email,
        "name": name[:100],
        "provider_user_id": provider_user_id,
        "supabase_user_id": str(supabase_user.get("id") or ""),
    }


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text
