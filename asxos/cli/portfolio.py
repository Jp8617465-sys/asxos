from __future__ import annotations

import asyncio
from datetime import date

import typer
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool

portfolio_app = typer.Typer(
    help="Portfolio construction (M13). Requires ASXOS_PERSONAL_USE=1.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Root-level commands (registered on the root app in main.py)
# ---------------------------------------------------------------------------

def build_portfolio(
    profile_name: str | None = typer.Option(None, "--profile", help="Profile name (default: active)"),
    as_of: str | None = typer.Option(None, "--as-of", help="Build date YYYY-MM-DD (default: today)"),
    signals_date: str | None = typer.Option(None, "--signals", help="Candidate evidence date YYYY-MM-DD (default: latest). Retained for the replacement candidate source; today it only appears in the unavailability message."),
    no_tax_overlay: bool = typer.Option(False, "--no-tax-overlay", help="Skip loss-harvest tagging"),
    no_constraints: bool = typer.Option(False, "--no-constraints", help="Skip constraint waterfall"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print result without writing to DB"),
    persist: bool = typer.Option(True, "--persist/--no-persist", help="Write run to DB"),
) -> None:
    """Construct a portfolio from the active profile + latest signals."""
    _require_personal_use()
    # --dry-run forces --no-persist (plan H.1 CRITICAL-6).
    if dry_run:
        persist = False

    build_date = None
    if as_of:
        try:
            build_date = date.fromisoformat(as_of)
        except ValueError as e:
            raise typer.BadParameter(f"--as-of must be YYYY-MM-DD: {e}") from e

    sig_date = None
    if signals_date:
        try:
            sig_date = date.fromisoformat(signals_date)
        except ValueError as e:
            raise typer.BadParameter(f"--signals must be YYYY-MM-DD: {e}") from e

    asyncio.run(
        _run_build_portfolio(
            profile_name=profile_name,
            as_of=build_date,
            signals_date=sig_date,
            apply_constraints=not no_constraints,
            apply_tax_overlay=not no_tax_overlay,
            do_persist=persist,
        )
    )


async def _run_build_portfolio(
    *,
    profile_name: str | None,
    as_of: date | None,
    signals_date: date | None,
    apply_constraints: bool,
    apply_tax_overlay: bool,
    do_persist: bool,
) -> None:
    from dataclasses import replace

    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            try:
                result = await svc.build(
                    conn,
                    profile_name=profile_name,
                    as_of=as_of,
                    signals_date=signals_date,
                    apply_constraints=apply_constraints,
                    apply_tax_overlay=apply_tax_overlay,
                )
            except RuntimeError as e:
                console.print(f"[red]build-portfolio failed:[/red] {e}")
                raise typer.Exit(code=1) from e

            run_id: int | None = None
            if do_persist:
                run_id = await svc.persist(conn, result)
                result = replace(result, run_id=run_id)
                console.print(f"[green]Wrote run {run_id}[/green] ({len(result.targets)} targets, {len(result.trades)} trades).")
    finally:
        await close_pool()

    s = result.summary
    console.print(
        f"Profile: {result.profile.name} · as_of: {result.as_of} · signals: {result.signals_as_of} · "
        f"model: {s.get('model_version', '?')}"
    )
    console.print(
        f"Trades: {s['n_buys']} buys (+${s['total_buy_aud']:,.0f}) · "
        f"{s['n_sells']} sells (${s['total_sell_aud']:,.0f}) · "
        f"{s['n_holds']} holds · {s['n_deferrals']} deferred"
    )

    table = Table(title=f"Target allocations (run {run_id or 'dry-run'})")
    table.add_column("symbol")
    table.add_column("weight", justify="right")
    table.add_column("target_aud", justify="right")
    table.add_column("sector")
    table.add_column("signal")
    table.add_column("flags")

    for t in sorted(result.targets, key=lambda x: -x.target_weight):
        flags = ", ".join(sorted(t.constraint_log.keys())) if t.constraint_log else ""
        table.add_row(
            t.symbol,
            f"{t.target_weight:.4f}",
            f"${t.target_weight * result.profile.capital_aud:,.0f}",
            t.sector or "—",
            t.signal_label,
            flags,
        )
    console.print(table)


def propose_trades(
    run_id: int | None = typer.Option(None, "--run-id", help="Run ID (default: latest)"),
    side: str | None = typer.Option(None, "--side", help="Filter: buy | sell | hold"),
    csv_path: str | None = typer.Option(None, "--csv", help="Write trades to CSV file"),
) -> None:
    """Show proposed trades from a build-portfolio run."""
    _require_personal_use()
    if side and side not in ("buy", "sell", "hold"):
        raise typer.BadParameter("--side must be buy, sell, or hold")
    asyncio.run(_run_propose_trades(run_id=run_id, side=side, csv_path=csv_path))


async def _run_propose_trades(
    *, run_id: int | None, side: str | None, csv_path: str | None
) -> None:
    import csv as _csv
    import io

    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            loaded = await svc.load_run(conn, run_id)
    finally:
        await close_pool()

    if loaded is None:
        console.print("[yellow]No runs found.[/yellow] Run `asx build-portfolio` first.")
        raise typer.Exit(code=1)

    run_hdr, _targets, trades = loaded
    if side:
        trades = [t for t in trades if t["side"] == side]

    table = Table(title=f"Proposed trades — run {run_hdr['run_id']} ({run_hdr['as_of']})")
    table.add_column("symbol")
    table.add_column("side")
    table.add_column("delta_qty", justify="right")
    table.add_column("delta_aud", justify="right")
    table.add_column("price", justify="right")
    table.add_column("tags")

    for t in trades:
        tags_str = str(t.get("rationale_tags") or "")[:60]
        table.add_row(
            t["symbol"],
            t["side"],
            f"{t['delta_qty']:+.2f}",
            f"${t['delta_aud']:+,.0f}",
            f"${t['reference_price']:,.2f}",
            tags_str,
        )
    console.print(table)

    if csv_path:
        buf = io.StringIO()
        writer = _csv.DictWriter(
            buf,
            fieldnames=["symbol", "side", "delta_qty", "delta_aud",
                        "target_qty", "current_qty", "reference_price",
                        "rationale_tags", "lot_hints"],
        )
        writer.writeheader()
        for t in trades:
            writer.writerow({k: t.get(k, "") for k in writer.fieldnames})
        with open(csv_path, "w") as f:
            f.write(buf.getvalue())
        console.print(f"[green]Wrote {len(trades)} trades to {csv_path}[/green]")


# ---------------------------------------------------------------------------
# portfolio sub-app commands
# ---------------------------------------------------------------------------

@portfolio_app.command("show")
def portfolio_show(
    run_id: int | None = typer.Option(None, "--run-id", help="Run ID (default: latest)"),
) -> None:
    """Show the target allocation table for a build-portfolio run."""
    _require_personal_use()
    asyncio.run(_run_portfolio_show(run_id))


async def _run_portfolio_show(run_id: int | None) -> None:
    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            loaded = await svc.load_run(conn, run_id)
    finally:
        await close_pool()

    if loaded is None:
        console.print("[yellow]No runs found.[/yellow] Run `asx build-portfolio` first.")
        raise typer.Exit(code=1)

    run_hdr, targets, _ = loaded
    console.print(
        f"Run {run_hdr['run_id']} — profile: {run_hdr['profile_name']} · "
        f"as_of: {run_hdr['as_of']} · signals: {run_hdr['signals_as_of']} · "
        f"model: {run_hdr['model_version']}"
    )

    table = Table(title="Target allocations")
    table.add_column("symbol")
    table.add_column("weight", justify="right")
    table.add_column("target_aud", justify="right")
    table.add_column("sector")
    table.add_column("signal")
    table.add_column("constraint_log")

    for t in targets:
        log = str(t.get("constraint_log") or "")[:40]
        table.add_row(
            t["symbol"],
            f"{t['target_weight']:.4f}",
            f"${t['target_aud']:,.0f}",
            t.get("sector") or "—",
            t.get("signal_label") or "",
            log,
        )
    console.print(table)


@portfolio_app.command("history")
def portfolio_history(
    days: int = typer.Option(30, "--days", help="Lookback window in days"),
) -> None:
    """List recent build-portfolio runs."""
    _require_personal_use()
    asyncio.run(_run_portfolio_history(days))


async def _run_portfolio_history(days: int) -> None:
    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            runs = await svc.list_runs(conn, days=days)
    finally:
        await close_pool()

    if not runs:
        console.print(f"[yellow]No runs in the last {days} days.[/yellow]")
        return

    table = Table(title=f"Portfolio runs (last {days} days)")
    table.add_column("run_id", justify="right")
    table.add_column("as_of")
    table.add_column("profile")
    table.add_column("signals_as_of")
    table.add_column("model")
    table.add_column("created_at")

    for r in runs:
        table.add_row(
            str(r["run_id"]),
            str(r["as_of"]),
            r["profile_name"],
            str(r["signals_as_of"]),
            r["model_version"],
            str(r["created_at"])[:16],
        )
    console.print(table)


@portfolio_app.command("paper-review")
def portfolio_paper_review(
    weeks: int = typer.Option(4, "--weeks", help="Minimum weeks of history required"),
    today: str = typer.Option("", "--today", help="Override today's date YYYY-MM-DD (testing)"),
) -> None:
    """Evaluate all build-portfolio runs that are ≥ WEEKS old against current prices.

    Prints a table of hypothetical P&L for each evaluable run.  Use this
    weekly during the paper-trading window (plan Part 0 Q3 / M13.8).
    """
    _require_personal_use()
    _today = date.fromisoformat(today) if today else date.today()
    asyncio.run(_run_portfolio_paper_review(weeks=weeks, today=_today))


async def _run_portfolio_paper_review(*, weeks: int, today: date) -> None:
    from asxos.domain.portfolio.paper_trade import (
        evaluate_run_from_db,
        list_evaluable_runs,
    )

    await init_pool()
    try:
        async with acquire() as conn:
            runs = await list_evaluable_runs(conn, weeks=weeks, today=today)

            if not runs:
                console.print(
                    f"[yellow]No evaluable runs found.[/yellow] "
                    f"Runs need at least {weeks} weeks of history. "
                    f"Run `asx build-portfolio` each week and check back."
                )
                return

            table = Table(
                title=f"Paper-trade review — {weeks}+ week outcomes (vs today {today})"
            )
            table.add_column("run_id", justify="right")
            table.add_column("run date")
            table.add_column("days held", justify="right")
            table.add_column("traded $", justify="right")
            table.add_column("P&L $", justify="right")
            table.add_column("return %", justify="right")
            table.add_column("missing prices")

            for r in runs:
                outcome = await evaluate_run_from_db(conn, r["run_id"], today)
                if outcome is None:
                    continue

                pnl_style = "green" if outcome.total_hypothetical_pnl_aud >= 0 else "red"
                table.add_row(
                    str(outcome.run_id),
                    str(outcome.run_as_of),
                    str(outcome.outcome_days),
                    f"${outcome.total_traded_aud:,.0f}",
                    f"[{pnl_style}]${outcome.total_hypothetical_pnl_aud:,.0f}[/{pnl_style}]",
                    f"[{pnl_style}]{outcome.hypothetical_return_pct:+.2f}%[/{pnl_style}]",
                    ", ".join(outcome.symbols_missing_exit_price) or "—",
                )

            console.print(table)
            console.print(
                f"\n[dim]Showing {len(runs)} run(s) with ≥{weeks} weeks of price history. "
                "Run [bold]asx portfolio signoff[/bold] once satisfied.[/dim]"
            )
    finally:
        await close_pool()


@portfolio_app.command("signoff")
def portfolio_signoff(
    note: str = typer.Option("", "--note", help="Optional free-text note to record"),
    force: bool = typer.Option(False, "--force", help="Skip the 4-week gate check"),
) -> None:
    """Record paper-trade sign-off and prompt to enable section 6 in the brief.

    Requires ≥4 evaluable runs (≥4 weeks of build-portfolio history) unless
    --force is passed.  Inserts a decisions journal entry tagged
    [m13_paper_signoff] and prints the Render REST API command to flip
    ASXOS_PORTFOLIO_BRIEF_ENABLED=1 (plan Part 0 Q3 / M13.8).
    """
    _require_personal_use()
    asyncio.run(_run_portfolio_signoff(note=note, force=force))


async def _run_portfolio_signoff(*, note: str, force: bool) -> None:
    from asxos.domain.portfolio.paper_trade import has_enough_paper_weeks, record_signoff

    today = date.today()

    await init_pool()
    try:
        async with acquire() as conn:
            if not force:
                ok = await has_enough_paper_weeks(conn, maturation_weeks=4, today=today)
                if not ok:
                    console.print(
                        "[red]Insufficient paper-trade history.[/red] "
                        "Need ≥4 weeks of matured paper-trade evidence with a "
                        "continuously-running weekly build cron (oldest run ≥28 days "
                        "old; no cron blackout >14 days). "
                        "Pass [bold]--force[/bold] to override."
                    )
                    raise typer.Exit(code=1)

            decisions_id = await record_signoff(conn, note=note, as_of=today)
    finally:
        await close_pool()

    console.print(f"[green]✓[/green] Sign-off recorded (decisions.id={decisions_id}).")
    console.print()
    console.print("[bold]Next step — flip the brief flag via the Render REST API:[/bold]")
    console.print(
        "  curl -X PUT -H \"Authorization: Bearer $RENDER_API_KEY\" \\\n"
        "       -H \"Content-Type: application/json\" -d '{\"value\":\"1\"}' \\\n"
        "       https://api.render.com/v1/services/crn-d883biq8qa3s73eud08g/env-vars/ASXOS_PORTFOLIO_BRIEF_ENABLED"
    )
    console.print()
    console.print(
        "[dim]The next Monday brief will include section 6 "
        "(Portfolio adjustments).[/dim]"
    )
