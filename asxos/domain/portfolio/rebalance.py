"""
Rebalance engine for the M13 portfolio layer (M13.6).

Pure functions only. No DB I/O. All arithmetic is Decimal; no numpy.

§5.1 boundary-defer logic (plan amendment I.4) lives here — inside
``compute_deltas`` — so that allocator-reductions, full exits, and
``universe_inactive`` forced-sells all receive the same CGT-eligibility
treatment.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from asxos.domain.portfolio.tax_overlay import near_boundary_lots
from asxos.domain.portfolio.types import (
    AllocationTarget,
    HoldingSnapshot,
    Profile,
    ProposedTrade,
    RebalanceResult,
)

# §5.1: sell is deferred if a lot is within this many days of CGT eligibility.
_BOUNDARY_WINDOW_DAYS: int = 30

# Defence-in-depth concentration alarm (hard-coded; separate from per_name_cap_pct).
_CONCENTRATION_ALARM_THRESHOLD: Decimal = Decimal("0.10")


# ---------------------------------------------------------------------------
# current_qty_by_symbol
# ---------------------------------------------------------------------------


def current_qty_by_symbol(holdings: list[HoldingSnapshot]) -> dict[str, Decimal]:
    """Aggregate held lot quantities per symbol.

    Returns a dict mapping symbol → total quantity held across all lots.
    An empty list returns an empty dict.
    """
    result: dict[str, Decimal] = {}
    for h in holdings:
        result[h.symbol] = result.get(h.symbol, Decimal("0")) + h.quantity
    return result


# ---------------------------------------------------------------------------
# compute_deltas
# ---------------------------------------------------------------------------


def compute_deltas(
    targets: list[AllocationTarget],
    current_qty: dict[str, Decimal],
    prices: dict[str, Decimal],
    capital_aud: Decimal,
    leverage_cap: Decimal,
    holdings: list[HoldingSnapshot] | None = None,
    defer_near_boundary_sells: bool = True,
    universe_inactive_symbols: frozenset[str] | None = None,
    drift_threshold_pct: Decimal = Decimal("0.005"),
) -> list[ProposedTrade]:
    """Diff target weights against current holdings, emit ProposedTrade[].

    Trade classification for each symbol in targets ∪ current_holdings:

    - **New buy**: in targets, not held → side='buy'
    - **Full sell**: held, not in targets → side='sell',
      rationale_tags['reason']='exited_universe'
    - **Universe-inactive forced-sell**: held and symbol in
      ``universe_inactive_symbols`` → side='sell',
      rationale_tags['reason']='universe_inactive', drift threshold ignored
    - **Partial change**: held AND in targets:
      - |delta_aud| < drift_threshold_pct × capital_aud → side='hold'
      - delta_qty > 0 → side='buy'
      - delta_qty < 0 → side='sell'

    §5.1 boundary check (plan amendment I.4):
        For any sell trade, if any held lot has
        ``0 < days_to_cgt_discount <= 30``, the trade receives
        ``rationale_tags['near_boundary_lot_ids'] = [lot_id, ...]``.
        If ``defer_near_boundary_sells=True``, the side is forced to 'hold'
        (the tags are preserved for explainability).

    Concentration alarm (defence-in-depth):
        Any buy trade where ``target_aud > 10% of capital_aud`` receives
        ``rationale_tags['concentration_alarm'] = True``. The per_name_cap
        constraint should prevent this in practice, but higher profile caps
        can permit it.

    Hard-fails:
        - ``prices`` is missing a key for any symbol in targets or
          current_qty — raises RuntimeError
        - Any reference_price <= 0 — raises RuntimeError

    Output order is alphabetical by symbol (deterministic).
    """
    inactive = universe_inactive_symbols or frozenset()
    target_by_symbol: dict[str, AllocationTarget] = {t.symbol: t for t in targets}

    # Pre-compute near-boundary lots for §5.1 check.
    boundary_by_symbol: dict[str, list[HoldingSnapshot]] = {}
    if holdings:
        boundary_by_symbol = near_boundary_lots(holdings, _BOUNDARY_WINDOW_DAYS)

    all_symbols: set[str] = set(target_by_symbol) | set(current_qty)
    drift_aud: Decimal = drift_threshold_pct * capital_aud

    result: list[ProposedTrade] = []

    for symbol in sorted(all_symbols):
        target = target_by_symbol.get(symbol)
        curr_qty = current_qty.get(symbol, Decimal("0"))

        ref_price = prices.get(symbol)
        if ref_price is None:
            raise RuntimeError(
                f"compute_deltas: no reference price for {symbol!r}; "
                "ensure the prices dict covers all held and target symbols"
            )
        if ref_price <= Decimal("0"):
            raise RuntimeError(
                f"compute_deltas: non-positive reference price for {symbol!r}: {ref_price}"
            )

        target_aud = target.target_weight * capital_aud if target else Decimal("0")
        target_qty = target_aud / ref_price
        delta_qty = target_qty - curr_qty
        delta_aud = delta_qty * ref_price

        tags: dict = {}
        hints: dict = {}

        # Universe-inactive forced-sell: override delta, ignore drift.
        is_universe_inactive = symbol in inactive and curr_qty > Decimal("0")
        if is_universe_inactive:
            side: str = "sell"
            tags["reason"] = "universe_inactive"
            # Full sell: sell the entire held position.
            delta_qty = -curr_qty
            delta_aud = delta_qty * ref_price
        elif abs(delta_aud) < drift_aud:
            side = "hold"
        elif delta_qty > Decimal("0"):
            side = "buy"
        else:
            side = "sell"
            if target is None:
                tags["reason"] = "exited_universe"

        # §5.1 boundary check on all sells (plan amendment I.4).
        if side == "sell" and symbol in boundary_by_symbol:
            near_lots = boundary_by_symbol[symbol]
            tags["near_boundary_lot_ids"] = [h.lot_id for h in near_lots]
            if defer_near_boundary_sells:
                side = "hold"  # deferred; tags preserved for transparency

        # Concentration alarm for buys (defence-in-depth).
        if side == "buy" and target_aud > _CONCENTRATION_ALARM_THRESHOLD * capital_aud:
            tags["concentration_alarm"] = True

        result.append(
            ProposedTrade(
                symbol=symbol,
                side=side,
                delta_qty=delta_qty,
                delta_aud=delta_aud,
                target_qty=target_qty,
                current_qty=curr_qty,
                reference_price=ref_price,
                rationale_tags=tags,
                lot_hints=hints,
            )
        )

    return result


# ---------------------------------------------------------------------------
# assemble_result
# ---------------------------------------------------------------------------


def assemble_result(
    *,
    profile: Profile,
    targets: list[AllocationTarget],
    trades: list[ProposedTrade],
    as_of: date,
    signals_as_of: date,
) -> RebalanceResult:
    """Package targets + trades + summary counts into a RebalanceResult.

    Summary keys:
        total_buy_aud   — sum of delta_aud for buy trades (Decimal, positive)
        total_sell_aud  — sum of abs(delta_aud) for sell trades (Decimal, positive)
        n_buys          — count of buy trades
        n_sells         — count of sell trades
        n_holds         — hold trades that are NOT CGT deferrals
        n_deferrals     — hold trades with 'near_boundary_lot_ids' in rationale_tags

    ``run_id`` is None; the CLI sets it after persisting via ``dataclasses.replace``.
    """
    n_buys = n_sells = n_holds = n_deferrals = 0
    total_buy_aud = Decimal("0")
    total_sell_aud = Decimal("0")

    for t in trades:
        if t.side == "buy":
            n_buys += 1
            total_buy_aud += t.delta_aud
        elif t.side == "sell":
            n_sells += 1
            total_sell_aud += abs(t.delta_aud)
        else:  # hold
            if "near_boundary_lot_ids" in t.rationale_tags:
                n_deferrals += 1
            else:
                n_holds += 1

    return RebalanceResult(
        run_id=None,
        as_of=as_of,
        signals_as_of=signals_as_of,
        profile=profile,
        targets=targets,
        trades=trades,
        summary={
            "total_buy_aud": total_buy_aud,
            "total_sell_aud": total_sell_aud,
            "n_buys": n_buys,
            "n_sells": n_sells,
            "n_holds": n_holds,
            "n_deferrals": n_deferrals,
        },
    )
