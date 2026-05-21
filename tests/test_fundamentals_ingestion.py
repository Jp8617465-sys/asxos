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
    from unittest.mock import AsyncMock, patch

    with patch("jobs.sync_fundamentals.fetch_and_upsert_fundamentals", side_effect=Exception("API down")):
        with patch("jobs.sync_fundamentals.acquire") as mock_acquire:
            mock_conn = AsyncMock()
            mock_acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)

            from jobs.sync_fundamentals import sync_symbol
            from datetime import date
            result = await sync_symbol("XYZ.AU", date.today())

    assert result is False
