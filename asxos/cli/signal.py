from __future__ import annotations

import asyncio

import typer

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool


def signal(
    symbol: str = typer.Argument(..., help="ASX symbol, e.g. BHP.AU"),
    shap_n: int = typer.Option(3, "--shap-n", help="Top SHAP factors to show"),
) -> None:
    """Print the latest signal for `symbol` with top SHAP drivers."""
    asyncio.run(_run_signal(symbol, shap_n=shap_n))


async def _run_signal(symbol: str, *, shap_n: int) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT model, model_version, as_of, prob_up, expected_return,
                       signal_label, confidence, regime, shap_factors
                FROM signals
                WHERE symbol = $1
                ORDER BY as_of DESC
                LIMIT 1
                """,
                symbol,
            )
    finally:
        await close_pool()

    if row is None:
        console.print(
            f"[yellow]No signal found for {symbol}.[/yellow] "
            "Run `python jobs/generate_signals.py` first."
        )
        raise typer.Exit(code=1)

    shap = row["shap_factors"] or {}
    if isinstance(shap, str):
        import json
        shap = json.loads(shap)
    ordered = sorted(
        ((k, v) for k, v in shap.items() if k != "bias" and v is not None),
        key=lambda kv: abs(float(kv[1])),
        reverse=True,
    )[:shap_n]
    factor_str = ", ".join(f"{k}{float(v):+.3f}" for k, v in ordered)

    console.print(
        f"[bold]{symbol}[/bold]: {row['signal_label']} "
        f"(prob_up {row['prob_up']:.3f}, exp_ret {row['expected_return']:+.4f}, "
        f"confidence {row['confidence']}, regime {row['regime']}) — as_of {row['as_of']}"
    )
    if factor_str:
        console.print(f"  drivers: {factor_str}")
