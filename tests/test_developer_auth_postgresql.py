import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.db import SessionLocal, engine
from app.main import app
from app.models import User, UserRole, UserSession, Workspace
from app.routers.developer_auth import DEVELOPER_EMAIL, DEVELOPER_USER_ID

HEADERS = {"X-Requested-With": "Prombutter-Extension"}


@pytest.fixture
async def isolated_developer_account(monkeypatch):
    if engine.url.database not in {"prombutter_ci", "prombutter_test"}:
        pytest.skip("Requires the isolated PostgreSQL CI database")
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(User.id).where((User.id == DEVELOPER_USER_ID) | (User.email == DEVELOPER_EMAIL))
        )
        if existing is not None:
            pytest.skip("A reserved developer account already exists; preserve its data")
    monkeypatch.setattr(settings, "APP_ENV", "local")
    monkeypatch.setattr(settings, "DEVELOPER_LOGIN_ENABLED", True)
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "COOKIE_SAMESITE", "lax")
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", "")
    owned_ids = [DEVELOPER_USER_ID]
    yield owned_ids
    async with SessionLocal() as session:
        await session.execute(delete(UserSession).where(UserSession.user_id.in_(owned_ids)))
        await session.execute(delete(Workspace).where(Workspace.owner_id.in_(owned_ids)))
        await session.execute(delete(User).where(User.id.in_(owned_ids)))
        await session.commit()


async def test_concurrent_developer_sessions_share_one_account_and_workspace(
    isolated_developer_account,
):
    async def authenticate():
        transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with AsyncClient(transport=transport, base_url="http://localhost") as client:
            issued = await client.post("/auth/developer-login", headers=HEADERS)
            assert issued.status_code == 200
            assert issued.json()["id"] == str(DEVELOPER_USER_ID)
            assert issued.json()["role"] == "USER"
            assert client.cookies.get("access_token")
            assert client.cookies.get("refresh_token")
            authenticated = await client.get("/auth/me")
            assert authenticated.status_code == 200
            assert authenticated.json()["id"] == str(DEVELOPER_USER_ID)
            workspace = await client.get("/workspaces")
            assert workspace.status_code == 200
            return workspace.json()["id"]

    workspaces = await asyncio.gather(*(authenticate() for _ in range(4)))
    assert len(set(workspaces)) == 1
    async with SessionLocal() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(User).where(User.id == DEVELOPER_USER_ID)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(Workspace)
                .where(Workspace.owner_id == DEVELOPER_USER_ID)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(UserSession)
                .where(UserSession.user_id == DEVELOPER_USER_ID)
            )
            == 4
        )


async def test_reserved_email_collision_returns_conflict_without_authentication(
    isolated_developer_account,
):
    other_id = uuid.uuid4()
    isolated_developer_account.append(other_id)
    async with SessionLocal() as session:
        session.add(User(id=other_id, email=DEVELOPER_EMAIL, name="Fixture", role=UserRole.USER))
        await session.commit()
    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post("/auth/developer-login", headers=HEADERS)
        assert response.status_code == 409
        assert response.json()["error_code"] == "ERR-AUTH-DEV-002"
        assert not client.cookies
    async with SessionLocal() as session:
        assert await session.get(User, DEVELOPER_USER_ID) is None
        assert (
            await session.scalar(
                select(func.count())
                .select_from(UserSession)
                .where(UserSession.user_id.in_(isolated_developer_account))
            )
            == 0
        )
