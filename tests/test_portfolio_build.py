"""
Hard-fail invariants for PortfolioService.build() (plan H.1 CRITICAL-3 / -5).

These guards were previously untested. The non-convergent-waterfall hard-fail
is covered in test_portfolio_constraints.py; here we cover the build()-level
gates: no active profile, and stale / missing signals.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from asxos.domain.portfolio.build import PortfolioService

_BUILD_DATE = date(2026, 6, 1)


@pytest.mark.asyncio
async def test_build_no_active_profile_raises(monkeypatch) -> None:
    # plan H.1 CRITICAL-5: hard-fail (not a warning) when no profile is active.
    async def _no_profile(conn):        return None

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _no_profile)
    with pytest.raises(RuntimeError, match="no active profile"):
        await PortfolioService().build(AsyncMock())


@pytest.mark.asyncio
async def test_build_stale_signals_raises(monkeypatch) -> None:
    # plan H.1 CRITICAL-3: signals_as_of more than 2 days before build → hard-fail.
    # The stale gate fires before any profile attribute is read, so a sentinel
    # non-None profile is sufficient.
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    stale = _BUILD_DATE - timedelta(days=3)  # 3 days > 2-day tolerance → just stale
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"symbol": "AAA", "as_of": stale}])

    with pytest.raises(RuntimeError, match="stale"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_signals_exactly_two_days_old_passes_stale_gate(monkeypatch) -> None:
    # Boundary: (build - as_of).days == 2 is NOT stale (the gate is `> 2`, not
    # `>= 2`). Proves the boundary. The pipeline then fails on the next gate
    # (no active model_version), which is how we confirm it passed the stale check.
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    fresh = _BUILD_DATE - timedelta(days=2)
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"symbol": "AAA", "as_of": fresh}])
    conn.fetchrow = AsyncMock(return_value=None)  # no active model_version

    with pytest.raises(RuntimeError, match="model_version"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_no_signals_raises(monkeypatch) -> None:
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])

    with pytest.raises(RuntimeError, match="no signals"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)
