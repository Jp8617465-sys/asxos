"""Tests for asxos/domain/portfolio/volatility.py — load_vols_for_symbols.

Mocks asyncpg connections; no real DB required.
asyncio_mode = "auto" in pyproject.toml — no @pytest.mark.asyncio needed.

Focus: the async batch loader's three untested branches —
  1. empty-symbols early return (no DB call at all)
  2. per-symbol grouping of flat ANY($1) rows into per-symbol close lists
  3. insufficient-history silent omit (symbol dropped, not raised)

This module is pure-Decimal + asyncpg only (no numpy/lightgbm/fastapi), so it
collects cleanly in the bare sandbox as well as in CI.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from asxos.domain.portfolio.volatility import load_vols_for_symbols

_AS_OF = date(2026, 6, 28)


def _make_conn(rows: list[dict]) -> MagicMock:
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)
    return conn


def _price_rows(symbol: str, n: int, *, start: float = 100.0) -> list[dict]:
    """n rows for `symbol`, gently trending so log returns are well-defined."""
    return [{"symbol": symbol, "close": Decimal(str(start + i))} for i in range(n)]


async def test_empty_symbols_returns_empty_without_db_call():
    conn = _make_conn([])
    result = await load_vols_for_symbols(conn, [], _AS_OF, window_days=60)

    assert result == {}
    # Early return MUST short-circuit before touching the DB.
    conn.fetch.assert_not_called()


async def test_groups_flat_rows_by_symbol_and_computes_vol():
    # window_days=5 needs 6 closes per symbol. Two symbols interleaved-then-grouped.
    rows = _price_rows("AAA.AU", 6, start=100.0) + _price_rows("BBB.AU", 6, start=50.0)
    conn = _make_conn(rows)

    result = await load_vols_for_symbols(conn, ["AAA.AU", "BBB.AU"], _AS_OF, window_days=5)

    assert set(result) == {"AAA.AU", "BBB.AU"}
    assert all(isinstance(v, Decimal) for v in result.values())
    assert all(v >= Decimal("0") for v in result.values())

    # Verify the query was issued with the symbols list, as_of, and window+1 cap.
    conn.fetch.assert_awaited_once()
    args = conn.fetch.await_args.args
    assert args[1] == ["AAA.AU", "BBB.AU"]
    assert args[2] == _AS_OF
    assert args[3] == 6  # window_days + 1


async def test_insufficient_history_symbol_silently_omitted():
    # GOOD has enough closes (6 for window 5); SHORT has only 3 → dropped, not raised.
    rows = _price_rows("GOOD.AU", 6) + _price_rows("SHORT.AU", 3)
    conn = _make_conn(rows)

    result = await load_vols_for_symbols(conn, ["GOOD.AU", "SHORT.AU"], _AS_OF, window_days=5)

    assert "GOOD.AU" in result
    assert "SHORT.AU" not in result  # silently omitted, no exception


async def test_invalid_close_symbol_omitted_not_raised():
    # A non-positive close makes annualised_vol raise ValueError → symbol dropped.
    bad = [{"symbol": "BAD.AU", "close": Decimal("0")} for _ in range(6)]
    conn = _make_conn(bad)

    result = await load_vols_for_symbols(conn, ["BAD.AU"], _AS_OF, window_days=5)

    assert result == {}
