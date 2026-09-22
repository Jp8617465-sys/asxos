"""`asx mandate` — the interview arbi drives, the derivation, and the memo.

James does not run CLIs (`github_commands.py`): in an attended session arbi
asks the questions and runs `init` with the answers, then `derive`; the memo
reaches him by email in the brief, and he ratifies with one line on the
pinned decisions issue (`MANDATE approve <id> <reason>`). `approve`/`reject`
here are the off-cycle escape hatch for the same transition.
"""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import Annotated

import typer
from rich.table import Table

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool

mandate_app = typer.Typer(
    help="The mandate layer (0062): goals in, a ratified mandate out. Requires ASXOS_PERSONAL_USE=1.",
    no_args_is_help=True,
    add_completion=False,
)


def _d(x: str) -> Decimal:
    return Decimal(x)


@mandate_app.command("init")
def mandate_init(
    as_of: str = typer.Option(..., "--as-of", help="YYYY-MM-DD"),
    investable: str = typer.Option(..., "--investable", help="AUD investable assets (decimal string)"),
    income: str = typer.Option(..., "--income", help="AUD income p.a."),
    savings: str = typer.Option(..., "--savings", help="AUD savings p.a. (≤ income)"),
    target_wealth: str = typer.Option(..., "--target-wealth", help="AUD target wealth"),
    horizon_years: int = typer.Option(..., "--horizon-years"),
    drawdown_tolerance: str = typer.Option(..., "--drawdown-tolerance", help="percent, e.g. 25"),
    emergency_months: int = typer.Option(..., "--emergency-months"),
    account: str = typer.Option(..., "--account", help="individual | smsf"),
    marginal_rate: str = typer.Option(..., "--marginal-rate", help="percent, e.g. 37"),
    brokerage: str = typer.Option(..., "--brokerage", help="AUD per side"),
    need: Annotated[list[str] | None, typer.Option("--need", help="liquidity call as DUE:AMOUNT:LABEL, repeatable")] = None,
) -> None:
    """Record a goals statement (append-only). Prints the goal_version_id."""
    _require_personal_use()
    from asxos.domain.mandate.types import Goals, LiquidityNeed

    needs = []
    for raw in need or []:
        due, amount, label = raw.split(":", 2)
        needs.append(LiquidityNeed(due=date.fromisoformat(due), amount_aud=_d(amount), label=label))
    goals = Goals(
        as_of=date.fromisoformat(as_of),
        investable_assets_aud=_d(investable), income_aud_pa=_d(income), savings_aud_pa=_d(savings),
        target_wealth_aud=_d(target_wealth), horizon_years=horizon_years,
        drawdown_tolerance_pct=_d(drawdown_tolerance), liquidity_needs=tuple(needs),
        emergency_months=emergency_months, account_type=account,  # type: ignore[arg-type]
        marginal_rate_pct=_d(marginal_rate), brokerage_aud_per_side=_d(brokerage),
    )
    asyncio.run(_run_init(goals))


async def _run_init(goals: object) -> None:
    from asxos.domain.mandate.repository import save_goals
    from asxos.domain.mandate.types import Goals

    assert isinstance(goals, Goals)
    await init_pool()
    try:
        async with acquire() as conn:
            gid = await save_goals(conn, goals)
        console.print(f"[green]goals recorded[/green] goal_version_id={gid} content_hash={goals.content_hash[:12]}…")
    finally:
        await close_pool()


@mandate_app.command("derive")
def mandate_derive(
    goals_id: int = typer.Option(..., "--goals", help="goal_version_id from `asx mandate init`"),
    memo_out: str = typer.Option("", "--memo-out", help="also write the memo HTML to this path"),
) -> None:
    """Derive the mandate for a goals row, store it at pending_review, print the id."""
    _require_personal_use()
    asyncio.run(_run_derive(goals_id, memo_out))


