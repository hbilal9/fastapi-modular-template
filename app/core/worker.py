import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    # One persistent loop per worker process: asyncpg connections bind to the
    # loop that created them, so reusing a single loop keeps the pool valid.
    global _loop
    if _loop is None:
        _loop = asyncio.new_event_loop()
    return _loop


def worker_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        _session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    return _get_loop().run_until_complete(coro)
