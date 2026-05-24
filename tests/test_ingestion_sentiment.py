"""
Sentiment ingestion unit tests — M14b.

Pure function tests: parse_sentiment_response(), upsert_sentiment() (mocked conn).
No network, no DB.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.ingestion.sentiment import (
    SentimentEntry,
    parse_sentiment_response,
    upsert_sentiment,
)

HOLDINGS = {"BHP.AU", "CBA.AU", "RIO.AU"}


# ---------------------------------------------------------------------------
# parse_sentiment_response — pure function tests
# ---------------------------------------------------------------------------


def _raw(symbol: str = "BHP.AU", dt: str = "2026-05-23", count: int = 15, normalized: float = 0.31) -> dict:
    return {"date": dt, "count": count, "normalized": normalized}


def test_parse_round_trip() -> None:
    """Standard EODHD row maps to SentimentEntry correctly."""
    entries = parse_sentiment_response([_raw()], symbol="BHP.AU", holdings=HOLDINGS)
    assert len(entries) == 1
    e = entries[0]
    assert e.symbol == "BHP.AU"
    assert e.as_of == date(2026, 5, 23)
    assert e.mention_count == 15
    assert e.sentiment_normalised == Decimal("0.31")


def test_parse_normalised_stored_as_decimal() -> None:
    """sentiment_normalised is Decimal, not float."""
    entries = parse_sentiment_response([_raw(normalized=0.123456)], symbol="BHP.AU", holdings=HOLDINGS)
    assert isinstance(entries[0].sentiment_normalised, Decimal)


def test_parse_symbol_not_in_holdings_returns_empty() -> None:
    """Symbol outside holdings set → empty list (not just filtered row)."""
    entries = parse_sentiment_response([_raw()], symbol="ZZZ.AU", holdings=HOLDINGS)
    assert entries == []


def test_parse_normalised_out_of_range_raises() -> None:
    """abs(normalized) > 1.5 → ValueError (hard-fail, rule #10)."""
    with pytest.raises(ValueError, match="outside \\[-1.5, 1.5\\]"):
        parse_sentiment_response([_raw(normalized=1.6)], symbol="BHP.AU", holdings=HOLDINGS)


def test_parse_normalised_negative_out_of_range_raises() -> None:
    """Negative extreme also hard-fails."""
    with pytest.raises(ValueError):
        parse_sentiment_response([_raw(normalized=-1.51)], symbol="BHP.AU", holdings=HOLDINGS)


def test_parse_normalised_at_limit_passes() -> None:
    """Exactly ±1.5 is allowed (boundary is inclusive)."""
    entries = parse_sentiment_response([_raw(normalized=1.5)], symbol="BHP.AU", holdings=HOLDINGS)
    assert len(entries) == 1
    assert entries[0].sentiment_normalised == Decimal("1.5")


def test_parse_negative_sentiment() -> None:
    """Negative normalised values round-trip correctly."""
    entries = parse_sentiment_response([_raw(normalized=-0.75)], symbol="BHP.AU", holdings=HOLDINGS)
    assert entries[0].sentiment_normalised == Decimal("-0.75")


def test_parse_deduplicates_by_date() -> None:
    """Same date appearing twice → only first occurrence kept."""
    raw = [_raw(dt="2026-05-23", normalized=0.1), _raw(dt="2026-05-23", normalized=0.9)]
    entries = parse_sentiment_response(raw, symbol="BHP.AU", holdings=HOLDINGS)
    assert len(entries) == 1
    assert entries[0].sentiment_normalised == Decimal("0.1")


def test_parse_multiple_dates() -> None:
    """Multiple distinct dates produce multiple entries."""
    raw = [_raw(dt="2026-05-21"), _raw(dt="2026-05-22"), _raw(dt="2026-05-23")]
    entries = parse_sentiment_response(raw, symbol="BHP.AU", holdings=HOLDINGS)
    assert len(entries) == 3
    dates = {e.as_of for e in entries}
    assert dates == {date(2026, 5, 21), date(2026, 5, 22), date(2026, 5, 23)}


def test_parse_missing_normalized_skips_row() -> None:
    """Row with normalized=None is silently skipped."""
    raw = [{"date": "2026-05-23", "count": 5, "normalized": None}]
    entries = parse_sentiment_response(raw, symbol="BHP.AU", holdings=HOLDINGS)
    assert entries == []


def test_parse_missing_count_defaults_to_zero() -> None:
    """count absent → mention_count=0 (doesn't drop the row)."""
    raw = [{"date": "2026-05-23", "normalized": 0.2}]
    entries = parse_sentiment_response(raw, symbol="BHP.AU", holdings=HOLDINGS)
    assert len(entries) == 1
    assert entries[0].mention_count == 0


def test_parse_unparseable_date_skips_row() -> None:
    """Unparseable date field → row silently skipped."""
    raw = [{"date": "not-a-date", "count": 5, "normalized": 0.3}]
    entries = parse_sentiment_response(raw, symbol="BHP.AU", holdings=HOLDINGS)
    assert entries == []


def test_parse_empty_raw_returns_empty() -> None:
    """Empty EODHD response → empty list (no crash)."""
    entries = parse_sentiment_response([], symbol="BHP.AU", holdings=HOLDINGS)
    assert entries == []


def test_parse_datetime_string_sliced_to_date() -> None:
    """EODHD date field as ISO datetime string — sliced to date correctly."""
    raw = [{"date": "2026-05-23T00:00:00+00:00", "count": 10, "normalized": 0.5}]
    entries = parse_sentiment_response(raw, symbol="BHP.AU", holdings=HOLDINGS)
    assert entries[0].as_of == date(2026, 5, 23)


# ---------------------------------------------------------------------------
# upsert_sentiment — with mocked asyncpg connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_returns_row_count() -> None:
    """upsert_sentiment returns number of entries processed."""
    conn = MagicMock()
    conn.executemany = AsyncMock()
    entries = [
        SentimentEntry("BHP.AU", date(2026, 5, 23), 10, Decimal("0.3")),
        SentimentEntry("BHP.AU", date(2026, 5, 22), 5, Decimal("-0.1")),
    ]
    result = await upsert_sentiment(conn, entries)
    assert result == 2
    assert conn.executemany.call_count == 1


@pytest.mark.asyncio
async def test_upsert_empty_list_returns_zero() -> None:
    """Empty entries list → returns 0, no DB call."""
    conn = MagicMock()
    conn.executemany = AsyncMock()
    result = await upsert_sentiment(conn, [])
    assert result == 0
    conn.executemany.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_passes_decimal_as_string() -> None:
    """upsert_sentiment passes sentiment_normalised as str (for ::numeric cast)."""
    conn = MagicMock()
    conn.executemany = AsyncMock()
    entry = SentimentEntry("CBA.AU", date(2026, 5, 23), 3, Decimal("0.123456"))
    await upsert_sentiment(conn, [entry])
    _, call_args, _ = conn.executemany.mock_calls[0]
    sql, payload = call_args
    assert payload[0][3] == "0.123456"   # Decimal cast to str
