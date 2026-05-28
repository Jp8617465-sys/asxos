from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool

profile_app = typer.Typer(
    help="Investment profile (M13). Requires ASXOS_PERSONAL_USE=1.",
    no_args_is_help=True,
    add_completion=False,
)


@profile_app.command("init")
def profile_init(
    name: str = typer.Option("baseline", "--name", help="Profile name"),
    account: str = typer.Option("individual", "--account", help="individual | smsf"),
    risk: str = typer.Option(
        "balanced", "--risk", help="conservative|balanced|growth|aggressive"
    ),
    capital: float = typer.Option(..., "--capital", help="AUD investable"),
    cash_floor: float = typer.Option(0.05, "--cash-floor"),
    leverage: float = typer.Option(1.0, "--leverage"),
    per_name_cap: float = typer.Option(0.10, "--per-name-cap"),
    sector_cap: float = typer.Option(0.30, "--sector-cap"),
    exclude_sectors: str = typer.Option("", "--exclude-sectors", help="comma-separated GICS"),
    exclude_symbols: str = typer.Option("", "--exclude-symbols", help="comma-separated symbols"),
    min_position: float = typer.Option(1000.0, "--min-position"),
    horizon_years: int = typer.Option(10, "--horizon-years"),
    defer_boundary: bool = typer.Option(
        True, "--defer-boundary/--no-defer-boundary",
        help="Defer sells within 30d of CGT discount eligibility (spec §5.1)",
    ),
    activate: bool = typer.Option(False, "--activate", help="Mark this row is_active=TRUE"),
) -> None:
    """Create a new investment profile."""
    _require_personal_use()
    asyncio.run(_run_profile_init(
        name=name, account=account, risk=risk, capital=capital,
        cash_floor=cash_floor, leverage=leverage,
        per_name_cap=per_name_cap, sector_cap=sector_cap,
        exclude_sectors=exclude_sectors, exclude_symbols=exclude_symbols,
        min_position=min_position, horizon_years=horizon_years,
        defer_boundary=defer_boundary, do_activate=activate,
    ))


async def _run_profile_init(
    *,
    name: str, account: str, risk: str, capital: float,
    cash_floor: float, leverage: float,
    per_name_cap: float, sector_cap: float,
    exclude_sectors: str, exclude_symbols: str,
    min_position: float, horizon_years: int,
    defer_boundary: bool, do_activate: bool,
) -> None:
    from decimal import Decimal

    from asxos.domain.portfolio.profile import activate as activate_fn
    from asxos.domain.portfolio.profile import save as save_profile

    excl_sectors = tuple(s.strip() for s in exclude_sectors.split(",") if s.strip())
    excl_symbols = tuple(s.strip() for s in exclude_symbols.split(",") if s.strip())

    await init_pool()
    try:
        async with acquire() as conn:
            try:
                pid = await save_profile(
                    conn,
                    name=name,
                    account_type=account,
                    risk_tolerance=risk,  # type: ignore[arg-type]
                    capital_aud=Decimal(str(capital)),
                    cash_floor_pct=Decimal(str(cash_floor)),
                    leverage_cap=Decimal(str(leverage)),
                    per_name_cap_pct=Decimal(str(per_name_cap)),
                    sector_cap_pct=Decimal(str(sector_cap)),
                    excluded_sectors=excl_sectors,
                    excluded_symbols=excl_symbols,
                    min_position_aud=Decimal(str(min_position)),
                    horizon_years=horizon_years,
                    defer_near_boundary_sells=defer_boundary,
                )
            except ValueError as e:
                raise typer.BadParameter(str(e)) from e

            console.print(f"[green]Created profile[/green] '{name}' (id {pid}).")

            if do_activate:
                await activate_fn(conn, name)
                console.print(f"[green]Activated[/green] '{name}'.")
    finally:
        await close_pool()


@profile_app.command("show")
def profile_show(
    name: str = typer.Option(None, "--name", help="Show this profile (default: active)"),
) -> None:
    """Show a profile's fields."""
    _require_personal_use()
    asyncio.run(_run_profile_show(name))


async def _run_profile_show(name: str | None) -> None:
    from asxos.domain.portfolio.profile import load_active, load_by_name

    await init_pool()
    try:
        async with acquire() as conn:
            p = await load_by_name(conn, name) if name else await load_active(conn)
    finally:
        await close_pool()

    if p is None:
        console.print(
            f"[yellow]{'No profile named ' + repr(name) if name else 'No active profile'}.[/yellow]"
        )
        raise typer.Exit(code=1)

    table = Table(title=f"Profile '{p.name}' (id {p.profile_id})")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("active", "✓" if p.is_active else "")
    table.add_row("account_type", p.account_type)
    table.add_row("risk_tolerance", f"{p.risk_tolerance} ({p.risk_tolerance_scalar})")
    table.add_row("capital_aud", f"${p.capital_aud:,.2f}")
    table.add_row("cash_floor_pct", f"{p.cash_floor_pct}")
    table.add_row("leverage_cap", f"{p.leverage_cap}")
    table.add_row("per_name_cap_pct", f"{p.per_name_cap_pct}")
    table.add_row("sector_cap_pct", f"{p.sector_cap_pct}")
    table.add_row("excluded_sectors", ", ".join(p.excluded_sectors) or "—")
    table.add_row("excluded_symbols", ", ".join(p.excluded_symbols) or "—")
    table.add_row("min_position_aud", f"${p.min_position_aud:,.2f}")
    table.add_row("horizon_years", str(p.horizon_years))
    table.add_row("defer_near_boundary_sells", "✓" if p.defer_near_boundary_sells else "")
    table.add_row(
        "score_weights",
        f"prob_up={p.score_weights_json['prob_up']}, "
        f"expected_return={p.score_weights_json['expected_return']}",
    )
    table.add_row("created_at", str(p.created_at))
    table.add_row("updated_at", str(p.updated_at))
    console.print(table)


@profile_app.command("activate")
def profile_activate_cmd(
    name: str = typer.Argument(..., help="Profile name to activate"),
) -> None:
    """Atomically flip is_active=TRUE on `name`. At most one row is active."""
    _require_personal_use()
    asyncio.run(_run_profile_activate(name))


async def _run_profile_activate(name: str) -> None:
    from asxos.domain.portfolio.profile import activate as activate_fn

    await init_pool()
    try:
        async with acquire() as conn:
            try:
                pid = await activate_fn(conn, name)
            except Exception as e:
                raise typer.BadParameter(str(e)) from e
    finally:
        await close_pool()
    console.print(f"[green]Activated[/green] '{name}' (id {pid}).")


@profile_app.command("list")
def profile_list_cmd() -> None:
    """List every profile with its active flag."""
    _require_personal_use()
    asyncio.run(_run_profile_list())


async def _run_profile_list() -> None:
    from asxos.domain.portfolio.profile import list_profiles

    await init_pool()
    try:
        async with acquire() as conn:
            profiles = await list_profiles(conn)
    finally:
        await close_pool()

    if not profiles:
        console.print("[yellow]No profiles yet.[/yellow] Create one with `asx profile init --capital N --activate`.")
        return

    table = Table(title=f"Profiles ({len(profiles)})")
    table.add_column("id", justify="right")
    table.add_column("name")
    table.add_column("active", justify="center")
    table.add_column("risk")
    table.add_column("capital")
    table.add_column("updated")
    for p in profiles:
        table.add_row(
            str(p.profile_id),
            p.name,
            "✓" if p.is_active else "",
            p.risk_tolerance,
            f"${p.capital_aud:,.0f}",
            str(p.updated_at),
        )
    console.print(table)
