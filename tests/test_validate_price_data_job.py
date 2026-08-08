"""Tests for jobs/validate_price_data.py — the anchor guard (2026-08-08).

First test file for this job wrapper (previously only AST-shape checks in
test_cron_pool_init.py — the systemic pure-function-tested / job-untested gap).

The defect pinned here: a Saturday manual dispatch validated calendar-today,
found every active symbol "missing" a price for a day the ASX never traded,
and paged `MISSING_PRICES: 1880`. The job now anchors to the latest COMPLETE
trading day (same util the brief uses) unless an explicit --as-of was given.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, patch

from jobs.validate_price_data import _run

_SATURDAY = date(2026, 8, 8)
_FRIDAY = date(2026, 8, 7)


class _FakeMonitor:
    def __init__(self, *a, **kw):
        self.rows_written = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _patches(latest, queried):
    conn = AsyncMock()

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    async def fake_anomalies(c, as_of):
        queried.append(as_of)
        return []

    return (
        patch("jobs.validate_price_data.init_pool", new=AsyncMock()),
        patch("jobs.validate_price_data.close_pool", new=AsyncMock()),
        patch("jobs.validate_price_data.acquire", new=fake_acquire),
        patch("jobs.validate_price_data.JobMonitor", new=_FakeMonitor),
        patch(
            "jobs.validate_price_data.latest_complete_trading_day",
            new=AsyncMock(return_value=latest),
        ),
        patch("jobs.validate_price_data._query_anomalies", new=fake_anomalies),
    )


def test_weekend_run_anchors_to_latest_complete_trading_day() -> None:
    """Saturday dispatch validates Friday — not a day the ASX never traded."""
    queried: list[date] = []
    p = _patches(latest=_FRIDAY, queried=queried)
    with p[0], p[1], p[2], p[3], p[4], p[5]:
        asyncio.run(_run(_SATURDAY))
    assert queried == [_FRIDAY], (
        "validating calendar-today on a non-trading day pages about every "
        "symbol; the check must anchor to the last day that actually traded"
    )


def test_explicit_as_of_bypasses_the_anchor() -> None:
    """--as-of means 'validate exactly this day' — anchor must not override."""
    queried: list[date] = []
    p = _patches(latest=_FRIDAY, queried=queried)
    with p[0], p[1], p[2], p[3], p[4], p[5]:
        asyncio.run(_run(_SATURDAY, anchor=False))
    assert queried == [_SATURDAY]


def test_no_complete_day_falls_back_to_as_of() -> None:
    """A dead pipeline (no complete day in the window) still validates as_of —
    in that state the loud MISSING_PRICES alarm is genuinely correct."""
    queried: list[date] = []
    p = _patches(latest=None, queried=queried)
    with p[0], p[1], p[2], p[3], p[4], p[5]:
        asyncio.run(_run(_SATURDAY))
    assert queried == [_SATURDAY]
