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


# ---------------------------------------------------------------------------
# M13 — Portfolio sub-typer (gated by ASXOS_PERSONAL_USE=1 per plan Part 0 Q1)
# ---------------------------------------------------------------------------

profile_app = typer.Typer(
    help="Investment profile (M13). Requires ASXOS_PERSONAL_USE=1.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(profile_app, name="profile")


def _require_personal_use() -> None:
    """Hard-fail if the personal-use firewall flag isn't set.
    Plan Part 0 Q1: this code path is "personal advice" under s766B; the
    flag is the architectural firewall preventing accidental public exposure."""
    import os

    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise typer.BadParameter(
            "Portfolio commands require ASXOS_PERSONAL_USE=1. "
            "This surface generates personal-advice outputs under s766B "
            "(Corporations Act 2001) and is gated to single-user use only. "
            "Set the env var in your shell or in your secrets file."
        )


@profile_app.command("init")
def profile_init(
    name: str = typer.Option("baseline", "--name", help="Profile name"),
    account: str = typer.Option("individual", "--account", help="individual | smsf"),
    risk: str = typer.Option(
        "balanced", "--risk", help="conservative|balanced|growth|aggressive"
    ),
    capital: float = typer.Option(..., "--capital", help="AUD investable"),
    cash_floor: float = typer.Option(0.05, "--cash-floor"),
    leverage: float = typer.Option(1.0, "--leverage"),
    per_name_cap: float = typer.Option(0.10, "--per-name-cap"),
    sector_cap: float = typer.Option(0.30, "--sector-cap"),
    exclude_sectors: str = typer.Option("", "--exclude-sectors", help="comma-separated GICS"),
    exclude_symbols: str = typer.Option("", "--exclude-symbols", help="comma-separated symbols"),
    min_position: float = typer.Option(1000.0, "--min-position"),
    horizon_years: int = typer.Option(10, "--horizon-years"),
    defer_boundary: bool = typer.Option(
        True, "--defer-boundary/--no-defer-boundary",
        help="Defer sells within 30d of CGT discount eligibility (spec §5.1)",
    ),
    activate: bool = typer.Option(False, "--activate", help="Mark this row is_active=TRUE"),
) -> None:
    """Create a new investment profile."""
    _require_personal_use()
    asyncio.run(_run_profile_init(
        name=name, account=account, risk=risk, capital=capital,
        cash_floor=cash_floor, leverage=leverage,
        per_name_cap=per_name_cap, sector_cap=sector_cap,
        exclude_sectors=exclude_sectors, exclude_symbols=exclude_symbols,
        min_position=min_position, horizon_years=horizon_years,
        defer_boundary=defer_boundary, do_activate=activate,
    ))


async def _run_profile_init(
    *,
    name: str, account: str, risk: str, capital: float,
    cash_floor: float, leverage: float,
    per_name_cap: float, sector_cap: float,
    exclude_sectors: str, exclude_symbols: str,
    min_position: float, horizon_years: int,
    defer_boundary: bool, do_activate: bool,
) -> None:
    from decimal import Decimal

    from asxos.domain.portfolio.profile import activate as activate_fn
    from asxos.domain.portfolio.profile import save as save_profile

    excl_sectors = tuple(s.strip() for s in exclude_sectors.split(",") if s.strip())
    excl_symbols = tuple(s.strip() for s in exclude_symbols.split(",") if s.strip())

    await init_pool()
    try:
        async with acquire() as conn:
            try:
                pid = await save_profile(
                    conn,
                    name=name,
                    account_type=account,
                    risk_tolerance=risk,  # type: ignore[arg-type]
                    capital_aud=Decimal(str(capital)),
                    cash_floor_pct=Decimal(str(cash_floor)),
                    leverage_cap=Decimal(str(leverage)),
                    per_name_cap_pct=Decimal(str(per_name_cap)),
                    sector_cap_pct=Decimal(str(sector_cap)),
                    excluded_sectors=excl_sectors,
                    excluded_symbols=excl_symbols,
                    min_position_aud=Decimal(str(min_position)),
                    horizon_years=horizon_years,
                    defer_near_boundary_sells=defer_boundary,
                )
            except ValueError as e:
                raise typer.BadParameter(str(e)) from e

            console.print(f"[green]Created profile[/green] '{name}' (id {pid}).")

            if do_activate:
                await activate_fn(conn, name)
                console.print(f"[green]Activated[/green] '{name}'.")
    finally:
        await close_pool()


@profile_app.command("show")
def profile_show(
    name: str = typer.Option(None, "--name", help="Show this profile (default: active)"),
) -> None:
    """Show a profile's fields."""
    _require_personal_use()
    asyncio.run(_run_profile_show(name))


async def _run_profile_show(name: str | None) -> None:
    from asxos.domain.portfolio.profile import load_active, load_by_name

    await init_pool()
    try:
        async with acquire() as conn:
            p = await load_by_name(conn, name) if name else await load_active(conn)
    finally:
        await close_pool()

    if p is None:
        console.print(
            f"[yellow]{'No profile named ' + repr(name) if name else 'No active profile'}.[/yellow]"
        )
        raise typer.Exit(code=1)

    table = Table(title=f"Profile '{p.name}' (id {p.profile_id})")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("active", "✓" if p.is_active else "")
    table.add_row("account_type", p.account_type)
    table.add_row("risk_tolerance", f"{p.risk_tolerance} ({p.risk_tolerance_scalar})")
    table.add_row("capital_aud", f"${p.capital_aud:,.2f}")
    table.add_row("cash_floor_pct", f"{p.cash_floor_pct}")
    table.add_row("leverage_cap", f"{p.leverage_cap}")
    table.add_row("per_name_cap_pct", f"{p.per_name_cap_pct}")
    table.add_row("sector_cap_pct", f"{p.sector_cap_pct}")
    table.add_row("excluded_sectors", ", ".join(p.excluded_sectors) or "—")
    table.add_row("excluded_symbols", ", ".join(p.excluded_symbols) or "—")
    table.add_row("min_position_aud", f"${p.min_position_aud:,.2f}")
    table.add_row("horizon_years", str(p.horizon_years))
    table.add_row("defer_near_boundary_sells", "✓" if p.defer_near_boundary_sells else "")
    table.add_row(
        "score_weights",
        f"prob_up={p.score_weights_json['prob_up']}, "
        f"expected_return={p.score_weights_json['expected_return']}",
    )
    table.add_row("created_at", str(p.created_at))
    table.add_row("updated_at", str(p.updated_at))
    console.print(table)


@profile_app.command("activate")
def profile_activate_cmd(
    name: str = typer.Argument(..., help="Profile name to activate"),
) -> None:
    """Atomically flip is_active=TRUE on `name`. At most one row is active."""
    _require_personal_use()
    asyncio.run(_run_profile_activate(name))


async def _run_profile_activate(name: str) -> None:
    from asxos.domain.portfolio.profile import activate as activate_fn

    await init_pool()
    try:
        async with acquire() as conn:
            try:
                pid = await activate_fn(conn, name)
            except Exception as e:
                raise typer.BadParameter(str(e)) from e
    finally:
        await close_pool()
    console.print(f"[green]Activated[/green] '{name}' (id {pid}).")


@profile_app.command("list")
def profile_list_cmd() -> None:
    """List every profile with its active flag."""
    _require_personal_use()
    asyncio.run(_run_profile_list())


async def _run_profile_list() -> None:
    from asxos.domain.portfolio.profile import list_profiles

    await init_pool()
    try:
        async with acquire() as conn:
            profiles = await list_profiles(conn)
    finally:
        await close_pool()

    if not profiles:
        console.print("[yellow]No profiles yet.[/yellow] Create one with `asx profile init --capital N --activate`.")
        return

    table = Table(title=f"Profiles ({len(profiles)})")
    table.add_column("id", justify="right")
    table.add_column("name")
    table.add_column("active", justify="center")
    table.add_column("risk")
    table.add_column("capital")
    table.add_column("updated")
    for p in profiles:
        table.add_row(
            str(p.profile_id),
            p.name,
            "✓" if p.is_active else "",
            p.risk_tolerance,
            f"${p.capital_aud:,.0f}",
            str(p.updated_at),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# M13.6 — build-portfolio, propose-trades, portfolio sub-typer
# ---------------------------------------------------------------------------

portfolio_app = typer.Typer(
    help="Portfolio construction (M13). Requires ASXOS_PERSONAL_USE=1.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(portfolio_app, name="portfolio")


@app.command("build-portfolio")
def build_portfolio(
    profile_name: str | None = typer.Option(None, "--profile", help="Profile name (default: active)"),
    as_of: str | None = typer.Option(None, "--as-of", help="Build date YYYY-MM-DD (default: today)"),
    signals_date: str | None = typer.Option(None, "--signals", help="Signals date YYYY-MM-DD (default: latest)"),
    no_tax_overlay: bool = typer.Option(False, "--no-tax-overlay", help="Skip loss-harvest tagging"),
    no_constraints: bool = typer.Option(False, "--no-constraints", help="Skip constraint waterfall"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print result without writing to DB"),
    persist: bool = typer.Option(True, "--persist/--no-persist", help="Write run to DB"),
) -> None:
    """Construct a portfolio from the active profile + latest signals."""
    _require_personal_use()
    # --dry-run forces --no-persist (plan H.1 CRITICAL-6).
    if dry_run:
        persist = False

    build_date = None
    if as_of:
        try:
            build_date = date.fromisoformat(as_of)
        except ValueError as e:
            raise typer.BadParameter(f"--as-of must be YYYY-MM-DD: {e}") from e

    sig_date = None
    if signals_date:
        try:
            sig_date = date.fromisoformat(signals_date)
        except ValueError as e:
            raise typer.BadParameter(f"--signals must be YYYY-MM-DD: {e}") from e

    asyncio.run(
        _run_build_portfolio(
            profile_name=profile_name,
            as_of=build_date,
            signals_date=sig_date,
            apply_constraints=not no_constraints,
            apply_tax_overlay=not no_tax_overlay,
            do_persist=persist,
        )
    )


async def _run_build_portfolio(
    *,
    profile_name: str | None,
    as_of: date | None,
    signals_date: date | None,
    apply_constraints: bool,
    apply_tax_overlay: bool,
    do_persist: bool,
) -> None:
    from dataclasses import replace

    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            try:
                result = await svc.build(
                    conn,
                    profile_name=profile_name,
                    as_of=as_of,
                    signals_date=signals_date,
                    apply_constraints=apply_constraints,
                    apply_tax_overlay=apply_tax_overlay,
                )
            except RuntimeError as e:
                console.print(f"[red]build-portfolio failed:[/red] {e}")
                raise typer.Exit(code=1) from e

            run_id: int | None = None
            if do_persist:
                run_id = await svc.persist(conn, result)
                result = replace(result, run_id=run_id)
                console.print(f"[green]Wrote run {run_id}[/green] ({len(result.targets)} targets, {len(result.trades)} trades).")
    finally:
        await close_pool()

    s = result.summary
    console.print(
        f"Profile: {result.profile.name} · as_of: {result.as_of} · signals: {result.signals_as_of} · "
        f"model: {s.get('model_version', '?')}"
    )
    console.print(
        f"Trades: {s['n_buys']} buys (+${s['total_buy_aud']:,.0f}) · "
        f"{s['n_sells']} sells (${s['total_sell_aud']:,.0f}) · "
        f"{s['n_holds']} holds · {s['n_deferrals']} deferred"
    )

    table = Table(title=f"Target allocations (run {run_id or 'dry-run'})")
    table.add_column("symbol")
    table.add_column("weight", justify="right")
    table.add_column("target_aud", justify="right")
    table.add_column("sector")
    table.add_column("signal")
    table.add_column("flags")

    for t in sorted(result.targets, key=lambda x: -x.target_weight):
        flags = ", ".join(sorted(t.constraint_log.keys())) if t.constraint_log else ""
        table.add_row(
            t.symbol,
            f"{t.target_weight:.4f}",
            f"${t.target_weight * result.profile.capital_aud:,.0f}",
            t.sector or "—",
            t.signal_label,
            flags,
        )
    console.print(table)


@app.command("propose-trades")
def propose_trades(
    run_id: int | None = typer.Option(None, "--run-id", help="Run ID (default: latest)"),
    side: str | None = typer.Option(None, "--side", help="Filter: buy | sell | hold"),
    csv_path: str | None = typer.Option(None, "--csv", help="Write trades to CSV file"),
) -> None:
    """Show proposed trades from a build-portfolio run."""
    _require_personal_use()
    if side and side not in ("buy", "sell", "hold"):
        raise typer.BadParameter("--side must be buy, sell, or hold")
    asyncio.run(_run_propose_trades(run_id=run_id, side=side, csv_path=csv_path))


async def _run_propose_trades(
    *, run_id: int | None, side: str | None, csv_path: str | None
) -> None:
    import csv as _csv
    import io

    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            loaded = await svc.load_run(conn, run_id)
    finally:
        await close_pool()

    if loaded is None:
        console.print("[yellow]No runs found.[/yellow] Run `asx build-portfolio` first.")
        raise typer.Exit(code=1)

    run_hdr, _targets, trades = loaded
    if side:
        trades = [t for t in trades if t["side"] == side]

    table = Table(title=f"Proposed trades — run {run_hdr['run_id']} ({run_hdr['as_of']})")
    table.add_column("symbol")
    table.add_column("side")
    table.add_column("delta_qty", justify="right")
    table.add_column("delta_aud", justify="right")
    table.add_column("price", justify="right")
    table.add_column("tags")

    for t in trades:
        tags_str = str(t.get("rationale_tags") or "")[:60]
        table.add_row(
            t["symbol"],
            t["side"],
            f"{t['delta_qty']:+.2f}",
            f"${t['delta_aud']:+,.0f}",
            f"${t['reference_price']:,.2f}",
            tags_str,
        )
    console.print(table)

    if csv_path:
        buf = io.StringIO()
        writer = _csv.DictWriter(
            buf,
            fieldnames=["symbol", "side", "delta_qty", "delta_aud",
                        "target_qty", "current_qty", "reference_price",
                        "rationale_tags", "lot_hints"],
        )
        writer.writeheader()
        for t in trades:
            writer.writerow({k: t.get(k, "") for k in writer.fieldnames})
        with open(csv_path, "w") as f:
            f.write(buf.getvalue())
        console.print(f"[green]Wrote {len(trades)} trades to {csv_path}[/green]")


@portfolio_app.command("show")
def portfolio_show(
    run_id: int | None = typer.Option(None, "--run-id", help="Run ID (default: latest)"),
) -> None:
    """Show the target allocation table for a build-portfolio run."""
    _require_personal_use()
    asyncio.run(_run_portfolio_show(run_id))


async def _run_portfolio_show(run_id: int | None) -> None:
    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            loaded = await svc.load_run(conn, run_id)
    finally:
        await close_pool()

    if loaded is None:
        console.print("[yellow]No runs found.[/yellow] Run `asx build-portfolio` first.")
        raise typer.Exit(code=1)

    run_hdr, targets, _ = loaded
    console.print(
        f"Run {run_hdr['run_id']} — profile: {run_hdr['profile_name']} · "
        f"as_of: {run_hdr['as_of']} · signals: {run_hdr['signals_as_of']} · "
        f"model: {run_hdr['model_version']}"
    )

    table = Table(title="Target allocations")
    table.add_column("symbol")
    table.add_column("weight", justify="right")
    table.add_column("target_aud", justify="right")
    table.add_column("sector")
    table.add_column("signal")
    table.add_column("constraint_log")

    for t in targets:
        log = str(t.get("constraint_log") or "")[:40]
        table.add_row(
            t["symbol"],
            f"{t['target_weight']:.4f}",
            f"${t['target_aud']:,.0f}",
            t.get("sector") or "—",
            t.get("signal_label") or "",
            log,
        )
    console.print(table)


@portfolio_app.command("history")
def portfolio_history(
    days: int = typer.Option(30, "--days", help="Lookback window in days"),
) -> None:
    """List recent build-portfolio runs."""
    _require_personal_use()
    asyncio.run(_run_portfolio_history(days))


async def _run_portfolio_history(days: int) -> None:
    from asxos.domain.portfolio.build import PortfolioService

    svc = PortfolioService()
    await init_pool()
    try:
        async with acquire() as conn:
            runs = await svc.list_runs(conn, days=days)
    finally:
        await close_pool()

    if not runs:
        console.print(f"[yellow]No runs in the last {days} days.[/yellow]")
        return

    table = Table(title=f"Portfolio runs (last {days} days)")
    table.add_column("run_id", justify="right")
    table.add_column("as_of")
    table.add_column("profile")
    table.add_column("signals_as_of")
    table.add_column("model")
    table.add_column("created_at")

    for r in runs:
        table.add_row(
            str(r["run_id"]),
            str(r["as_of"]),
            r["profile_name"],
            str(r["signals_as_of"]),
            r["model_version"],
            str(r["created_at"])[:16],
        )
    console.print(table)


@portfolio_app.command("paper-review")
def portfolio_paper_review(
    weeks: int = typer.Option(4, "--weeks", help="Minimum weeks of history required"),
    today: str = typer.Option("", "--today", help="Override today's date YYYY-MM-DD (testing)"),
) -> None:
    """Evaluate all build-portfolio runs that are ≥ WEEKS old against current prices.

    Prints a table of hypothetical P&L for each evaluable run.  Use this
    weekly during the paper-trading window (plan Part 0 Q3 / M13.8).
    """
    _require_personal_use()
    _today = date.fromisoformat(today) if today else date.today()
    asyncio.run(_run_portfolio_paper_review(weeks=weeks, today=_today))


async def _run_portfolio_paper_review(*, weeks: int, today: date) -> None:
    from asxos.domain.portfolio.paper_trade import (
        evaluate_run_from_db,
        list_evaluable_runs,
    )

    await init_pool()
    try:
        async with acquire() as conn:
            runs = await list_evaluable_runs(conn, weeks=weeks, today=today)

            if not runs:
                console.print(
                    f"[yellow]No evaluable runs found.[/yellow] "
                    f"Runs need at least {weeks} weeks of history. "
                    f"Run `asx build-portfolio` each week and check back."
                )
                return

            table = Table(
                title=f"Paper-trade review — {weeks}+ week outcomes (vs today {today})"
            )
            table.add_column("run_id", justify="right")
            table.add_column("run date")
            table.add_column("days held", justify="right")
            table.add_column("traded $", justify="right")
            table.add_column("P&L $", justify="right")
            table.add_column("return %", justify="right")
            table.add_column("missing prices")

            for r in runs:
                outcome = await evaluate_run_from_db(conn, r["run_id"], today)
                if outcome is None:
                    continue

                pnl_style = "green" if outcome.total_hypothetical_pnl_aud >= 0 else "red"
                table.add_row(
                    str(outcome.run_id),
                    str(outcome.run_as_of),
                    str(outcome.outcome_days),
                    f"${outcome.total_traded_aud:,.0f}",
                    f"[{pnl_style}]${outcome.total_hypothetical_pnl_aud:,.0f}[/{pnl_style}]",
                    f"[{pnl_style}]{outcome.hypothetical_return_pct:+.2f}%[/{pnl_style}]",
                    ", ".join(outcome.symbols_missing_exit_price) or "—",
                )

            console.print(table)
            console.print(
                f"\n[dim]Showing {len(runs)} run(s) with ≥{weeks} weeks of price history. "
                "Run [bold]asx portfolio signoff[/bold] once satisfied.[/dim]"
            )
    finally:
        await close_pool()


@portfolio_app.command("signoff")
def portfolio_signoff(
    note: str = typer.Option("", "--note", help="Optional free-text note to record"),
    force: bool = typer.Option(False, "--force", help="Skip the 4-week gate check"),
) -> None:
    """Record paper-trade sign-off and prompt to enable section 6 in the brief.

    Requires ≥4 evaluable runs (≥4 weeks of build-portfolio history) unless
    --force is passed.  Inserts a decisions journal entry tagged
    [m13_paper_signoff] and prints the Render MCP command to flip
    ASXOS_PORTFOLIO_BRIEF_ENABLED=1 (plan Part 0 Q3 / M13.8).
    """
    _require_personal_use()
    asyncio.run(_run_portfolio_signoff(note=note, force=force))


async def _run_portfolio_signoff(*, note: str, force: bool) -> None:
    from asxos.domain.portfolio.paper_trade import has_enough_paper_weeks, record_signoff

    today = date.today()

    await init_pool()
    try:
        async with acquire() as conn:
            if not force:
                ok = await has_enough_paper_weeks(conn, min_weeks=4, today=today)
                if not ok:
                    console.print(
                        "[red]Insufficient paper-trade history.[/red] "
                        "Need ≥4 evaluable runs (each ≥4 weeks old). "
                        "Pass [bold]--force[/bold] to override."
                    )
                    raise typer.Exit(code=1)

            decisions_id = await record_signoff(conn, note=note, as_of=today)
    finally:
        await close_pool()

    console.print(f"[green]✓[/green] Sign-off recorded (decisions.id={decisions_id}).")
    console.print()
    console.print("[bold]Next step — flip the brief flag via Render MCP:[/bold]")
    console.print(
        "  mcp__render__update_environment_variables(\n"
        "      serviceId='crn-d883biq8qa3s73eud08g',  # asxos-compose-brief\n"
        "      envVars=[{'key': 'ASXOS_PORTFOLIO_BRIEF_ENABLED', 'value': '1'}]\n"
        "  )"
    )
    console.print()
    console.print(
        "[dim]The next Monday brief will include section 6 "
        "(Portfolio adjustments).[/dim]"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
