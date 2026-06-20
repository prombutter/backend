import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db import get_session
from app.models.base import Base
# ensure models are loaded
import app.models.parts

# Create an in-memory SQLite database for tests
engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def override_get_session():
    async with TestingSessionLocal() as session:
        yield session

fastapi_app.dependency_overrides[get_session] = override_get_session

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture(scope="function")
def test_workspace_id():
    return uuid.uuid4()
