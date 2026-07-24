"""
Section 1: Wealth state — M-Brief-Skeleton.

Reads the latest portfolio_daily_snapshots row on or before the as_of date (an
exact match is not required: the snapshot's as_of is anchored to the latest
complete trading day, so it rarely equals the brief's calendar as_of). Returns
no_data only if no snapshot exists on or before this date (portfolio cron may
not have run yet, or M13 is not enabled).

SeverityItems produced:
  - green: cash ratio, portfolio MV, capital AUD (informational)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from asxos.domain.brief.severity import portfolio_drawdown, position_concentration
from asxos.domain.brief.types import SectionResult, SectionStatus, SeverityItem, SeverityLevel
from asxos.domain.prices.fx import is_foreign_symbol

_SECTION = "wealth_state"


async def collect_wealth_state(conn: Any, as_of: date) -> SectionResult:
    """Query portfolio_daily_snapshots and build a wealth state section."""
    import time
    start_ms = int(time.monotonic() * 1000)

    # Latest snapshot on or before the brief date, not an exact match. The brief
    # calendar as_of (date.today()) never equals the snapshot's as_of, which is now
    # anchored to the latest COMPLETE trading day (e.g. Friday) by snapshot_portfolio.
    # An exact `= $1` returned no_data on every weekend/holiday brief; `<= $1 ... LIMIT 1`
    # self-heals, matching how peak_row/inception_row below already scope to `<= $1`.
    row = await conn.fetchrow(
        """
        SELECT capital_aud, holdings_mv_aud, cash_aud,
               us_holdings_mv_aud, us_holdings_cost_aud,
               fx_rate_audusd, unrealised_fx_pnl_aud,
               benchmark_tr_level, trailing_div_yield_pct
        FROM portfolio_daily_snapshots
        WHERE as_of <= $1
        ORDER BY as_of DESC
        LIMIT 1
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

    # (Removed) The since-inception "Portfolio vs XJO-TR · alpha" line differenced
    # a flow-affected capital_aud snapshot balance as if it were a return index — a
    # static cash placeholder that later vanished produced a false −75.7% loss and a
    # bogus alpha. A valid time-/money-weighted return needs a contributions/
    # withdrawals ledger this system does not have; the honest, broker-matching
    # unrealised-return line lives in the V1 discipline section
    # (asxos/domain/theses/discipline.py::unrealised_return, native price only).
    # Re-add a portfolio return here only against a rebuilt, flow-adjusted series.

    # Drawdown from high-water mark
    if peak_row and peak_row["peak"] is not None:
        peak_capital = Decimal(str(peak_row["peak"]))
        dd_item = portfolio_drawdown(capital, peak_capital, section=_SECTION)
        if dd_item:
            items.append(dd_item)

    # Per-holding concentration (only when we have per-symbol price data)
    if holdings_rows and mv > 0:
        fx = Decimal(str(fx_rate)) if fx_rate is not None else None
        priced: list[tuple[str, Decimal]] = []
        for hr in holdings_rows:
            mv_local = Decimal(str(hr["mv_local"]))
            sym = hr["symbol"]
            if is_foreign_symbol(sym):
                if fx is None:
                    continue
                mv_aud = mv_local / fx
            else:
                mv_aud = mv_local
            priced.append((sym, mv_aud))
        # The denominator must come from the SAME source as the numerator (the priced
        # per-holding MVs), not the snapshot's holdings_mv_aud which may be derived
        # from a different price date/source — else concentration % is skewed. Fall
        # back to the snapshot MV only if nothing priced (e.g. all-FX, no fx rate).
        total_priced = sum((m for _, m in priced), Decimal("0"))
        denom = total_priced if total_priced > 0 else mv
        for sym, mv_aud in priced:
            conc_item = position_concentration(sym, mv_aud, denom, section=_SECTION)
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
