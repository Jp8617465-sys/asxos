"""
News ingestion from EODHD /news (M14a).

Parse + upsert pattern mirrors asxos/ingestion/regulatory.py.

Pure functions: parse_news_response(), _parse_sentiment(), _normalise_symbol(), _extract_polarity().
Async I/O:      upsert_news().

EODHD /news response shape (per item):
  {
    "date":     "2026-05-23T04:30:00+00:00",   # ISO datetime string — always slice [:10]
    "title":    "BHP Q1 Results ...",
    "link":     "https://...",
    "symbols":  ["BHP.AU", "RIO.AU"],          # may lack .AU suffix
    "sentiment": {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}  # numeric dict
    "content":  "Full article text ...",
  }

Gotchas:
  1. date is ISO datetime string → always slice [:10] before fromisoformat()
  2. sentiment shape varies by plan tier — use _parse_sentiment() and _extract_polarity() always
  3. symbols may lack .AU suffix — normalise with _normalise_symbol()
  4. content may be absent — use content_snippet = (content or "")[:500]
  5. sentiment_polarity: None means absent (structurally neutral — not zero-sentiment)
     Hard-fail (rule #10) if abs(polarity) > 1.5
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

import asyncpg

_POLARITY_LIMIT = Decimal("1.5")


@dataclass(frozen=True)
class NewsItem:
    url: str
    title: str
    published_at: date
    symbols: list[str]       # normalised to BHP.AU format, intersection with holdings
    sentiment: str           # "positive" | "negative" | "neutral" | ""
    content_snippet: str
    sentiment_polarity: Decimal | None = field(default=None)  # numeric ∈ [-1.5, +1.5]; None if absent


def _parse_sentiment(raw_item: dict) -> str:
    """Extract text sentiment label from EODHD sentiment field.

    EODHD /news on current plan tiers returns a dict with numeric fields:
      {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}
    Older or lower plan tiers return a string label in the dict: {"polarity": "Positive"}
    or a plain string, or the field may be absent entirely.
    """
    s = raw_item.get("sentiment")
    if isinstance(s, dict):
        pol = s.get("polarity")
        if pol is None:
            return ""
        # Try numeric interpretation first (current plan tier shape).
        try:
            v = float(pol)
            if v > 0.05:
                return "positive"
            if v < -0.05:
                return "negative"
            return "neutral"
        except (TypeError, ValueError):
            # Fallback: string label in dict (older plan tier shape).
            return str(pol).lower()
    return (s or "").lower() if isinstance(s, str) else ""


def _extract_polarity(raw_item: dict) -> Decimal | None:
    """Extract numeric polarity from EODHD sentiment dict.

    EODHD returns: {"polarity": -0.953, "neg": 0.05, "neu": 0.942, "pos": 0.008}
    Returns None (not 0.0) when polarity is absent or non-numeric (e.g. "Positive").
    Absence is structurally neutral — not zero-sentiment.
    Hard-fails only if the value IS numeric but outside [-1.5, +1.5] (rule #10).
    """
    s = raw_item.get("sentiment")
    if not isinstance(s, dict):
        return None
    v = s.get("polarity")
    if v is None:
        return None
    try:
        pol = Decimal(str(float(v)))
    except (TypeError, ValueError, ArithmeticError):
        # Non-numeric polarity label (e.g. "Positive") — no numeric signal available.
        return None
    if abs(pol) > _POLARITY_LIMIT:
        raise ValueError(
            f"polarity={pol} outside [-1.5, +1.5] — hard-fail per rule #10"
        )
    return pol


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
                sentiment_polarity=_extract_polarity(item),
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
            str(item.sentiment_polarity) if item.sentiment_polarity is not None else None,
        )
        for item in items
    ]

    await conn.executemany(
        """
        INSERT INTO holding_news
            (url, title, published_at, symbols, sentiment, content_snippet, sentiment_polarity)
        VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7::numeric)
        ON CONFLICT (url) DO UPDATE SET
            symbols = (
                SELECT jsonb_agg(DISTINCT sym ORDER BY sym)
                FROM (
                    SELECT jsonb_array_elements_text(holding_news.symbols) AS sym
                    UNION
                    SELECT jsonb_array_elements_text(EXCLUDED.symbols)
                ) merged
            ),
            sentiment          = EXCLUDED.sentiment,
            sentiment_polarity = COALESCE(holding_news.sentiment_polarity, EXCLUDED.sentiment_polarity),
            ingested_at        = NOW()
        """,
        payload,
    )
    return len(payload)
