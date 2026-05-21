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
