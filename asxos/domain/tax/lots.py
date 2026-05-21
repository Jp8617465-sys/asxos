"""
Lot-selection strategies for disposals: FIFO, LIFO, min-CGT.

Each strategy takes the active lots for a symbol, the quantity to sell, the
sale price (AUD), and the sale date, and returns a list of LotSelection
records — one per lot drawn down.

min-CGT brute-forces small subsets to minimise post-discount realised gain;
account-type matters because the discount differs (spec §2).
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
    """Brute-force search over subsets of `lots` (up to max_combo_size at a
    time) for the combination whose post-discount realised gain is smallest.

    For larger portfolios the user should pre-filter the candidate lot pool;
    above max_combo_size lots, we fall back to FIFO (deterministic baseline)."""
    if len(lots) > max_combo_size:
        return select_fifo(lots, qty_to_sell, sale_price_aud, sale_date)

    discount = cgt_discount_rate(account_type)
    best: tuple[Decimal, list[LotSelection]] | None = None

    # Try every combination size from 1..N and every order within (we always
    # take full lots first, partial last to maximise flexibility).
    for r in range(1, len(lots) + 1):
        for combo in combinations(lots, r):
            available = sum((lot.quantity for lot in combo), Decimal("0"))
            if available < qty_to_sell:
                continue
            sels = _draw(list(combo), qty_to_sell, sale_price_aud, sale_date)
            cost = _post_discount_gain(sels, discount)
            if best is None or cost < best[0]:
                best = (cost, sels)

    if best is None:
        raise ValueError(f"no lot combination can supply {qty_to_sell} units")
    return best[1]


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
