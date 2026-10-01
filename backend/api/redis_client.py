from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from config import get_settings


class RedisStore(Protocol):
    async def set(self, key: str, value: str, *, ex: int) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...


class InMemoryRedisStore:
    def __init__(self) -> None:
        self._values: dict[str, tuple[str, datetime]] = {}

    async def set(self, key: str, value: str, *, ex: int) -> None:
        self._values[key] = (value, datetime.now(UTC) + timedelta(seconds=ex))

    async def get(self, key: str) -> str | None:
        item = self._values.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at <= datetime.now(UTC):
            self._values.pop(key, None)
            return None
        return value

    async def delete(self, key: str) -> None:
        self._values.pop(key, None)


class RedisAdapter:
    def __init__(self, client: Any) -> None:
        self.client = client

    async def set(self, key: str, value: str, *, ex: int) -> None:
        await self.client.set(key, value, ex=ex)

    async def get(self, key: str) -> str | None:
        value = await self.client.get(key)
        return value.decode("utf-8") if isinstance(value, bytes) else value

    async def delete(self, key: str) -> None:
        await self.client.delete(key)


_redis: RedisStore = InMemoryRedisStore()


async def get_redis() -> RedisStore:
    global _redis
    settings = get_settings()
    if isinstance(_redis, InMemoryRedisStore) and settings.redis_url and settings.redis_url != "redis://localhost:6379/0":
        from redis.asyncio import Redis
        _redis = RedisAdapter(Redis.from_url(settings.redis_url))
    return _redis


def set_redis(client: RedisStore) -> None:
    global _redis
    _redis = client
