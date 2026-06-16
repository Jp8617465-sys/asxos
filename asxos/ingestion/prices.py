"""Price ingestion logic — separated from the job script."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import asyncpg

from asxos.domain.position_monitor.fetcher import eodhd_symbol
from asxos.domain.prices.coverage import PriceDateStatus, classify_row_count
from asxos.ingestion.eodhd import EODHDClient


def _to_symbol(code: str, *, exchange: str = "AU") -> str:
    """Append exchange suffix when the raw EODHD code has no dot.

    EODHD bulk endpoints return bare codes (e.g. "BHP", "AAPL") without
    an exchange suffix. For AU calls the default ".AU" is always correct;
    US calls must pass exchange="US" so "AAPL" → "AAPL.US" not "AAPL.AU".
    """
    return code if "." in code else f"{code}.{exchange}"


def to_price_rows(raw: list[dict[str, Any]], universe: set[str], *, exchange: str = "AU") -> list[tuple[Any, ...]]:
    """Filter bulk API response to universe symbols with valid close prices."""
    rows = []
    for item in raw:
        symbol = _to_symbol(item.get("code", ""), exchange=exchange)
        if symbol not in universe:
            continue
        close = item.get("close")
        if close is None:
            continue
        rows.append((
            symbol,
            date.fromisoformat(item["date"]),
            item.get("open"),
            item.get("high"),
            item.get("low"),
            close,
            item.get("volume"),
            item.get("adjusted_close"),
        ))
    return rows


async def upsert_prices(conn: asyncpg.Connection, rows: list[tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    await conn.executemany(
        """
        INSERT INTO prices (symbol, dt, open, high, low, close, volume, adj_close)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (symbol, dt) DO UPDATE SET
            open      = EXCLUDED.open,
            high      = EXCLUDED.high,
            low       = EXCLUDED.low,
            close     = EXCLUDED.close,
            volume    = EXCLUDED.volume,
            adj_close = EXCLUDED.adj_close
        """,
        rows,
    )
    return len(rows)


async def fetch_and_upsert_bulk(
    target_date: date,
    client: EODHDClient,
    conn: asyncpg.Connection,
    universe: set[str],
) -> int:
    raw = await client.daily_prices_bulk("AU", date=target_date.isoformat())
    rows = to_price_rows(raw, universe)
    return await upsert_prices(conn, rows)


# ---------------------------------------------------------------------------
# FX rates — M15
# ---------------------------------------------------------------------------

def to_fx_rows(raw: list[dict[str, Any]], *, pair: str) -> list[tuple[Any, ...]]:
    """Convert EODHD per-symbol price response to fx_rates rows.

    EODHD AUDUSD.FOREX returns the same shape as equity per-symbol prices:
      [{"date": "YYYY-MM-DD", "open": ..., "close": 0.640000, ...}, ...]

    We store only the close as the daily rate.
    """
    rows = []
    for item in raw:
        close = item.get("close")
        if close is None:
            continue
        try:
            dt = date.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue
        rows.append((pair, dt, close))
    return rows


async def upsert_fx_rates(conn: asyncpg.Connection, rows: list[tuple[Any, ...]]) -> int:
    """UPSERT fx_rates rows.  ON CONFLICT updates the rate (idempotent rerun)."""
    if not rows:
        return 0
    await conn.executemany(
        """
        INSERT INTO fx_rates (pair, dt, rate)
        VALUES ($1, $2, $3)
        ON CONFLICT (pair, dt) DO UPDATE SET
            rate = EXCLUDED.rate
        """,
        rows,
    )
    return len(rows)


# ---------------------------------------------------------------------------
# US per-symbol prices — M15
# ---------------------------------------------------------------------------

def to_us_price_rows(raw: list[dict[str, Any]], *, symbol: str) -> list[tuple[Any, ...]]:
    """Convert EODHD per-symbol response to price rows for a US holding.

    Unlike the bulk AU endpoint, per-symbol responses have no 'code' field —
    the symbol is already known from the request URL.
    """
    rows = []
    for item in raw:
        close = item.get("close")
        if close is None:
            continue
        try:
            dt = date.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue
        rows.append((
            symbol,
            dt,
            item.get("open"),
            item.get("high"),
            item.get("low"),
            close,
            item.get("volume"),
            item.get("adjusted_close"),
        ))
    return rows


async def fetch_and_upsert_us_symbol(
    symbol: str,
    from_date: date,
    client: EODHDClient,
    conn: asyncpg.Connection,
) -> int:
    """Fetch + upsert prices for a single US holding.  Returns rows written.

    Remaps stored exchange suffix (e.g. HUBS.NYSE) → EODHD format (HUBS.US)
    for the API call; inserts prices under the original symbol so the FK to
    universe(symbol) holds.
    """
    api_sym = eodhd_symbol(symbol)
    raw = await client.daily_prices(api_sym, from_date=from_date.isoformat())
    rows = to_us_price_rows(raw, symbol=symbol)
    return await upsert_prices(conn, rows)


# ---------------------------------------------------------------------------
# Price-completeness classification — Batch 1 Step 2 (additive, non-gating)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyncCompleteness:
    """ASX-equity completeness verdict for a single sync_prices run.

    The verdict is derived ONLY from Phase-1 AU bulk equity rows (``au_rows``).
    Phase-2 US (``us_rows``) and Phase-3 FX (``fx_rows``) writes are carried for
    context but DELIBERATELY excluded from the classification: a non-trading ASX
    day can still produce US/FX residue — the 2026-06-14 incident wrote 12/14
    residue rows on a day with no ASX session — and that residue must never read
    as ASX equity coverage.

    v1 limitation: the verdict counts the AU bulk rows returned for the run; it
    does not yet assert those rows carry ``dt == target`` (an EODHD holiday
    response can echo the prior trading day's closes). Target-date assertion via
    the DB coverage helper is a deliberate later step.
    """

    target: date
    status: PriceDateStatus
    au_rows: int
    us_rows: int
    fx_rows: int

    @property
    def is_complete(self) -> bool:
        return self.status is PriceDateStatus.COMPLETE


def classify_sync_completeness(
    target: date, *, au_rows: int, us_rows: int, fx_rows: int
) -> SyncCompleteness:
    """Classify a sync_prices run's ASX-equity completeness from phase counts.

    Uses the floor-only threshold (``classify_row_count`` with a trailing median
    of 0 → ``MIN_COMPLETE_ROWS``) so the verdict needs no DB round-trip: the
    active ASX universe is ~1,800 symbols, so the 1,500-row floor cleanly
    separates a full session from residue. US and FX counts never enter the
    classification, so FX-only or US-only runs can never look ASX-complete.
    """
    status = classify_row_count(au_rows, 0)
    return SyncCompleteness(
        target=target,
        status=status,
        au_rows=au_rows,
        us_rows=us_rows,
        fx_rows=fx_rows,
    )
