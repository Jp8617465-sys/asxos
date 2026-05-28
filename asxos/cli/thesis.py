"""asx thesis — trade thesis management CLI.

Commands:
  asx thesis open SYMBOL   — open a new thesis (research or watching)
  asx thesis show SYMBOL   — detailed view of the most recent thesis for a symbol
  asx thesis list          — summary table of all (or filtered) theses
  asx thesis enter SYMBOL  — transition to active (capital deployed)
  asx thesis revise SYMBOL — revise one field with an audit event
  asx thesis review SYMBOL — discipline event: reviewed, no change
  asx thesis hold SYMBOL   — alias for review
  asx thesis exit SYMBOL   — close the position
  asx thesis history SYMBOL — full revision log
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import typer
from rich.table import Table

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.theses import service as svc
from asxos.domain.theses.types import REVISABLE_FIELDS, Thesis

thesis_app = typer.Typer(
    help="Trade thesis management.",
    no_args_is_help=True,
    add_completion=False,
)

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_TIMELINE_RE = re.compile(r"^(\d+)(m|d)$", re.IGNORECASE)


def _parse_timeline(value: str) -> int:
    """Parse '18m' → 540 days, '90d' → 90 days."""
    m = _TIMELINE_RE.match(value.strip())
    if not m:
        raise typer.BadParameter(
            f"Invalid timeline {value!r}. Use Nm (months) or Nd (days), e.g. '18m' or '90d'."
        )
    n = int(m.group(1))
    unit = m.group(2).lower()
    return n * 30 if unit == "m" else n


def _parse_entry(value: str) -> tuple[Decimal, Decimal]:
    """Parse '60-65' → (60, 65) or '62' → (62, 62)."""
    value = value.strip()
    if "-" in value:
        parts = value.split("-", 1)
        try:
            lo, hi = Decimal(parts[0].strip()), Decimal(parts[1].strip())
        except InvalidOperation as exc:
            raise typer.BadParameter(f"Invalid entry band {value!r}. Use 'lo-hi' or single price.") from exc
        if lo > hi:
            raise typer.BadParameter(f"entry_band_lower ({lo}) must be ≤ entry_band_upper ({hi})")
        return lo, hi
    try:
        p = Decimal(value)
        return p, p
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid entry price {value!r}.") from exc


def _parse_decimal(value: str, label: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid {label}: {value!r}") from exc


def _thesis_summary_row(t: Thesis) -> tuple:
    """Return (symbol, status, thesis_id, entry_band, stop, target, days_since, overdue)."""
    days_since = (date.today() - t.opened_at.date()).days
    overdue = date.today() > t.revisit_due_at.date()
    entry = (
        f"{t.entry_band_lower}–{t.entry_band_upper}"
        if t.entry_band_lower and t.entry_band_upper
        else "—"
    )
    return (
        t.symbol,
        t.status,
        str(t.thesis_id),
        entry,
        str(t.stop_price or "—"),
        str(t.target_price or "—"),
        f"{days_since}d",
        "[red]YES[/red]" if overdue else "[green]no[/green]",
    )


# ---------------------------------------------------------------------------
# Async runners
# ---------------------------------------------------------------------------

async def _run(coro):  # type: ignore[no-untyped-def]
    """Boot pool, run coro, close pool."""
    await init_pool()
    try:
        return await coro
    finally:
        await close_pool()


async def _get_open_thesis(symbol: str) -> tuple[svc.asyncpg.Connection, Thesis]:
    """Used by enter/revise/review/exit — gets most recent thesis by symbol."""
    raise NotImplementedError("caller must use acquire() context")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@thesis_app.command("open")
def thesis_open(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    status: str = typer.Option("watching", "--status", help="research|watching"),
    thesis: str = typer.Option("", "--thesis", help="Thesis text (the 'why')"),
    entry: str = typer.Option("", "--entry", help="Entry band: '60-65' or single price"),
    stop: str = typer.Option("", "--stop", help="Stop price"),
    target: str = typer.Option("", "--target", help="Target price"),
    timeline: str = typer.Option("", "--timeline", help="Timeline: 18m or 90d"),
    themes: str = typer.Option("", "--themes", help="Comma-separated theme codes"),
    reason: str = typer.Option("Initial thesis", "--reason", help="Opening rationale"),
) -> None:
    """Open a new investment thesis (research or watching status)."""
    if status not in ("research", "watching"):
        raise typer.BadParameter("--status must be 'research' or 'watching'")

    entry_lo: Decimal | None = None
    entry_hi: Decimal | None = None
    if entry:
        entry_lo, entry_hi = _parse_entry(entry)

    stop_d: Decimal | None = _parse_decimal(stop, "stop") if stop else None
    target_d: Decimal | None = _parse_decimal(target, "target") if target else None
    timeline_days: int | None = _parse_timeline(timeline) if timeline else None
    theme_list = [c.strip() for c in themes.split(",") if c.strip()] if themes else []
    thesis_text: str | None = thesis.strip() or None

    asyncio.run(_open_thesis(
        symbol, status, thesis_text, entry_lo, entry_hi,
        stop_d, target_d, timeline_days, theme_list, reason,
    ))


async def _open_thesis(
    symbol: str, status: str, thesis_text: str | None,
    entry_lo: Decimal | None, entry_hi: Decimal | None,
    stop_d: Decimal | None, target_d: Decimal | None,
    timeline_days: int | None, theme_list: list[str], reason: str,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.open_thesis(
                conn, symbol,
                status=status,
                thesis_text=thesis_text,
                entry_band_lower=entry_lo,
                entry_band_upper=entry_hi,
                stop_price=stop_d,
                target_price=target_d,
                timeline_days=timeline_days,
                themes=theme_list,
                reasoning=reason,
            )
        console.print(f"[green]✓[/green] Opened thesis #{t.thesis_id} for {t.symbol} ({t.status})")
        _print_thesis_detail(t)
    finally:
        await close_pool()


@thesis_app.command("show")
def thesis_show(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
) -> None:
    """Show the most recent thesis for a symbol (all fields)."""
    asyncio.run(_show_thesis(symbol))


async def _show_thesis(symbol: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
        if t is None:
            console.print(f"[yellow]No thesis found for {symbol}[/yellow]")
            raise typer.Exit(1)
        _print_thesis_detail(t)
    finally:
        await close_pool()


@thesis_app.command("list")
def thesis_list(
    status: str = typer.Option("", "--status", help="Filter: research|watching|active|exited|expired"),
) -> None:
    """List all theses (or filter by status)."""
    asyncio.run(_list_theses(status.strip() or None))


async def _list_theses(status: str | None) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theses = await svc.list_theses(conn, status=status)
        if not theses:
            console.print("[yellow]No theses found.[/yellow]")
            return
        table = Table(title="Theses", show_header=True)
        for col in ("Symbol", "Status", "ID", "Entry band", "Stop", "Target", "Age", "Overdue"):
            table.add_column(col)
        for t in theses:
            table.add_row(*_thesis_summary_row(t))
        console.print(table)
    finally:
        await close_pool()


@thesis_app.command("enter")
def thesis_enter(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    at: str = typer.Option(..., "--at", help="Actual entry price"),
    qty: int = typer.Option(0, "--qty", help="Number of shares (informational)"),
) -> None:
    """Transition thesis to active — capital deployed."""
    price = _parse_decimal(at, "entry price")
    asyncio.run(_enter_thesis(symbol, price, qty or None))


async def _enter_thesis(symbol: str, price: Decimal, qty: int | None) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.enter_thesis(conn, t.thesis_id, price, qty)
        console.print(f"[green]✓[/green] Thesis #{t.thesis_id} {symbol} entered at {price}")
        _print_thesis_detail(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("revise")
def thesis_revise(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    reason: str = typer.Option(..., "--reason", help="Why you are revising this field"),
    thesis: str = typer.Option("", "--thesis", help="New thesis text"),
    stop: str = typer.Option("", "--stop", help="New stop price"),
    target: str = typer.Option("", "--target", help="New target price"),
    entry: str = typer.Option("", "--entry", help="New entry band: '60-65'"),
    timeline: str = typer.Option("", "--timeline", help="New timeline: 18m or 90d"),
    new_status: str = typer.Option("", "--status", help="New status"),
) -> None:
    """Revise one field on the most recent thesis for a symbol.

    One field per invocation. --reason is required.
    """
    changes: dict[str, object] = {}
    if thesis:
        changes["thesis_text"] = thesis.strip()
    if stop:
        changes["stop_price"] = _parse_decimal(stop, "stop")
    if target:
        changes["target_price"] = _parse_decimal(target, "target")
    if timeline:
        changes["timeline_days"] = _parse_timeline(timeline)
    if new_status:
        changes["status"] = new_status.strip()
    if entry:
        lo, hi = _parse_entry(entry)
        changes["entry_band_lower"] = lo
        changes["entry_band_upper"] = hi

    if not changes:
        console.print("[red]Specify at least one field to revise (--thesis, --stop, --target, --entry, --timeline, --status)[/red]")
        raise typer.Exit(1)

    asyncio.run(_revise_thesis(symbol, changes, reason))


async def _revise_thesis(symbol: str, changes: dict, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)

            for field, value in changes.items():
                if field not in REVISABLE_FIELDS:
                    console.print(f"[red]Field {field!r} is not revisable[/red]")
                    raise typer.Exit(1)
                t = await svc.revise_thesis(conn, t.thesis_id, field, value, reason)

        console.print(f"[green]✓[/green] Revised thesis #{t.thesis_id} for {symbol}")
        _print_thesis_detail(t)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


def _thesis_review_cmd(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    reason: str = typer.Option(..., "--reason", help="Why you are still holding (required)"),
) -> None:
    """Record a deliberate 'reviewed, no change' discipline event.

    This is the core discipline scaffold. You must state why you are still
    holding. No field is changed. The event is recorded in thesis_revisions.
    """
    asyncio.run(_review_thesis(symbol, reason))


# Register as both 'review' and 'hold' (alias)
thesis_app.command("review")(_thesis_review_cmd)
thesis_app.command("hold", help="Alias for 'review' — deliberate hold discipline event.")(_thesis_review_cmd)


async def _review_thesis(symbol: str, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.review_thesis(conn, t.thesis_id, reason)
        console.print(
            f"[green]✓[/green] Reviewed thesis #{t.thesis_id} for {symbol} — "
            f"next review due {t.revisit_due_at.date()}"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("exit")
def thesis_exit(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    at: str = typer.Option(..., "--at", help="Exit price"),
    stop: bool = typer.Option(False, "--stop", help="Stopped out"),
    hit_target: bool = typer.Option(False, "--target", help="Target hit"),
    reason: str = typer.Option("", "--reason", help="Exit reasoning"),
) -> None:
    """Close a thesis position."""
    price = _parse_decimal(at, "exit price")
    if stop and hit_target:
        raise typer.BadParameter("Cannot use both --stop and --target")
    rev_type = "exited_by_stop" if stop else ("exited_by_target" if hit_target else "exited")
    asyncio.run(_exit_thesis(symbol, price, rev_type, reason))


async def _exit_thesis(symbol: str, price: Decimal, rev_type: str, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            t = await svc.exit_thesis(conn, t.thesis_id, price, revision_type=rev_type, reasoning=reason)
        console.print(
            f"[green]✓[/green] Exited thesis #{t.thesis_id} for {symbol} at {price} ({rev_type})"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@thesis_app.command("history")
def thesis_history(
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
) -> None:
    """Show the full revision history for a symbol's most recent thesis."""
    asyncio.run(_thesis_history(symbol))


