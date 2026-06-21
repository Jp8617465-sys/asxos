"""
Fundamentals ingestion — fetch from EODHD and upsert to fundamentals table.
Failure on one symbol does not abort a run; callers use try/except per symbol.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import asyncpg

from asxos.ingestion.eodhd import EODHDClient


def _dec(val: Any) -> Decimal | None:
    if val is None:
        return None
    try:
        d = Decimal(str(val))
        return None if d.is_nan() or d.is_infinite() else d
    except InvalidOperation:
        return None


def _int(val: Any) -> int | None:
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _str(val: Any) -> str | None:
    """Trimmed string, or None for missing/blank. Never raises."""
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def parse_fundamentals(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten EODHD /fundamentals/{symbol} response into a flat dict.
    Any missing or unparseable field returns None — never raises.
    """
    highlights = raw.get("Highlights") or {}
    valuation  = raw.get("Valuation")  or {}
    shares     = raw.get("SharesStats") or {}
    general    = raw.get("General")     or {}

    return {
        "pe_ratio":           _dec(highlights.get("PERatio")),
        "pb_ratio":           _dec(valuation.get("PriceBookMRQ")),
        "eps":                _dec(highlights.get("EarningsShare")),
        "market_cap":         _dec(highlights.get("MarketCapitalization")),
        "shares_outstanding": _int(shares.get("SharesOutstanding")),
        "dividend_yield":     _dec(highlights.get("DividendYield")),
        # EODHD exposes the Morningstar-style sector under General.Sector
        # (GICSSector is null on the current plan). It feeds universe.sector
        # via propagate_sector_to_universe().
        "sector":             _str(general.get("Sector")),
    }


async def fetch_and_upsert_fundamentals(
    symbol: str,
    as_of: date,
    client: EODHDClient,
    conn: asyncpg.Connection,
) -> None:
    raw = await client.fundamentals(symbol)
    f = parse_fundamentals(raw)
    await conn.execute(
        """
        INSERT INTO fundamentals (
            symbol, as_of,
            pe_ratio, pb_ratio, eps, market_cap, shares_outstanding,
            dividend_yield, sector
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (symbol, as_of) DO UPDATE SET
            pe_ratio           = EXCLUDED.pe_ratio,
            pb_ratio           = EXCLUDED.pb_ratio,
            eps                = EXCLUDED.eps,
            market_cap         = EXCLUDED.market_cap,
            shares_outstanding = EXCLUDED.shares_outstanding,
            dividend_yield     = EXCLUDED.dividend_yield,
            sector             = EXCLUDED.sector
        """,
        symbol, as_of,
        f["pe_ratio"], f["pb_ratio"], f["eps"],
        f["market_cap"], f["shares_outstanding"], f["dividend_yield"],
        f["sector"],
    )


async def propagate_market_cap_to_universe(conn: asyncpg.Connection) -> int:
    """Copy each symbol's latest non-null ``fundamentals.market_cap`` into
    ``universe.market_cap``.

    ``universe.market_cap`` is a denormalised cache read by the portfolio
    allocator (``domain/portfolio/build.py`` → ``allocator.filter_buy_universe``)
    and by the signal feature engine (``domain/signals/loader.py``); no other
    step maintains it, so without this propagation it stays NULL and the
    allocator filters every candidate out via the market-cap floor.

    This is the single propagation path: the daily ``sync_fundamentals`` job
    calls it after the per-symbol upserts, and the one-time backfill uses the
    same query. Idempotent — only rows whose value actually changes are
    written (``IS DISTINCT FROM``). Returns the number of universe rows updated.
    """
    status = await conn.execute(
        """
        UPDATE universe u
        SET market_cap = lf.market_cap
        FROM (
            SELECT DISTINCT ON (symbol) symbol, market_cap
            FROM fundamentals
            WHERE market_cap IS NOT NULL
            ORDER BY symbol, as_of DESC
        ) lf
        WHERE u.symbol = lf.symbol
          AND u.market_cap IS DISTINCT FROM lf.market_cap
        """
    )
    # asyncpg returns a command tag like "UPDATE 1843".
    return int(status.split()[-1]) if status else 0


async def propagate_sector_to_universe(conn: asyncpg.Connection) -> int:
    """Copy each symbol's latest non-blank ``fundamentals.sector`` into
    ``universe.sector``.

    ``universe.sector`` is the cache the portfolio allocator's sector cap
    groups on (``domain/portfolio/constraints.py`` → ``apply_sector_cap`` via
    ``build.py``). The EODHD exchange-symbol-list used by ``sync_universe``
    does not return a sector for ASX names, so without this propagation every
    row carries ``sector=''`` and the constraint waterfall cannot converge
    (all weight collapses into one un-cappable bucket).

    Mirror of :func:`propagate_market_cap_to_universe` — the single sector
    propagation path, called by ``sync_fundamentals`` after the per-symbol
    upserts and reused for the one-time backfill. Idempotent (``IS DISTINCT
    FROM``); blank fundamentals sectors are ignored so a stale '' never
    overwrites a real value. Returns the number of universe rows updated.
    """
    status = await conn.execute(
        """
        UPDATE universe u
        SET sector = lf.sector
        FROM (
            SELECT DISTINCT ON (symbol) symbol, sector
            FROM fundamentals
            WHERE sector IS NOT NULL AND sector <> ''
            ORDER BY symbol, as_of DESC
        ) lf
        WHERE u.symbol = lf.symbol
          AND u.sector IS DISTINCT FROM lf.sector
        """
    )
    # asyncpg returns a command tag like "UPDATE 1843".
    return int(status.split()[-1]) if status else 0
