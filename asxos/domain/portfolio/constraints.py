"""
Constraint waterfall for the M13 portfolio allocator (M13.4).

Waterfall order per the plan (Part B M13.4):
    loop ≤ max_iterations:
        1. per-name cap  — clip overweight names; freeze them
        2. sector cap    — scale unfrozen sector members down proportionally
        3. residual      — redistribute freed weight to unfrozen by inv_vol_score
        4. converged?    — break if no cap violated; else continue
    → RuntimeError with diagnostic if still violating after max_iterations

Pre-flight infeasibility check (plan M13.4 + H.1 R3):
    hard-fail if target_sum > N × per_name_cap  (over-allocation)
    hard-fail if target_sum < min_position_aud / capital_aud  (under-allocation)

All arithmetic is Decimal; no numpy (plan Part C).
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from asxos.domain.portfolio.types import AllocationTarget, Profile

# Tolerance for convergence comparisons — Decimal arithmetic is exact but
# intermediate operations accumulate small rounding at the ULP level.
_EPS = Decimal("1e-10")


# ---------------------------------------------------------------------------
# Step 1 — per-name cap
# ---------------------------------------------------------------------------


def apply_per_name_cap(
    targets: list[AllocationTarget],
    cap: Decimal,
) -> tuple[list[AllocationTarget], set[str]]:
    """Clip any target_weight above `cap` to exactly `cap`. Mark the symbol frozen.

    Returns (updated_targets, symbols_capped_this_call). The caller accumulates
    the frozen set across iterations.
    """
    result: list[AllocationTarget] = []
    newly_frozen: set[str] = set()

    for t in targets:
        if t.target_weight > cap + _EPS:
            log = dict(t.constraint_log)
            log["capped_by_per_name"] = True
            result.append(replace(t, target_weight=cap, constraint_log=log))
            newly_frozen.add(t.symbol)
        else:
            result.append(t)

    return result, newly_frozen


# ---------------------------------------------------------------------------
# Step 2 — sector cap
# ---------------------------------------------------------------------------


def apply_sector_cap(
    targets: list[AllocationTarget],
    cap: Decimal,
    frozen: set[str],
) -> list[AllocationTarget]:
    """Scale unfrozen members of any sector whose total weight exceeds `cap`.

    For a sector with frozen weight F and unfrozen weight U where F + U > cap:
      - If F >= cap: impossible to fix via unfrozen scaling; leave as-is
        (will fail the convergence check → eventually hit the hard-fail).
      - Else: scale_factor = (cap - F) / U; apply to each unfrozen member.

    Frozen members are never touched.
    """
    # Partition sector totals into frozen and unfrozen.
    sector_frozen: dict[str | None, Decimal] = {}
    sector_unfrozen: dict[str | None, Decimal] = {}
    for t in targets:
        if t.symbol in frozen:
            sector_frozen[t.sector] = sector_frozen.get(t.sector, Decimal("0")) + t.target_weight
        else:
            sector_unfrozen[t.sector] = sector_unfrozen.get(t.sector, Decimal("0")) + t.target_weight

    # Identify sectors over the cap and compute per-sector scale factors.
    scale_by_sector: dict[str | None, Decimal] = {}
    for sector in set(sector_frozen) | set(sector_unfrozen):
        f = sector_frozen.get(sector, Decimal("0"))
        u = sector_unfrozen.get(sector, Decimal("0"))
        if f + u <= cap + _EPS:
            continue  # not over cap
        available = cap - f
        if available <= Decimal("0") or u <= _EPS:
            # Frozen members alone meet or exceed sector_cap; can't fix by
            # scaling unfrozen.  Convergence check will catch this.
            continue
        scale_by_sector[sector] = available / u

    if not scale_by_sector:
        return targets

    result: list[AllocationTarget] = []
    for t in targets:
        if t.symbol in frozen or t.sector not in scale_by_sector:
            result.append(t)
        else:
            new_weight = t.target_weight * scale_by_sector[t.sector]
            log = dict(t.constraint_log)
            log["capped_by_sector"] = True
            result.append(replace(t, target_weight=new_weight, constraint_log=log))

    return result


# ---------------------------------------------------------------------------
# Step 3 — residual redistribution
# ---------------------------------------------------------------------------


def redistribute_residual(
    targets: list[AllocationTarget],
    target_sum: Decimal,
    frozen: set[str],
) -> list[AllocationTarget]:
    """Push unallocated weight back to unfrozen names proportional to inv_vol_score.

    Residual = target_sum - sum(all target_weights). If all names are frozen
    or total unfrozen inv_vol_score is zero, the residual stays as cash.
    """
    current_sum = sum(t.target_weight for t in targets)
    residual = target_sum - current_sum

    if abs(residual) <= _EPS:
        return targets

    unfrozen = [(i, t) for i, t in enumerate(targets) if t.symbol not in frozen]
    if not unfrozen:
        # All frozen; residual becomes additional cash (acceptable).
        return targets

    total_inv_vol = sum(t.inv_vol_score for _, t in unfrozen)
    result = list(targets)

    if total_inv_vol <= _EPS:
        # Equal distribution as fallback (should not occur with valid vol data).
        share = residual / Decimal(len(unfrozen))
        for idx, t in unfrozen:
            result[idx] = replace(t, target_weight=t.target_weight + share)
    else:
        for idx, t in unfrozen:
            share = residual * (t.inv_vol_score / total_inv_vol)
            result[idx] = replace(t, target_weight=t.target_weight + share)

    return result


# ---------------------------------------------------------------------------
# Convergence check (internal)
# ---------------------------------------------------------------------------


def _is_converged(
    targets: list[AllocationTarget],
    per_name_cap: Decimal,
    sector_cap: Decimal,
) -> bool:
    """Return True iff no per-name or sector cap is violated within _EPS."""
    for t in targets:
        if t.target_weight > per_name_cap + _EPS:
            return False

    sector_sums: dict[str | None, Decimal] = {}
    for t in targets:
        sector_sums[t.sector] = sector_sums.get(t.sector, Decimal("0")) + t.target_weight
    for total in sector_sums.values():
        if total > sector_cap + _EPS:
            return False

    return True


# ---------------------------------------------------------------------------
# Main waterfall entry point
# ---------------------------------------------------------------------------


def apply_constraints(
    targets: list[AllocationTarget],
    profile: Profile,
    max_iterations: int = 5,
) -> list[AllocationTarget]:
    """Pre-flight feasibility check then the per-name → sector → residual waterfall.

    Hard-fails (RuntimeError) on:
    - Over-allocation infeasibility: target_sum > N × per_name_cap
    - Under-allocation infeasibility: target_sum < min_position_aud / capital_aud
    - Non-convergence: still violating caps after max_iterations

    On non-convergence, the error message includes a per-violation diagnostic
    (plan H.1 R1) to assist debugging.
    """
    n = len(targets)
    target_sum = profile.leverage_cap - profile.cash_floor_pct
    per_name_cap = profile.per_name_cap_pct
    sector_cap = profile.sector_cap_pct

    # Pre-flight: over-allocation (plan M13.4).
    max_deployable = per_name_cap * Decimal(n)
    if target_sum > max_deployable + _EPS:
        raise RuntimeError(
            f"pre-flight infeasibility: target_sum={target_sum} > "
            f"N({n}) × per_name_cap({per_name_cap}) = {max_deployable}. "
            "Reduce cash_floor_pct, add more candidates, or raise per_name_cap_pct."
        )

    # Pre-flight: under-allocation (plan H.1 R3).
    if profile.capital_aud > Decimal("0"):
        min_weight = profile.min_position_aud / profile.capital_aud
        if target_sum < min_weight - _EPS:
            raise RuntimeError(
                f"pre-flight infeasibility: target_sum={target_sum} < "
                f"min_position_aud/capital_aud={min_weight}. "
                "Cannot place even one minimum-size position."
            )

    current = list(targets)
    all_frozen: set[str] = set()

    for iteration in range(1, max_iterations + 1):
        # Step 1: per-name cap.
        current, newly_frozen = apply_per_name_cap(current, per_name_cap)
        all_frozen |= newly_frozen

        # Step 2: sector cap (only unfrozen members scaled).
        current = apply_sector_cap(current, sector_cap, all_frozen)

        # Step 3: redistribute residual to unfrozen names by 1/sigma.
        current = redistribute_residual(current, target_sum, all_frozen)

        # Step 4: convergence check.
        if _is_converged(current, per_name_cap, sector_cap):
            return current

    # Non-convergence — build diagnostic (plan H.1 R1).
    violations: list[str] = []
    sector_sums: dict[str | None, Decimal] = {}
    for t in current:
        if t.target_weight > per_name_cap + _EPS:
            violations.append(
                f"{t.symbol}: weight={t.target_weight:.6f} > per_name_cap={per_name_cap}"
            )
        sector_sums[t.sector] = sector_sums.get(t.sector, Decimal("0")) + t.target_weight
    for sector, total in sector_sums.items():
        if total > sector_cap + _EPS:
            violations.append(
                f"sector {sector!r}: sum={total:.6f} > sector_cap={sector_cap}"
            )

    raise RuntimeError(
        f"constraint waterfall did not converge after {max_iterations} iterations. "
        f"Violations: {'; '.join(violations) or 'none detected (rounding?)'}"
    )


# ---------------------------------------------------------------------------
# Post-waterfall: drop dust positions
# ---------------------------------------------------------------------------


def trim_min_position(
    targets: list[AllocationTarget],
    capital_aud: Decimal,
    min_position_aud: Decimal,
) -> list[AllocationTarget]:
    """Drop positions whose AUD value (target_weight × capital_aud) is below
    min_position_aud. The dropped weight is NOT redistributed — it becomes
    additional cash. A 12-position portfolio beats a 13th at $300.
    """
    return [t for t in targets if t.target_weight * capital_aud >= min_position_aud]
