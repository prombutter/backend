"""Supabase OAuth + 앱 세션 엔드포인트."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlencode
from uuid import UUID

import jwt
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.schemas.auth import (
    LogoutRequest,
    OAuthStartResponse,
    RefreshRequest,
    SupabaseTokenExchangeRequest,
    TokenResponse,
    UserPublic,
)
from app.security.tokens import create_oauth_state, decode_access_token, decode_oauth_state
from app.services import auth_service
from app.services.supabase_auth import (
    SupabaseAuthError,
    build_authorize_url,
    exchange_code_for_session,
    extract_google_profile,
    generate_pkce_pair,
    get_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "pb_oauth_state"
SUPPORTED_PROVIDERS = {"google"}


def _token_response(result: auth_service.AuthSessionResult) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        expires_at=result.access_token_expires_at,
        refresh_expires_at=result.refresh_token_expires_at,
        is_new_user=result.is_new_user,
        user=UserPublic(
            id=result.user_id,
            email=result.email,
            name=result.name,
            role=result.role,
            workspace_id=result.workspace_id,
            onboarding_completed=result.onboarding_completed,
        ),
    )


def _set_oauth_cookie(response: Response, state_jwt: str) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state_jwt,
        httponly=True,
        secure=settings.is_production_like,
        samesite="lax",
        max_age=600,
        path="/auth",
    )


def _clear_oauth_cookie(response: Response) -> None:
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path="/auth")


def _frontend_redirect_allowed(url: str) -> bool:
    allowed = settings.oauth_frontend_redirect_list
    if not allowed:
        return True
    return any(url == a or url.startswith(a.rstrip("/") + "/") for a in allowed)


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    session: SessionDep,
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> Response:
    """
    Supabase → 백엔드 콜백.
    code 교환 후 앱 세션 발급 → FE redirect_uri 해시 프래그먼트로 토큰 전달.
    """
    if error:
        detail = error_description or error
        raise HTTPException(status_code=400, detail=f"OAuth error: {detail}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    state_jwt = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state_jwt:
        raise HTTPException(status_code=400, detail="Missing OAuth state cookie; restart login")
    try:
        state = decode_oauth_state(state_jwt)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc
    if state.get("typ") != "oauth_state":
        raise HTTPException(status_code=400, detail="Invalid OAuth state type")

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
        result = await auth_service.upsert_google_user_and_session(
            session,
            email=profile["email"],
            name=profile["name"],
            provider_user_id=profile["provider_user_id"],
            provider_access_token=sb_session.get("provider_token") or sb_session.get("access_token"),
            provider_refresh_token=sb_session.get("provider_refresh_token")
            or sb_session.get("refresh_token"),
            device_info=request.headers.get("user-agent"),
        )
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code or 502,
            detail={"message": str(exc), "supabase": exc.detail},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to complete OAuth login: {exc}") from exc

    params = urlencode(
        {
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": "bearer",
            "is_new_user": "true" if result.is_new_user else "false",
            "provider": provider,
        }
    )
    dest = f"{frontend}#{params}" if "#" not in frontend else f"{frontend}&{params}"
    resp = RedirectResponse(url=dest, status_code=status.HTTP_302_FOUND)
    _clear_oauth_cookie(resp)
    return resp


@router.get("/oauth/{provider}", response_model=OAuthStartResponse)
async def oauth_start(
    provider: Literal["google"],
    response: Response,
    redirect_uri: str | None = Query(
        default=None,
        description="로그인 성공 후 FE 로 돌아갈 URL (미지정 시 OAUTH_FRONTEND_REDIRECT)",
    ),
) -> OAuthStartResponse:
    """Supabase Auth Google OAuth 시작 (PKCE). authorize_url + state 쿠키 설정."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not settings.supabase_configured_for_oauth:
        raise HTTPException(
            status_code=503,
            detail="Supabase OAuth is not configured (SUPABASE_URL / SUPABASE_ANON_KEY).",
        )

    frontend = (redirect_uri or settings.oauth_frontend_redirect).strip()
    if not frontend:
        raise HTTPException(status_code=400, detail="redirect_uri (or OAUTH_FRONTEND_REDIRECT) required")
    if not _frontend_redirect_allowed(frontend):
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
            redirect_to=settings.oauth_callback_url.rstrip("/"),
            code_challenge=challenge,
            scopes="email profile openid",
        )
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code or 503, detail=str(exc)) from exc

    _set_oauth_cookie(response, state_jwt)
    return OAuthStartResponse(authorize_url=authorize_url, provider=provider)


