"""asx replay — point-in-time replay + lineage (Stage 1 exit clauses 1 and 2).

Read-only. No persistence. Not personal-use gated: it reads no holdings, no
theses, no tax, and never `signals`. Output is evidence, not a recommendation.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date

import typer

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.replay import replay_snapshot, resolve_lineage

replay_app = typer.Typer(
    help="Replay one symbol at one cutoff using only facts knowable by then.",
    no_args_is_help=True,
    add_completion=False,
)


@replay_app.command("show")
def replay_show(
    symbol: str = typer.Argument(..., help="rs_security_master.symbol, e.g. TLS.AU"),
    cutoff: str = typer.Option(..., "--cutoff", help="Knowledge cutoff YYYY-MM-DD (end of day, UTC)"),
    allow_estimated: bool = typer.Option(
        False, "--allow-estimated",
        help="Admit knowledge_tier = estimated / NULL rows (recorded in the snapshot; hash differs).",
    ),
    twice: bool = typer.Option(
        True, "--twice/--once",
        help="Run the replay twice and refuse to report if the hashes differ.",
    ),
) -> None:
    """Print the replay snapshot, its hash, and the lineage report."""
    asyncio.run(_show(symbol, date.fromisoformat(cutoff), not allow_estimated, twice))


async def _show(symbol: str, cutoff: date, require_filed: bool, twice: bool) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            first = await replay_snapshot(conn, symbol=symbol, cutoff=cutoff, require_filed=require_filed)
            if twice:
                second = await replay_snapshot(conn, symbol=symbol, cutoff=cutoff, require_filed=require_filed)
                if second.hash != first.hash:
                    raise typer.Exit(code=2)
            lineage = await resolve_lineage(conn, first)
    finally:
        await close_pool()

    console.print(json.dumps(first.payload, indent=2, sort_keys=True))
    console.print(json.dumps(lineage.as_payload(), indent=2, sort_keys=True))
    console.print(
        f"[dim]replay sha256={first.hash} reproducible={'yes' if twice else 'not checked'} "
        f"fundamentals={first.fundamentals_status} price={first.price_status} "
        f"lineage_complete={lineage.complete}[/dim]"
    )
