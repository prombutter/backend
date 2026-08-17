"""
PB-67 인증/워크스페이스 API 테스트 (DoD)

해피패스(signup→login→me→refresh→logout) + 401(만료/무토큰/무효) + 400(중복)
+ 워크스페이스 자동생성 + 가입 2회 시 워크스페이스 1개 유지 + RT 회전 방어.
위치: tests/test_auth.py
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import text

from app.core.config import settings
from app.core.cookies import ACCESS_COOKIE, REFRESH_COOKIE
from app.db import engine

PW = "password123!"  # 8자+ 영문·숫자·특수문자 (인증 명세 1.5)


# ===== signup =====
async def test_signup_creates_user_and_workspace(client, make_email):
    email = make_email()
    r = await client.post("/auth/signup", json={"email": email, "password": PW})
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == email
    assert data["name"] == email.split("@")[0]  # name 미입력 → 이메일 앞부분
    assert data["role"] == "USER"
    assert "password_hash" not in data  # 민감 정보 미노출
    # 쿠키 발급 확인
    assert client.cookies.get(ACCESS_COOKIE)
    assert client.cookies.get(REFRESH_COOKIE)
    # 워크스페이스 자동 생성 (이름 = "{이름}의 워크스페이스")
    ws = await client.get("/workspaces")
    assert ws.status_code == 200
    assert ws.json()["name"] == f"{email.split('@')[0]}의 워크스페이스"


async def test_signup_weak_password_422(client, make_email):
    email = make_email()
    # 특수문자 없음 → 규칙 위반 → 422 (pydantic 검증)
    r = await client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 422


async def test_signup_duplicate_email_400(client, make_email):
    email = make_email()
    r1 = await client.post("/auth/signup", json={"email": email, "password": PW})
    assert r1.status_code == 201
    r2 = await client.post("/auth/signup", json={"email": email, "password": PW})
    assert r2.status_code == 400


async def test_signup_twice_keeps_one_workspace(client, make_email):
    email = make_email()
    await client.post("/auth/signup", json={"email": email, "password": PW})
    await client.post("/auth/signup", json={"email": email, "password": PW})  # 400 duplicate
    async with engine.connect() as conn:
        uid = await conn.scalar(text("select id from users where email=:e"), {"e": email})
        cnt = await conn.scalar(
            text("select count(*) from workspaces where owner_id=:u"), {"u": uid}
        )
    assert cnt == 1


# ===== 해피패스 =====
async def test_happy_path(client, make_email):
    email = make_email()
    assert (
        await client.post("/auth/signup", json={"email": email, "password": PW})
    ).status_code == 201
    client.cookies.clear()
    assert (
        await client.post("/auth/login", json={"email": email, "password": PW})
    ).status_code == 200
    assert (await client.get("/auth/me")).status_code == 200
    assert (await client.post("/auth/refresh")).status_code == 200
    assert (await client.get("/auth/me")).status_code == 200  # 회전 후 새 AT로도 동작
    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401  # 로그아웃 후 쿠키 삭제


# ===== 401 =====
async def test_me_without_token_401(client):
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_invalid_token_401(client):
    client.cookies.set(ACCESS_COOKIE, "not.a.valid.jwt")
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_expired_token_401(client, make_email):
    email = make_email()
    await client.post("/auth/signup", json={"email": email, "password": PW})
    uid = (await client.get("/auth/me")).json()["id"]
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": uid,
            "type": "access",
            "iat": int((now - timedelta(minutes=30)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),  # 1분 전 만료
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    client.cookies.set(ACCESS_COOKIE, expired)
    assert (await client.get("/auth/me")).status_code == 401


async def test_login_wrong_password_401(client, make_email):
    email = make_email()
    await client.post("/auth/signup", json={"email": email, "password": PW})
    client.cookies.clear()
    r = await client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert r.status_code == 401


async def test_login_unknown_email_401(client, make_email):
    email = make_email()  # 가입하지 않은 이메일 (정리 대상으로 추적)
    r = await client.post("/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 401


# ===== RT 회전 =====
async def test_refresh_rotation_rejects_old_rt(client, make_email):
    email = make_email()
    await client.post("/auth/signup", json={"email": email, "password": PW})
    old_rt = client.cookies.get(REFRESH_COOKIE)
    r = await client.post("/auth/refresh")
    assert r.status_code == 200
    new_rt = client.cookies.get(REFRESH_COOKIE)
    assert old_rt != new_rt  # 새 RT로 교체됨
    # 폐기된 옛 RT 재사용 → 거부
    client.cookies.set(REFRESH_COOKIE, old_rt)
    assert (await client.post("/auth/refresh")).status_code == 401


# ===== workspaces =====
async def test_workspaces_returns_my_workspace(client, make_email):
    email = make_email()
    await client.post("/auth/signup", json={"email": email, "password": PW})
    r = await client.get("/workspaces")
    assert r.status_code == 200
    assert r.json()["name"] == f"{email.split('@')[0]}의 워크스페이스"
