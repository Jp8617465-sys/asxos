from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from asxos.config import BriefSettings, settings

# Startup guard: validate brief env vars are present before the app boots.
# BriefSettings() raises ValidationError immediately if any are missing.
# Do NOT remove — this is intentional, not dead code.
_brief_settings = BriefSettings()  # type: ignore[call-arg]  # pydantic-settings reads from env vars
from asxos.db import acquire, close_pool, init_pool  # noqa: E402
from asxos.schema_drift import check as migration_check  # noqa: E402


async def _check_migration_drift() -> None:
    """Hard-fail if applied migrations and migrations/ disagree by NAME.

    Replaces a hand-maintained ``REQUIRED_MIGRATIONS`` integer compared with
    ``<``. That form could not detect a migration applied to production with no
    file in this repo — the count rises and the guard passes — which is the
    failure that leaves production carrying schema the repo cannot reproduce.
    It had been green while exactly that was true (see 0018, and 0040's own
    provenance note recording the same thing in July).

    The comparison lives in scripts/check_migration_drift.py so the same logic
    runs from CI and by hand without booting the app.
    """
    if settings.skip_migration_drift_check:
        return
    async with acquire() as conn:
        await migration_check(conn)


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
