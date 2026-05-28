from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool


def tax_view(
    account_type: str = typer.Option("individual", "--account", help="individual or smsf"),
    marginal_rate: float = typer.Option(0.37, "--marginal", help="Individual marginal rate, e.g. 0.37"),
    fund_pension_proportion: float = typer.Option(
        0.0, "--pension-prop", help="SMSF fund_pension_proportion in [0, 1]"
    ),
    carried_forward_loss: float = typer.Option(0.0, "--cf-loss", help="Carried-forward capital loss (AUD)"),
    tsb_ref: float = typer.Option(0.0, "--tsb-ref", help="SMSF total super balance ref (max open/close)"),
) -> None:
    """Print a tax-view summary from current_holdings."""
    if account_type not in ("individual", "smsf"):
        raise typer.BadParameter("account must be 'individual' or 'smsf'")
    asyncio.run(
        _run_tax_view(
            account_type=account_type,
            marginal_rate=marginal_rate,
            fund_pension_proportion=fund_pension_proportion,
            carried_forward_loss=carried_forward_loss,
            tsb_ref=tsb_ref,
        )
    )


async def _run_tax_view(
    *,
    account_type: str,
    marginal_rate: float,
    fund_pension_proportion: float,
    carried_forward_loss: float,
    tsb_ref: float,
) -> None:
    from decimal import Decimal

    from asxos.domain.tax.cgt import days_to_eligibility
    from asxos.domain.tax.positions import tax_view_individual, tax_view_smsf
    from asxos.domain.tax.types import HoldingLot, IndividualConfig, SMSFConfig

    await init_pool()
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, symbol, acquired_at, quantity,
                       cost_base_normal, cost_base_div296, account_type
                FROM current_holdings
                WHERE account_type = $1
                ORDER BY symbol, acquired_at
                """,
                account_type,
            )
    finally:
        await close_pool()

    lots = [
        HoldingLot(
            lot_id=r["id"],
            symbol=r["symbol"],
            acquired_at=r["acquired_at"],
            quantity=Decimal(str(r["quantity"])),
            cost_base_normal=Decimal(str(r["cost_base_normal"])),
            cost_base_div296=Decimal(str(r["cost_base_div296"])),
            account_type=r["account_type"],
        )
        for r in rows
    ]

    if account_type == "individual":
        cfg = IndividualConfig(
            marginal_rate=Decimal(str(marginal_rate)),
            carried_forward_capital_loss=Decimal(str(carried_forward_loss)),
        )
        view = tax_view_individual(lots=lots, realised_gains=[], dividends=[], config=cfg)
    else:
        cfg = SMSFConfig(
            fund_pension_proportion=Decimal(str(fund_pension_proportion)),
            carried_forward_capital_loss=Decimal(str(carried_forward_loss)),
        )
        view = tax_view_smsf(
            lots=lots,
            realised_gains=[],
            dividends=[],
            config=cfg,
            tsb_ref=Decimal(str(tsb_ref)) if tsb_ref > 0 else None,
        )

    table = Table(title=f"Tax view — {account_type}  ({view.holdings_count} active lots)")
    table.add_column("lot")
    table.add_column("symbol")
    table.add_column("acquired_at")
    table.add_column("qty", justify="right")
    table.add_column("cost_base_aud", justify="right")
    table.add_column("days_to_discount", justify="right")

    for lot in lots[:50]:
        d = days_to_eligibility(lot.acquired_at)
        table.add_row(
            str(lot.lot_id),
            lot.symbol,
            lot.acquired_at.isoformat(),
            str(lot.quantity),
            str(lot.cost_base_normal),
            "eligible" if d == 0 else str(d),
        )

    console.print(table)
    if view.eligibility_alerts:
        console.print("[yellow]Crossing 12-month boundary in next 30 days:[/yellow]")
        for a in view.eligibility_alerts:
            console.print(f"  - {a}")
    if view.div296_outcome:
        d = view.div296_outcome
        console.print(
            f"Div 296: tier1={d.tier_1:.2f}, tier2={d.tier_2:.2f}, total={d.total:.2f}"
            + (" [yellow](provisional)[/yellow]" if d.is_provisional else "")
        )


def tax_action(
    days_ahead: int = typer.Option(30, "--days", help="Window for crossing-boundary alerts"),
) -> None:
    """Surface tax actions: lots crossing the 12-month CGT boundary soon."""
    asyncio.run(_run_tax_action(days_ahead))


async def _run_tax_action(days_ahead: int) -> None:
    from datetime import timedelta

    from asxos.domain.tax.cgt import days_to_eligibility

    await init_pool()
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, symbol, acquired_at, quantity, account_type
                FROM current_holdings
                ORDER BY acquired_at
                """
            )
    finally:
        await close_pool()

    soon = []
    for r in rows:
        d = days_to_eligibility(r["acquired_at"])
        if 0 < d <= days_ahead:
            soon.append((r, d))

    if not soon:
        console.print(f"[green]No lots crossing 12-month boundary in next {days_ahead} days.[/green]")
        return

    table = Table(title=f"Lots crossing 12-month CGT boundary in next {days_ahead} days")
    table.add_column("lot")
    table.add_column("symbol")
    table.add_column("account")
    table.add_column("qty", justify="right")
    table.add_column("acquired_at")
    table.add_column("eligible_at")
    table.add_column("days", justify="right")

    for r, d in soon:
        eligible_at = r["acquired_at"] + timedelta(days=366)
        table.add_row(
            str(r["id"]),
            r["symbol"],
            r["account_type"],
            str(r["quantity"]),
            r["acquired_at"].isoformat(),
            eligible_at.isoformat(),
            str(d),
        )
    console.print(table)
