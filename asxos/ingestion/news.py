"""
News ingestion from EODHD /news (M14a).

Parse + upsert pattern mirrors asxos/ingestion/regulatory.py.

Pure functions: parse_news_response(), _parse_sentiment(), _normalise_symbol().
Async I/O:      upsert_news().

EODHD /news response shape (per item):
  {
    "date":     "2026-05-23T04:30:00+00:00",   # ISO datetime string — always slice [:10]
    "title":    "BHP Q1 Results ...",
    "link":     "https://...",
    "symbols":  ["BHP.AU", "RIO.AU"],          # may lack .AU suffix
    "sentiment": {"polarity": "Positive"}       # or a plain string, or absent
    "content":  "Full article text ...",
  }

Gotchas:
  1. date is ISO datetime string → always slice [:10] before fromisoformat()
  2. sentiment shape varies by plan tier — use _parse_sentiment() always
  3. symbols may lack .AU suffix — normalise with _normalise_symbol()
  4. content may be absent — use content_snippet = (content or "")[:500]
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta

import asyncpg


@dataclass(frozen=True)
class NewsItem:
    url: str
    title: str
    published_at: date
    symbols: list[str]   # normalised to BHP.AU format, intersection with holdings
    sentiment: str       # "positive" | "negative" | "neutral" | ""
    content_snippet: str


def _parse_sentiment(raw_item: dict) -> str:
    """EODHD sentiment is nested dict on some plan tiers, a plain string or absent on others."""
    s = raw_item.get("sentiment")
    if isinstance(s, dict):
        return (s.get("polarity") or "").lower()
    return (s or "").lower() if isinstance(s, str) else ""


def _normalise_symbol(sym: str) -> str:
    """Append .AU suffix when the symbol has no exchange suffix and is ≤5 chars."""
    if "." not in sym and len(sym) <= 5:
        return f"{sym}.AU"
    return sym


def parse_news_response(
    raw: list[dict],
    *,
    holdings: set[str],
    as_of: date,
) -> list[NewsItem]:
    """Parse EODHD /news response into NewsItem records.

    Filters to items:
      - published within the last 2 days of as_of (belt-and-suspenders;
        paid tiers honour the ``from`` param but we validate locally)
      - whose normalised symbols overlap with the current holdings set

    Deduplicates by URL within the batch.
    Returns results in input order (caller can sort if needed).
    """
    cutoff = as_of - timedelta(days=2)
    seen_urls: set[str] = set()
    out: list[NewsItem] = []

    for item in raw:
        url = (item.get("link") or item.get("url") or "").strip()
        title = (item.get("title") or "").strip()
        if not url or not title:
            continue

        # Deduplicate within the batch.
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Parse published date — EODHD returns ISO datetime strings.
        raw_date = item.get("date") or item.get("published_at") or ""
        try:
            pub_date = date.fromisoformat(str(raw_date)[:10])
        except (ValueError, TypeError):
            pub_date = as_of  # fall back to today rather than drop the item

        # Staleness filter: drop items older than 2 days from as_of.
        if pub_date < cutoff:
            continue

        # Normalise symbols and intersect with current holdings.
        raw_symbols = item.get("symbols") or []
        if isinstance(raw_symbols, str):
            try:
                raw_symbols = json.loads(raw_symbols)
            except (json.JSONDecodeError, ValueError):
                raw_symbols = [raw_symbols] if raw_symbols else []

        normalised = [_normalise_symbol(s) for s in raw_symbols if isinstance(s, str) and s]
        matched = [s for s in normalised if s in holdings]
        if not matched:
            continue  # item is not relevant to any current holding

        # Content snippet — capped at 500 chars.
        content = item.get("content") or item.get("summary") or ""
        content_snippet = str(content)[:500]

        out.append(
            NewsItem(
                url=url,
                title=title,
                published_at=pub_date,
                symbols=matched,
                sentiment=_parse_sentiment(item),
                content_snippet=content_snippet,
            )
        )

    return out


async def upsert_news(conn: asyncpg.Connection, items: list[NewsItem]) -> int:
    """UPSERT holding_news rows.  On URL conflict, merges the symbols arrays.

    Returns the number of rows processed (inserted or updated).
    Uses executemany for batch efficiency (mirrors ingest_regulatory pattern).

    The symbols merge SQL is a PostgreSQL JSONB set-union:
      jsonb_agg(DISTINCT sym ORDER BY sym) over the union of old + new symbols.
    """
    if not items:
        return 0

    payload = [
        (
            item.url,
            item.title,
            item.published_at,
            json.dumps(item.symbols),   # passed as JSON string, cast to JSONB via $4::jsonb
            item.sentiment,
            item.content_snippet,
        )
        for item in items
    ]

    await conn.executemany(
        """
        INSERT INTO holding_news (url, title, published_at, symbols, sentiment, content_snippet)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6)
        ON CONFLICT (url) DO UPDATE SET
            symbols = (
                SELECT jsonb_agg(DISTINCT sym ORDER BY sym)
                FROM (
                    SELECT jsonb_array_elements_text(holding_news.symbols) AS sym
                    UNION
                    SELECT jsonb_array_elements_text(EXCLUDED.symbols)
                ) merged
            ),
            sentiment   = EXCLUDED.sentiment,
            ingested_at = NOW()
        """,
        payload,
    )
    return len(payload)
