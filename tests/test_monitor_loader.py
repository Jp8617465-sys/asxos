"""
Tests for asxos.domain.portfolio.monitor_loader row-mapping guards.

_position_from_row guards nullable numeric columns so a NULL prob_up /
expected_return (from the LEFT JOINs) becomes Decimal('0') instead of crashing
the whole load with Decimal(str(None)) -> InvalidOperation.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.portfolio.monitor_loader import _position_from_row


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "symbol": "CBA.AU",
        "sector": "Financials",
        "target_weight": Decimal("0.1"),
        "target_aud": Decimal("50000"),
        "signal_label": "BUY",
        "prob_up": Decimal("0.62"),
        "expected_return": Decimal("0.04"),
        "target_qty": Decimal("100"),
        "reference_price": Decimal("95.50"),
        "entry_close": Decimal("95.50"),
        "entry_adj_close": Decimal("95.50"),
    }
    base.update(overrides)
    return base


def test_position_from_row_maps_all_fields() -> None:
    p = _position_from_row(_row())
    assert p.symbol == "CBA.AU"
    assert p.prob_up == Decimal("0.62")
    assert p.expected_return == Decimal("0.04")
    assert p.entry_close == Decimal("95.50")


def test_null_prob_up_and_expected_return_become_zero() -> None:
    # A NULL prob_up / expected_return must not crash the load.
    p = _position_from_row(_row(prob_up=None, expected_return=None))
    assert p.prob_up == Decimal("0")
    assert p.expected_return == Decimal("0")


def test_missing_trade_and_price_fall_back() -> None:
    # No proposed_trade / no price row (LEFT JOIN nulls) → qty 0, entry_close 0.
    p = _position_from_row(
        _row(reference_price=None, entry_close=None, entry_adj_close=None, target_qty=None)
    )
    assert p.qty == Decimal("0")
    assert p.entry_close == Decimal("0")
    assert p.entry_adj_close == Decimal("0")  # falls back to entry_close
