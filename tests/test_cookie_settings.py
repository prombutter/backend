"""
쿠키 속성 설정 검증 — PB-140

SameSite·Secure 조합이 어긋나면 브라우저가 쿠키를 조용히 버린다. 증상은 "로그인이 풀린다"
하나뿐이고 원인은 응답 헤더를 직접 뜯어보기 전에는 드러나지 않는다. 설정을 읽는 시점에
막히는지를 여기서 지킨다.

위치: tests/test_cookie_settings.py
"""

import pytest

from app.core.config import Settings

_BASE = {"SECRET_KEY": "x" * 32, "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/d"}


def _settings(**overrides) -> Settings:
    # _env_file=None: 개발자 로컬 .env 가 섞여 들어와 결과가 사람마다 달라지는 것을 막는다.
    return Settings(_env_file=None, **{**_BASE, **overrides})


def test_lax_is_default():
    assert _settings(APP_ENV="local").cookie_samesite_effective == "lax"


def test_samesite_is_case_insensitive():
    s = _settings(APP_ENV="production", COOKIE_SAMESITE="None", COOKIE_SECURE=True)
    assert s.cookie_samesite_effective == "none"


def test_samesite_none_requires_secure():
    # APP_ENV=local + CORS 가 http 라 cookie_secure_effective 가 False 로 떨어지는 조합.
    s = _settings(
        APP_ENV="local",
        COOKIE_SAMESITE="none",
        COOKIE_SECURE=False,
        CORS_ORIGINS="http://localhost:3000",
    )
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        _ = s.cookie_samesite_effective


def test_unknown_samesite_rejected():
    with pytest.raises(RuntimeError, match="lax"):
        _ = _settings(COOKIE_SAMESITE="sameorigin").cookie_samesite_effective


def test_non_local_env_forces_secure():
    # 운영·스테이징에서는 COOKIE_SECURE 를 안 넣어도 Secure 가 켜진다.
    assert _settings(APP_ENV="production", COOKIE_SECURE=False).cookie_secure_effective is True


def test_cookie_domain_blank_means_unset():
    assert _settings(COOKIE_DOMAIN="   ").cookie_domain_effective is None
    assert _settings(COOKIE_DOMAIN=".prombutter.com").cookie_domain_effective == ".prombutter.com"
