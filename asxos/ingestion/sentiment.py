"""
Sentiment ingestion — M14b (REV-K, 2026-05-24).

REV-K pivot: EODHD /sentiments has no ASX coverage on the Fundamentals Data Feed tier.
signal_sentiment is now populated by SQL aggregation from holding_news.sentiment_polarity
in jobs/ingest_sentiment.py — NOT from a /sentiments API call.

parse_sentiment_response() was removed (dead code — written for /sentiments which returns
empty for all ASX symbols). See scratch/m14_backfill_report.md for the discovery context.

Remaining exports:
  SentimentEntry         — dataclass for a single (symbol, as_of) sentiment row
  upsert_sentiment()     — UPSERT into signal_sentiment; called by future M14c/M14d layers
                           (ingest_sentiment.py currently runs aggregation SQL directly)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import asyncpg


@dataclass(frozen=True)
class SentimentEntry:
    symbol: str
    as_of: date
    mention_count: int
    sentiment_normalised: Decimal  # NUMERIC(8,6); abs <= 1.5 guaranteed by source


async def upsert_sentiment(conn: asyncpg.Connection, entries: list[SentimentEntry]) -> int:
    """UPSERT signal_sentiment rows.  On (symbol, as_of) conflict, updates values.

    Returns the number of rows processed (inserted or updated).
    Uses executemany for batch efficiency (mirrors ingest_regulatory pattern).
    sentiment_normalised is passed as text and cast to NUMERIC(8,6) by Postgres.
    """
    if not entries:
        return 0

    payload = [
        (
            entry.symbol,
            entry.as_of,
            entry.mention_count,
            str(entry.sentiment_normalised),   # text → Postgres NUMERIC(8,6)
        )
        for entry in entries
    ]

    await conn.executemany(
        """
        INSERT INTO signal_sentiment (symbol, as_of, mention_count, sentiment_normalised)
        VALUES ($1, $2, $3, $4::numeric)
        ON CONFLICT (symbol, as_of) DO UPDATE SET
            mention_count        = EXCLUDED.mention_count,
            sentiment_normalised = EXCLUDED.sentiment_normalised,
            ingested_at          = NOW()
        """,
        payload,
    )
    return len(payload)
