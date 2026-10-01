from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from database import InMemoryDatabase, set_database
from main import app
from redis_client import InMemoryRedisStore, set_redis


@pytest_asyncio.fixture(autouse=True)
async def reset_stores() -> None:
    set_database(InMemoryDatabase())
    set_redis(InMemoryRedisStore())
    yield


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
