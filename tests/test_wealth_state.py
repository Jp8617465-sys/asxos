"""
Tests for the wealth_state brief collector's concentration denominator.

The per-holding concentration % must use the priced per-holding MVs as the
denominator (same source as the numerator), not the snapshot holdings_mv_aud,
which may be derived from a different price date/source.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from asxos.domain.brief.collectors.wealth_state import collect_wealth_state
from asxos.domain.brief.types import SeverityLevel


def _snapshot(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "capital_aud": Decimal("210"),
        # NOTE: snapshot total MV (200) deliberately != priced sum (100) below,
        # so the test distinguishes the two possible denominators.
        "holdings_mv_aud": Decimal("200"),
        "cash_aud": Decimal("10"),
        "us_holdings_mv_aud": None,
        "us_holdings_cost_aud": None,
        "fx_rate_audusd": None,
        "unrealised_fx_pnl_aud": None,
        "benchmark_tr_level": None,
        "trailing_div_yield_pct": None,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_concentration_uses_priced_sum_not_snapshot_mv() -> None:
    conn = AsyncMock()
    # fetchrow: (1) snapshot, (2) peak (None → drawdown skipped).
    conn.fetchrow = AsyncMock(side_effect=[_snapshot(), {"peak": None}])
    # fetch: priced holdings summing to 100 (60 + 40), NOT 200
    conn.fetch = AsyncMock(
        return_value=[
            {"symbol": "CBA.AU", "mv_local": Decimal("60")},
            {"symbol": "BHP.AU", "mv_local": Decimal("40")},
        ]
    )

    result = await collect_wealth_state(conn, __import__("datetime").date(2026, 6, 1))

    # CBA is 60/100 = 60% (red) against the priced sum; against the snapshot's 200
    # it would have been only 30% (yellow). A red "concentrated position" item with
    # 60.0% proves the denominator is the priced sum.
    conc = [i for i in result.items if "concentrated position" in i.message]
    assert any("CBA.AU: 60.0%" in i.message and i.level == SeverityLevel.red for i in conc)


@pytest.mark.asyncio
async def test_no_false_return_line_from_capital_diff() -> None:
    """Regression: the removed 'Portfolio vs XJO-TR · alpha' line differenced a
    flow-affected capital_aud balance and reported a false −75.7% loss + bogus
    alpha. Even with a benchmark level present on the snapshot, NO
    return/alpha/benchmark line renders now — the honest broker-matching
    unrealised return lives in the V1 discipline section instead
    (asxos/domain/theses/discipline.py::unrealised_return).
    """
    conn = AsyncMock()
    snapshot = _snapshot(
        capital_aud=Decimal("7707"),
        benchmark_tr_level=Decimal("11427"),
    )
    # Two fetchrow calls now (snapshot, peak) — the inception-anchor query is gone.
    conn.fetchrow = AsyncMock(side_effect=[snapshot, {"peak": None}])
    conn.fetch = AsyncMock(return_value=[])

    result = await collect_wealth_state(conn, __import__("datetime").date(2026, 7, 16))
    joined = " ".join(i.message for i in result.items)
    for banned in ("XJO-TR", "alpha", "Portfolio +", "Portfolio -", "lagging"):
        assert banned not in joined


@pytest.mark.asyncio
async def test_holdings_price_join_is_latest_close_not_exact_date() -> None:
    """Register #8 (2026-08-09 red-team): the holdings join must take the latest
    close ON OR BEFORE the brief date. The brief's calendar as_of is always ahead
    of the newest price row, so an exact `p.dt = $1` join returned zero holdings
    on every brief and the concentration RED (a 100% single-name book!) could
    never render. Text-level pin on the emitted SQL."""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[_snapshot(), {"peak": None}])
    conn.fetch = AsyncMock(return_value=[])

    await collect_wealth_state(conn, __import__("datetime").date(2026, 6, 1))

    holdings_sql = conn.fetch.await_args.args[0]
    assert "dt <= $1" in holdings_sql, "holdings join regressed to an exact-date match"
    assert "p.dt = $1" not in holdings_sql
    assert "LATERAL" in holdings_sql
