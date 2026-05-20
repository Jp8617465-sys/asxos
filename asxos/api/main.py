from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool

REQUIRED_MIGRATIONS = 1  # bump each time a new migration is applied


async def _check_migration_drift() -> None:
    if settings.skip_migration_drift_check:
        return
    async with acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM supabase_migrations.schema_migrations"
        )
    if count < REQUIRED_MIGRATIONS:
        raise RuntimeError(
            f"Migration drift: {count} migrations applied, "
            f"{REQUIRED_MIGRATIONS} required. "
            "Run the pending migrations via Supabase MCP before starting."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Hard-fail on any dependency init failure — no logger.warning(); continue
    await init_pool()

    async with acquire() as conn:
        await conn.fetchval("SELECT 1")

    await _check_migration_drift()

    yield

    await close_pool()


app = FastAPI(title="asxos", lifespan=lifespan)

from asxos.api.routes.health import router as health_router  # noqa: E402

app.include_router(health_router)
