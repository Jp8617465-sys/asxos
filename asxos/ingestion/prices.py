"""Price ingestion logic — separated from the job script."""
from __future__ import annotations

from datetime import date

import asyncpg

from asxos.ingestion.eodhd import EODHDClient


def _to_symbol(code: str) -> str:
    return code if "." in code else f"{code}.AU"


def to_price_rows(raw: list[dict], universe: set[str]) -> list[tuple]:
    """Filter bulk API response to universe symbols with valid close prices."""
    rows = []
    for item in raw:
        symbol = _to_symbol(item.get("code", ""))
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


async def upsert_prices(conn: asyncpg.Connection, rows: list[tuple]) -> int:
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
