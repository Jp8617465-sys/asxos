from __future__ import annotations

import asyncio
from datetime import date

import typer
from rich.table import Table

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.models.model_a import predict_with_shap, top_shap_factors
from asxos.domain.signals.loader import load_features_for_date


def predict(
    target_date: str = typer.Argument(..., help="Prediction date, YYYY-MM-DD"),
    top: int = typer.Option(10, "--top", help="Number of ranked rows to show"),
    shap_n: int = typer.Option(3, "--shap-n", help="Top SHAP factors per row"),
) -> None:
    """Run Model A for one date; print the top-N table with SHAP factors."""
    try:
        as_of = date.fromisoformat(target_date)
    except ValueError as e:
        raise typer.BadParameter(f"target_date must be YYYY-MM-DD: {e}") from e

    asyncio.run(_run_predict(as_of, top=top, shap_n=shap_n))


async def _run_predict(target_date: date, *, top: int, shap_n: int) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            features = await load_features_for_date(conn, target_date)

        if features.empty:
            console.print(
                f"[yellow]No features computable for {target_date.isoformat()}.[/yellow] "
                "Check that prices and fundamentals are ingested for the lookback window."
            )
            raise typer.Exit(code=1)

        # predict_with_shap goes through the model cache, which queries
        # model_versions — keep the pool open until predict returns.
        preds, shap_df = await predict_with_shap(features)
    finally:
        await close_pool()
    head = preds.head(top)

    table = Table(
        title=f"Model A — {target_date.isoformat()}  ({len(preds)} symbols ranked)"
    )
    table.add_column("rank", justify="right")
    table.add_column("symbol")
    table.add_column("prob_up", justify="right")
    table.add_column("exp_ret", justify="right")
    table.add_column(f"top {shap_n} SHAP")

    for symbol, row in head.iterrows():
        factors = top_shap_factors(shap_df.loc[symbol], n=shap_n)
        factor_str = ", ".join(f"{name}{val:+.3f}" for name, val in factors)
        table.add_row(
            str(int(row["rank"])),
            str(symbol),
            f"{row['prob_up']:.3f}",
            f"{row['expected_return']:+.4f}",
            factor_str,
        )

    console.print(table)
