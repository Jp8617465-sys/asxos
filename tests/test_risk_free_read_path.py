"""Pins on ke's risk-free source after it moved to the point-in-time series (#301).

`market_context_current` and `risk_free_rates` carry the SAME FRED series — see
`capm.RISK_FREE_LABEL`, which is explicit that the daily table holds "a MONTHLY
series carried forward". The difference is that the daily table forward-fills it
and only begins 2026-07-03, so it could not answer "what was the rate at a 2025
cutoff", and the sealed value-to-price replay hard-failed on exactly that.

That equivalence was verified live before the switch rather than assumed: on
2026-09-16 `market_context_current`'s latest value and `risk_free_rates`'
2026-08-01 observation are both 5.015 — the same number, because one is the
other carried forward.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from asxos.domain.valuation import capm, universe
from asxos.domain.valuation.inputs import assert_valuation_sql_admissible


class _Conn:
    """Records what was asked for, and answers only the risk-free query."""

    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        self.calls.append((query, args))
        if "risk_free_rates" in query:
            return self.row
        if "fx_rates" in query:
            return {"dt": date(2025, 3, 31), "rate": Decimal("0.63")}
        return None

    async def fetch(self, query: str, *a: object, **k: object) -> list[Any]:
        return []


def test_the_risk_free_query_names_the_pit_series_not_the_daily_table() -> None:
    sql = universe.SQL_RISK_FREE_LATEST
    assert "risk_free_rates" in sql
    assert "market_context_current" not in sql
    # Filtered by series, so a later daily series in the same table cannot be
    # silently mixed into the monthly one.
    assert "series = $2" in sql


def test_the_series_id_is_shared_not_written_twice() -> None:
    assert capm.RISK_FREE_SERIES_ID == "IRLTLT01AUM156N"
    assert capm.RISK_FREE_SERIES == f"FRED {capm.RISK_FREE_SERIES_ID}"


def test_the_query_still_clears_the_rule_11_screen() -> None:
    """A new table in the valuation read path must be admitted deliberately."""
    assert_valuation_sql_admissible(universe.SQL_RISK_FREE_LATEST)


@pytest.mark.asyncio
async def test_percent_is_converted_to_a_fraction_once() -> None:
    conn = _Conn({"as_of": date(2025, 3, 1), "aus_10y_yield": Decimal("4.421")})
    market = await universe.load_market_inputs(conn, cutoff_date=date(2025, 3, 31))

    assert market.risk_free == Decimal("0.04421")
    assert market.risk_free_as_of == date(2025, 3, 1)


@pytest.mark.asyncio
async def test_the_series_id_is_bound_as_a_parameter() -> None:
    conn = _Conn({"as_of": date(2025, 3, 1), "aus_10y_yield": Decimal("4.421")})
    await universe.load_market_inputs(conn, cutoff_date=date(2025, 3, 31))

    rf_call = next(c for c in conn.calls if "risk_free_rates" in c[0])
    assert rf_call[1] == (date(2025, 3, 31), capm.RISK_FREE_SERIES_ID)


@pytest.mark.asyncio
async def test_a_missing_observation_hard_fails_and_names_the_backfill() -> None:
    """Never substitute a later rate at an earlier cutoff — that is look-ahead."""
    conn = _Conn(None)
    with pytest.raises(RuntimeError, match="backfill_risk_free"):
        await universe.load_market_inputs(conn, cutoff_date=date(2025, 3, 31))
