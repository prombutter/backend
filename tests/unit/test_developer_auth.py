import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.security import decode_token
from app.db import get_session
from app.deps import get_current_user
from app.models import User, UserRole, Workspace
from app.routers.developer_auth import DEVELOPER_EMAIL, DEVELOPER_USER_ID, router

EXTENSION_HEADERS = {
    "X-Requested-With": "Prombutter-Extension",
    "Origin": "chrome-extension://" + "a" * 32,
}


@pytest.fixture
def developer_app(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "local")
    monkeypatch.setattr(settings, "DEVELOPER_LOGIN_ENABLED", True)
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "COOKIE_SAMESITE", "lax")
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", "")
    monkeypatch.setattr(settings, "CORS_ORIGINS", "http://localhost:3000")
    user = User(
        id=DEVELOPER_USER_ID,
        email=DEVELOPER_EMAIL,
        name="Developer",
        role=UserRole.USER,
        created_at=datetime.now(timezone.utc),
    )
    workspace = Workspace(id=uuid.uuid4(), owner_id=user.id, name="Developer workspace")
    session = SimpleNamespace(
        execute=AsyncMock(),
        get=AsyncMock(return_value=user),
        scalar=AsyncMock(return_value=workspace),
        add=lambda row: sessions.append(row),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )
    sessions = []
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(router)

    async def synthetic_session():
        yield session

    app.dependency_overrides[get_session] = synthetic_session

    @app.get("/auth/me")
    async def me(user: User = Depends(get_current_user)):
        return {"id": str(user.id)}

    return app, session, sessions


@pytest.mark.parametrize(
    "environment,enabled,host,client_host,headers",
    [
        ("production", True, "localhost", "127.0.0.1", EXTENSION_HEADERS),
        ("staging", True, "localhost", "127.0.0.1", EXTENSION_HEADERS),
        ("local", False, "localhost", "127.0.0.1", EXTENSION_HEADERS),
        ("local", True, "api.example.com", "127.0.0.1", EXTENSION_HEADERS),
        ("local", True, "localhost.evil.example", "127.0.0.1", EXTENSION_HEADERS),
        ("local", True, "localhost", "192.0.2.1", EXTENSION_HEADERS),
        ("local", True, "localhost", "testclient", EXTENSION_HEADERS),
        ("local", True, "localhost", "127.0.0.1", {}),
        ("local", True, "localhost", "127.0.0.1", {**EXTENSION_HEADERS, "Origin": "null"}),
        (
            "local",
            True,
            "localhost",
            "127.0.0.1",
            {**EXTENSION_HEADERS, "Origin": "http://localhost:3000"},
        ),
        (
            "local",
            True,
            "localhost",
            "127.0.0.1",
            {**EXTENSION_HEADERS, "Forwarded": "for=127.0.0.1"},
        ),
        (
            "local",
            True,
            "localhost",
            "127.0.0.1",
            {**EXTENSION_HEADERS, "X-Forwarded-For": "127.0.0.1"},
        ),
        (
            "local",
            True,
            "localhost",
            "127.0.0.1",
            {**EXTENSION_HEADERS, "X-Forwarded-Host": "localhost"},
        ),
        (
            "local",
            True,
            "localhost",
            "127.0.0.1",
            {**EXTENSION_HEADERS, "X-Forwarded-Proto": "http"},
        ),
    ],
)
async def test_developer_login_denied_before_database_access(
    developer_app, monkeypatch, environment, enabled, host, client_host, headers
):
    app, session, sessions = developer_app
    monkeypatch.setattr(settings, "APP_ENV", environment)
    monkeypatch.setattr(settings, "DEVELOPER_LOGIN_ENABLED", enabled)
    transport = ASGITransport(app=app, client=(client_host, 1234))
    async with AsyncClient(transport=transport, base_url=f"http://{host}") as client:
        response = await client.post("/auth/developer-login", headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    session.execute.assert_not_called()
    session.commit.assert_not_called()
    assert not sessions


@pytest.mark.parametrize("host,client_host", [("localhost", "127.0.0.1"), ("[::1]", "::1")])
async def test_developer_login_issues_real_cookies_and_reuses_account(
    developer_app, host, client_host
):
    app, session, sessions = developer_app
    transport = ASGITransport(app=app, client=(client_host, 1234))
    async with AsyncClient(transport=transport, base_url=f"http://{host}") as client:
        for _ in range(2):
            response = await client.post("/auth/developer-login", headers=EXTENSION_HEADERS)
            assert response.status_code == 200
            assert response.json()["id"] == str(DEVELOPER_USER_ID)
            assert response.json()["role"] == "USER"
            assert "password_hash" not in response.json()
            assert set(client.cookies.keys()) == {"access_token", "refresh_token"}
            assert all("HttpOnly" in value for value in response.headers.get_list("set-cookie"))
            access_type = decode_token(client.cookies["access_token"])["type"]
            refresh_type = decode_token(client.cookies["refresh_token"])["type"]
            assert access_type == "access"
            assert refresh_type == "refresh"
            me = await client.get("/auth/me")
            assert me.status_code == 200
            assert me.json()["id"] == str(DEVELOPER_USER_ID)
    assert session.commit.await_count == 2
    assert len(sessions) == 2
    assert all(row.user_id == DEVELOPER_USER_ID for row in sessions)
    statements = [str(call.args[0]) for call in session.execute.call_args_list]
    assert all("ON CONFLICT" in statement and "DO NOTHING" in statement for statement in statements)


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("role", UserRole.SUPER_ADMIN),
        ("email", "other@example.com"),
        ("password_hash", "synthetic-existing-password-hash"),
    ],
)
async def test_developer_login_never_takes_over_existing_accounts(developer_app, attribute, value):
    app, session, sessions = developer_app
    setattr(session.get.return_value, attribute, value)
    transport = ASGITransport(app=app, client=("127.0.0.1", 1234))
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post("/auth/developer-login", headers=EXTENSION_HEADERS)
    assert response.status_code == 409
    assert "set-cookie" not in response.headers
    session.commit.assert_not_called()
    assert not sessions


async def test_developer_login_does_not_issue_cookies_after_database_failure(developer_app):
    app, session, sessions = developer_app
    session.commit.side_effect = RuntimeError("synthetic database failure")
    transport = ASGITransport(app=app, client=("127.0.0.1", 1234), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post("/auth/developer-login", headers=EXTENSION_HEADERS)
    assert response.status_code == 500
    assert "set-cookie" not in response.headers
