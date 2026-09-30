"""Shared pytest fixtures.

The test suite runs against a real PostgreSQL database. Point
``TEST_DATABASE_URL`` at it (defaults to ``postgresql+asyncpg://scholar:scholar@localhost:5432/scholar_test``).
Each test session creates a throwaway schema, so the dev database is never touched.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["ENVIRONMENT"] = "test"

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://scholar:scholar@localhost:55433/scholar_test",
)

TEST_SCHEMA = "scholar_test"


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=None)
    async with eng.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{TEST_SCHEMA}"'))
        await conn.execute(text(f'SET search_path TO "{TEST_SCHEMA}"'))
        await conn.run_sync(_build_metadata)
    yield eng
    async with eng.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
    await eng.dispose()


def _build_metadata(sync_conn) -> None:
    from app.db.base import Base
    from app import models  # noqa: F401

    Base.metadata.create_all(sync_conn)


@pytest_asyncio.fixture
async def session(engine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def seeded(session: AsyncSession) -> AsyncSession:
    """A session pre-loaded with categories, grades, settings and a superadmin."""
    from app.db.base import Base
    from app.models import AppSetting, Category, Grade, User
    from app.core.security import hash_password

    now_year = 2026
    for spec in (
        ("current_year", 1, "I.", "បានទទួលពាក្យបាក់ឌុបឆ្នាំ{year}"),
        ("before_current_year", 2, "II.", "បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ{year}"),
        ("other_province", 3, "III.", "បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង"),
    ):
        session.add(Category(code=spec[0], position=spec[1], roman_numeral=spec[2], title_template=spec[3]))
    for i, code in enumerate(("A", "B", "C", "D", "E"), start=1):
        session.add(Grade(code=code, position=i))
    session.add(AppSetting(key="current_year", value=str(now_year), value_type="int"))
    session.add(
        User(
            email="admin@test.example.com",
            username="admin",
            full_name="Test Admin",
            hashed_password=hash_password("TestPass123!"),
            role="superadmin",
            is_active=True,
            is_superuser=True,
        )
    )
    await session.commit()
    return session


@pytest_asyncio.fixture
async def client(engine) -> AsyncIterator[AsyncClient]:
    """An HTTP client wired to the ASGI app, using the test schema."""
    from app.main import create_app
    from app.db import session as session_module

    app = create_app()
    app.dependency_overrides[session_module.get_db] = _override_db(engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _override_db(engine):
    from app.db import session as session_module

    async def _get_db():
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as s:
            yield s

    return _get_db


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.example.com", "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def any_uuid() -> uuid.UUID:
    return uuid.uuid4()
