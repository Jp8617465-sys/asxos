from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from asxos.config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        str(settings.database_url),
        min_size=2,
        max_size=15,   # Phase-2: 5 parallel collectors + Phase-1 slack + safety margin
        command_timeout=30,
        ssl="require",
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialised — call init_pool() first")
    return _pool


@asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection]:
    async with get_pool().acquire() as conn:
        yield conn
