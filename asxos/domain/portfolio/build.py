"""
PortfolioService — orchestrator for ``asx build-portfolio`` (M13.6).

DB I/O is isolated here; domain functions in rebalance.py, allocator.py,
constraints.py, and tax_overlay.py remain pure.

Plan compliance notes:
  H.1 CRITICAL-3 — signals recency asserted: signals_as_of must be within
                    2 days of the build date.
  H.1 CRITICAL-4 / governance Section 4.4 Step B — model_version fetched
                    from model_versions WHERE is_active=TRUE AND
                    approved_for_allocation=TRUE, hard-failing on 0 or >1
                    eligible rows, and written to rebalance_runs.
  H.1 CRITICAL-5 — hard-fail if no active profile.
  H.2 QUICK-WIN-5 — asyncpg executemany for batch INSERT.
  H.2 QUICK-WIN-7 — RETURNING run_id instead of currval().
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from asxos.domain.models.production_gate import resolve_production_model
from asxos.domain.portfolio import allocator as _allocator
from asxos.domain.portfolio import constraints as _constraints
from asxos.domain.portfolio import rebalance as _rebalance
from asxos.domain.portfolio import tax_overlay as _tax
from asxos.domain.portfolio.profile import load_active, load_by_name
from asxos.domain.portfolio.types import (
    AllocationCandidate,
    HoldingSnapshot,
    RebalanceResult,
)
from asxos.domain.portfolio.volatility import load_vols_for_symbols
from asxos.domain.prices.fx import is_foreign_symbol
from asxos.domain.tax.cgt import days_to_eligibility


def forced_sell_inactive_symbols(universe_rows: list[Any]) -> frozenset[str]:
    """Symbols eligible for the universe_inactive forced-sell.

    Feeds ``compute_deltas(universe_inactive_symbols=...)`` in rebalance.py,
    where a held symbol in this set is force-sold (drift threshold ignored).

    An AU equity that has gone is_active=FALSE is a real delisting → still
    force-sold. Held US holdings (.US/.NYSE/.NASDAQ/.AMEX) are is_active=FALSE by
    design — they are not ASX-equity-universe members (the AXJO.INDX precedent),
    NOT delisted — so they are excluded here and never auto-liquidated. `.INDX`
    benchmark rows are likewise never held, so they don't reach the forced-sell.
    """
    return frozenset(
        r["symbol"]
        for r in universe_rows
        if not r["is_active"] and not is_foreign_symbol(r["symbol"])
    )


def rebalance_holding_snapshots(
    holdings_rows: list[Any],
    prices: dict[str, Decimal],
    account_type: Any,
    build_date: date,
) -> list[HoldingSnapshot]:
    """current_holdings rows + latest prices → HoldingSnapshot[] for the rebalance.

    Two exclusions:
    - **US/foreign holdings** (.US/.NYSE/.NASDAQ/.AMEX) are NOT part of the ASX-AUD
      rebalance strategy — no ASX signal/target, their close is USD (not the AUD this
      snapshot assumes), and they must not be auto-liquidated as an "exited universe"
      sell. They are tracked elsewhere (daily snapshot valuation, check_us_positions
      stop monitor) and deliberately never reach `compute_deltas`. This is the primary
      guard that a held US holding is not force-sold (it never enters the rebalance).
    - **No price data** — a symbol with no close is omitted (can't value it).
    """
    out: list[HoldingSnapshot] = []
    for r in holdings_rows:
        sym = r["symbol"]
        if is_foreign_symbol(sym):
            continue
        price = prices.get(sym)
        if price is None:
            continue
        out.append(
            HoldingSnapshot(
                lot_id=r["lot_id"],
                symbol=sym,
                acquired_at=r["acquired_at"],
                quantity=Decimal(str(r["quantity"])),
                cost_base_normal=Decimal(str(r["cost_base_normal"])),
                cost_base_div296=Decimal(str(r["cost_base_div296"])),
                account_type=account_type,  # plan H.1 CRITICAL-1 resolution
                current_price_aud=price,
                days_to_cgt_discount=days_to_eligibility(r["acquired_at"], build_date),
            )
        )
    return out


class PortfolioService:
    """Orchestrate the full portfolio construction pipeline.

    All public methods are async and expect an open asyncpg connection.
    The CLI initialises this once per invocation and passes the connection
    from the pool; the service never manages the pool itself.
    """

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    async def build(
        self,
        conn: Any,
        *,
        profile_name: str | None = None,
        as_of: date | None = None,
        signals_date: date | None = None,
        apply_constraints: bool = True,
        apply_tax_overlay: bool = True,
    ) -> RebalanceResult:
        """Run the full portfolio construction pipeline.

        Steps (plan Part B M13.6):
        1. Load profile — hard-fail if none active
        2. Resolve the production model — hard-fail if 0 or >1 rows are
           both is_active AND approved_for_allocation (governance Section
           4.4 Step B). Runs before signals because that query filters on
           the resolved model name.
        3. Load latest signals for that model — hard-fail if empty or stale
        4. Load universe rows
        5. Load 60-day vol for candidate symbols
        6. Build AllocationCandidate[]
        7. allocator.allocate() → AllocationTarget[]
        8. (optional) constraints.apply_constraints() + trim_min_position()
        9. Load current_holdings + latest prices → HoldingSnapshot[]
        10. rebalance.compute_deltas() [§5.1 check inside]
        11. (optional) tax_overlay.tag_loss_harvest()
        12. assemble_result()

        Hard-fails (RuntimeError) on:
        - No active profile (plan H.1 CRITICAL-5)
        - No model_version is both active and approved_for_allocation, or
          more than one is (plan H.1 CRITICAL-4 / governance Section 4.4
          Step B) — checked before signals are fetched
        - No signals / stale signals (>2 days old, plan H.1 CRITICAL-3)
        - Empty buy universe after filtering
        - Non-convergent constraint waterfall
        - Missing prices for any held or target symbol
        """
        # Step 1: profile.
        profile = (
            await load_by_name(conn, profile_name)
            if profile_name
            else await load_active(conn)
        )
        if profile is None:
            raise RuntimeError(
                "no active profile; run `asx profile init --activate` first "
                "(plan H.1 CRITICAL-5)"
            )

        build_date = as_of or date.today()

        # Governance Section 4.4 Step B / plan H.1 CRITICAL-4: resolve the
        # single active+approved_for_allocation model before the signals
        # fetch, since that query needs the gated model name to filter on.
        # Gate condition + error messages live in production_gate.py so
        # build.py and compose.py (the other model_versions consumer) can't
        # drift apart on the invariant.
        model_rows = await conn.fetch(
            "SELECT model, version FROM model_versions "
            "WHERE is_active = TRUE AND approved_for_allocation = TRUE"
        )
        production_model = resolve_production_model(model_rows)
        model_version: str = model_rows[0]["version"]

        # Step 2: signals.
        if signals_date:
            signals_rows = await conn.fetch(
                """
                SELECT symbol, as_of, signal_label, prob_up,
                       expected_return, confidence, model_version
                FROM signals
                WHERE model = $1 AND as_of = $2
                ORDER BY symbol
                """,
                production_model,
                signals_date,
            )
        else:
            signals_rows = await conn.fetch(
                """
                SELECT symbol, as_of, signal_label, prob_up,
                       expected_return, confidence, model_version
                FROM signals
                WHERE model = $1
                  AND as_of = (SELECT MAX(as_of) FROM signals WHERE model = $1)
                ORDER BY symbol
                """,
                production_model,
            )
        if not signals_rows:
            raise RuntimeError(
                f"no signals for {'date ' + signals_date.isoformat() if signals_date else 'latest date'}; "
                "run the signal-generation job first"
            )

        signals_as_of: date = signals_rows[0]["as_of"]

        # Plan H.1 CRITICAL-3: reject stale signals.
        if (build_date - signals_as_of).days > 2:
            raise RuntimeError(
                f"signals are stale: signals_as_of={signals_as_of} is more than "
                f"2 days before build date {build_date}. "
                "Run the signal-generation job to refresh."
            )

        # Step 3: universe.
        universe_rows = await conn.fetch(
            "SELECT symbol, sector, market_cap, is_active FROM universe ORDER BY symbol"
        )
        universe_by_symbol = {r["symbol"]: r for r in universe_rows}
        inactive_symbols = forced_sell_inactive_symbols(universe_rows)

        # Step 4+5: vol + candidates (plan H.2 QUICK-WIN-6: vol for buys only).
        signal_symbols = [r["symbol"] for r in signals_rows]
        vols = await load_vols_for_symbols(conn, signal_symbols, build_date)

        candidates: list[AllocationCandidate] = []
        for r in signals_rows:
            sym = r["symbol"]
            if sym not in vols:
                continue  # insufficient price history — silently omit
            u = universe_by_symbol.get(sym)
            if u is None:
                continue  # not in universe
            candidates.append(
                AllocationCandidate(
                    symbol=sym,
                    sector=u["sector"],
                    market_cap_aud=(
                        Decimal(str(u["market_cap"]))
                        if u["market_cap"] is not None
                        else None
                    ),
                    signal_label=r["signal_label"],
                    prob_up=Decimal(str(r["prob_up"])),
                    expected_return=Decimal(str(r["expected_return"])),
                    daily_vol=vols[sym],
                    confidence=r["confidence"],
                )
            )

        # Step 6: allocate.
        targets = _allocator.allocate(candidates=candidates, profile=profile)

        # Step 7: constraints.
        if apply_constraints:
            targets = _constraints.apply_constraints(targets, profile)
            targets = _constraints.trim_min_position(
                targets, profile.capital_aud, profile.min_position_aud
            )

        # Step 8: current holdings + prices.
        holdings_rows = await conn.fetch(
            """
            SELECT id AS lot_id, symbol, acquired_at, quantity,
                   cost_base_normal, cost_base_div296
            FROM current_holdings
            ORDER BY symbol, acquired_at
            """
        )

        all_price_symbols = {t.symbol for t in targets} | {r["symbol"] for r in holdings_rows}
        price_rows = await conn.fetch(
            """
            SELECT DISTINCT ON (symbol) symbol, close
            FROM prices
            WHERE symbol = ANY($1::text[])
            ORDER BY symbol, dt DESC
            """,
            list(all_price_symbols),
        )
        prices: dict[str, Decimal] = {
            r["symbol"]: Decimal(str(r["close"])) for r in price_rows
        }

        holdings = rebalance_holding_snapshots(
            holdings_rows, prices, profile.account_type, build_date
        )

        current_qty = _rebalance.current_qty_by_symbol(holdings)

        # Step 9: deltas (§5.1 inside compute_deltas).
        trades = _rebalance.compute_deltas(
            targets=targets,
            current_qty=current_qty,
            prices=prices,
            capital_aud=profile.capital_aud,
            leverage_cap=profile.leverage_cap,
            holdings=holdings,
            defer_near_boundary_sells=profile.defer_near_boundary_sells,
            universe_inactive_symbols=inactive_symbols,
        )

        # Step 10: loss-harvest tagging.
        if apply_tax_overlay:
            losses = _tax.unrealised_losses(holdings)
            trades = _tax.tag_loss_harvest(trades, losses)

        # Step 11: assemble.
        result = _rebalance.assemble_result(
            profile=profile,
            targets=targets,
            trades=trades,
            as_of=build_date,
            signals_as_of=signals_as_of,
        )
        # Inject model_version into summary for persist() and Rich display.
        return replace(result, summary={**result.summary, "model_version": model_version})

    # ------------------------------------------------------------------
    # persist
    # ------------------------------------------------------------------

    async def persist(self, conn: Any, result: RebalanceResult) -> int:
        """Write a RebalanceResult to the DB atomically. Returns run_id.

        Idempotent on same-day re-run: DELETE WHERE (profile_id, as_of)
        cascades to target_allocations and proposed_trades, then re-inserts.

        Uses RETURNING run_id (plan H.2 QUICK-WIN-7) and executemany
        for batch inserts (plan H.2 QUICK-WIN-5).
        """
        profile = result.profile
        model_version = str(result.summary.get("model_version", "unknown"))

        async with conn.transaction():
            await conn.execute(
                "DELETE FROM rebalance_runs WHERE profile_id = $1 AND as_of = $2",
                profile.profile_id,
                result.as_of,
            )
            run_row = await conn.fetchrow(
                """
                INSERT INTO rebalance_runs
                    (profile_id, as_of, signals_as_of, model_version, capital_aud)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING run_id
                """,
                profile.profile_id,
                result.as_of,
                result.signals_as_of,
                model_version,
                profile.capital_aud,
            )
            run_id: int = run_row["run_id"]

            await conn.executemany(
                """
                INSERT INTO target_allocations
                    (run_id, symbol, target_weight, target_aud, sector,
                     signal_label, prob_up, expected_return, inv_vol_score,
                     constraint_log)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                [
                    (
                        run_id,
                        t.symbol,
                        t.target_weight,
                        t.target_weight * profile.capital_aud,
                        t.sector,
                        t.signal_label,
                        t.prob_up,
                        t.expected_return,
                        t.inv_vol_score,
                        json.dumps(t.constraint_log),
                    )
                    for t in result.targets
                ],
            )

            await conn.executemany(
                """
                INSERT INTO proposed_trades
                    (run_id, symbol, side, delta_qty, delta_aud,
                     target_qty, current_qty, reference_price,
                     rationale_tags, lot_hints)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                [
                    (
                        run_id,
                        t.symbol,
                        t.side,
                        t.delta_qty,
                        t.delta_aud,
                        t.target_qty,
                        t.current_qty,
                        t.reference_price,
                        json.dumps(t.rationale_tags),
                        json.dumps(t.lot_hints),
                    )
                    for t in result.trades
                ],
            )

        return run_id

    # ------------------------------------------------------------------
    # load_run / list_runs
    # ------------------------------------------------------------------

    async def load_run(
        self,
        conn: Any,
        run_id: int | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]] | None:
        """Load a run's header, targets, and trades.

        If ``run_id`` is None, returns the most recent run. Returns None
        if no runs exist.
        """
        if run_id is not None:
            run = await conn.fetchrow(
                """
                SELECT r.run_id, r.as_of, r.signals_as_of, r.model_version,
                       r.capital_aud, r.created_at,
                       p.name AS profile_name, p.profile_id
                FROM rebalance_runs r
                JOIN profiles p USING (profile_id)
                WHERE r.run_id = $1
                """,
                run_id,
            )
        else:
            run = await conn.fetchrow(
                """
                SELECT r.run_id, r.as_of, r.signals_as_of, r.model_version,
                       r.capital_aud, r.created_at,
                       p.name AS profile_name, p.profile_id
                FROM rebalance_runs r
                JOIN profiles p USING (profile_id)
                ORDER BY r.as_of DESC, r.created_at DESC
                LIMIT 1
                """
            )
        if run is None:
            return None

        rid = run["run_id"]
        targets = await conn.fetch(
            "SELECT * FROM target_allocations WHERE run_id = $1 ORDER BY symbol", rid
        )
        trades = await conn.fetch(
            "SELECT * FROM proposed_trades WHERE run_id = $1 ORDER BY symbol", rid
        )
        return dict(run), [dict(r) for r in targets], [dict(r) for r in trades]

    async def list_runs(self, conn: Any, days: int = 30) -> list[dict[str, Any]]:
        """List rebalance runs from the last ``days`` days, newest first."""
        cutoff = date.today() - timedelta(days=days)
        rows = await conn.fetch(
            """
            SELECT r.run_id, r.as_of, r.signals_as_of, r.model_version,
                   r.capital_aud, r.created_at, p.name AS profile_name
            FROM rebalance_runs r
            JOIN profiles p USING (profile_id)
            WHERE r.as_of >= $1
            ORDER BY r.as_of DESC, r.created_at DESC
            """,
            cutoff,
        )
        return [dict(r) for r in rows]
