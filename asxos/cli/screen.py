"""asx screen — Tier 2a mechanical screening CLI.

Commands:
  asx screen list                     — list active curated_composite rules
  asx screen run NAME [--sector S]    — evaluate a rule, print a shortlist
                                         [--limit N] [--no-log]

Read-only reporting over existing data (universe/fundamentals/prices) plus
one audit-log write to screening_runs (unless --no-log). Not gated by
_require_personal_use() — a screen touches no portfolio/holdings data and
produces no investment content (see the governance note in
asxos/domain/screening/evaluator.py's module docstring); the gate is
reserved for CLI commands that mutate governance_status or touch capital.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

import typer
from rich.table import Table

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.screening.evaluator import decode_rule_json, evaluate_rule, log_run
from asxos.domain.screening.types import ScreeningRule, ScreenRunResult

screen_app = typer.Typer(
    help="Tier 2a mechanical screening.",
    no_args_is_help=True,
    add_completion=False,
)


@screen_app.command("list")
def screen_list() -> None:
    """List active curated_composite screening rules."""
    asyncio.run(_list_rules())


async def _list_rules() -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, description, is_active FROM screening_rules "
                "WHERE is_active ORDER BY name"
            )
        if not rows:
            console.print("[yellow]No active screening rules defined.[/yellow]")
            return
        table = Table(title="Screening rules", show_header=True)
        for col in ("ID", "Name", "Description"):
            table.add_column(col)
        for r in rows:
            table.add_row(str(r["id"]), r["name"], r["description"] or "—")
        console.print(table)
    finally:
        await close_pool()


@screen_app.command("run")
def screen_run(
    name: str = typer.Argument(..., help="screening_rules.name"),
    sector: str = typer.Option("", "--sector", help="Narrow to one sector (must match the rule's own sector_scope, if any)"),
    limit: int = typer.Option(20, "--limit", help="Max symbols in the printed shortlist"),
    no_log: bool = typer.Option(False, "--no-log", help="Evaluate without writing to screening_runs"),
) -> None:
    """Evaluate a screening rule and print the shortlist.

    Base population is always active au_equity universe rows; the rule's
    conditions further narrow it. See docs/proposals/thesis-coverage-
    framework-2026-07-11.md Tier 2a.
    """
    asyncio.run(_run_screen(name, sector or None, limit, no_log))


async def _run_screen(name: str, sector: str | None, limit: int, no_log: bool) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, source_method, rule_json::text AS rule_json_raw, is_active "
                "FROM screening_rules WHERE name = $1",
                name,
            )
            if row is None:
                console.print(f"[red]Error:[/red] screening rule {name!r} not found")
                raise typer.Exit(1)

            rule_json = decode_rule_json(row["rule_json_raw"])
            rule = ScreeningRule(
                id=row["id"], name=row["name"], source_method=row["source_method"],
                rule_json=rule_json, is_active=row["is_active"],
            )

            result = await evaluate_rule(conn, rule, sector=sector, limit=limit)

            if not no_log:
                await log_run(conn, result, rule_json)

        _print_result(result)
    except typer.Exit:
        raise
    except (ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


def _print_result(result: ScreenRunResult) -> None:
    scope = result.sector_scope or "(cross-sector)"
    console.print(
        f"[bold]{result.rule_name}[/bold] — sector: {scope} · "
        f"universe: {result.universe_size} · matches: {result.match_count} "
        f"(showing {len(result.matches)}) · {result.duration_ms}ms"
    )
    if not result.matches:
        console.print("[yellow]No matches.[/yellow]")
        return
    fields = sorted({k for m in result.matches for k in m.values})
    table = Table(show_header=True)
    table.add_column("Symbol")
    table.add_column("Sector")
    for f in fields:
        table.add_column(f)
    for m in result.matches:
        table.add_row(
            m.symbol, m.sector or "—",
            *[_fmt(m.values.get(f)) for f in fields],
        )
    console.print(table)


def _fmt(v: Decimal | str | None) -> str:
    if v is None:
        return "—"
    return str(v)
