"""
PortfolioService — orchestrator for ``asx build-portfolio`` (M13.6).

DB I/O is isolated here; domain functions in rebalance.py, allocator.py,
constraints.py, and tax_overlay.py remain pure.

Plan compliance notes:
  H.1 CRITICAL-3 — candidate recency. NO LONGER ENFORCED HERE, and enforced
                    nowhere else today. The Model A signals fetch and its
                    empty / >2-day-stale hard-fails were retired by mission
                    P1-04 (manifest A1/A2) along with the feed they guarded.
                    Nothing can go stale while no candidates load at all, so
                    this is a debt rather than a live hole — the assertion is
                    owed by whatever candidate source replaces them, inside
                    candidates.py, as a raise and never a warning
                    (CLAUDE.md #10).
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

from asxos import clock
from asxos.domain.models.production_gate import resolve_production_model
from asxos.domain.portfolio import allocator as _allocator
from asxos.domain.portfolio import constraints as _constraints
from asxos.domain.portfolio import rebalance as _rebalance
from asxos.domain.portfolio import tax_overlay as _tax
from asxos.domain.portfolio.candidates import load_allocation_candidates
from asxos.domain.portfolio.profile import load_active, load_by_name
from asxos.domain.portfolio.types import HoldingSnapshot, RebalanceResult
from asxos.domain.prices.fx import is_foreign_symbol
from asxos.domain.tax.cgt import days_to_eligibility


def forced_sell_inactive_symbols(universe_rows: list[Any]) -> frozenset[str]:
    """Symbols eligible for the universe_inactive forced-sell.

    Feeds ``compute_deltas(universe_inactive_symbols=...)`` in rebalance.py,
    where a held symbol in this set is force-sold (drift threshold ignored).

    Only ``security_kind = 'au_equity'`` rows are eligible: an AU equity (incl.
    A-REITs, which stay au_equity) that has gone is_active=FALSE is a real
    delisting → still force-sold. Every fund/foreign kind (etf/lic/hybrid/index/
    us_equity) is excluded and never auto-liquidated — a held ETF or US holding is
    not an ASX-equity delisting. (Pre-0037 this keyed on ``not is_foreign_symbol``;
    security_kind now carries that meaning directly, and also excludes .AU-suffixed
    ETFs — e.g. VGS.AU — which the suffix check could not.)
    """
    return frozenset(
        r["symbol"]
        for r in universe_rows
        if r["security_kind"] == "au_equity" and not r["is_active"]
    )


def rebalance_holding_snapshots(
    holdings_rows: list[Any],
    prices: dict[str, Decimal],
    account_type: Any,
    build_date: date,
    non_equity_symbols: frozenset[str] = frozenset(),
) -> list[HoldingSnapshot]:
    """current_holdings rows + latest prices → HoldingSnapshot[] for the rebalance.

    Three exclusions:
    - **US/foreign holdings** (.US/.NYSE/.NASDAQ/.AMEX) are NOT part of the ASX-AUD
      rebalance strategy — no ASX signal/target, their close is USD (not the AUD this
      snapshot assumes), and they must not be auto-liquidated as an "exited universe"
      sell. They are tracked elsewhere (daily snapshot valuation, check_us_positions
      stop monitor) and deliberately never reach `compute_deltas`. This is the primary
      guard that a held US holding is not force-sold (it never enters the rebalance).
    - **Non-au_equity holdings** (ETF/LIC/hybrid/index by `security_kind` — e.g. a held
      VGS.AU) are excluded for the same reason: a fund carries no ASX single-name
      signal/target, so if it entered the rebalance it would miss `targets` and fall
      through to an `exited_universe` full-sell. `non_equity_symbols` is computed from
      `universe.security_kind` in `build()`. This closes the SECOND auto-liquidation path
      (the forced-sell set in `forced_sell_inactive_symbols` closes the `universe_inactive`
      path); together they guarantee a held fund is valued but never force-sold. Note this
      is what catches a **.AU-suffixed** ETF, which `is_foreign_symbol` cannot.
    - **No price data** — a symbol with no close is omitted (can't value it).
    """
    out: list[HoldingSnapshot] = []
    for r in holdings_rows:
        sym = r["symbol"]
        if is_foreign_symbol(sym) or sym in non_equity_symbols:
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

        **This pipeline cannot complete today, by design.** Step 3 always raises
        ``CandidateSourceUnavailable`` — mission P1-04 retired the Model A
        candidate feed and substituted nothing — so steps 4-10 are unreachable
        and ``asx build-portfolio`` exits 1. The list below is the contract a
        replacement candidate source slots into, not a description of a working
        run.

        Steps (plan Part B M13.6):
        1. Load profile — hard-fail if none active
        2. Resolve the production model — hard-fail if 0 or >1 rows are
           both is_active AND approved_for_allocation (governance Section
           4.4 Step B). Runs before candidates are loaded, and STAYS ahead
           of whatever candidate source replaces the retired Model A feed:
           it is rule #11's mechanical enforcement point (manifest E1).
        3. Load allocation candidates — currently raises
           CandidateSourceUnavailable (manifest A1/A2, mission P1-04)
        4. Load universe rows
        5. allocator.allocate() → AllocationTarget[]
        6. (optional) constraints.apply_constraints() + trim_min_position()
        7. Load current_holdings + latest prices → HoldingSnapshot[]
        8. rebalance.compute_deltas() [§5.1 check inside]
        9. (optional) tax_overlay.tag_loss_harvest()
        10. assemble_result()

        Hard-fails (RuntimeError) on:
        - No active profile (plan H.1 CRITICAL-5)
        - No model_version is both active and approved_for_allocation, or
          more than one is (plan H.1 CRITICAL-4 / governance Section 4.4
          Step B) — checked before candidates are loaded
        - No candidate source wired (CandidateSourceUnavailable, a
          RuntimeError subclass) — the retired Model A signals read is not
          replaced by an assumed or synthesised candidate set
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

        build_date = as_of or clock.today()

        # Step 2. Governance Section 4.4 Step B / plan H.1 CRITICAL-4: resolve the
        # single active+approved_for_allocation model. Gate condition + error
        # messages live in production_gate.py so every consumer of the
        # invariant states it identically.
        #
        # DO NOT DELETE. This is rule #11's mechanical enforcement point
        # (docs/product/model-a-reference-manifest.md, row E1) — the one place
        # where a revoked `approved_for_allocation` becomes a refusal to
        # allocate. It contains no Model A token, so a token-driven cleanup
        # cannot see it.
        #
        # It originally sat here because the signals query below needed the
        # gated model name to filter on. That query is gone (mission P1-04,
        # manifest A1) and this block is deliberately unchanged: the gate is
        # NOT scaffolding for the query it used to feed. Whatever candidate
        # source is eventually wired into candidates.py must be loaded BELOW
        # this point, so that revoking approval still stops allocation.
        # `tests/test_portfolio_build.py::test_model_gate_runs_before_the_candidate_source`
        # holds that ordering.
        model_rows = await conn.fetch(
            "SELECT model, version FROM model_versions "
            "WHERE is_active = TRUE AND approved_for_allocation = TRUE"
        )
        production_model = resolve_production_model(model_rows)
        model_version: str = model_rows[0]["version"]

        # Step 3: candidates (manifest A1/A2 — the retired Model A `signals`
        # read). The candidate source now lives behind one seam in
        # candidates.py, which raises CandidateSourceUnavailable until a
        # model-independent source is wired. The approval gate above is
        # UNCHANGED and still runs first: it is rule #11's mechanical
        # enforcement point (manifest E1) and must outlive the query it used to
        # feed. `production_model` is threaded through so the unavailability
        # message can name which approved model the retired feed belonged to.
        candidates, candidates_as_of = await load_allocation_candidates(
            conn,
            approved_model=production_model,
            build_date=build_date,
            as_of=signals_date,
        )

        # Step 4: universe.
        universe_rows = await conn.fetch(
            "SELECT symbol, sector, market_cap, is_active, security_kind FROM universe ORDER BY symbol"
        )
        universe_by_symbol = {r["symbol"]: r for r in universe_rows}
        inactive_symbols = forced_sell_inactive_symbols(universe_rows)

        # Step 5: allocate.
        targets = _allocator.allocate(candidates=candidates, profile=profile)

        # Step 6: constraints.
        if apply_constraints:
            targets = _constraints.apply_constraints(targets, profile)
            targets = _constraints.trim_min_position(
                targets, profile.capital_aud, profile.min_position_aud
            )

        # Step 7: current holdings + prices.
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

        # Held funds/foreign (non-au_equity) are excluded from the rebalance so they are
        # never proposed for an exited_universe sell — the mirror of the forced-sell guard.
        non_equity_symbols = frozenset(
            sym for sym, r in universe_by_symbol.items()
            if r["security_kind"] != "au_equity"
        )
        holdings = rebalance_holding_snapshots(
            holdings_rows, prices, profile.account_type, build_date,
            non_equity_symbols=non_equity_symbols,
        )

        current_qty = _rebalance.current_qty_by_symbol(holdings)

        # Step 8: deltas (§5.1 inside compute_deltas).
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

        # Step 9: loss-harvest tagging.
        if apply_tax_overlay:
            losses = _tax.unrealised_losses(holdings)
            trades = _tax.tag_loss_harvest(trades, losses)

        # Step 10: assemble.
        result = _rebalance.assemble_result(
            profile=profile,
            targets=targets,
            trades=trades,
            as_of=build_date,
            # `signals_as_of` is the frozen name of the RebalanceResult field and
            # of the rebalance_runs column behind it; renaming either needs a
            # migration, which is out of P1-04's scope. The VALUE it now carries
            # is the candidate evidence date from candidates.py, not a Model A
            # signal date.
            signals_as_of=candidates_as_of,
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
        cutoff = clock.today() - timedelta(days=days)
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
