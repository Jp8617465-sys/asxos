"""
Sentiment ingestion from EODHD /sentiments (M14b).

Parse + upsert pattern mirrors asxos/ingestion/news.py.

Pure functions:  parse_sentiment_response(), (validation helpers inline).
Async I/O:       upsert_sentiment().

EODHD /sentiments response shape (per item):
  {
    "date":       "2026-05-23",    # ISO date string (NOT datetime like /news)
    "count":      42,              # mention volume for that day
    "normalized": 0.31,            # daily-aggregated sentiment ∈ [-1, +1] approx
  }

Gotchas:
  1. normalized is a float — cast to Decimal(str(val)) immediately on parse
  2. Hard-fail if abs(sentiment_normalised) > Decimal("1.5") (rule #10 / non-negotiable)
  3. date field is ISO date string — fromisoformat(raw[:10]) (same [:10] guard as news)
  4. count may be absent or None — default to 0 rather than drop the row
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import asyncpg

_NORMALISED_LIMIT = Decimal("1.5")


@dataclass(frozen=True)
class SentimentEntry:
    symbol: str
    as_of: date
    mention_count: int
    sentiment_normalised: Decimal  # Decimal(str(raw_float)); abs <= 1.5 guaranteed


def parse_sentiment_response(
    raw: list[dict],
    *,
    symbol: str,
    holdings: set[str],
) -> list[SentimentEntry]:
    """Parse EODHD /sentiments response into SentimentEntry records.

    Validates that abs(normalized) <= 1.5 — hard-fails on violation (rule #10).
    Skips rows for symbols not in holdings.
    Deduplicates by as_of within the batch (keeps first occurrence).
    """
    if symbol not in holdings:
        return []

    seen_dates: set[date] = set()
    out: list[SentimentEntry] = []

    for item in raw:
        # Parse date — EODHD returns bare ISO date strings for /sentiments.
        raw_date = item.get("date") or ""
        try:
            as_of = date.fromisoformat(str(raw_date)[:10])
        except (ValueError, TypeError):
            continue  # unparseable date — skip silently

        # Deduplicate within the batch.
        if as_of in seen_dates:
            continue
        seen_dates.add(as_of)

        # mention_count — default to 0 if absent.
        raw_count = item.get("count")
        try:
            mention_count = int(raw_count) if raw_count is not None else 0
        except (TypeError, ValueError):
            mention_count = 0

        # normalized — must be present; cast to Decimal immediately.
        raw_normalised = item.get("normalized")
        if raw_normalised is None:
            continue  # no signal value; skip row

        try:
            normalised = Decimal(str(raw_normalised))
        except Exception as exc:
            raise ValueError(
                f"Cannot parse sentiment_normalised={raw_normalised!r} for {symbol}: {exc}"
            ) from exc

        # Hard-fail on out-of-range values (rule #10 — no graceful warnings in infra code).
        if abs(normalised) > _NORMALISED_LIMIT:
            raise ValueError(
                f"sentiment_normalised={normalised} for {symbol} on {as_of} "
                f"is outside [-1.5, 1.5] — hard-fail per rule #10"
            )

        out.append(
            SentimentEntry(
                symbol=symbol,
                as_of=as_of,
                mention_count=mention_count,
                sentiment_normalised=normalised,
            )
        )

    return out


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
