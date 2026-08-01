"""Supabase Google OAuth — 원격 auth 세션(쿠키 AT/RT)과 연동."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cookies import set_auth_cookies
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.db import get_session
from app.models import User, UserSession, Workspace
from app.schemas import UserResponse
from app.security.oauth_state import create_oauth_state, decode_oauth_state
from app.services.google_oauth import upsert_google_user
from app.services.supabase_auth import (
    SupabaseAuthError,
    build_authorize_url,
    exchange_code_for_session,
    extract_google_profile,
    generate_pkce_pair,
    get_user,
)

router = APIRouter(prefix="/auth", tags=["auth-oauth"])

OAUTH_STATE_COOKIE = "pb_oauth_state"
SUPPORTED = {"google"}


class OAuthStartResponse(BaseModel):
    authorize_url: str
    provider: str


class SupabaseExchangeRequest(BaseModel):
    access_token: str = Field(min_length=20)
    refresh_token: str | None = None
    provider_token: str | None = None
    provider_refresh_token: str | None = None


class OAuthTokenResponse(BaseModel):
    """FE SDK 교환용 — 쿠키도 함께 심는다."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool
    user: UserResponse


def _frontend_allowed(url: str) -> bool:
    allowed = settings.oauth_frontend_redirect_list
    return any(url == a or url.startswith(a.rstrip("/") + "/") for a in allowed)


def _set_state_cookie(response: Response, state_jwt: str) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state_jwt,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/auth",
    )


async def _issue_session(session: AsyncSession, user: User, response: Response) -> tuple[str, str]:
    ws = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    workspace_id = str(ws.id) if ws else None
    access_token = create_access_token(str(user.id), workspace_id=workspace_id)
    refresh_token, _jti = create_refresh_token(str(user.id), workspace_id=workspace_id)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    session.add(
        UserSession(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=expires_at,
        )
    )
    set_auth_cookies(response, access_token, refresh_token)
    return access_token, refresh_token


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> Response:
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error_description or error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    state_jwt = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state_jwt:
        raise HTTPException(status_code=400, detail="Missing OAuth state cookie; restart login")
    try:
        state = decode_oauth_state(state_jwt)
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc

    code_verifier = str(state["cv"])
    frontend = str(state["redirect"])
    provider = str(state.get("provider") or "google")

    try:
        sb_session = await exchange_code_for_session(
            auth_code=code,
            code_verifier=code_verifier,
        )
        sb_user = sb_session.get("user") or await get_user(sb_session["access_token"])
        profile = extract_google_profile(sb_user)
        user, is_new = await upsert_google_user(
            session,
            email=profile["email"],
            name=profile["name"],
            provider_user_id=profile["provider_user_id"],
            provider_access_token=sb_session.get("provider_token") or sb_session.get("access_token"),
            provider_refresh_token=sb_session.get("provider_refresh_token")
            or sb_session.get("refresh_token"),
        )
        access_token, refresh_token = await _issue_session(session, user, response)
        await session.commit()
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code or 502,
            detail={"message": str(exc), "supabase": exc.detail},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to complete OAuth login: {exc}") from exc

    params = urlencode(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "is_new_user": "true" if is_new else "false",
            "provider": provider,
        }
    )
    dest = f"{frontend}#{params}" if "#" not in frontend else f"{frontend}&{params}"
    resp = RedirectResponse(url=dest, status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(OAUTH_STATE_COOKIE, path="/auth")
    # redirect response needs cookies from set_auth_cookies on same Response
    # re-apply on redirect response
    set_auth_cookies(resp, access_token, refresh_token)
    return resp


@router.get("/oauth/{provider}", response_model=OAuthStartResponse)
async def oauth_start(
    provider: Literal["google"],
    response: Response,
    redirect_uri: str | None = Query(default=None),
) -> OAuthStartResponse:
    if provider not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not settings.supabase_oauth_ready:
        raise HTTPException(status_code=503, detail="Supabase OAuth is not configured")

    frontend = (redirect_uri or settings.OAUTH_FRONTEND_REDIRECT).strip()
    if not frontend or not _frontend_allowed(frontend):
        raise HTTPException(status_code=400, detail="redirect_uri is not allowed")

    verifier, challenge = generate_pkce_pair()
    state_jwt = create_oauth_state(
        code_verifier=verifier,
        provider=provider,
        frontend_redirect=frontend,
    )
    try:
        authorize_url = build_authorize_url(
            provider=provider,
            redirect_to=settings.OAUTH_CALLBACK_URL.rstrip("/"),
            code_challenge=challenge,
            scopes="email profile openid",
        )
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code or 503, detail=str(exc)) from exc

    _set_state_cookie(response, state_jwt)
    return OAuthStartResponse(authorize_url=authorize_url, provider=provider)


@router.get("/oauth/{provider}/redirect")
async def oauth_start_redirect(
    provider: Literal["google"],
    redirect_uri: str | None = Query(default=None),
) -> RedirectResponse:
    if provider not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not settings.supabase_oauth_ready:
        raise HTTPException(status_code=503, detail="Supabase OAuth is not configured")

    frontend = (redirect_uri or settings.OAUTH_FRONTEND_REDIRECT).strip()
    if not frontend or not _frontend_allowed(frontend):
        raise HTTPException(status_code=400, detail="redirect_uri is not allowed")

    verifier, challenge = generate_pkce_pair()
    state_jwt = create_oauth_state(
        code_verifier=verifier,
        provider=provider,
        frontend_redirect=frontend,
    )
    authorize_url = build_authorize_url(
        provider=provider,
        redirect_to=settings.OAUTH_CALLBACK_URL.rstrip("/"),
        code_challenge=challenge,
        scopes="email profile openid",
    )
    resp = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    _set_state_cookie(resp, state_jwt)
    return resp


@router.post("/oauth/supabase", response_model=OAuthTokenResponse)
async def exchange_supabase_token(
    body: SupabaseExchangeRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> OAuthTokenResponse:
    if not settings.supabase_oauth_ready:
        raise HTTPException(status_code=503, detail="Supabase OAuth is not configured")
    try:
        sb_user = await get_user(body.access_token)
        profile = extract_google_profile(sb_user)
        user, is_new = await upsert_google_user(
            session,
            email=profile["email"],
            name=profile["name"],
            provider_user_id=profile["provider_user_id"],
            provider_access_token=body.provider_token or body.access_token,
            provider_refresh_token=body.provider_refresh_token or body.refresh_token,
        )
        access_token, refresh_token = await _issue_session(session, user, response)
        await session.commit()
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code or 401,
            detail={"message": str(exc), "supabase": exc.detail},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {exc}") from exc

    return OAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=is_new,
        user=UserResponse.model_validate(user),
    )
