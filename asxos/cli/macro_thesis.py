"""asx macro-thesis — macro thesis governance CLI.

Commands:
  asx macro-thesis list                       — summary table of all macro theses
  asx macro-thesis show ID                    — detailed view
  asx macro-thesis open --from-agent-run ID   — create a draft from a logged
                                                 agent proposal (auto-advances
                                                 draft -> evidence_complete
                                                 -> pending_review)
  asx macro-thesis approve ID                 — governance_status pending_review
                                                 -> approved
  asx macro-thesis reject ID                  — governance_status draft/
                                                 evidence_complete/pending_review
                                                 -> rejected
"""
from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.macro_theses import service as svc
from asxos.domain.macro_theses.types import MacroThesis

macro_thesis_app = typer.Typer(
    help="Macro thesis governance.",
    no_args_is_help=True,
    add_completion=False,
)


@macro_thesis_app.command("list")
def macro_thesis_list() -> None:
    """List all macro theses, most recent first."""
    _require_personal_use()
    asyncio.run(_list_macro_theses())


async def _list_macro_theses() -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theses = await svc.list_macro_theses(conn)
        if not theses:
            console.print("[yellow]No macro theses yet.[/yellow]")
            return
        table = Table(title="Macro theses", show_header=True)
        for col in ("ID", "Title", "Regime", "Governance", "Created"):
            table.add_column(col)
        for mt in theses:
            table.add_row(
                str(mt.macro_thesis_id), mt.title, mt.regime_quadrant,
                mt.governance_status, str(mt.created_at.date()),
            )
        console.print(table)
    finally:
        await close_pool()


@macro_thesis_app.command("show")
def macro_thesis_show(
    macro_thesis_id: int = typer.Argument(..., help="Macro thesis ID"),
) -> None:
    """Detailed view of one macro thesis."""
    _require_personal_use()
    asyncio.run(_show_macro_thesis(macro_thesis_id))


async def _show_macro_thesis(macro_thesis_id: int) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            mt = await svc.get_macro_thesis(conn, macro_thesis_id)
        if mt is None:
            console.print(f"[red]Error:[/red] Macro thesis {macro_thesis_id} not found")
            raise typer.Exit(1)
        _print_macro_thesis_detail(mt)
    finally:
        await close_pool()


@macro_thesis_app.command("open")
def macro_thesis_open(
    from_agent_run: int = typer.Option(
        0, "--from-agent-run",
        help="agent_runs.run_id to create a draft macro thesis from (required)",
    ),
) -> None:
    """Create a macro thesis draft from a logged agent_runs proposal.

    Auto-advances draft -> evidence_complete -> pending_review in the same
    transaction (the evidence requirement is already satisfied by
    construction — see asxos/domain/macro_theses/service.py's docstring).
    """
    _require_personal_use()
    if not from_agent_run:
        console.print("[red]Error:[/red] --from-agent-run is required")
        raise typer.Exit(1)
    asyncio.run(_open_macro_thesis_from_agent_run(from_agent_run))


async def _open_macro_thesis_from_agent_run(run_id: int) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            mt = await svc.create_macro_thesis_from_agent_run(conn, run_id)
        console.print(
            f"[green]✓[/green] Opened draft macro thesis #{mt.macro_thesis_id} "
            f"from agent run #{run_id} (governance_status={mt.governance_status})"
        )
        _print_macro_thesis_detail(mt)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@macro_thesis_app.command("approve")
def macro_thesis_approve(
    macro_thesis_id: int = typer.Argument(..., help="Macro thesis ID"),
    reason: str = typer.Option(..., "--reason", help="Why you are approving this"),
) -> None:
    """Approve a macro thesis pending review — governance_status -> 'approved'."""
    _require_personal_use()
    asyncio.run(_approve_macro_thesis(macro_thesis_id, reason))


async def _approve_macro_thesis(macro_thesis_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            mt = await svc.approve_object(conn, macro_thesis_id, reasoning=reason)
        console.print(f"[green]✓[/green] Approved macro thesis #{mt.macro_thesis_id}")
        _print_macro_thesis_detail(mt)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@macro_thesis_app.command("reject")
def macro_thesis_reject(
    macro_thesis_id: int = typer.Argument(..., help="Macro thesis ID"),
    reason: str = typer.Option(..., "--reason", help="Why you are rejecting this"),
) -> None:
    """Reject a macro thesis — governance_status -> 'rejected'."""
    _require_personal_use()
    asyncio.run(_reject_macro_thesis(macro_thesis_id, reason))


async def _reject_macro_thesis(macro_thesis_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            mt = await svc.reject_object(conn, macro_thesis_id, reasoning=reason)
        console.print(f"[yellow]✗[/yellow] Rejected macro thesis #{mt.macro_thesis_id}")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


def _print_macro_thesis_detail(mt: MacroThesis) -> None:
    """Print a macro thesis in a key-value Rich panel."""
    rows = [
        ("ID", str(mt.macro_thesis_id)),
        ("Title", mt.title),
        ("Governance", mt.governance_status),
        ("Regime quadrant", mt.regime_quadrant),
        ("Horizon", f"{mt.horizon_months} months" if mt.horizon_months else "—"),
        ("Thesis", mt.thesis_text),
        ("Catalyst", mt.catalyst),
        ("Falsifier", mt.falsifier),
        ("Data signals", ", ".join(mt.data_signals) or "—"),
        ("Source run", str(mt.source_run_id) if mt.source_run_id else "human-authored"),
        ("Created", str(mt.created_at.date())),
        ("Retired", str(mt.retired_at) if mt.retired_at else "—"),
    ]

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")
    for key, val in rows:
        table.add_row(key, val)

    console.print(table)
