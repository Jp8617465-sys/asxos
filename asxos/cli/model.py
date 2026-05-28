from __future__ import annotations

import asyncio

import typer
from rich.table import Table

from asxos.cli._common import console
from asxos.db import acquire, close_pool, init_pool

model_app = typer.Typer(help="Model registry commands.", no_args_is_help=True)


@model_app.command("activate")
def model_activate(
    version: str = typer.Argument(..., help="Version to activate, e.g. v1_6"),
    model: str = typer.Option("model_a", "--model", help="Model name"),
) -> None:
    """Flip the active row in model_versions atomically. Restart picks it up."""
    asyncio.run(_run_model_activate(model, version))


async def _run_model_activate(model: str, version: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            target = await conn.fetchrow(
                "SELECT version FROM model_versions WHERE model = $1 AND version = $2",
                model,
                version,
            )
            if target is None:
                console.print(
                    f"[red]no row found for {model} {version} — has retrain_model_a run?[/red]"
                )
                raise typer.Exit(code=1)

            previous = await conn.fetchrow(
                "SELECT version FROM model_versions WHERE model = $1 AND is_active = TRUE",
                model,
            )
            async with conn.transaction():
                await conn.execute(
                    "UPDATE model_versions SET is_active = FALSE WHERE model = $1",
                    model,
                )
                await conn.execute(
                    "UPDATE model_versions SET is_active = TRUE "
                    "WHERE model = $1 AND version = $2",
                    model,
                    version,
                )
    finally:
        await close_pool()

    prev_version = previous["version"] if previous else "(none)"
    console.print(
        f"[green]Activated {model} {version}[/green] (was {prev_version}). "
        "Restart any running API for the cache to pick it up within 60s anyway."
    )


@model_app.command("list")
def model_list(model: str = typer.Option("model_a", "--model")) -> None:
    """Show all versions of `model` with their active flag and AUC."""
    asyncio.run(_run_model_list(model))


async def _run_model_list(model: str) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            rows = await conn.fetch(
                "SELECT version, roc_auc, is_active, trained_at, notes "
                "FROM model_versions WHERE model = $1 "
                "ORDER BY trained_at DESC",
                model,
            )
    finally:
        await close_pool()

    if not rows:
        console.print(f"[yellow]no versions found for {model}[/yellow]")
        return

    table = Table(title=f"{model} versions")
    table.add_column("version")
    table.add_column("active")
    table.add_column("roc_auc", justify="right")
    table.add_column("trained_at")
    table.add_column("notes")

    for r in rows:
        table.add_row(
            r["version"],
            "*" if r["is_active"] else "",
            f"{r['roc_auc']:.4f}" if r["roc_auc"] else "",
            r["trained_at"].isoformat() if r["trained_at"] else "",
            (r["notes"] or "")[:60],
        )
    console.print(table)
