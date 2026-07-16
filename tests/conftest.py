"""
pytest 공용 fixture — PB-67

- client: ASGI in-process HTTP 클라이언트 (서버 안 띄우고 앱 직접 호출)
- make_email: 고유 테스트 이메일 발급 + 테스트 후 관련 DB 행 정리
- _dispose_engine: 각 테스트 후 async 엔진 풀 정리 (테스트별 이벤트 루프 충돌 방지)

방식 A: 실제 로컬 DB 에 쓰고, 만든 데이터는 teardown 에서 삭제한다.
위치: tests/conftest.py
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.security import hash_email
from app.db import engine
from app.main import app


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """각 테스트가 끝나면 커넥션 풀을 비운다.
    pytest-asyncio는 테스트마다 새 이벤트 루프를 쓰는데, asyncpg 커넥션은
    루프에 묶여 있어 재사용 시 깨진다. 매 테스트 후 dispose로 새로 맺게 한다."""
    yield
    await engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def make_email():
    """호출할 때마다 고유 테스트 이메일을 발급하고, 테스트 종료 시 그 이메일의
    users/workspaces/user_sessions/login_attempts 행을 모두 삭제한다."""
    used: list[str] = []

    def _make() -> str:
        # example.com = 테스트용 예약 도메인 (email-validator 통과, 실제 발송 안 됨)
        email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
        used.append(email)
        return email

    yield _make

    async with engine.begin() as conn:
        for email in used:
            uid = await conn.scalar(text("select id from users where email=:e"), {"e": email})
            if uid is not None:
                await conn.execute(
                    text("delete from user_sessions where user_id=:u"), {"u": uid}
                )
                # 프롬프트 계열 먼저 정리 (workspaces FK 때문에 순서 중요): blocks → prompts
                await conn.execute(
                    text(
                        "delete from prompt_blocks where prompt_id in "
                        "(select p.id from prompts p join workspaces w on w.id=p.workspace_id "
                        "where w.owner_id=:u)"
                    ),
                    {"u": uid},
                )
                await conn.execute(
                    text(
                        "delete from prompts where workspace_id in "
                        "(select id from workspaces where owner_id=:u)"
                    ),
                    {"u": uid},
                )
                await conn.execute(text("delete from workspaces where owner_id=:u"), {"u": uid})
                await conn.execute(text("delete from users where id=:u"), {"u": uid})
            # login_attempts는 email_hash만 저장하므로 해시로 매칭해 삭제
            await conn.execute(
                text("delete from login_attempts where email_hash=:h"),
                {"h": hash_email(email)},
            )
