"""
Volatility estimation for the M13 portfolio allocator.

annualised_vol_from_prices — pure, Decimal-only.
load_vols_for_symbols     — async, one batch SELECT against `prices`.

No numpy. Python 3.12 Decimal.ln() for log returns (plan Part C).
Cap: window_days <= 252 (plan H.2 QUICK-WIN-4).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import asyncpg


def annualised_vol_from_prices(
    closes: list[Decimal],
    *,
    window_days: int = 60,
    trading_days_per_year: int = 252,
) -> Decimal:
    """Annualised std-dev of log returns. Decimal throughout (Python 3.12 Decimal.ln()).

    Hard-fails if:
    - window_days > 252 (plan H.2 QUICK-WIN-4 cap)
    - len(closes) < window_days + 1 (insufficient history for window_days log returns)
    - any close <= 0 (log return is undefined)
    """
    if window_days > 252:
        raise ValueError(
            f"window_days {window_days} exceeds 252-day cap (plan H.2 QUICK-WIN-4)"
        )
    if len(closes) < window_days + 1:
        raise ValueError(
            f"insufficient price history: need at least {window_days + 1} closes, "
            f"got {len(closes)}"
        )
    if any(c <= Decimal("0") for c in closes):
        raise ValueError(
            "all closes must be > 0; log return is undefined for non-positive prices"
        )

    # Use the most-recent (window_days + 1) closes → window_days log returns.
    window = closes[-(window_days + 1) :]
    log_returns: list[Decimal] = [
        window[i].ln() - window[i - 1].ln() for i in range(1, len(window))
    ]

    n = len(log_returns)  # == window_days
    if n == 1:
        # Single return → population variance is 0; sample variance undefined.
        return Decimal("0")

    mean = sum(log_returns, Decimal("0")) / Decimal(n)
    # Sample variance (n - 1) — standard for vol estimation.
    variance = sum((r - mean) ** 2 for r in log_returns) / Decimal(n - 1)
    daily_std = variance.sqrt()
    return daily_std * Decimal(trading_days_per_year).sqrt()


async def load_vols_for_symbols(
    conn: asyncpg.Connection,
    symbols: list[str],
    as_of: date,
    window_days: int = 60,
) -> dict[str, Decimal]:
    """Batch-load close prices and compute annualised vol per symbol up to `as_of`.

    Uses asyncpg's native ANY($1::text[]) pattern (plan H.2 QUICK-WIN-2).
    Symbols with insufficient price history are silently omitted — the caller
    (allocator.filter_buy_universe) handles exclusion.
    """
    if not symbols:
        return {}

    # Fetch the most-recent (window_days + 1) closes per symbol via a window
    # function. ORDER BY dt ASC gives oldest-first for the vol calc.
    rows = await conn.fetch(
        """
        SELECT symbol, close
        FROM (
            SELECT symbol, close, dt,
                   ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY dt DESC) AS rn
            FROM prices
            WHERE symbol = ANY($1::text[])
              AND dt <= $2
        ) sub
        WHERE rn <= $3
        ORDER BY symbol, dt ASC
        """,
        symbols,
        as_of,
        window_days + 1,
    )

    by_symbol: dict[str, list[Decimal]] = {}
    for row in rows:
        by_symbol.setdefault(row["symbol"], []).append(Decimal(str(row["close"])))

    result: dict[str, Decimal] = {}
    for sym, closes in by_symbol.items():
        try:
            result[sym] = annualised_vol_from_prices(closes, window_days=window_days)
        except ValueError:
            pass  # insufficient history or invalid close — omit symbol
    return result
