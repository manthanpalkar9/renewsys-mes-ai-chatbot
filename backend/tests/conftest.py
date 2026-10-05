"""
Test configuration.

The `setup_db` fixture is explicitly NOT autouse here.
Tests that need a database (auth, chat HTTP tests) can request it explicitly.
LLM intent tests do NOT need a database — they test pure Python logic.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.database import get_db
from app.models.user import Base, User, UserRole
from app.core.security import get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def setup_db():
    """Fixture to set up test DB. Must be requested explicitly by tests that need it."""
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as db:
            admin_user = User(
                username="admin_test",
                email="admin@test.com",
                hashed_password=get_password_hash("password123"),
                role=UserRole.ADMIN,
            )
            normal_user = User(
                username="user_test",
                email="user@test.com",
                hashed_password=get_password_hash("password123"),
                role=UserRole.USER,
            )
            db.add_all([admin_user, normal_user])
            await db.commit()

    async def _teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_setup())
    yield
    loop.run_until_complete(_teardown())
    loop.close()


@pytest.fixture
def client(setup_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "password123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "user_test", "password": "password123"}
    )
    return response.json()["access_token"]
