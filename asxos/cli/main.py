"""
asx — Typer CLI entrypoint.

Commands added per BUILD_GUIDE milestone:
  M6  — `asx predict <date>`
  M7+ — `asx signal`, `asx tax-view`, `asx journal`, ...
"""
from __future__ import annotations

import asyncio
from datetime import date

import typer
from rich.console import Console
from rich.table import Table

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.models.model_a import predict_with_shap, top_shap_factors
from asxos.domain.signals.loader import load_features_for_date

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


@app.callback()
def _main() -> None:
    """asx — asxos CLI."""


@app.command()
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
    finally:
        await close_pool()

    if features.empty:
        console.print(
            f"[yellow]No features computable for {target_date.isoformat()}.[/yellow] "
            "Check that prices and fundamentals are ingested for the lookback window."
        )
        raise typer.Exit(code=1)

    preds, shap_df = await predict_with_shap(features)
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


if __name__ == "__main__":  # pragma: no cover
    app()
