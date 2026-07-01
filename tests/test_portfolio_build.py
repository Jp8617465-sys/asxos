"""
Hard-fail invariants for PortfolioService.build() (plan H.1 CRITICAL-3 / -5).

These guards were previously untested. The non-convergent-waterfall hard-fail
is covered in test_portfolio_constraints.py; here we cover the build()-level
gates: no active profile, the contamination-isolation model gate, and
stale / missing signals.

Ordering note: the model gate (Section 4.4 Step B) runs BEFORE the signals
fetch, because that query needs the gated model name to filter on. Tests
that exercise a later gate must route the model_versions query to a single
approved row so the flow reaches the gate under test.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from asxos.domain.portfolio.build import PortfolioService

_BUILD_DATE = date(2026, 6, 1)
_ONE_APPROVED_MODEL = [{"model": "model_a", "version": "v1_5"}]


def _route_fetch(model_versions_rows, signal_rows):
    """conn.fetch side_effect: model_versions gate, signals, else [].

    The [] default keeps downstream queries (universe, prices) safe for
    tests that only care about an earlier gate — a generic catch-all row
    would otherwise crash on a missing key (e.g. universe reads
    ``r["is_active"]``) before the gate under test ever fires.
    """

    async def _fetch(query, *args, **kwargs):
        if "model_versions" in query:
            return model_versions_rows
        if "FROM signals" in query:
            return signal_rows
        return []

    return _fetch


@pytest.mark.asyncio
async def test_build_no_active_profile_raises(monkeypatch) -> None:
    # plan H.1 CRITICAL-5: hard-fail (not a warning) when no profile is active.
    async def _no_profile(conn):        return None

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _no_profile)
    with pytest.raises(RuntimeError, match="no active profile"):
        await PortfolioService().build(AsyncMock())


@pytest.mark.asyncio
async def test_build_no_approved_model_raises(monkeypatch) -> None:
    # Section 4.4 Step B: zero active+approved_for_allocation rows is a
    # configuration invariant violation — hard-fail before ever touching signals.
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=_route_fetch([], []))

    with pytest.raises(RuntimeError, match="approved_for_allocation"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_multiple_approved_models_raises(monkeypatch) -> None:
    # Multi-sleeve blending is out of v1 scope (portfolio-conventions.md) —
    # more than one eligible model is a hard-fail, not a silent arbitrary pick.
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    two_models = [
        {"model": "model_a", "version": "v1_5"},
        {"model": "factor_sleeve", "version": "v1_0"},
    ]
    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=_route_fetch(two_models, []))

    with pytest.raises(RuntimeError, match="multiple models"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_stale_signals_raises(monkeypatch) -> None:
    # plan H.1 CRITICAL-3: signals_as_of more than 2 days before build → hard-fail.
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    stale = _BUILD_DATE - timedelta(days=3)  # 3 days > 2-day tolerance → just stale
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        side_effect=_route_fetch(
            _ONE_APPROVED_MODEL, [{"symbol": "AAA", "as_of": stale}]
        )
    )

    with pytest.raises(RuntimeError, match="stale"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_signals_exactly_two_days_old_passes_stale_gate(monkeypatch) -> None:
    # Boundary: (build - as_of).days == 2 is NOT stale (the gate is `> 2`, not
    # `>= 2`). Proves the boundary by confirming execution reaches allocation
    # (a sentinel raised from _allocator.allocate) — well past the model gate,
    # the signals fetch, and the stale gate, all of which must have passed
    # cleanly to get there.
    async def _profile(conn):        return object()

    def _sentinel_allocate(*, candidates, profile):
        raise RuntimeError("SENTINEL_REACHED_ALLOCATE")

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    monkeypatch.setattr(
        "asxos.domain.portfolio.build._allocator.allocate", _sentinel_allocate
    )
    fresh = _BUILD_DATE - timedelta(days=2)
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        side_effect=_route_fetch(
            _ONE_APPROVED_MODEL, [{"symbol": "AAA", "as_of": fresh}]
        )
    )

    with pytest.raises(RuntimeError, match="SENTINEL_REACHED_ALLOCATE"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)


@pytest.mark.asyncio
async def test_build_no_signals_raises(monkeypatch) -> None:
    async def _profile(conn):        return object()

    monkeypatch.setattr("asxos.domain.portfolio.build.load_active", _profile)
    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=_route_fetch(_ONE_APPROVED_MODEL, []))

    with pytest.raises(RuntimeError, match="no signals"):
        await PortfolioService().build(conn, as_of=_BUILD_DATE)
