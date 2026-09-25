"""The pooled DB session must pin its ``TimeZone`` GUC to UTC.

Why this is a test and not a comment: ``asxos/brief/compose.py``'s job-freshness
window compares a ``timestamp WITHOUT time zone`` (from ``$1::date ± INTERVAL``)
against a ``timestamptz``, and Postgres resolves that through the session
``TimeZone``. Before 2026-08-23 the pool passed no ``server_settings``, so the
comparison inherited whatever the database or role default happened to be. A
single ``ALTER ROLE ... SET timezone = 'Australia/Sydney'`` — by anyone, at any
point — would have slid that window off the UTC pipeline it covers, with no
error and no failing test. The whole failure mode is silence, which is exactly
the kind that needs an assertion rather than a docstring.

These run without a database: ``asyncpg.create_pool`` is patched and the call
kwargs inspected.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import asxos.db as db


@pytest.mark.asyncio
async def test_init_pool_pins_session_timezone_to_utc() -> None:
    with patch.object(db.asyncpg, "create_pool", new=AsyncMock(return_value="pool")) as cp:
        try:
            await db.init_pool()
        finally:
            db._pool = None

    kwargs = cp.await_args.kwargs
    assert "server_settings" in kwargs, (
        "init_pool passed no server_settings — the session TimeZone is "
        "unpinned and compose.py's freshness window silently depends on the "
        "database/role default"
    )
    assert kwargs["server_settings"]["timezone"] == "UTC"


@pytest.mark.asyncio
async def test_init_pool_does_not_pin_a_reporting_timezone() -> None:
    """UTC specifically, not the reporting timezone.

    Every stored boundary in this codebase is ``timestamptz`` at UTC;
    the reporting zone (``asxos.clock``) is for presentation. Pinning the session to
    Australia/Sydney would be a plausible-looking "fix" that reintroduces the
    exact offset this guards against, so it is asserted against by name.
    """
    with patch.object(db.asyncpg, "create_pool", new=AsyncMock(return_value="pool")) as cp:
        try:
            await db.init_pool()
        finally:
            db._pool = None

    assert cp.await_args.kwargs["server_settings"]["timezone"] != "Australia/Sydney"


def test_compose_freshness_docstring_does_not_claim_the_guc_is_unpinned() -> None:
    """The analysis in compose.py must not still describe the old, fixed state.

    It read "unpinned here, since asxos/db.py::init_pool passes no
    server_settings". Leaving that in place after pinning it would be the drift
    class this PR exists to close, reintroduced one file over.
    """
    import inspect

    from asxos.brief import compose

    assert "passes no ``server_settings``" not in inspect.getsource(compose)
