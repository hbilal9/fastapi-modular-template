from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

_redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_redis_pool)


RedisSession = Annotated[redis.Redis, Depends(get_redis)]
