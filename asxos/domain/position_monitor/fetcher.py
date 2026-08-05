"""
EODHD + FRED data fetcher for the position monitor.

Fetches:
  - current price, 50d MA, 200d MA, avg weekly move  (EODHD daily_prices)
  - VIX 5d % move (FRED VIXCLS), US HY OAS 5d % move (FRED BAMLH0A0HYM2)

All arithmetic uses Decimal; no numpy.

Symbol normalisation is NOT defined here any more — ``eodhd_symbol()`` moved to
``asxos/ingestion/symbols.py`` (HUBS.NYSE → HUBS.US, CRM.NASDAQ → CRM.US, BHP.AU
unchanged) so the suffix map has one home and stdlib-only callers can reach it.
It is re-exported below purely to keep existing imports working; change the map
in ``symbols.py``, never here.
"""
from __future__ import annotations

import asyncio
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from asxos.clients.fred import get_client as get_fred
from asxos.ingestion.eodhd import get_client as get_eodhd
from asxos.ingestion.symbols import eodhd_symbol

# eodhd_symbol() moved to asxos/ingestion/symbols.py so the suffix map has one
# home and so stdlib-only callers (asxos/ingestion/news.py) can reach it without
# dragging httpx/tenacity/fred in through this module. Re-exported here to keep
# the existing import path working.

# FRED series IDs
_SERIES_VIX = "VIXCLS"
_SERIES_HY_OAS = "BAMLH0A0HYM2"

# Days of EODHD history to request (~10 extra over 200 to absorb trading gaps)
_PRICE_LOOKBACK = "220d"


class PriceData(NamedTuple):
    current_price: Decimal
    ma_50d: Decimal
    ma_200d: Decimal
    avg_weekly_move: Decimal


class MacroData(NamedTuple):
    vix_5d_move: Decimal
    hy_oas_5d_move: Decimal


# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------

# eodhd_symbol is defined in asxos/ingestion/symbols.py — imported at the top of
# this module and re-exported for the existing call sites.


# ---------------------------------------------------------------------------
# MA and weekly-move calculations — pure Decimal arithmetic
# ---------------------------------------------------------------------------

def sma(closes: list[Decimal], period: int) -> Decimal:
    """Simple moving average over the last `period` closes."""
    if len(closes) < period:
        raise RuntimeError(
            f"Insufficient price history: need {period} closes, got {len(closes)}"
        )
    window = closes[-period:]
    return (sum(window, Decimal("0")) / Decimal(str(period))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def avg_weekly_move(closes: list[Decimal]) -> Decimal:
    """Mean absolute weekly return over the last ~4 weeks of trading days.

    Uses 5-day intervals on the trailing 25 closes so each interval is one
    calendar week of trading. Returns a fallback of 0.030 (3%) when fewer
    than 6 closes are available.
    """
    window = closes[-25:] if len(closes) >= 25 else closes
    if len(window) < 6:
        return Decimal("0.030")

    returns: list[Decimal] = []
    for i in range(5, len(window)):
        prior = window[i - 5]
        if prior != Decimal("0"):
            returns.append(abs((window[i] - prior) / prior))

    if not returns:
        return Decimal("0.030")

    avg = sum(returns, Decimal("0")) / Decimal(str(len(returns)))
    return avg.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# FRED 5d move
# ---------------------------------------------------------------------------

def _pct_change_5d(values_desc: list[Decimal | None]) -> Decimal:
    """Percent change between the most recent and 5th non-None observation.

    values_desc: newest-first list (FRED sort_order='desc').
    Raises RuntimeError if fewer than 6 non-None values are found.
    """
    non_null = [v for v in values_desc if v is not None]
    if len(non_null) < 6:
        raise RuntimeError(
            f"Insufficient observations for 5d move: need 6, got {len(non_null)}"
        )
    latest, five_ago = non_null[0], non_null[5]
    if five_ago == Decimal("0"):
        raise RuntimeError("Cannot compute 5d move: prior value is zero")
    return ((latest - five_ago) / five_ago * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


# ---------------------------------------------------------------------------
# Public async fetch functions
# ---------------------------------------------------------------------------

async def fetch_price_data(symbol: str) -> PriceData:
    """Fetch ~220 days of price history and compute MAs + weekly move.

    Raises RuntimeError if EODHD returns no data or fewer than 200 closes.
    """
    eodhd = get_eodhd()
    sym = eodhd_symbol(symbol)
    rows = await eodhd.daily_prices(sym, from_date=f"-{_PRICE_LOOKBACK}")
    if not rows:
        raise RuntimeError(
            f"No price data returned from EODHD for {sym!r}. "
            "Verify the symbol format and that your EODHD plan includes this exchange."
        )

    closes = [
        Decimal(str(r["close"]))
        for r in rows
        if r.get("close") is not None
    ]
    if len(closes) < 200:
        raise RuntimeError(
            f"Insufficient price history for {sym!r}: "
            f"need 200 closes, got {len(closes)}"
        )

    return PriceData(
        current_price=closes[-1],
        ma_50d=sma(closes, 50),
        ma_200d=sma(closes, 200),
        avg_weekly_move=avg_weekly_move(closes),
    )


async def fetch_macro_data() -> MacroData:
    """Fetch VIX and US HY OAS 5d % moves from FRED.

    Raises RuntimeError if either series returns fewer than 6 non-None
    observations (e.g. during extended holiday clusters).
    """
    fred = get_fred()

    vix_obs, hy_obs = await asyncio.gather(
        fred.get_series(_SERIES_VIX, limit=10, sort_order="desc"),
        fred.get_series(_SERIES_HY_OAS, limit=10, sort_order="desc"),
    )

    return MacroData(
        vix_5d_move=_pct_change_5d([obs.value for obs in vix_obs]),
        hy_oas_5d_move=_pct_change_5d([obs.value for obs in hy_obs]),
    )
