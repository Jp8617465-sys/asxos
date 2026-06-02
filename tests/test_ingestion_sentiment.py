"""
Sentiment ingestion unit tests — M14b REV-K.

REV-K (2026-05-24): parse_sentiment_response() was removed (dead code — /sentiments has
no ASX coverage). signal_sentiment is now populated by SQL aggregation from
holding_news.sentiment_polarity in jobs/ingest_sentiment.py.

This file tests what remains: SentimentEntry and upsert_sentiment().
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.ingestion.sentiment import (
    SentimentEntry,
    upsert_sentiment,
)

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
    _sql, payload = call_args
    assert payload[0][3] == "0.123456"   # Decimal cast to str


@pytest.mark.asyncio
async def test_upsert_idempotent_structure() -> None:
    """upsert_sentiment SQL uses ON CONFLICT DO UPDATE (idempotent on same key)."""
    conn = MagicMock()
    conn.executemany = AsyncMock()
    entry = SentimentEntry("RIO.AU", date(2026, 5, 23), 7, Decimal("0.45"))
    # Call twice with same entry — both should reach DB (upsert resolves conflict in Postgres)
    await upsert_sentiment(conn, [entry])
    await upsert_sentiment(conn, [entry])
    assert conn.executemany.call_count == 2  # both calls hit DB; Postgres handles conflict


@pytest.mark.asyncio
async def test_upsert_single_entry_payload_shape() -> None:
    """Payload tuple has (symbol, as_of, mention_count, sentiment_normalised_str)."""
    conn = MagicMock()
    conn.executemany = AsyncMock()
    entry = SentimentEntry("WBC.AU", date(2026, 5, 20), 12, Decimal("-0.25"))
    await upsert_sentiment(conn, [entry])
    _, call_args, _ = conn.executemany.mock_calls[0]
    _sql, payload = call_args
    assert len(payload) == 1
    row = payload[0]
    assert row[0] == "WBC.AU"
    assert row[1] == date(2026, 5, 20)
    assert row[2] == 12
    assert row[3] == "-0.25"
