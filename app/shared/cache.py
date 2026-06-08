import json
from typing import Any

from redis.asyncio import Redis


async def cache_get(redis: Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    return json.loads(raw) if raw is not None else None


async def cache_set(redis: Redis, key: str, value: Any, ttl: int = 300) -> None:
    await redis.set(key, json.dumps(value), ex=ttl)


async def cache_delete(redis: Redis, key: str) -> None:
    await redis.delete(key)
