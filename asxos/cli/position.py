"""
asx position — position monitor CLI.

Commands:
  asx position monitor SYMBOL   — run a weekly monitor; auto-fetches price + macro,
                                   prompts for sentiment inputs with last-run defaults
  asx position history SYMBOL   — show table of past monitor runs
"""
from __future__ import annotations

import asyncio
from datetime import date

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.portfolio.profile import load_active
from asxos.domain.position_monitor.display import format_history, format_monitor
from asxos.domain.position_monitor.fetcher import fetch_macro_data, fetch_price_data
from asxos.domain.position_monitor.service import (
    build_monitor_result,
    get_last_sentiment_inputs,
    list_runs,
    load_position_context,
    save_run,
)
from asxos.domain.position_monitor.types import MonitorInput
from asxos.domain.underlyings.service import list_thesis_underlyings

position_app = typer.Typer(
    help="Weekly position monitor.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# monitor
# ---------------------------------------------------------------------------

@position_app.command("monitor")
def monitor(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE or BHP.AU"),
    as_of: str = typer.Option(
        "", "--as-of", help="ISO date override (default: today)"
    ),
    no_save: bool = typer.Option(
        False, "--no-save", help="Display only; don't persist to DB"
    ),
    regime: str = typer.Option(
        "", "--regime", help="Regime label override (e.g. risk_on_narrowing)"
    ),
    intraday: bool = typer.Option(
        False, "--intraday", help="Mark price as intraday (not a confirmed close)"
    ),
) -> None:
    """Run a weekly monitor for a position.

    Price (current, 50d MA, 200d MA, avg weekly move) is auto-fetched from EODHD.
    VIX 5d move and US HY OAS 5d move are auto-fetched from FRED.
    Retail ratio and news sentiment require manual input (no free Stocktwits API)
    but default to last week's values so entry is a quick review + confirm.

    Data sources for manual inputs:
      retail_ratio   — stocktwits.com/symbol/SYMBOL  (current / 90d avg)
      news_sentiment — stocktwits.com/symbol/SYMBOL  (bullish % ratio, 0–1)
    """
    _require_personal_use()
    asyncio.run(_monitor_async(symbol, as_of or None, no_save, regime or None, intraday))


async def _monitor_async(
    symbol: str,
    as_of_str: str | None,
    no_save: bool,
    regime: str | None,
    intraday: bool = False,
) -> None:
    run_date = date.fromisoformat(as_of_str) if as_of_str else date.today()

    console.print(f"[bold]Fetching price data for {symbol}…[/bold]")
    try:
        price_data = await fetch_price_data(symbol)
    except RuntimeError as exc:
        console.print(f"[red]Price fetch failed: {exc}[/red]")
        raise typer.Exit(1) from None

    console.print("[bold]Fetching macro data (VIX + HY OAS)…[/bold]")
    try:
        macro_data = await fetch_macro_data()
    except RuntimeError as exc:
        console.print(f"[red]Macro fetch failed: {exc}[/red]")
        raise typer.Exit(1) from None

    console.print("[dim]Price and macro data fetched.[/dim]")

    await init_pool()
    try:
        async with acquire() as conn:
            # The monitored position is the ACTIVE PROFILE's: an individual and
            # their SMSF are separate CGT taxpayers, so lots are scoped to the
            # active account_type (never pooled). Hard-fail with no active profile —
            # without it we cannot know whose lots to aggregate (mirrors
            # PortfolioService.build()'s no-active-profile RuntimeError).
            profile = await load_active(conn)
            if profile is None:
                console.print(
                    "[red]No active profile. Run "
                    "`asx portfolio profile activate <name>` first.[/red]"
                )
                raise typer.Exit(1)
            account_type = profile.account_type
            last = await get_last_sentiment_inputs(conn, symbol)
            ctx = await load_position_context(
                conn, symbol, account_type=account_type, as_of=run_date
            )

            # Load DB underlyings if a thesis exists for this symbol
            thesis_id = ctx.get("thesis_id")
            thesis_underlyings = (
                await list_thesis_underlyings(conn, thesis_id)
                if thesis_id is not None
                else None
            )

        # Sentiment prompts with last-run defaults (pool stays open; connection released above)
        default_retail = float(last["retail_ratio"]) if last else 1.0
        default_sentiment = float(last["news_sentiment"]) if last else 0.5

        console.print(
            "\n[yellow]Manual inputs required[/yellow] "
            "(Stocktwits: stocktwits.com/symbol/"
            + symbol.split(".")[0]
            + ")"
        )
        retail_ratio_f = typer.prompt(
            "  Retail ratio (current mentions / 90d avg)",
            default=default_retail,
            type=float,
        )
        news_sentiment_f = typer.prompt(
            "  News sentiment (bullish ratio, 0.0–1.0)",
            default=default_sentiment,
            type=float,
        )

        # Optional volume + short interest prompts (Enter to skip)
        last_vol = last.get("volume_vs_avg_pct") if last else None
        last_si = last.get("short_interest_pct") if last else None
        vol_default = str(float(last_vol)) if last_vol is not None else ""
        si_default = str(float(last_si)) if last_si is not None else ""

        vol_input = typer.prompt(
            "  Volume vs 30d avg % [Enter to skip]", default=vol_default
        )
        si_input = typer.prompt(
            "  Short interest % of float [Enter to skip]", default=si_default
        )

        from decimal import Decimal

        volume_vs_avg_pct = (
            Decimal(vol_input.strip()).quantize(Decimal("0.1"))
            if vol_input.strip()
            else None
        )
        short_interest_pct = (
            Decimal(si_input.strip()).quantize(Decimal("0.01"))
            if si_input.strip()
            else None
        )

        inputs = MonitorInput(
            symbol=symbol,
            as_of=run_date,
            current_price=price_data.current_price,
            ma_50d=price_data.ma_50d,
            ma_200d=price_data.ma_200d,
            avg_weekly_move=price_data.avg_weekly_move,
            vix_5d_move=macro_data.vix_5d_move,
            hy_oas_5d_move=macro_data.hy_oas_5d_move,
            retail_ratio=Decimal(str(retail_ratio_f)).quantize(Decimal("0.01")),
            news_sentiment=Decimal(str(news_sentiment_f)).quantize(Decimal("0.01")),
            stop_price=ctx.get("stop_price"),
            cost_usd=ctx.get("cost_usd"),
            shares=ctx.get("shares"),
            acquired=ctx.get("acquired"),
            cgt_date=ctx.get("cgt_date"),
            regime_label=regime,
            account_type=account_type,
            lots=ctx.get("lots") or (),
            all_eligible=ctx.get("all_eligible", False),
            price_type="intraday" if intraday else "close",
            volume_vs_avg_pct=volume_vs_avg_pct,
            short_interest_pct=short_interest_pct,
            analyst_buy_count=ctx.get("analyst_buy_count"),
            analyst_neutral_count=ctx.get("analyst_neutral_count"),
            analyst_sell_count=ctx.get("analyst_sell_count"),
            analyst_consensus_target=ctx.get("analyst_consensus_target"),
        )

        result = build_monitor_result(inputs, thesis_underlyings=thesis_underlyings)

        console.print(format_monitor(result))

        if not no_save:
            async with acquire() as conn:
                run_id = await save_run(conn, result)
            console.print(f"[dim]Run saved (run_id={run_id})[/dim]")
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

@position_app.command("history")
def history(
    symbol: str = typer.Argument(..., help="Symbol, e.g. HUBS.NYSE"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of past runs to show"),
) -> None:
    """Show a table of past monitor runs for a symbol."""
    _require_personal_use()
    asyncio.run(_history_async(symbol, limit))


async def _history_async(symbol: str, limit: int) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            runs = await list_runs(conn, symbol, limit=limit)
    finally:
        await close_pool()

    console.print(format_history(runs))
