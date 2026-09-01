from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from asxos import clock
from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool

journal_app = typer.Typer(help="Decisions journal.", no_args_is_help=True)

_VALID_ACTIONS = {"BUY", "SELL", "HOLD", "REVIEW", "NOTE"}


@journal_app.command("add")
def journal_add(
    symbol: str = typer.Argument(..., help="Symbol (e.g. BHP.AU) or '-' for portfolio-level"),
    action: str = typer.Argument(..., help=f"One of {sorted(_VALID_ACTIONS)}"),
    rationale: str = typer.Option(..., "--rationale", help="Why you took this action"),
    tax_note: str = typer.Option("", "--tax-note", help="CGT/franking notes"),
) -> None:
    """Record a portfolio decision."""
    _require_personal_use()
    action = action.upper()
    if action not in _VALID_ACTIONS:
        raise typer.BadParameter(f"action must be one of {sorted(_VALID_ACTIONS)}")
    sym = None if symbol == "-" else symbol
    asyncio.run(_run_journal_add(sym, action, rationale, tax_note))


async def _run_journal_add(symbol: str | None, action: str, rationale: str, tax_note: str) -> None:

    await init_pool()
    try:
        async with acquire() as conn:
            # signal_ref was a `signals`-table enrichment (Model A). The table
            # has had no writer since P1-02 retired the signal-generation
            # pipeline (rule #11) and the column is now always NULL on insert.
            inserted = await conn.fetchrow(
                """
                INSERT INTO decisions
                    (symbol, decision_date, action, rationale, signal_ref, tax_note)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, decision_date
                """,
                symbol,
                clock.today(),
                action,
                rationale,
                None,
                tax_note,
            )
    finally:
        await close_pool()

    console.print(
        f"[green]Recorded decision[/green] #{inserted['id']}: "
        f"{symbol or 'portfolio'} {action} on {inserted['decision_date']}"
    )


@journal_app.command("list")
def journal_list(
    days: int = typer.Option(30, "--days", help="Lookback window"),
    symbol: str | None = typer.Option(None, "--symbol", help="Filter to one symbol"),
) -> None:
    """Show the most recent decisions."""
    _require_personal_use()
    asyncio.run(_run_journal_list(days, symbol))


async def _run_journal_list(days: int, symbol: str | None) -> None:
    from datetime import timedelta

    await init_pool()
    try:
        async with acquire() as conn:
            cutoff = clock.today() - timedelta(days=days)
            if symbol:
                rows = await conn.fetch(
                    """
                    SELECT id, symbol, decision_date, action, rationale,
                           signal_ref, tax_note, created_at
                    FROM decisions
                    WHERE decision_date >= $1 AND symbol = $2
                    ORDER BY decision_date DESC, id DESC
                    """,
                    cutoff,
                    symbol,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, symbol, decision_date, action, rationale,
                           signal_ref, tax_note, created_at
                    FROM decisions
                    WHERE decision_date >= $1
                    ORDER BY decision_date DESC, id DESC
                    """,
                    cutoff,
                )
    finally:
        await close_pool()

    if not rows:
        console.print(f"[yellow]No decisions in the last {days} days.[/yellow]")
        return

    table = Table(title=f"Decisions (last {days} days)")
    table.add_column("#")
    table.add_column("date")
    table.add_column("symbol")
    table.add_column("action")
    table.add_column("rationale")
    table.add_column("signal_ref")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["decision_date"].isoformat(),
            r["symbol"] or "portfolio",
            r["action"],
            (r["rationale"] or "")[:60],
            r["signal_ref"] or "",
        )
    console.print(table)


@journal_app.command("review")
def journal_review(
    stale_days: int = typer.Option(60, "--stale-days", help="Flag decisions older than N days"),
) -> None:
    """Flag decisions older than `--stale-days` that may warrant a follow-up."""
    _require_personal_use()
    asyncio.run(_run_journal_review(stale_days))


async def _run_journal_review(stale_days: int) -> None:
    from datetime import timedelta

    await init_pool()
    try:
        async with acquire() as conn:
            cutoff = clock.today() - timedelta(days=stale_days)
            rows = await conn.fetch(
                """
                SELECT id, symbol, decision_date, action, rationale, signal_ref
                FROM decisions
                WHERE decision_date <= $1
                  AND action IN ('BUY', 'SELL', 'REVIEW')
                ORDER BY decision_date ASC
                """,
                cutoff,
            )
    finally:
        await close_pool()

    if not rows:
        console.print(f"[green]No actionable decisions older than {stale_days} days.[/green]")
        return

    table = Table(title=f"Decisions stale > {stale_days} days (consider follow-up)")
    table.add_column("#")
    table.add_column("date")
    table.add_column("symbol")
    table.add_column("action")
    table.add_column("rationale")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["decision_date"].isoformat(),
            r["symbol"] or "portfolio",
            r["action"],
            (r["rationale"] or "")[:80],
        )
    console.print(table)