async def _thesis_history(symbol: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            t = await svc.get_thesis_by_symbol(conn, symbol)
            if t is None:
                console.print(f"[red]No thesis found for {symbol}[/red]")
                raise typer.Exit(1)
            history = await svc.get_history(conn, t.thesis_id)

        table = Table(title=f"Thesis #{t.thesis_id} — {symbol} history", show_header=True)
        for col in ("Date", "Type", "Fields changed", "Reasoning"):
            table.add_column(col)
        for rev in history:
            fields = ", ".join(rev.diff.keys()) or "—"
            table.add_row(
                str(rev.revised_at.date()),
                rev.revision_type,
                fields,
                rev.reasoning[:80] + ("…" if len(rev.reasoning) > 80 else ""),
            )
        console.print(table)
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_thesis_detail(t: Thesis) -> None:
    """Print a thesis in a key-value Rich panel."""
    deadline_str = "—"
    if t.timeline_days and t.opened_at:
        deadline = t.opened_at.date() + timedelta(days=t.timeline_days)
        days_elapsed = (date.today() - t.opened_at.date()).days
        deadline_str = f"{deadline} ({days_elapsed}/{t.timeline_days}d elapsed)"

    overdue = date.today() > t.revisit_due_at.date()
    revisit_str = str(t.revisit_due_at.date())
    if overdue:
        revisit_str = f"[red]{revisit_str} OVERDUE[/red]"

    rows = [
        ("ID", str(t.thesis_id)),
        ("Symbol", t.symbol),
        ("Status", t.status),
        ("Thesis", t.thesis_text or "[dim]not articulated[/dim]"),
        ("Entry band", f"{t.entry_band_lower}–{t.entry_band_upper}" if t.entry_band_lower else "—"),
        ("Stop", str(t.stop_price or "—")),
        ("Target", str(t.target_price or "—")),
        ("Timeline", deadline_str),
        ("Themes", ", ".join(t.themes) or "—"),
        ("Actual entry", f"{t.actual_entry_price} on {t.actual_entry_at.date()}" if t.actual_entry_price else "—"),
        ("Actual exit", f"{t.actual_exit_price} on {t.actual_exit_at.date()}" if t.actual_exit_price else "—"),
        ("Opened", str(t.opened_at.date())),
        ("Last revisited", str(t.last_revisited_at.date())),
        ("Next revisit due", revisit_str),
    ]

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")
    for key, val in rows:
        table.add_row(key, val)

    console.print(table)

    if t.invalidation_conditions:
        console.print("\n[bold]Invalidation conditions:[/bold]")
        for ic in t.invalidation_conditions:
            colour = {"active": "yellow", "triggered": "red", "resolved": "green"}.get(ic.status, "white")
            note = f" — {ic.note}" if ic.note else ""
            console.print(f"  [{colour}][{ic.status}][/{colour}] {ic.condition}{note}")
