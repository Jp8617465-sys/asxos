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
        # Pin the session TimeZone GUC rather than inheriting whatever the
        # database or role default happens to be.
        #
        # asxos/brief/compose.py:694-698 analyses the dependency in full: the
        # freshness window compares `$1::date ± INTERVAL` — a `timestamp
        # WITHOUT time zone` — against a `timestamptz`, and Postgres resolves
        # that comparison through the session TimeZone. Setting the database or
        # role timezone to Australia/Sydney would slide that window ~10 hours
        # off the 20:30-22:30 UTC pipeline it exists to cover, silently: no
        # error, no failing test, just a window that stops matching the runs it
        # is meant to find.
        #
        # Until this line the invariant held only because nobody had set a
        # role-level timezone — a property of the database's configuration
        # history, not of this code. One ALTER ROLE ... SET timezone by anyone,
        # ever, would have broken it. Now the pool states its requirement.
        #
        # UTC specifically, not the reporting timezone: every stored boundary in
        # this codebase is timestamptz at UTC, and settings.asxos_tz is for
        # presentation. Do not "improve" this to Australia/Sydney.
        server_settings={"timezone": "UTC"},
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
