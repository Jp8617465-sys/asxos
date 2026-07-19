"""
Weekly opportunity cost computation — M-Opportunity-Cost-v1.

Runs at 20:05 UTC Saturday (after build_portfolio at 20:00 Saturday).

For each active thesis:
  1. Build candidate set: watching theses + cash pseudo-candidate
  2. Load the holding snapshot for the thesis (most recent lot prices)
  3. Compute CGT friction and rank candidates by net expected return
  4. Delete stale scenarios for this (thesis_id, as_of), then insert fresh ones

Hard-fail: DB connection failure.
Soft-degrade: single-thesis failures logged; job continues to next thesis.

CGT marginal rate: flat 0.45 approximation per domain module caveat.
spec §5.1 calendar arithmetic used via HoldingSnapshot.days_to_cgt_discount.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date
from decimal import Decimal

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.brief.opportunity_cost import rank_by_opportunity_cost
from asxos.domain.portfolio.types import AllocationCandidate, HoldingSnapshot
from asxos.domain.tax.cgt import days_to_eligibility
from asxos.domain.tax.types import AccountType
from asxos.jobs._helpers import require_personal_use_job
from asxos.jobs.utils.job_monitor import JobMonitor

_JOB = "compute_opportunity_cost"
_CASH_RATE = Decimal("0.045")       # approximate RBA cash rate for cash candidate
_CASH_EXPECTED_RETURN = Decimal("0.045")


async def _build_candidates(conn, as_of: date) -> list[AllocationCandidate]:
    """Build redeployment candidates from watching theses + a cash pseudo-candidate."""
    rows = await conn.fetch(
        """
        SELECT t.symbol, t.target_price, t.entry_band_lower, t.entry_band_upper,
               s.expected_return, s.prob_up
        FROM theses t
        LEFT JOIN LATERAL (
            SELECT expected_return, prob_up
            FROM signals
            WHERE symbol = t.symbol
              AND as_of <= $1
            ORDER BY as_of DESC
            LIMIT 1
        ) s ON TRUE
        WHERE t.status = 'watching'
        """,
        as_of,
    )

    candidates: list[AllocationCandidate] = []
    for row in rows:
        expected_return = row["expected_return"]
        if expected_return is None:
            # Fall back to target/entry midpoint if no signal
            if row["target_price"] and row["entry_band_lower"]:
                entry_mid = (Decimal(str(row["entry_band_lower"])) + Decimal(str(row["entry_band_upper"] or row["entry_band_lower"]))) / 2
                expected_return = (Decimal(str(row["target_price"])) - entry_mid) / entry_mid
            else:
                continue  # skip candidates with no return estimate

        candidates.append(AllocationCandidate(
            symbol=row["symbol"],
            sector=None,
            market_cap_aud=None,
            signal_label="BUY",
            prob_up=Decimal(str(row["prob_up"])) if row["prob_up"] is not None else Decimal("0.55"),
            expected_return=Decimal(str(expected_return)),
            daily_vol=Decimal("0.02"),   # placeholder — not used for ranking
            confidence=1,
        ))

    # Cash pseudo-candidate
    candidates.append(AllocationCandidate(
        symbol="CASH",
        sector=None,
        market_cap_aud=None,
        signal_label="HOLD",
        prob_up=Decimal("1.0"),
        expected_return=_CASH_EXPECTED_RETURN,
        daily_vol=Decimal("0"),
        confidence=3,
    ))
    return candidates


async def _load_holding_snapshot(conn, thesis_id: int, symbol: str, as_of: date) -> HoldingSnapshot | None:
    """Load aggregate position as a single HoldingSnapshot (summed across lots)."""
    row = await conn.fetchrow(
        """
        SELECT
            MIN(hl.lot_id)                  AS lot_id,
            SUM(hl.quantity)                AS quantity,
            SUM(hl.cost_base_normal)        AS cost_base_normal,
            SUM(hl.cost_base_div296)        AS cost_base_div296,
            MIN(hl.acquired_at)             AS earliest_acquired,
            p.close                         AS current_price_aud
        FROM holding_lots hl
        JOIN prices p ON p.symbol = hl.symbol AND p.dt = $2
        WHERE hl.symbol = $1
          AND hl.disposed_at IS NULL
        GROUP BY p.close
        """,
        symbol, as_of,
    )
    if row is None or row["quantity"] is None:
        return None

    earliest_acquired = row["earliest_acquired"]
    dte = days_to_eligibility(earliest_acquired, as_of)

    return HoldingSnapshot(
        lot_id=row["lot_id"],
        symbol=symbol,
        acquired_at=earliest_acquired,
        quantity=Decimal(str(row["quantity"])),
        cost_base_normal=Decimal(str(row["cost_base_normal"])),
        cost_base_div296=Decimal(str(row["cost_base_div296"])),
        account_type=AccountType.individual,
        current_price_aud=Decimal(str(row["current_price_aud"])),
        days_to_cgt_discount=dte,
    )


async def _process_thesis(conn, thesis_id: int, symbol: str, as_of: date,
                           candidates: list[AllocationCandidate]) -> int:
    """Compute and persist opportunity cost scenarios for one thesis."""
    holding = await _load_holding_snapshot(conn, thesis_id, symbol, as_of)
    if holding is None:
        print(f"  {symbol}: no holding snapshot (no lots or price missing) — skipping", file=sys.stderr)
        return 0

    ranked = rank_by_opportunity_cost(candidates, holding)

    # Refresh: delete old scenarios for this (thesis_id, as_of) before inserting
    await conn.execute(
        "DELETE FROM opportunity_cost_scenarios WHERE thesis_id = $1 AND as_of = $2",
        thesis_id, as_of,
    )

    inserted = 0
    for item in ranked:
        await conn.execute(
            """
            INSERT INTO opportunity_cost_scenarios
                (thesis_id, as_of, alternative_symbol, alternative_source,
                 gross_expected_return, estimated_cgt_friction, net_expected_return)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            thesis_id, as_of,
            item.candidate.symbol,
            "cash" if item.candidate.symbol == "CASH" else "watchlist",
            item.gross_expected_return,
            item.estimated_cgt_friction,
            item.net_expected_return,
        )
        inserted += 1

    return inserted


async def main() -> None:
    # Personal-use firewall (Part 0 Q1 / CLAUDE.md #10). In-code backstop so a
    # missing flag fails loud rather than relying on render.yaml alone.
    require_personal_use_job()
    as_of = date.today()
    total_scenarios = 0

    await init_pool()
    try:
        async with JobMonitor(_JOB, as_of) as monitor:
            async with acquire() as conn:
                active_theses = await conn.fetch(
                    "SELECT thesis_id, symbol FROM theses WHERE status = 'active' ORDER BY symbol"
                )

                if not active_theses:
                    print("No active theses — nothing to compute.", file=sys.stderr)
                    monitor.rows_written = 0
                    return

                candidates = await _build_candidates(conn, as_of)
                print(f"Built {len(candidates)} candidates ({len(candidates)-1} watchlist + 1 cash)")

                for row in active_theses:
                    thesis_id = row["thesis_id"]
                    symbol = row["symbol"]
                    try:
                        n = await _process_thesis(conn, thesis_id, symbol, as_of, candidates)
                        total_scenarios += n
                        print(f"  {symbol}: {n} scenarios inserted")
                    except Exception as exc:
                        # Soft-degrade: one thesis failure does not abort the job
                        print(f"  {symbol}: ERROR — {exc}", file=sys.stderr)

            monitor.rows_written = total_scenarios
            print(f"compute_opportunity_cost complete: {total_scenarios} scenarios for {len(active_theses)} theses")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
