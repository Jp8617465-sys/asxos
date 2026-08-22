"""asx results-review — W1-1 PIT snapshot presentation.

Read-only. No persistence. Not personal-use gated (no holdings/tax).
Symbol is required (vendor-namespaced, e.g. TLS.AU / BHP.AU). HUBS and
CBA are Stage 4 negative controls and are not this command's target.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time

import typer

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.results_review.pit_db import adapt_pit_snapshot, fetch_pit_snapshot
from asxos.domain.results_review.presentation import present_adapted

results_review_app = typer.Typer(
    help="Results-review PIT snapshot (integration evidence, not Stage 4).",
    no_args_is_help=True,
    add_completion=False,
)


@results_review_app.command("show")
def results_review_show(
    symbol: str = typer.Argument(..., help="rs_security_master.symbol, e.g. BHP.AU"),
    period_end: str = typer.Option(..., "--period-end", help="Yearly period_end YYYY-MM-DD"),
    cutoff: str = typer.Option(..., "--cutoff", help="Knowledge cutoff date YYYY-MM-DD (UTC)"),
) -> None:
    """Render one PIT-backed results review (honest abstain while G2 is closed)."""
    asyncio.run(_show(symbol, date.fromisoformat(period_end), date.fromisoformat(cutoff)))


async def _show(symbol: str, period_end: date, cutoff_day: date) -> None:
    cutoff = datetime.combine(cutoff_day, time(23, 59, 59), tzinfo=UTC)
    await init_pool()
    try:
        async with acquire() as conn:
            snapshot = await fetch_pit_snapshot(
                conn, symbol=symbol, period_end=period_end, cutoff=cutoff_day
            )
        adapted = adapt_pit_snapshot(snapshot, cutoff=cutoff)
        presented = present_adapted(adapted, evaluated_at=cutoff)
    finally:
        await close_pool()
    console.print(presented.presentation_markdown)
    console.print(
        f"[dim]acquisition={presented.acquisition} data_mode={presented.data_mode} "
        f"outcome={adapted.case.review.outcome} "
        f"sha256={presented.presentation_sha256}[/dim]"
    )
