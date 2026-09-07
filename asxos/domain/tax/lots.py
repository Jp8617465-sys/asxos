"""
Lot-selection strategies for disposals: FIFO, LIFO, min-CGT.

Each strategy takes the active lots for a symbol, the quantity to sell, the
sale price (AUD), and the sale date, and returns a list of LotSelection
records — one per lot drawn down.

min-CGT brute-forces small subsets to minimise post-discount realised gain;
account-type matters because the discount differs (spec §2). The search covers
both WHICH lots are drawn and WHICH ONE bears the partial draw (spec §5.5) —
before v1.6 the partial always fell on the last lot of each combination in input
order, so the minimum was only found when the input happened to be ordered
favourably (audit 2026-06-27 LOW #1; TC-25).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from itertools import combinations

from asxos.domain.tax.cgt import cgt_discount_rate, is_discountable
from asxos.domain.tax.types import AccountType, HoldingLot, LotSelection


def _selection(
    lot: HoldingLot, qty: Decimal, sale_price: Decimal, sale_date: date
) -> LotSelection:
    gain = (sale_price - lot.cost_base_normal / lot.quantity) * qty
    holding_days = (sale_date - lot.acquired_at).days
    return LotSelection(
        lot_id=lot.lot_id,
        qty_sold=qty,
        realised_gain_aud=gain,
        holding_period_days=holding_days,
        discountable=is_discountable(lot.acquired_at, sale_date),
    )


def select_fifo(
    lots: list[HoldingLot],
    qty_to_sell: Decimal,
    sale_price_aud: Decimal,
    sale_date: date,
) -> list[LotSelection]:
    out: list[LotSelection] = []
    remaining = qty_to_sell
    for lot in sorted(lots, key=lambda x: x.acquired_at):
        if remaining <= 0:
            break
        take = min(remaining, lot.quantity)
        out.append(_selection(lot, take, sale_price_aud, sale_date))
        remaining -= take
    if remaining > 0:
        raise ValueError(f"insufficient lots: {remaining} units short of {qty_to_sell}")
    return out


def select_lifo(
    lots: list[HoldingLot],
    qty_to_sell: Decimal,
    sale_price_aud: Decimal,
    sale_date: date,
) -> list[LotSelection]:
    out: list[LotSelection] = []
    remaining = qty_to_sell
    for lot in sorted(lots, key=lambda x: x.acquired_at, reverse=True):
        if remaining <= 0:
            break
        take = min(remaining, lot.quantity)
        out.append(_selection(lot, take, sale_price_aud, sale_date))
        remaining -= take
    if remaining > 0:
        raise ValueError(f"insufficient lots: {remaining} units short of {qty_to_sell}")
    return out


def select_min_cgt(
    lots: list[HoldingLot],
    qty_to_sell: Decimal,
    sale_price_aud: Decimal,
    sale_date: date,
    *,
    account_type: AccountType,
    max_combo_size: int = 6,
) -> list[LotSelection]:
    """Spec §5.5 — brute-force search for the selection whose post-discount
    realised gain is smallest.

    Search space: every subset of `lots` (sizes 1..N, N ≤ max_combo_size)
    whose quantity covers `qty_to_sell`, and within each subset every choice
    of the lot that bears the partial draw (the others are drawn in full).
    A subset whose quantity equals the sale exactly has no partial and is
    evaluated once. Ties resolve to the first candidate in enumeration order:
    fewer lots first, then the order the lots were supplied, then the partial
    on the earliest-listed lot — deterministic, so a staged sell reproduces.

    Above max_combo_size lots the function falls back to FIFO (deterministic
    baseline); capital-facing callers refuse rather than accept the fallback
    (`decision_engine/staging.py` MIN_CGT_MAX_LOTS)."""
    if len(lots) > max_combo_size:
        return select_fifo(lots, qty_to_sell, sale_price_aud, sale_date)

    discount = cgt_discount_rate(account_type)
    best: tuple[Decimal, list[LotSelection]] | None = None

    for r in range(1, len(lots) + 1):
        for combo in combinations(lots, r):
            available = sum((lot.quantity for lot in combo), Decimal("0"))
            if available < qty_to_sell:
                continue
            for order in _partial_bearer_orders(list(combo), available, qty_to_sell):
                sels = _draw(order, qty_to_sell, sale_price_aud, sale_date)
                cost = _post_discount_gain(sels, discount)
                if best is None or cost < best[0]:
                    best = (cost, sels)

    if best is None:
        raise ValueError(f"no lot combination can supply {qty_to_sell} units")
    return best[1]


def _partial_bearer_orders(
    combo: list[HoldingLot], available: Decimal, qty: Decimal
) -> list[list[HoldingLot]]:
    """Every draw order that differs in WHICH lot bears the partial (spec §5.5).

    `_draw` takes lots in order and the last lot drawn absorbs the remainder,
    so moving each candidate to the end enumerates the partial-bearer choice
    without permuting the full lots (their order cannot change the gain). An
    exact-fit combination has no partial: one order suffices."""
    if available == qty or len(combo) == 1:
        return [combo]
    return [[*combo[:i], *combo[i + 1 :], combo[i]] for i in range(len(combo))]


def _draw(
    lots: list[HoldingLot],
    qty: Decimal,
    sale_price: Decimal,
    sale_date: date,
) -> list[LotSelection]:
    """Draw down the supplied lots in order until `qty` is met."""
    out: list[LotSelection] = []
    remaining = qty
    for lot in lots:
        if remaining <= 0:
            break
        take = min(remaining, lot.quantity)
        out.append(_selection(lot, take, sale_price, sale_date))
        remaining -= take
    return out


def _post_discount_gain(sels: list[LotSelection], discount: Decimal) -> Decimal:
    total = Decimal("0")
    for s in sels:
        gain = s.realised_gain_aud
        if gain > 0 and s.discountable:
            gain = gain * (Decimal("1") - discount)
        total += gain
    return total
