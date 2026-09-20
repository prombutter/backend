"""
인증 쿠키 헬퍼 — PB-67 / PB-140

AT(access)/RT(refresh)를 HttpOnly 쿠키로 주고받는다.
- HttpOnly: JS에서 접근 불가 → XSS로 토큰 탈취 방어
- Secure·SameSite·Domain 은 전부 환경변수로 정한다(PB-140). 하드코딩해 두면 운영 도메인
  구성이 바뀔 때마다 코드를 고쳐 다시 배포해야 하고, 그 전까지 로그인 세션이 조용히
  전송되지 않는다.

값은 호출 시점에 읽는다. 모듈 로드 시점에 굳혀 두면 설정 변경이 반영되지 않는다.

위치: app/core/cookies.py
"""

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"

_COOKIE_PATH = "/"


def _cookie_kwargs() -> dict:
    return {
        "secure": settings.cookie_secure_effective,
        "samesite": settings.cookie_samesite_effective,
        "path": _COOKIE_PATH,
        "domain": settings.cookie_domain_effective,
    }


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """응답에 AT/RT 쿠키를 심는다. max_age는 각 토큰 만료(분→초)와 맞춘다."""
    common = _cookie_kwargs()
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        **common,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    """로그아웃 시 AT/RT 쿠키를 삭제한다.

    삭제도 심을 때와 같은 path·domain·samesite·secure 로 보내야 한다. 하나라도 어긋나면
    브라우저가 다른 쿠키로 보고 원본을 남겨 둔다. 로그아웃했는데 세션이 살아 있게 된다.
    """
    response.delete_cookie(ACCESS_COOKIE, **_cookie_kwargs())
    response.delete_cookie(REFRESH_COOKIE, **_cookie_kwargs())
