"""
Section 1: Wealth state — M-Brief-Skeleton.

Reads portfolio_daily_snapshots for the as_of date. Returns no_data if the
snapshot table is empty or has no row for this date (portfolio cron may not
have run yet, or M13 is not enabled).

SeverityItems produced:
  - green: cash ratio, portfolio MV, capital AUD (informational)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from asxos.domain.brief.severity import portfolio_drawdown, position_concentration
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel

_SECTION = "wealth_state"


async def collect_wealth_state(conn: Any, as_of: date) -> SectionResult:
    """Query portfolio_daily_snapshots and build a wealth state section."""
    import time
    start_ms = int(time.monotonic() * 1000)

    row = await conn.fetchrow(
        """
        SELECT capital_aud, holdings_mv_aud, cash_aud,
               us_holdings_mv_aud, us_holdings_cost_aud,
               fx_rate_audusd, unrealised_fx_pnl_aud
        FROM portfolio_daily_snapshots
        WHERE as_of = $1
        """,
        as_of,
    )

    peak_row = await conn.fetchrow(
        "SELECT MAX(capital_aud) AS peak FROM portfolio_daily_snapshots WHERE as_of <= $1",
        as_of,
    )

    holdings_rows = await conn.fetch(
        """
        SELECT ch.symbol, (ch.quantity * p.close)::numeric AS mv_local
        FROM current_holdings ch
        JOIN prices p ON p.symbol = ch.symbol AND p.dt = $1
        ORDER BY mv_local DESC
        """,
        as_of,
    )

    elapsed_ms = int(time.monotonic() * 1000) - start_ms

    if row is None:
        return SectionResult(
            name=_SECTION,
            status=SectionStatus.no_data,
            items=(),
            elapsed_ms=elapsed_ms,
            error="no portfolio snapshot for this date",
        )

    capital = Decimal(str(row["capital_aud"] or 0))
    mv = Decimal(str(row["holdings_mv_aud"] or 0))
    cash = Decimal(str(row["cash_aud"] or 0))
    us_mv = row["us_holdings_mv_aud"]
    fx_rate = row["fx_rate_audusd"]
    fx_pnl = row["unrealised_fx_pnl_aud"]

    items: list[SeverityItem] = []

    # Cash ratio: yellow if < 5% of capital
    if capital > Decimal("0"):
        cash_ratio = cash / capital * 100
        if cash_ratio < Decimal("5"):
            items.append(SeverityItem(
                level=SeverityLevel.yellow,
                message=f"Cash {cash_ratio:.1f}% of portfolio — low liquidity",
                section=_SECTION,
            ))
        else:
            items.append(SeverityItem(
                level=SeverityLevel.green,
                message=f"Portfolio AUD {capital:,.0f} · MV {mv:,.0f} · Cash {cash:,.0f} ({cash_ratio:.1f}%)",
                section=_SECTION,
            ))

    # Drawdown from high-water mark
    if peak_row and peak_row["peak"] is not None:
        peak_capital = Decimal(str(peak_row["peak"]))
        dd_item = portfolio_drawdown(capital, peak_capital, section=_SECTION)
        if dd_item:
            items.append(dd_item)

    # Per-holding concentration (only when we have per-symbol price data)
    if holdings_rows and mv > 0:
        fx = Decimal(str(fx_rate)) if fx_rate is not None else None
        _NON_AU = (".US", ".NYSE", ".NASDAQ", ".AMEX")
        for hr in holdings_rows:
            mv_local = Decimal(str(hr["mv_local"]))
            sym = hr["symbol"]
            if any(sym.endswith(sfx) for sfx in _NON_AU):
                if fx is None:
                    continue
                mv_aud = mv_local / fx
            else:
                mv_aud = mv_local
            conc_item = position_concentration(sym, mv_aud, mv, section=_SECTION)
            if conc_item:
                items.append(conc_item)

    # FX P&L (US holdings only; positive = AUD depreciation benefit)
    if fx_pnl is not None and fx_rate is not None:
        fx_pnl_d = Decimal(str(fx_pnl))
        sign = "+" if fx_pnl_d >= 0 else ""
        us_mv_d = Decimal(str(us_mv)) if us_mv is not None else Decimal("0")
        items.append(SeverityItem(
            level=SeverityLevel.green,
            message=(
                f"US holdings MV A${us_mv_d:,.0f}  "
                f"FX P&L {sign}{fx_pnl_d:,.0f}  "
                f"(AUDUSD {Decimal(str(fx_rate)):.4f})"
            ),
            section=_SECTION,
        ))

    return SectionResult(
        name=_SECTION,
        status=SectionStatus.ok,
        items=tuple(items),
        elapsed_ms=elapsed_ms,
    )
