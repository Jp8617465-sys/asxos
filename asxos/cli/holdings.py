from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import typer

from asxos.cli._common import _require_personal_use, console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.prices.fx import is_foreign_symbol


def import_holdings(
    csv_path: str = typer.Argument(..., help="Path to a holdings CSV (see asxos/domain/tax/import_csv.py)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse + validate without writing"),
) -> None:
    """Bulk-import lots from CSV into holding_lots. All-or-nothing per file."""
    _require_personal_use()  # portfolio-conventions Part 0 Q1 — gate before touching holding data

    from pathlib import Path

    from asxos.domain.tax.import_csv import parse_csv

    rows = parse_csv(Path(csv_path))
    console.print(f"Parsed {len(rows)} rows from {csv_path}")
    if dry_run:
        for r in rows[:5]:
            console.print(f"  {r}")
        console.print("[yellow]--dry-run: no rows written.[/yellow]")
        return

    asyncio.run(_run_import_holdings(rows))
    console.print(f"[green]Inserted {len(rows)} lots.[/green]")


def _infer_currency(symbol: str) -> str:
    """Infer currency from exchange suffix.

    Any US-exchange suffix (.US/.NYSE/.NASDAQ/.AMEX) → USD; everything else → AUD.
    """
    return "USD" if is_foreign_symbol(symbol) else "AUD"


async def _ensure_in_universe(conn: Any, symbol: str) -> None:
    """Demand-driven universe insert — idempotent.

    Runs before every holding_lots INSERT so FK never fails on non-AU
    symbols (e.g. AAPL.US from wife's ESPP).  The sync_universe job
    owns AU records; this handles US and any future exchange suffixes.
    """
    await conn.execute(
        """
        INSERT INTO universe (symbol, currency, is_active)
        VALUES ($1, $2, TRUE)
        ON CONFLICT (symbol) DO NOTHING
        """,
        symbol,
        _infer_currency(symbol),
    )


async def _resolve_fx_rate(conn: Any, acquired_at: Any) -> Decimal | None:
    """Look up AUDUSD rate on acquired_at from fx_rates table.

    Returns None if no rate is available (e.g. fx_rates not yet populated).
    Caller must decide how to handle None — import is blocked until rate exists.
    """
    row = await conn.fetchrow(
        "SELECT rate FROM fx_rates WHERE pair = 'AUDUSD' AND dt = $1",
        acquired_at,
    )
    return Decimal(str(row["rate"])) if row else None


async def _run_import_holdings(rows: list[Any]) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            async with conn.transaction():
                for r in rows:
                    await _ensure_in_universe(conn, r.symbol)

                    cost_base_normal = r.cost_base_normal
                    acquisition_fx_rate = None

                    if r.cost_base_usd is not None:
                        # US lot: resolve AUD cost base from FX rate
                        fx_rate = await _resolve_fx_rate(conn, r.acquired_at)
                        if fx_rate is None:
                            raise RuntimeError(
                                f"No AUDUSD FX rate for {r.acquired_at} — "
                                "run sync_prices.py first to populate fx_rates"
                            )
                        acquisition_fx_rate = fx_rate
                        cost_base_normal = r.cost_base_usd / fx_rate

                    await conn.execute(
                        """
                        INSERT INTO holding_lots
                            (symbol, acquired_at, quantity, cost_base_normal,
                             cost_base_div296, account_type, broker_ref, notes,
                             cost_base_usd, acquisition_fx_rate)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                        r.symbol,
                        r.acquired_at,
                        r.quantity,
                        cost_base_normal,
                        r.cost_base_div296 if r.cost_base_usd is None else cost_base_normal,
                        r.account_type,
                        r.broker_ref,
                        r.notes,
                        r.cost_base_usd,
                        acquisition_fx_rate,
                    )
    finally:
        await close_pool()