async def _run_derive(goals_id: int, memo_out: str) -> None:
    from asxos.domain.mandate.derive import derive
    from asxos.domain.mandate.memo import render_memo
    from asxos.domain.mandate.repository import load_goals, save_mandate

    await init_pool()
    try:
        async with acquire() as conn:
            goals = await load_goals(conn, goals_id)
            mandate = derive(goals)
            memo = render_memo(goals, mandate)
            mid = await save_mandate(conn, mandate, goal_version_id=goals_id, memo_html=memo)
        if memo_out:
            with open(memo_out, "w", encoding="utf-8") as fh:
                fh.write(memo)
        o = mandate.outputs
        console.print(
            f"[green]mandate {mid}[/green] pending_review · {o.structure} · deployable A${o.deployable_capital_aud.value} · "
            f"cash floor {o.cash_floor_pct.value} % · names {o.n_single_feasible.value} · ETF core {o.etf_core_pct.value} % of deployable"
        )
        console.print(f"ratify from the pinned decisions issue: `MANDATE approve {mid} <reason>`")
    finally:
        await close_pool()


@mandate_app.command("show")
def mandate_show(mandate_id: int = typer.Argument(...)) -> None:
    """Every derived figure with its trace."""
    _require_personal_use()
    asyncio.run(_run_show(mandate_id))


async def _run_show(mandate_id: int) -> None:
    from asxos.domain.mandate.repository import load_mandate
    from asxos.domain.mandate.types import Traced

    await init_pool()
    try:
        async with acquire() as conn:
            stored = await load_mandate(conn, mandate_id)
    finally:
        await close_pool()
    o = stored.mandate.outputs
    t = Table(title=f"mandate {stored.mandate_id} · {stored.governance_status} · {stored.derivation_version} · {o.structure}")
    t.add_column("figure")
    t.add_column("value", justify="right")
    t.add_column("traced to")
    for name, value in o:
        if isinstance(value, Traced):
            t.add_row(name, str(value.value), value.traced_to)
    for a in o.sleeve_allocations:
        t.add_row(a.sleeve_id, f"{a.weight_pct} % of deployable", "sleeve allocation")
    console.print(t)


@mandate_app.command("list")
def mandate_list(limit: int = typer.Option(20, "--limit")) -> None:
    _require_personal_use()
    asyncio.run(_run_list(limit))


async def _run_list(limit: int) -> None:
    from asxos.domain.mandate.repository import list_mandates

    await init_pool()
    try:
        async with acquire() as conn:
            rows = await list_mandates(conn, limit=limit)
    finally:
        await close_pool()
    t = Table(title="mandates")
    for col in ("mandate_id", "goal_version_id", "governance_status", "derivation_version", "as_of", "created_at"):
        t.add_column(col)
    for r in rows:
        t.add_row(*(str(r[c]) for c in ("mandate_id", "goal_version_id", "governance_status", "derivation_version", "as_of", "created_at")))
    console.print(t)


@mandate_app.command("approve")
def mandate_approve(mandate_id: int = typer.Argument(...), reason: str = typer.Option(..., "--reason")) -> None:
    """pending_review → approved (the phone verb is `MANDATE approve <id> <reason>`)."""
    _require_personal_use()
    asyncio.run(_run_transition(mandate_id, reason, approve=True))


@mandate_app.command("reject")
def mandate_reject(mandate_id: int = typer.Argument(...), reason: str = typer.Option(..., "--reason")) -> None:
    _require_personal_use()
    asyncio.run(_run_transition(mandate_id, reason, approve=False))


async def _run_transition(mandate_id: int, reason: str, *, approve: bool) -> None:
    from asxos.domain.mandate.repository import approve_mandate, reject_mandate

    await init_pool()
    try:
        async with acquire() as conn:
            async with conn.transaction():
                stored = await (approve_mandate if approve else reject_mandate)(conn, mandate_id, reasoning=reason)
        console.print(f"mandate {stored.mandate_id} is now [bold]{stored.governance_status}[/bold]")
    finally:
        await close_pool()
