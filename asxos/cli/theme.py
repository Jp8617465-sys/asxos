"""asx theme — investment theme stewardship CLI.

Commands:
  asx theme create CODE    — create a new theme
  asx theme list           — list all themes
  asx theme review CODE    — detailed view: metadata + linked theses + adjacencies
  asx theme adjacency add CODE_A CODE_B — add bidirectional adjacency
  asx theme stage CODE STAGE -- set lifecycle stage (user-confirmed)
  asx theme attach CODE SYMBOL -- set symbol exposure to theme
  asx theme coverage           — universe -> segment coverage rollup
  asx theme approve ID         — governance_status pending_review -> approved
  asx theme reject ID          — governance_status draft/evidence_complete/
                                  pending_review -> rejected
  asx theme holding approve ID — same, for one theme_holdings row (holding_id)
  asx theme holding reject ID  — same, for one theme_holdings row (holding_id)

Note: 'open --from-agent-run' has no theme equivalent yet — no
create_theme_from_agent_run() exists (unlike theses/macro_theses); it lands
alongside the theme-researcher/instrument-selector agents (Phase 2c). These
approve/reject verbs exist now so that dependency chain has one fewer link
to build when those agents ship.
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal, InvalidOperation

import typer
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.themes import service as svc
from asxos.domain.themes.types import Theme

theme_app = typer.Typer(
    help="Theme stewardship.",
    no_args_is_help=True,
    add_completion=False,
)

adjacency_app = typer.Typer(help="Theme adjacency management.", no_args_is_help=True)
theme_app.add_typer(adjacency_app, name="adjacency")

holding_app = typer.Typer(help="Theme-holding governance.", no_args_is_help=True)
theme_app.add_typer(holding_app, name="holding")

_VALID_STAGES = (
    "early", "early-institutional", "broad-institutional",
    "mainstream", "late-retail", "mature",
)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@theme_app.command("create")
def theme_create(
    code: str = typer.Argument(..., help="Theme slug: 'ai-infrastructure'"),
    name: str = typer.Option(..., "--name", help="Display name"),
    description: str = typer.Option(..., "--description", help="What the theme is about"),
    conviction: str = typer.Option("medium", "--conviction", help="low|medium|high"),
    stage: str = typer.Option("early", "--stage", help=f"Lifecycle stage: {_VALID_STAGES}"),
    started: str = typer.Option("", "--started", help="Start date YYYY-MM-DD (default today)"),
) -> None:
    """Create a new investment theme."""
    started_date: date | None = None
    if started:
        try:
            started_date = date.fromisoformat(started)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid date {started!r}. Use YYYY-MM-DD.") from exc
    asyncio.run(_create_theme(code, name, description, conviction, stage, started_date))


async def _create_theme(
    code: str, name: str, description: str,
    conviction: str, stage: str, started_at: date | None,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theme = await svc.create_theme(
                conn, code, name, description,
                conviction_band=conviction,
                stage=stage,
                started_at=started_at,
            )
        console.print(f"[green]✓[/green] Created theme [bold]{theme.theme_code}[/bold] (#{theme.theme_id})")
        _print_theme_detail(theme)
    except (ValueError, typer.BadParameter) as exc:
        # User-input errors get a clean one-line message; unexpected/infra errors
        # propagate with a traceback (CLAUDE.md non-negotiable #10 — fail loudly).
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@theme_app.command("list")
def theme_list() -> None:
    """List all themes."""
    asyncio.run(_list_themes())


async def _list_themes() -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            themes = await svc.list_themes(conn)
        if not themes:
            console.print("[yellow]No themes defined.[/yellow]")
            return
        table = Table(title="Themes", show_header=True)
        for col in ("Code", "Name", "Stage", "Suggested", "Conviction", "Active", "Last reviewed"):
            table.add_column(col)
        for t in themes:
            active = "[green]yes[/green]" if t.retired_at is None else f"[dim]retired {t.retired_at}[/dim]"
            suggested = t.stage_suggested or "—"
            stage_cell = t.stage
            if t.stage_suggested and t.stage_suggested != t.stage:
                stage_cell = f"[yellow]{t.stage}[/yellow]"  # diverges from auto-suggestion
            table.add_row(
                t.theme_code, t.name, stage_cell, suggested,
                t.conviction_band, active, str(t.last_reviewed_at.date()),
            )
        console.print(table)
    finally:
        await close_pool()


@theme_app.command("coverage")
def theme_coverage() -> None:
    """Universe -> segment coverage rollup: where are we structurally blind?

    Sector for au_equity; one bucket per non-equity security_kind
    (ETF/LIC/hybrid have no GICS sector). See docs/proposals/
    thesis-coverage-framework-2026-07-11.md Tier 1a.
    """
    asyncio.run(_show_coverage())


async def _show_coverage() -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            segments = await svc.get_coverage_rollup(conn)
        if not segments:
            console.print("[yellow]No active universe symbols found.[/yellow]")
            return

        total_symbols = sum(s.symbol_count for s in segments)
        total_theme = sum(s.theme_covered_count for s in segments)
        total_thesis = sum(s.thesis_covered_count for s in segments)

        table = Table(title="Universe coverage", show_header=True)
        for col in ("Kind", "Segment", "Symbols", "Theme-covered", "Thesis-covered"):
            table.add_column(col)
        for s in segments:
            segment_label = s.sector if s.sector is not None else "(non-equity)"
            theme_cell = _coverage_cell(s.theme_covered_count, s.symbol_count)
            thesis_cell = _coverage_cell(s.thesis_covered_count, s.symbol_count)
            table.add_row(
                s.security_kind, segment_label, str(s.symbol_count),
                theme_cell, thesis_cell,
            )
        console.print(table)
        console.print(
            f"\n[bold]Total:[/bold] {total_symbols} active symbols · "
            f"{total_theme} theme-covered ({total_theme / total_symbols:.1%}) · "
            f"{total_thesis} thesis-covered ({total_thesis / total_symbols:.1%})"
        )
    finally:
        await close_pool()


def _coverage_cell(covered: int, total: int) -> str:
    if covered == 0:
        return "[red]0[/red]"
    if covered == total:
        return f"[green]{covered}[/green]"
    return f"[yellow]{covered}[/yellow]"


@theme_app.command("review")
def theme_review(
    code: str = typer.Argument(..., help="Theme code"),
) -> None:
    """Detailed view: theme metadata + linked theses + adjacencies."""
    asyncio.run(_review_theme(code))


async def _review_theme(code: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theme = await svc.get_theme(conn, code)
            if theme is None:
                console.print(f"[red]Theme {code!r} not found[/red]")
                raise typer.Exit(1)
            holdings = await svc.list_theme_holdings(conn, code)

            # Fetch open theses whose symbol appears in holdings
            symbols = [h.symbol for h in holdings]
            thesis_rows = []
            if symbols:
                thesis_rows = await conn.fetch(
                    """
                    SELECT thesis_id, symbol, status, stop_price, target_price,
                           opened_at, last_revisited_at
                    FROM theses
                    WHERE symbol = ANY($1::text[])
                      AND status NOT IN ('exited', 'expired')
                    ORDER BY symbol, opened_at DESC
                    """,
                    symbols,
                )

        _print_theme_detail(theme)

        if theme.adjacent_codes:
            console.print(f"\n[bold]Adjacent themes:[/bold] {', '.join(theme.adjacent_codes)}")

        if holdings:
            console.print("\n[bold]Symbol exposures:[/bold]")
            h_table = Table(show_header=True)
            for col in ("Symbol", "Strength", "Direction", "Source", "Mechanism"):
                h_table.add_column(col)
            for h in holdings:
                h_table.add_row(
                    h.symbol,
                    str(h.exposure_strength),
                    h.direction,
                    h.source,
                    (h.mechanism_text[:60] + "…") if len(h.mechanism_text) > 60 else h.mechanism_text or "—",
                )
            console.print(h_table)

        if thesis_rows:
            console.print("\n[bold]Open theses on theme symbols:[/bold]")
            t_table = Table(show_header=True)
            for col in ("Symbol", "Status", "Thesis ID", "Stop", "Target", "Opened"):
                t_table.add_column(col)
            for r in thesis_rows:
                t_table.add_row(
                    r["symbol"], r["status"], str(r["thesis_id"]),
                    str(r["stop_price"] or "—"),
                    str(r["target_price"] or "—"),
                    str(r["opened_at"].date()),
                )
            console.print(t_table)
    finally:
        await close_pool()


@adjacency_app.command("add")
def adjacency_add(
    code_a: str = typer.Argument(..., help="First theme code"),
    code_b: str = typer.Argument(..., help="Second theme code"),
) -> None:
    """Add a bidirectional adjacency between two themes."""
    asyncio.run(_add_adjacency(code_a, code_b))


async def _add_adjacency(code_a: str, code_b: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            await svc.add_adjacency(conn, code_a, code_b)
        console.print(f"[green]✓[/green] {code_a} ↔ {code_b} are now adjacent")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@theme_app.command("stage")
def theme_stage(
    code: str = typer.Argument(..., help="Theme code"),
    stage: str = typer.Argument(..., help=f"One of: {', '.join(_VALID_STAGES)}"),
    note: str = typer.Option(..., "--note", help="Why you believe the theme is at this stage (required)"),
) -> None:
    """Set the user-confirmed lifecycle stage for a theme.

    This updates themes.stage (user-confirmed). It does NOT touch
    stage_suggested — that is written only by the auto-classifier.

    If stage_suggested differs from stage, the divergence is shown.
    """
    asyncio.run(_set_stage(code, stage, note))


async def _set_stage(code: str, stage: str, note: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            old_theme = await svc.get_theme(conn, code)
            theme = await svc.set_stage(conn, code, stage, note)
        old_stage = old_theme.stage if old_theme else "?"
        console.print(
            f"[green]✓[/green] {code}: stage {old_stage} → {theme.stage}"
        )
        if theme.stage_suggested and theme.stage_suggested != theme.stage:
            console.print(
                f"[yellow]Note:[/yellow] auto-suggested stage is {theme.stage_suggested!r} "
                f"— your manual override is recorded."
            )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@theme_app.command("attach")
def theme_attach(
    code: str = typer.Argument(..., help="Theme code"),
    symbol: str = typer.Argument(..., help="Symbol, e.g. CBA.AU"),
    strength: str = typer.Option(..., "--strength", help="Exposure [0-1], e.g. 0.7"),
    direction: str = typer.Option("positive", "--direction", help="positive|negative"),
    mechanism: str = typer.Option("", "--mechanism", help="Mechanism explanation"),
    note: str = typer.Option("", "--note", help="Optional note"),
) -> None:
    """Set a symbol's exposure strength and direction for a theme.

    Upserts the theme_holdings row: (theme_id, symbol) PK.
    Also syncs the denormalised theses.themes TEXT[] for open theses.
    """
    try:
        strength_d = Decimal(strength)
    except InvalidOperation as exc:
        raise typer.BadParameter(f"Invalid strength {strength!r}. Use a decimal in [0, 1].") from exc
    asyncio.run(_attach_thesis(code, symbol, strength_d, direction, mechanism, note or None))


async def _attach_thesis(
    code: str, symbol: str, strength: Decimal,
    direction: str, mechanism: str, note: str | None,
) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            holding = await svc.attach_thesis(
                conn, code, symbol,
                exposure_strength=strength,
                direction=direction,
                mechanism_text=mechanism,
                source="user",
                note=note,
            )
        console.print(
            f"[green]✓[/green] {symbol} → {code}: "
            f"exposure {holding.exposure_strength} ({holding.direction})"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@theme_app.command("approve")
def theme_approve(
    theme_id: int = typer.Argument(..., help="Theme ID"),
    reason: str = typer.Option(..., "--reason", help="Why you are approving this"),
) -> None:
    """Approve a theme pending review — governance_status -> 'approved'."""
    _require_personal_use()
    asyncio.run(_approve_theme(theme_id, reason))


async def _approve_theme(theme_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theme = await svc.approve_theme(conn, theme_id, reasoning=reason)
        console.print(f"[green]✓[/green] Approved theme [bold]{theme.theme_code}[/bold] (#{theme.theme_id})")
        _print_theme_detail(theme)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@theme_app.command("reject")
def theme_reject(
    theme_id: int = typer.Argument(..., help="Theme ID"),
    reason: str = typer.Option(..., "--reason", help="Why you are rejecting this"),
) -> None:
    """Reject a theme — governance_status -> 'rejected'."""
    _require_personal_use()
    asyncio.run(_reject_theme(theme_id, reason))


async def _reject_theme(theme_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            theme = await svc.reject_theme(conn, theme_id, reasoning=reason)
        console.print(f"[yellow]✗[/yellow] Rejected theme [bold]{theme.theme_code}[/bold] (#{theme.theme_id})")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@holding_app.command("approve")
def theme_holding_approve(
    holding_id: int = typer.Argument(..., help="theme_holdings.holding_id (surrogate key)"),
    reason: str = typer.Option(..., "--reason", help="Why you are approving this"),
) -> None:
    """Approve a theme_holdings row pending review — governance_status -> 'approved'."""
    _require_personal_use()
    asyncio.run(_approve_theme_holding(holding_id, reason))


async def _approve_theme_holding(holding_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            holding = await svc.approve_theme_holding(conn, holding_id, reasoning=reason)
        console.print(
            f"[green]✓[/green] Approved theme holding #{holding_id} "
            f"({holding.symbol} -> theme #{holding.theme_id})"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


@holding_app.command("reject")
def theme_holding_reject(
    holding_id: int = typer.Argument(..., help="theme_holdings.holding_id (surrogate key)"),
    reason: str = typer.Option(..., "--reason", help="Why you are rejecting this"),
) -> None:
    """Reject a theme_holdings row — governance_status -> 'rejected'."""
    _require_personal_use()
    asyncio.run(_reject_theme_holding(holding_id, reason))


async def _reject_theme_holding(holding_id: int, reason: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            holding = await svc.reject_theme_holding(conn, holding_id, reasoning=reason)
        console.print(
            f"[yellow]✗[/yellow] Rejected theme holding #{holding_id} "
            f"({holding.symbol} -> theme #{holding.theme_id})"
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    finally:
        await close_pool()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_theme_detail(theme: Theme) -> None:
    rows = [
        ("ID", str(theme.theme_id)),
        ("Code", theme.theme_code),
        ("Name", theme.name),
        ("Description", theme.description),
        ("Conviction", theme.conviction_band),
        ("Stage", theme.stage),
        ("Stage suggested", str(theme.stage_suggested or "—")),
        ("Started", str(theme.started_at)),
        ("Retired", str(theme.retired_at or "—")),
        ("Last reviewed", str(theme.last_reviewed_at.date())),
    ]
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")
    for key, val in rows:
        table.add_row(key, val)
    console.print(table)
