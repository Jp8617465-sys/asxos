"""
Lot-selection tests for FIFO / LIFO / min-CGT (spec §5 + lots.py).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.tax.lots import select_fifo, select_lifo, select_min_cgt
from asxos.domain.tax.types import HoldingLot


def _lot(lot_id: int, acquired: date, qty: str, cost_total: str) -> HoldingLot:
    return HoldingLot(
        lot_id=lot_id,
        symbol="X.AU",
        acquired_at=acquired,
        quantity=Decimal(qty),
        cost_base_normal=Decimal(cost_total),
        cost_base_div296=Decimal(cost_total),
        account_type="individual",
    )


def test_fifo_draws_oldest_first() -> None:
    lots = [
        _lot(1, date(2023, 1, 1), "100", "1000"),
        _lot(2, date(2024, 1, 1), "100", "1500"),
    ]
    sels = select_fifo(lots, Decimal("80"), Decimal("20"), date(2025, 6, 1))
    assert len(sels) == 1
    assert sels[0].lot_id == 1
    assert sels[0].qty_sold == Decimal("80")
    # Realised: (20 - 10) * 80 = 800
    assert sels[0].realised_gain_aud == Decimal("800")
    assert sels[0].discountable is True  # held > 12 months


def test_fifo_spans_multiple_lots() -> None:
    lots = [
        _lot(1, date(2023, 1, 1), "50", "500"),
        _lot(2, date(2024, 1, 1), "50", "750"),
        _lot(3, date(2024, 6, 1), "100", "2000"),
    ]
    sels = select_fifo(lots, Decimal("120"), Decimal("25"), date(2025, 7, 1))
    assert [s.lot_id for s in sels] == [1, 2, 3]
    assert [s.qty_sold for s in sels] == [Decimal("50"), Decimal("50"), Decimal("20")]


def test_lifo_draws_newest_first() -> None:
    lots = [
        _lot(1, date(2023, 1, 1), "100", "1000"),
        _lot(2, date(2024, 6, 1), "100", "2000"),
    ]
    sels = select_lifo(lots, Decimal("80"), Decimal("25"), date(2025, 7, 1))
    assert sels[0].lot_id == 2


def test_insufficient_lots_raises() -> None:
    lots = [_lot(1, date(2024, 1, 1), "50", "500")]
    with pytest.raises(ValueError, match="insufficient"):
        select_fifo(lots, Decimal("100"), Decimal("20"), date(2025, 1, 1))


def test_min_cgt_prefers_discountable_when_gain_positive() -> None:
    # Two lots with identical qty + cost: pre-discount gain identical at sale.
    # But the older lot's gain qualifies for the 50% discount → lower post-discount gain.
    lots = [
        _lot(1, date(2023, 1, 1), "100", "1000"),  # eligible (>12mo)
        _lot(2, date(2025, 5, 1), "100", "1000"),  # ineligible
    ]
    sels = select_min_cgt(
        lots, Decimal("100"), Decimal("20"), date(2025, 6, 1), account_type="individual"
    )
    # Picking lot 1 yields a discounted gain ($500 post-discount) vs lot 2's $1000.
    assert sels[0].lot_id == 1


def test_min_cgt_picks_smallest_gain_among_discountable() -> None:
    # Two lots both eligible for discount; pick the one with smaller gain.
    lots = [
        _lot(1, date(2022, 1, 1), "100", "1500"),  # cost/unit 15 → gain (20-15)*100 = 500
        _lot(2, date(2022, 6, 1), "100", "1900"),  # cost/unit 19 → gain (20-19)*100 = 100
    ]
    sels = select_min_cgt(
        lots, Decimal("100"), Decimal("20"), date(2025, 6, 1), account_type="individual"
    )
    assert sels[0].lot_id == 2


def test_min_cgt_falls_back_to_fifo_above_combo_limit() -> None:
    # 7 lots > max_combo_size=6 → falls back to FIFO baseline.
    lots = [_lot(i, date(2024, 1, i), "10", "100") for i in range(1, 8)]
    sels = select_min_cgt(
        lots,
        Decimal("30"),
        Decimal("20"),
        date(2025, 7, 1),
        account_type="individual",
        max_combo_size=6,
    )
    # FIFO returns lots 1, 2, 3
    assert [s.lot_id for s in sels] == [1, 2, 3]


# --- spec §5.5 — the partial-bearing lot is part of the search (v1.6, TC-25) ---
#
# Before v1.6 `_draw` always put the partial on the LAST lot of each combination in
# input order, so the minimum was found only when the caller happened to list the
# better full lot first (audit 2026-06-27 LOW #1). These pin the defect shape.


def _tc25_lots() -> list[HoldingLot]:
    # Lot A: 100 u @ 120, acquired 2024-03-01 → NOT discountable at 2025-01-15
    #        (earliest qualifying 2025-03-02, §5.1).
    # Lot B: 200 u @ 100, acquired 2023-01-01 → discountable.
    return [
        _lot(1, date(2024, 3, 1), "100", "12000"),
        _lot(2, date(2023, 1, 1), "200", "20000"),
    ]


def test_tc25_min_cgt_chooses_which_lot_bears_the_partial() -> None:
    """spec §5.5 / §11 TC-25. Sell 250 @ 160 on 2025-01-15, individual (d = 0.5).

    Draw A in full + 150 of B: 4,000 + (9,000 × 0.5) = 8,500.
    Draw B in full + 50 of A:  (12,000 × 0.5) + 2,000 = 8,000  ← the minimum.
    With A listed first the old search could only produce 8,500."""
    sels = select_min_cgt(
        _tc25_lots(), Decimal("250"), Decimal("160"), date(2025, 1, 15), account_type="individual"
    )
    by_id = {s.lot_id: s for s in sels}
    assert by_id[2].qty_sold == Decimal("200") and by_id[2].realised_gain_aud == Decimal("12000")
    assert by_id[1].qty_sold == Decimal("50") and by_id[1].realised_gain_aud == Decimal("2000")
    assert by_id[2].discountable is True and by_id[1].discountable is False
    post_discount = Decimal("12000") * Decimal("0.5") + Decimal("2000")
    assert post_discount == Decimal("8000")


def test_tc25_result_is_independent_of_input_order() -> None:
    lots = _tc25_lots()
    a = select_min_cgt(lots, Decimal("250"), Decimal("160"), date(2025, 1, 15), account_type="individual")
    b = select_min_cgt(
        list(reversed(lots)), Decimal("250"), Decimal("160"), date(2025, 1, 15), account_type="individual"
    )
    assert sorted((s.lot_id, s.qty_sold) for s in a) == sorted((s.lot_id, s.qty_sold) for s in b)


def test_min_cgt_three_lots_partial_on_the_middle_lot() -> None:
    # Three discountable lots, per-unit gains 5 / 1 / 3 at $20; sell 250 of 300.
    # The 50 units left behind should come from the highest-gain lot (lot 1, 5/u), so the
    # partial must fall on lot 1 — the middle of neither input order nor combination order.
    lots = [
        _lot(3, date(2022, 3, 1), "100", "1700"),  # 17/u → gain 3/u
        _lot(1, date(2022, 1, 1), "100", "1500"),  # 15/u → gain 5/u
        _lot(2, date(2022, 2, 1), "100", "1900"),  # 19/u → gain 1/u
    ]
    sels = select_min_cgt(lots, Decimal("250"), Decimal("20"), date(2025, 6, 1), account_type="individual")
    by_id = {s.lot_id: s for s in sels}
    assert by_id[1].qty_sold == Decimal("50")
    assert by_id[2].qty_sold == Decimal("100") and by_id[3].qty_sold == Decimal("100")
    # (3×100 + 1×100 + 5×50) × 0.5 = 325 post-discount; any other partial bearer is higher.
    total = sum(s.realised_gain_aud for s in sels) * Decimal("0.5")
    assert total == Decimal("325")


def test_min_cgt_exact_fit_has_no_partial_and_is_stable() -> None:
    lots = [
        _lot(1, date(2022, 1, 1), "100", "1500"),
        _lot(2, date(2022, 6, 1), "100", "1900"),
    ]
    sels = select_min_cgt(lots, Decimal("200"), Decimal("20"), date(2025, 6, 1), account_type="individual")
    assert sorted(s.lot_id for s in sels) == [1, 2]
    assert all(s.qty_sold == Decimal("100") for s in sels)