@router.get("/oauth/{provider}/redirect")
async def oauth_start_redirect(
    provider: Literal["google"],
    redirect_uri: str | None = Query(default=None),
) -> RedirectResponse:
    """브라우저 전용: 곧바로 Supabase authorize 로 302."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not settings.supabase_configured_for_oauth:
        raise HTTPException(status_code=503, detail="Supabase OAuth is not configured")

    frontend = (redirect_uri or settings.oauth_frontend_redirect).strip()
    if not frontend or not _frontend_redirect_allowed(frontend):
        raise HTTPException(status_code=400, detail="redirect_uri is not allowed")

    verifier, challenge = generate_pkce_pair()
    state_jwt = create_oauth_state(
        code_verifier=verifier,
        provider=provider,
        frontend_redirect=frontend,
    )
    authorize_url = build_authorize_url(
        provider=provider,
        redirect_to=settings.oauth_callback_url.rstrip("/"),
        code_challenge=challenge,
        scopes="email profile openid",
    )
    resp = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    _set_oauth_cookie(resp, state_jwt)
    return resp


@router.post("/oauth/supabase", response_model=TokenResponse)
async def exchange_supabase_token(
    body: SupabaseTokenExchangeRequest,
    request: Request,
    session: SessionDep,
) -> TokenResponse:
    """
    FE 가 Supabase JS SDK 로 OAuth 완료 후 받은 access_token 을
    PromButter 앱 세션(JWT + refresh)으로 교환.
    """
    if not settings.supabase_configured_for_oauth:
        raise HTTPException(status_code=503, detail="Supabase OAuth is not configured")
    try:
        sb_user = await get_user(body.access_token)
        profile = extract_google_profile(sb_user)
        result = await auth_service.upsert_google_user_and_session(
            session,
            email=profile["email"],
            name=profile["name"],
            provider_user_id=profile["provider_user_id"],
            provider_access_token=body.provider_token or body.access_token,
            provider_refresh_token=body.provider_refresh_token or body.refresh_token,
            device_info=body.device_info or request.headers.get("user-agent"),
        )
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code or 401,
            detail={"message": str(exc), "supabase": exc.detail},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {exc}") from exc
    return _token_response(result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request, session: SessionDep) -> TokenResponse:
    try:
        result = await auth_service.refresh_session(
            session,
            raw_refresh_token=body.refresh_token,
            device_info=body.device_info or request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return _token_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    session: SessionDep,
    body: LogoutRequest | None = None,
) -> Response:
    """세션 폐기. Authorization Bearer 및/또는 body.refresh_token."""
    session_id: UUID | None = None
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_access_token(auth.split(" ", 1)[1])
            session_id = UUID(str(payload["sid"]))
        except Exception:  # noqa: BLE001
            session_id = None

    raw_refresh = body.refresh_token if body else None
    if session_id is None and not raw_refresh:
        raise HTTPException(status_code=400, detail="Bearer token or refresh_token required")
    await auth_service.revoke_session(
        session,
        session_id=session_id,
        raw_refresh_token=raw_refresh,
    )
    return Response(status_code=204)


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        workspace_id=user.get("workspace_id"),
        onboarding_completed=bool(user.get("onboarding_completed")),
    )
