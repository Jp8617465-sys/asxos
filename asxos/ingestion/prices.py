"""Price ingestion logic — separated from the job script."""
from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg

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
    """Fetch + upsert prices for a single US holding.  Returns rows written."""
    raw = await client.daily_prices(symbol, from_date=from_date.isoformat())
    rows = to_us_price_rows(raw, symbol=symbol)
    return await upsert_prices(conn, rows)
