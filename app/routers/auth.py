"""
인증 라우터 — PB-67

POST /auth/signup · /auth/login · /auth/refresh · /auth/logout
GET  /auth/me

골격 단계: 라우터/스키마/시그니처만. 본문은 ②(signup) ③(login/refresh/logout/me)에서 채운다.
위치: app/routers/auth.py
"""

import ipaddress
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.security import (
    REFRESH,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_email,
    hash_password,
    hash_token,
    verify_password,
)
from app.db import get_session
from app.deps import get_current_user
from app.models import LoginAttempt, User, UserSession, Workspace
from app.schemas import LoginRequest, SignupRequest, UserResponse, ForgotPasswordRequest, ResetPasswordRequest

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
)


def _client_ip(request: Request) -> str | None:
    """유효한 IP면 반환, 아니면 None (login_attempts.ip_address는 INET 타입)."""
    host = request.client.host if request.client else None
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        return None

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_session(session: AsyncSession, user: User, response: Response) -> None:
    """AT/RT 발급 → user_sessions에 RT 해시 저장 → 쿠키 심기. signup/login 공용."""
    # 유저의 기본 워크스페이스 조회 (존재 시 토큰에 포함)
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


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    # 1. 이메일 중복 체크 (email은 citext라 대소문자 무시)
    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # 2. User 생성 (name 미입력 시 이메일 앞부분으로 — 잠정, 기획 확인 중)
    name = body.name or body.email.split("@")[0]
    user = User(email=body.email, name=name, password_hash=hash_password(body.password))
    session.add(user)
    await session.flush()  # user.id 확보 (commit 전)

    # 3. 워크스페이스 자동 생성 (1:1 — 이미 있으면 새로 안 만듦)
    #    이름은 "{유저 이름}의 워크스페이스" (인증 명세 1.4)
    ws = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if ws is None:
        session.add(Workspace(owner_id=user.id, name=f"{name}의 워크스페이스"))

    # 4. 토큰 발급 + 세션 저장 + 쿠키
    await _issue_session(session, user, response)

    # 5. 한 번에 커밋 (1~4 중 하나라도 실패 시 전체 롤백)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.scalar(select(User).where(User.email == body.email))
    ip = _client_ip(request)
    email_hash = hash_email(body.email)

    # 유저 없음 OR 비번 불일치 → 동일한 401 (계정 존재 여부 노출 방지)
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        session.add(LoginAttempt(ip_address=ip, success=False, email_hash=email_hash))
        if user is not None:
            user.failed_login_count += 1
            user.last_failed_login_at = datetime.now(timezone.utc)
        await session.commit()
        raise _INVALID_CREDENTIALS

    # 성공
    session.add(LoginAttempt(ip_address=ip, success=True, email_hash=email_hash))
    user.failed_login_count = 0
    await _issue_session(session, user, response)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise _INVALID_CREDENTIALS
    try:
        payload = decode_token(token)
    except JWTError:
        raise _INVALID_CREDENTIALS
    if payload.get("type") != REFRESH:
        raise _INVALID_CREDENTIALS

    # 해당 refresh 세션 찾기 (해시로 조회)
    old = await session.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == hash_token(token))
    )
    now = datetime.now(timezone.utc)
    # 세션 없음 / 이미 폐기됨 / 만료 → 거부 (재사용 공격 방어)
    if old is None or old.revoked_at is not None or old.expires_at <= now:
        raise _INVALID_CREDENTIALS

    # 회전: 헌 세션 폐기 → 새 토큰/세션 발급
    old.revoked_at = now
    user = await session.get(User, old.user_id)
    if user is None:
        raise _INVALID_CREDENTIALS
    await _issue_session(session, user, response)
    await session.commit()
    return {"detail": "refreshed"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        sess = await session.scalar(
            select(UserSession).where(UserSession.refresh_token_hash == hash_token(token))
        )
        if sess is not None and sess.revoked_at is None:
            sess.revoked_at = datetime.now(timezone.utc)
            await session.commit()
    clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user

import logging
logger = logging.getLogger(__name__)

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await session.scalar(select(User).where(User.email == body.email))
    if not user:
        return {"detail": "If your email is registered, you will receive a password reset link."}
        
    # 임시 토큰 발급 (10분 만료)
    reset_token = _create_token(str(user.id), "reset_password", 10)
    
    # 콘솔에 출력 (이메일 발송 대체)
    logger.info(f"Password reset requested for {user.email}. Token: {reset_token}")
    print(f"=====================================")
    print(f"Password Reset Token for {user.email}")
    print(f"Token: {reset_token}")
    print(f"=====================================")
    
    return {"detail": "If your email is registered, you will receive a password reset link."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        payload = decode_token(body.token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    if payload.get("type") != "reset_password":
        raise HTTPException(status_code=400, detail="Invalid token type")
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token payload")
        
    import uuid
    user = await session.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = hash_password(body.new_password)
    await session.commit()
    
    return {"detail": "Password has been successfully reset."}
