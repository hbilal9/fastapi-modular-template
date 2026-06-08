from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request

from app.core.dependencies import RedisSession
from app.core.exceptions import AppError


def rate_limit(max_requests: int, window_seconds: int) -> Callable[..., Coroutine[Any, Any, None]]:
    async def dependency(request: Request, redis: RedisSession) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"rl:{request.url.path}:{client}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        if count > max_requests:
            raise AppError("Too many requests.", 429)

    return dependency
