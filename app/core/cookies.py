"""
인증 쿠키 헬퍼 — PB-67

AT(access)/RT(refresh)를 HttpOnly 쿠키로 주고받는다.
- HttpOnly: JS에서 접근 불가 → XSS로 토큰 탈취 방어
- 로컬 개발은 http라 secure=False. 배포(https) 시 settings로 True 전환 필요.

위치: app/core/cookies.py
"""

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"

# 로컬 개발 기준. 배포 시 secure=True, samesite="none"(크로스 도메인) 등 조정 필요.
_COOKIE_SECURE = settings.COOKIE_SECURE
_COOKIE_SAMESITE = "lax"
_COOKIE_PATH = "/"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """응답에 AT/RT 쿠키를 심는다. max_age는 각 토큰 만료(분→초)와 맞춘다."""
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path=_COOKIE_PATH,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAMESITE,
        path=_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    """로그아웃 시 AT/RT 쿠키를 삭제한다."""
    response.delete_cookie(ACCESS_COOKIE, path=_COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE, path=_COOKIE_PATH)
