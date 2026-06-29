"""
Tests for fundamentals ingestion.
No network calls — EODHDClient is mocked.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from asxos.ingestion.fundamentals import parse_fundamentals

# ---------------------------------------------------------------------------
# parse_fundamentals — happy path
# ---------------------------------------------------------------------------

_FULL_RESPONSE = {
    "General": {
        "Sector": "Financial Services",
    },
    "Highlights": {
        "PERatio": "12.5",
        "EarningsShare": "3.20",
        "DividendYield": "0.045",
        "MarketCapitalization": 150_000_000_000,
    },
    "Valuation": {
        "PriceBookMRQ": "1.80",
    },
    "SharesStats": {
        "SharesOutstanding": "5000000000",
    },
}


def test_parse_full_response():
    f = parse_fundamentals(_FULL_RESPONSE)
    assert f["pe_ratio"] == Decimal("12.5")
    assert f["pb_ratio"] == Decimal("1.80")
    assert f["eps"] == Decimal("3.20")
    assert f["dividend_yield"] == Decimal("0.045")
    assert f["market_cap"] == Decimal("150000000000")
    assert f["shares_outstanding"] == 5_000_000_000
    assert f["sector"] == "Financial Services"


# ---------------------------------------------------------------------------
# parse_fundamentals — missing / malformed fields → None, no raise
# ---------------------------------------------------------------------------

def test_parse_empty_response():
    f = parse_fundamentals({})
    assert f["pe_ratio"] is None
    assert f["pb_ratio"] is None
    assert f["eps"] is None
    assert f["market_cap"] is None
    assert f["shares_outstanding"] is None
    assert f["dividend_yield"] is None
    assert f["sector"] is None


def test_parse_blank_sector():
    """Whitespace-only or empty General.Sector parses to None, not ''."""
    raw = {**_FULL_RESPONSE, "General": {"Sector": "   "}}
    assert parse_fundamentals(raw)["sector"] is None
    raw = {**_FULL_RESPONSE, "General": {"Sector": ""}}
    assert parse_fundamentals(raw)["sector"] is None


def test_parse_trillion_dollar_market_cap_preserved():
    # A >10^12 market cap (the value that overflows NUMERIC(18,6) and motivates
    # migration 0029 widening to NUMERIC(24,6)) parses to the exact Decimal with
    # no loss. Overflow itself is a DB-write concern; this pins that the value
    # flows through the parser intact, so the widened column receives it whole.
    raw = {**_FULL_RESPONSE, "Highlights": {**_FULL_RESPONSE["Highlights"],
                                            "MarketCapitalization": 3_500_000_000_000}}
    assert parse_fundamentals(raw)["market_cap"] == Decimal("3500000000000")


def test_parse_null_pe_ratio():
    raw = {**_FULL_RESPONSE, "Highlights": {**_FULL_RESPONSE["Highlights"], "PERatio": None}}
    f = parse_fundamentals(raw)
    assert f["pe_ratio"] is None


def test_parse_string_none_value():
    raw = {**_FULL_RESPONSE, "Highlights": {**_FULL_RESPONSE["Highlights"], "PERatio": "None"}}
    f = parse_fundamentals(raw)
    assert f["pe_ratio"] is None


def test_parse_nan_value():
    raw = {**_FULL_RESPONSE, "Highlights": {**_FULL_RESPONSE["Highlights"], "PERatio": float("nan")}}
    f = parse_fundamentals(raw)
    assert f["pe_ratio"] is None


def test_parse_malformed_shares():
    raw = {**_FULL_RESPONSE, "SharesStats": {"SharesOutstanding": "N/A"}}
    f = parse_fundamentals(raw)
    assert f["shares_outstanding"] is None


# ---------------------------------------------------------------------------
# sync_fundamentals — one symbol failure does not abort the run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_symbol_failure_does_not_raise():
    """sync_symbol catches all exceptions and returns False without propagating."""
    from unittest.mock import AsyncMock, MagicMock, patch

    with patch("jobs.sync_fundamentals.get_client", return_value=MagicMock()):
        with patch("jobs.sync_fundamentals.fetch_and_upsert_fundamentals", side_effect=Exception("API down")):
         with patch("jobs.sync_fundamentals.acquire") as mock_acquire:
            mock_conn = AsyncMock()
            mock_acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)

            from datetime import date

            from jobs.sync_fundamentals import sync_symbol
            result = await sync_symbol("XYZ.AU", date.today())

    assert result is False


# ---------------------------------------------------------------------------
# propagate_market_cap_to_universe — copies latest fundamentals → universe cache
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_propagate_market_cap_returns_rowcount():
    """Returns the rows-updated count parsed from the asyncpg command tag."""
    from unittest.mock import AsyncMock

    from asxos.ingestion.fundamentals import propagate_market_cap_to_universe

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 1843")

    n = await propagate_market_cap_to_universe(conn)

    assert n == 1843
    # Direction + idempotency contract: writes universe.market_cap from
    # fundamentals, only where the value actually changes.
    sql = conn.execute.call_args[0][0]
    assert "UPDATE universe" in sql
    assert "fundamentals" in sql
    assert "market_cap" in sql
    assert "IS DISTINCT FROM" in sql


@pytest.mark.asyncio
async def test_propagate_market_cap_zero_when_no_change():
    """Idempotent re-run updates nothing → returns 0."""
    from unittest.mock import AsyncMock

    from asxos.ingestion.fundamentals import propagate_market_cap_to_universe

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 0")

    assert await propagate_market_cap_to_universe(conn) == 0


# ---------------------------------------------------------------------------
# propagate_sector_to_universe — copies latest fundamentals.sector → universe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_propagate_sector_returns_rowcount():
    """Returns the rows-updated count parsed from the asyncpg command tag."""
    from unittest.mock import AsyncMock

    from asxos.ingestion.fundamentals import propagate_sector_to_universe

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 1843")

    n = await propagate_sector_to_universe(conn)

    assert n == 1843
    # Direction + idempotency contract: writes universe.sector from
    # fundamentals, ignores blank sectors, only where the value changes.
    sql = conn.execute.call_args[0][0]
    assert "UPDATE universe" in sql
    assert "fundamentals" in sql
    assert "sector" in sql
    assert "sector <> ''" in sql
    assert "IS DISTINCT FROM" in sql


@pytest.mark.asyncio
async def test_propagate_sector_zero_when_no_change():
    """Idempotent re-run updates nothing → returns 0."""
    from unittest.mock import AsyncMock

    from asxos.ingestion.fundamentals import propagate_sector_to_universe

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="UPDATE 0")

    assert await propagate_sector_to_universe(conn) == 0
