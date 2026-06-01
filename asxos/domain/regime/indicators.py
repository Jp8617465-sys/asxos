"""
Market indicator loader for regime classification — M-Market-Context.

load_from_db(conn, as_of): reads from market_context_current view.
  Hard-fails if critical indicators (asx200_close, avix, us_hy_oas) are None.

These are read-path helpers for the classifier and brief collectors.
The write path lives in jobs/ingest_market_context.py.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

_CRITICAL = {"asx200_close", "avix", "us_hy_oas"}


async def load_from_db(
    conn: Any,
    as_of: date,
) -> dict[str, Decimal | None]:
    """Load the latest market_context row for as_of from the current view.

    Raises RuntimeError if no row exists or if any critical indicator is NULL.
    """
    row = await conn.fetchrow(
        "SELECT * FROM market_context_current WHERE as_of = $1",
        as_of,
    )
    if row is None:
        raise RuntimeError(
            f"load_from_db: no market_context row for as_of={as_of}. "
            "Has ingest_market_context run successfully today?"
        )

    indicator_cols = {
        "asx200_close", "asx200_daily_change_pct",
        "pct_above_50d_ma", "pct_above_200d_ma", "net_new_highs_lows_10d",
        "avix", "avix_5d_change_pct", "avix_30d_band_pos",
        "rba_cash_rate", "aud_usd", "aus_10y_yield", "iron_ore_62fe",
        "us_hy_oas", "us_10y_2y_spread", "vix",
    }
    indicators: dict[str, Decimal | None] = {}
    for col in indicator_cols:
        raw = row[col]
        indicators[col] = Decimal(str(raw)) if raw is not None else None

    missing_critical = [c for c in _CRITICAL if indicators.get(c) is None]
    if missing_critical:
        raise RuntimeError(
            f"load_from_db: critical indicators are NULL for as_of={as_of}: "
            f"{missing_critical}. Cannot classify regime."
        )

    return indicators
