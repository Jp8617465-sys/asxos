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


def parse_fundamentals(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten EODHD /fundamentals/{symbol} response into a flat dict.
    Any missing or unparseable field returns None — never raises.
    """
    highlights = raw.get("Highlights") or {}
    valuation  = raw.get("Valuation")  or {}
    shares     = raw.get("SharesStats") or {}

    return {
        "pe_ratio":           _dec(highlights.get("PERatio")),
        "pb_ratio":           _dec(valuation.get("PriceBookMRQ")),
        "eps":                _dec(highlights.get("EarningsShare")),
        "market_cap":         _dec(highlights.get("MarketCapitalization")),
        "shares_outstanding": _int(shares.get("SharesOutstanding")),
        "dividend_yield":     _dec(highlights.get("DividendYield")),
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
            pe_ratio, pb_ratio, eps, market_cap, shares_outstanding, dividend_yield
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (symbol, as_of) DO UPDATE SET
            pe_ratio           = EXCLUDED.pe_ratio,
            pb_ratio           = EXCLUDED.pb_ratio,
            eps                = EXCLUDED.eps,
            market_cap         = EXCLUDED.market_cap,
            shares_outstanding = EXCLUDED.shares_outstanding,
            dividend_yield     = EXCLUDED.dividend_yield
        """,
        symbol, as_of,
        f["pe_ratio"], f["pb_ratio"], f["eps"],
        f["market_cap"], f["shares_outstanding"], f["dividend_yield"],
    )
