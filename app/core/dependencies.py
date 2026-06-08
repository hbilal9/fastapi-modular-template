import uuid
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.modules.auth.models import User

DbSession = Annotated[AsyncSession, Depends(get_db)]

_redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_redis_pool)


RedisSession = Annotated[redis.Redis, Depends(get_redis)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DbSession,
) -> User:
    if creds is None:
        raise AppError("Not authenticated.", 401)
    payload = security.decode_token(creds.credentials, "access")
    if payload is None:
        raise AppError("Invalid or expired token.", 401)
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise AppError("User not found.", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
