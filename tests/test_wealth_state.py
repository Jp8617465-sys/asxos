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
    # fetchrow: (1) snapshot, (2) peak (None → drawdown skipped), (3) inception
    # (None → benchmark line omitted).
    conn.fetchrow = AsyncMock(side_effect=[_snapshot(), {"peak": None}, None])
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
async def test_benchmark_line_rendered_since_inception() -> None:
    # Current snapshot: capital 210, benchmark_tr_level 7140 (approx path).
    # Inception: capital 200, benchmark_tr_level 7000.
    # Portfolio +5.0%, XJO-TR +2.0% → alpha +3.0% (positive → green).
    conn = AsyncMock()
    snapshot = _snapshot(
        capital_aud=Decimal("210"),
        benchmark_tr_level=Decimal("7140"),
        trailing_div_yield_pct=Decimal("4.0"),
    )
    inception = {
        "as_of": __import__("datetime").date(2026, 1, 1),
        "capital_aud": Decimal("200"),
        "benchmark_tr_level": Decimal("7000"),
    }
    conn.fetchrow = AsyncMock(side_effect=[snapshot, {"peak": None}, inception])
    conn.fetch = AsyncMock(return_value=[])

    result = await collect_wealth_state(conn, __import__("datetime").date(2026, 6, 1))

    bench = [i for i in result.items if "XJO-TR" in i.message]
    assert len(bench) == 1
    msg = bench[0].message
    assert "Portfolio +5.0%" in msg
    assert "XJO-TR approx +2.0%" in msg  # approx flag from non-NULL trailing yield
    assert "alpha +3.0%" in msg
    assert bench[0].level == SeverityLevel.green


@pytest.mark.asyncio
async def test_benchmark_line_omitted_when_no_benchmark_data() -> None:
    # benchmark_tr_level NULL on the current snapshot → no benchmark line at all
    # (self-healing: appears once Stage 1 backfills).
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[_snapshot(), {"peak": None}, None])
    conn.fetch = AsyncMock(return_value=[])

    result = await collect_wealth_state(conn, __import__("datetime").date(2026, 6, 1))
    assert not any("XJO-TR" in i.message for i in result.items)


@pytest.mark.asyncio
async def test_benchmark_underperformance_is_yellow() -> None:
    # Portfolio flat, benchmark up → negative alpha → yellow.
    conn = AsyncMock()
    snapshot = _snapshot(
        capital_aud=Decimal("200"),
        benchmark_tr_level=Decimal("7350"),
        trailing_div_yield_pct=None,  # real-index path → no "approx" flag
    )
    inception = {
        "as_of": __import__("datetime").date(2026, 1, 1),
        "capital_aud": Decimal("200"),
        "benchmark_tr_level": Decimal("7000"),
    }
    conn.fetchrow = AsyncMock(side_effect=[snapshot, {"peak": None}, inception])
    conn.fetch = AsyncMock(return_value=[])

    result = await collect_wealth_state(conn, __import__("datetime").date(2026, 6, 1))
    bench = [i for i in result.items if "XJO-TR" in i.message]
    assert len(bench) == 1
    assert bench[0].level == SeverityLevel.yellow
    assert "XJO-TR +5.0%" in bench[0].message  # no "approx" on the real-index path
    assert "alpha -5.0%" in bench[0].message
