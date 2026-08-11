import os
from pathlib import Path

TEST_DB_PATH = Path("test_ac_store.db")

os.environ["ENVIRONMENT"] = "test"
os.environ[
    "DATABASE_URL"
] = (
    f"sqlite+aiosqlite:///"
    f"{TEST_DB_PATH.resolve()}"
)

os.environ[
    "INITIAL_ADMIN_USERNAME"
] = "admin"

os.environ[
    "INITIAL_ADMIN_EMAIL"
] = "admin@acstore.local"

os.environ[
    "INITIAL_ADMIN_PASSWORD"
] = "Admin@12345"

os.environ[
    "INITIAL_ADMIN_FULL_NAME"
] = "System Administrator"


from app.core.config import get_settings

get_settings.cache_clear()


import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.init_db import create_initial_admin
from app.db.seed_data import seed_system_data
from app.db.seed_inventory import seed_inventory_data
from app.db.session import get_db_session
from app.main import app


TEST_DATABASE_URL = (
    "sqlite+aiosqlite:///"
    + str(TEST_DB_PATH.resolve())
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db_session():
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[
    get_db_session
] = override_get_db_session


@pytest.fixture(
    autouse=True,
)
async def test_database():
    #
    # Every test receives a completely fresh database.
    #
    # This prevents state created by Customer, Sales,
    # Payment, Inventory, Return, etc. tests from leaking
    # into another test.
    #

    await test_engine.dispose()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    async with test_engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    async with TestSessionLocal() as session:
        await seed_system_data(
            session
        )

        await seed_inventory_data(
            session
        )

        await create_initial_admin(
            session
        )

    yield

    await test_engine.dispose()

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture
async def db_session(
    test_database,
):
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def client(
    test_database,
):
    transport = ASGITransport(
        app=app,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.fixture
async def admin_token(
    client,
):
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username":
                "admin@acstore.local",
            "password":
                "Admin@12345",
        },
    )

    assert response.status_code == 200

    data = response.json()

    token = data.get(
        "access_token"
    )

    assert token

    return token


@pytest.fixture
async def admin_headers(
    admin_token,
):
    return {
        "Authorization":
            f"Bearer {admin_token}",
    }
