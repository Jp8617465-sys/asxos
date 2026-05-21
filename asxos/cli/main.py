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


@app.command()
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


@app.command("import-holdings")
def import_holdings(
    csv_path: str = typer.Argument(..., help="Path to a holdings CSV (see asxos/domain/tax/import_csv.py)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse + validate without writing"),
) -> None:
    """Bulk-import lots from CSV into holding_lots. All-or-nothing per file."""
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


async def _run_import_holdings(rows: list) -> None:
    await init_pool()
    try:
        async with acquire() as conn:
            async with conn.transaction():
                for r in rows:
                    await conn.execute(
                        """
                        INSERT INTO holding_lots
                            (symbol, acquired_at, quantity, cost_base_normal,
                             cost_base_div296, account_type, broker_ref, notes)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        r.symbol,
                        r.acquired_at,
                        r.quantity,
                        r.cost_base_normal,
                        r.cost_base_div296,
                        r.account_type,
                        r.broker_ref,
                        r.notes,
                    )
    finally:
        await close_pool()


@app.command("tax-view")
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

    from asxos.domain.tax.cgt import days_to_eligibility

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


@app.command("tax-action")
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


model_app = typer.Typer(help="Model registry commands.", no_args_is_help=True)
app.add_typer(model_app, name="model")


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


journal_app = typer.Typer(help="Decisions journal.", no_args_is_help=True)
app.add_typer(journal_app, name="journal")


_VALID_ACTIONS = {"BUY", "SELL", "HOLD", "REVIEW", "NOTE"}


@journal_app.command("add")
def journal_add(
    symbol: str = typer.Argument(..., help="Symbol (e.g. BHP.AU) or '-' for portfolio-level"),
    action: str = typer.Argument(..., help=f"One of {sorted(_VALID_ACTIONS)}"),
    rationale: str = typer.Option(..., "--rationale", help="Why you took this action"),
    tax_note: str = typer.Option("", "--tax-note", help="CGT/franking notes"),
) -> None:
    """Record a portfolio decision against today's signal context."""
    action = action.upper()
    if action not in _VALID_ACTIONS:
        raise typer.BadParameter(f"action must be one of {sorted(_VALID_ACTIONS)}")
    sym = None if symbol == "-" else symbol
    asyncio.run(_run_journal_add(sym, action, rationale, tax_note))


async def _run_journal_add(symbol: str | None, action: str, rationale: str, tax_note: str) -> None:
    from datetime import date as _date

    await init_pool()
    try:
        async with acquire() as conn:
            signal_ref = None
            if symbol:
                row = await conn.fetchrow(
                    """
                    SELECT model, model_version, as_of
                    FROM signals
                    WHERE symbol = $1
                    ORDER BY as_of DESC
                    LIMIT 1
                    """,
                    symbol,
                )
                if row:
                    signal_ref = f"{row['model']}@{row['model_version']}@{row['as_of'].isoformat()}"

            inserted = await conn.fetchrow(
                """
                INSERT INTO decisions
                    (symbol, decision_date, action, rationale, signal_ref, tax_note)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, decision_date
                """,
                symbol,
                _date.today(),
                action,
                rationale,
                signal_ref,
                tax_note,
            )
    finally:
        await close_pool()

    console.print(
        f"[green]Recorded decision[/green] #{inserted['id']}: "
        f"{symbol or 'portfolio'} {action} on {inserted['decision_date']}"
        + (f" (signal {signal_ref})" if signal_ref else "")
    )


@journal_app.command("list")
def journal_list(
    days: int = typer.Option(30, "--days", help="Lookback window"),
    symbol: str | None = typer.Option(None, "--symbol", help="Filter to one symbol"),
) -> None:
    """Show the most recent decisions."""
    asyncio.run(_run_journal_list(days, symbol))


async def _run_journal_list(days: int, symbol: str | None) -> None:
    from datetime import date as _date
    from datetime import timedelta

    await init_pool()
    try:
        async with acquire() as conn:
            cutoff = _date.today() - timedelta(days=days)
            if symbol:
                rows = await conn.fetch(
                    """
                    SELECT id, symbol, decision_date, action, rationale,
                           signal_ref, tax_note, created_at
                    FROM decisions
                    WHERE decision_date >= $1 AND symbol = $2
                    ORDER BY decision_date DESC, id DESC
                    """,
                    cutoff,
                    symbol,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, symbol, decision_date, action, rationale,
                           signal_ref, tax_note, created_at
                    FROM decisions
                    WHERE decision_date >= $1
                    ORDER BY decision_date DESC, id DESC
                    """,
                    cutoff,
                )
    finally:
        await close_pool()

    if not rows:
        console.print(f"[yellow]No decisions in the last {days} days.[/yellow]")
        return

    table = Table(title=f"Decisions (last {days} days)")
    table.add_column("#")
    table.add_column("date")
    table.add_column("symbol")
    table.add_column("action")
    table.add_column("rationale")
    table.add_column("signal_ref")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["decision_date"].isoformat(),
            r["symbol"] or "portfolio",
            r["action"],
            (r["rationale"] or "")[:60],
            r["signal_ref"] or "",
        )
    console.print(table)


@journal_app.command("review")
def journal_review(
    stale_days: int = typer.Option(60, "--stale-days", help="Flag decisions older than N days"),
) -> None:
    """Flag decisions older than `--stale-days` that may warrant a follow-up."""
    asyncio.run(_run_journal_review(stale_days))


async def _run_journal_review(stale_days: int) -> None:
    from datetime import date as _date
    from datetime import timedelta

    await init_pool()
    try:
        async with acquire() as conn:
            cutoff = _date.today() - timedelta(days=stale_days)
            rows = await conn.fetch(
                """
                SELECT id, symbol, decision_date, action, rationale, signal_ref
                FROM decisions
                WHERE decision_date <= $1
                  AND action IN ('BUY', 'SELL', 'REVIEW')
                ORDER BY decision_date ASC
                """,
                cutoff,
            )
    finally:
        await close_pool()

    if not rows:
        console.print(f"[green]No actionable decisions older than {stale_days} days.[/green]")
        return

    table = Table(title=f"Decisions stale > {stale_days} days (consider follow-up)")
    table.add_column("#")
    table.add_column("date")
    table.add_column("symbol")
    table.add_column("action")
    table.add_column("rationale")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["decision_date"].isoformat(),
            r["symbol"] or "portfolio",
            r["action"],
            (r["rationale"] or "")[:80],
        )
    console.print(table)


@app.command("brief")
def brief(
    as_of: str = typer.Option(None, "--as-of", help="Brief date YYYY-MM-DD; defaults to today"),
    send: bool = typer.Option(False, "--send", help="Dispatch via Resend (default: stdout-only)"),
) -> None:
    """Render the morning brief; pass --send to dispatch via Resend."""
    from datetime import date as _date

    target = _date.fromisoformat(as_of) if as_of else _date.today()
    asyncio.run(_run_brief(target, send=send))


async def _run_brief(target: date, *, send: bool) -> None:
    from asxos.brief.compose import collect, render_html

    await init_pool()
    try:
        data = await collect(target)
        html = render_html(data)
    finally:
        await close_pool()

    typer.echo(html)

    if send:
        from asxos.brief.email import send_brief

        result = send_brief(html, as_of=target)
        console.print(
            f"[green]Sent to {result.to}[/green] · subject='{result.subject}' · id={result.message_id}"
        )


if __name__ == "__main__":  # pragma: no cover
    app()
