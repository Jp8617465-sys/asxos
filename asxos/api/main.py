from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from asxos.config import BriefSettings, settings

# Startup guard: validate brief env vars are present before the app boots.
# BriefSettings() raises ValidationError immediately if any are missing.
# Do NOT remove — this is intentional, not dead code.
_brief_settings = BriefSettings()  # type: ignore[call-arg]  # pydantic-settings reads from env vars
from asxos.db import acquire, close_pool, init_pool  # noqa: E402
from asxos.domain.models.cache import get_cache  # noqa: E402

REQUIRED_MIGRATIONS = 94  # bump each time a new migration is applied; 0040 (thesis_report_sections, applied 2026-07-19 out-of-band, file reconstructed 2026-07-21) — observed count from supabase_migrations.schema_migrations


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

    # Warm the model cache — hard-fail if the active artefact is missing.
    await get_cache().get("model_a")

    yield

    await close_pool()


app = FastAPI(title="asxos", lifespan=lifespan)

from asxos.api.routes.health import router as health_router  # noqa: E402

app.include_router(health_router)
