"""
Tests for asxos/domain/portfolio/tax_overlay.py (M13.5).

Coverage targets (plan I.10):
  - near_boundary_lots: window filtering, at-zero exclusion, edge, multi-symbol
  - unrealised_losses: loss detection, gain/at-cost exclusion, multi-lot symbol
  - tag_loss_harvest: sell tagging, no-tag for buys/holds, lot ordering,
    no-new-names invariant, sum-preserving invariant, existing-tags preserved
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.portfolio.tax_overlay import (
    near_boundary_lots,
    tag_loss_harvest,
    unrealised_losses,
)
from asxos.domain.portfolio.types import HoldingSnapshot, ProposedTrade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_snapshot(
    *,
    lot_id: int = 1,
    symbol: str = "BHP",
    acquired_at: date = date(2024, 1, 1),
    quantity: Decimal = Decimal("100"),
    cost_base_normal: Decimal = Decimal("5000"),
    cost_base_div296: Decimal = Decimal("5000"),
    account_type: str = "individual",
    current_price_aud: Decimal = Decimal("40"),  # market value = 4000 < 5000 → loss
    days_to_cgt_discount: int = 15,
) -> HoldingSnapshot:
    return HoldingSnapshot(
        lot_id=lot_id,
        symbol=symbol,
        acquired_at=acquired_at,
        quantity=quantity,
        cost_base_normal=cost_base_normal,
        cost_base_div296=cost_base_div296,
        account_type=account_type,
        current_price_aud=current_price_aud,
        days_to_cgt_discount=days_to_cgt_discount,
    )


def make_trade(
    *,
    symbol: str = "BHP",
    side: str = "sell",
    delta_qty: Decimal = Decimal("-100"),
    delta_aud: Decimal = Decimal("-4000"),
    target_qty: Decimal = Decimal("0"),
    current_qty: Decimal = Decimal("100"),
    reference_price: Decimal = Decimal("40"),
    rationale_tags: dict | None = None,
    lot_hints: dict | None = None,
) -> ProposedTrade:
    return ProposedTrade(
        symbol=symbol,
        side=side,
        delta_qty=delta_qty,
        delta_aud=delta_aud,
        target_qty=target_qty,
        current_qty=current_qty,
        reference_price=reference_price,
        rationale_tags=rationale_tags if rationale_tags is not None else {},
        lot_hints=lot_hints if lot_hints is not None else {},
    )


# ---------------------------------------------------------------------------
# near_boundary_lots
# ---------------------------------------------------------------------------


def test_near_boundary_lots_within_window() -> None:
    """Lot inside window (15 of 30) is included."""
    h = make_snapshot(days_to_cgt_discount=15)
    result = near_boundary_lots([h])
    assert "BHP" in result
    assert result["BHP"] == [h]


def test_near_boundary_lots_already_eligible_excluded() -> None:
    """Lot at days=0 (already eligible) is excluded — no deferral benefit."""
    h = make_snapshot(days_to_cgt_discount=0)
    result = near_boundary_lots([h])
    assert result == {}


def test_near_boundary_lots_at_window_edge() -> None:
    """Lot exactly at window_days=30 is included (boundary is inclusive)."""
    h = make_snapshot(days_to_cgt_discount=30)
    result = near_boundary_lots([h], window_days=30)
    assert "BHP" in result


def test_near_boundary_lots_over_window_excluded() -> None:
    """Lot at days=31 with window=30 is excluded."""
    h = make_snapshot(days_to_cgt_discount=31)
    result = near_boundary_lots([h], window_days=30)
    assert result == {}


def test_near_boundary_lots_multi_symbol() -> None:
    """Multiple symbols; only those within window are returned."""
    within = make_snapshot(symbol="BHP", lot_id=1, days_to_cgt_discount=10)
    outside = make_snapshot(symbol="CBA", lot_id=2, days_to_cgt_discount=60)
    eligible = make_snapshot(symbol="RIO", lot_id=3, days_to_cgt_discount=0)
    result = near_boundary_lots([within, outside, eligible])
    assert "BHP" in result
    assert "CBA" not in result
    assert "RIO" not in result


def test_near_boundary_lots_custom_window() -> None:
    """Custom window=14: lot at 15 excluded, lot at 14 included."""
    h14 = make_snapshot(symbol="BHP", lot_id=1, days_to_cgt_discount=14)
    h15 = make_snapshot(symbol="CBA", lot_id=2, days_to_cgt_discount=15)
    result = near_boundary_lots([h14, h15], window_days=14)
    assert "BHP" in result
    assert "CBA" not in result


def test_near_boundary_lots_multiple_lots_same_symbol() -> None:
    """Two near-boundary lots on same symbol → both returned."""
    h1 = make_snapshot(lot_id=1, days_to_cgt_discount=10)
    h2 = make_snapshot(lot_id=2, days_to_cgt_discount=25)
    result = near_boundary_lots([h1, h2])
    assert len(result["BHP"]) == 2


def test_near_boundary_lots_empty_input() -> None:
    assert near_boundary_lots([]) == {}


# ---------------------------------------------------------------------------
# unrealised_losses
# ---------------------------------------------------------------------------


def test_unrealised_losses_simple_loss() -> None:
    """market_value (40×100=4000) < cost_base (5000) → loss lot included."""
    h = make_snapshot(current_price_aud=Decimal("40"), cost_base_normal=Decimal("5000"))
    result = unrealised_losses([h])
    assert "BHP" in result
    assert result["BHP"] == [h]


def test_unrealised_losses_gain_excluded() -> None:
    """market_value (60×100=6000) > cost_base (5000) → gain lot excluded."""
    h = make_snapshot(current_price_aud=Decimal("60"), cost_base_normal=Decimal("5000"))
    result = unrealised_losses([h])
    assert result == {}


def test_unrealised_losses_at_cost_excluded() -> None:
    """market_value == cost_base → exactly at cost, nothing to harvest, excluded."""
    h = make_snapshot(current_price_aud=Decimal("50"), cost_base_normal=Decimal("5000"))
    result = unrealised_losses([h])
    assert result == {}


def test_unrealised_losses_multi_lot_same_symbol() -> None:
    """For same symbol: loss lot included, gain lot excluded."""
    loss = make_snapshot(lot_id=1, current_price_aud=Decimal("40"), cost_base_normal=Decimal("5000"))
    gain = make_snapshot(lot_id=2, current_price_aud=Decimal("60"), cost_base_normal=Decimal("5000"))
    result = unrealised_losses([loss, gain])
    assert "BHP" in result
    assert len(result["BHP"]) == 1
    assert result["BHP"][0].lot_id == 1


def test_unrealised_losses_multi_symbol() -> None:
    """Two loss symbols are both returned."""
    h_bhp = make_snapshot(symbol="BHP", lot_id=1, current_price_aud=Decimal("40"), cost_base_normal=Decimal("5000"))
    h_cba = make_snapshot(symbol="CBA", lot_id=2, current_price_aud=Decimal("90"), cost_base_normal=Decimal("10000"))
    result = unrealised_losses([h_bhp, h_cba])
    assert "BHP" in result
    assert "CBA" in result


def test_unrealised_losses_empty_input() -> None:
    assert unrealised_losses([]) == {}


# ---------------------------------------------------------------------------
# tag_loss_harvest
# ---------------------------------------------------------------------------


def test_tag_loss_harvest_sell_tagged() -> None:
    """Sell trade on a loss symbol gets reason, spec_ref, and lot_hints."""
    h = make_snapshot(lot_id=10)
    trade = make_trade(symbol="BHP", side="sell")
    losses = {"BHP": [h]}

    result = tag_loss_harvest([trade], losses)
    assert len(result) == 1
    t = result[0]
    assert t.rationale_tags["reason"] == "loss_harvest"
    assert t.rationale_tags["spec_ref"] == "§5.2"
    assert t.lot_hints["preferred_lot_ids"] == [10]


def test_tag_loss_harvest_buy_not_tagged() -> None:
    """Buy trade on a loss symbol passes through unchanged."""
    h = make_snapshot(lot_id=10)
    trade = make_trade(symbol="BHP", side="buy", delta_qty=Decimal("50"), delta_aud=Decimal("2000"))
    losses = {"BHP": [h]}

    result = tag_loss_harvest([trade], losses)
    assert result[0].rationale_tags == {}
    assert result[0].lot_hints == {}
    assert result[0].side == "buy"


def test_tag_loss_harvest_hold_not_tagged() -> None:
    """Hold trade on a loss symbol passes through unchanged."""
    h = make_snapshot(lot_id=10)
    trade = make_trade(symbol="BHP", side="hold", delta_qty=Decimal("0"), delta_aud=Decimal("0"))
    losses = {"BHP": [h]}

    result = tag_loss_harvest([trade], losses)
    assert result[0].rationale_tags == {}


def test_tag_loss_harvest_sell_no_loss_unchanged() -> None:
    """Sell trade on a symbol NOT in losses passes through unchanged."""
    trade = make_trade(symbol="BHP", side="sell")
    result = tag_loss_harvest([trade], {})
    assert result[0].rationale_tags == {}
    assert result[0].lot_hints == {}


def test_tag_loss_harvest_lot_ordering_largest_loss_first() -> None:
    """Lots are sorted by ascending unrealised gain (largest loss at front)."""
    # lot 1: price=30, qty=100, cost=5000 → gain = 3000 - 5000 = -2000 (larger loss)
    # lot 2: price=45, qty=100, cost=5000 → gain = 4500 - 5000 = -500 (smaller loss)
    h1 = make_snapshot(lot_id=1, current_price_aud=Decimal("30"), cost_base_normal=Decimal("5000"))
    h2 = make_snapshot(lot_id=2, current_price_aud=Decimal("45"), cost_base_normal=Decimal("5000"))
    trade = make_trade(symbol="BHP", side="sell")
    losses = {"BHP": [h2, h1]}  # intentionally out of order

    result = tag_loss_harvest([trade], losses)
    assert result[0].lot_hints["preferred_lot_ids"] == [1, 2]


def test_tag_loss_harvest_no_new_names_invariant() -> None:
    """Symbol set in output equals symbol set in input."""
    trades = [
        make_trade(symbol="BHP", side="sell"),
        make_trade(symbol="CBA", side="buy", delta_qty=Decimal("50"), delta_aud=Decimal("4000")),
    ]
    h = make_snapshot(symbol="BHP", lot_id=99)
    losses = {"BHP": [h]}

    result = tag_loss_harvest(trades, losses)
    assert {t.symbol for t in result} == {"BHP", "CBA"}


def test_tag_loss_harvest_sum_preserving_invariant() -> None:
    """delta_aud sum is unchanged — tag-only operation."""
    trades = [
        make_trade(symbol="BHP", side="sell", delta_aud=Decimal("-4000")),
        make_trade(symbol="CBA", side="buy", delta_qty=Decimal("20"), delta_aud=Decimal("3000")),
    ]
    h = make_snapshot(symbol="BHP", lot_id=5)
    losses = {"BHP": [h]}

    original_sum = sum(t.delta_aud for t in trades)
    result = tag_loss_harvest(trades, losses)
    result_sum = sum(t.delta_aud for t in result)
    assert result_sum == original_sum


def test_tag_loss_harvest_existing_tags_preserved() -> None:
    """Pre-existing rationale_tags keys are preserved; only new keys added."""
    trade = make_trade(
        symbol="BHP",
        side="sell",
        rationale_tags={"capped_by_per_name": True},
    )
    h = make_snapshot(lot_id=7)
    losses = {"BHP": [h]}

    result = tag_loss_harvest([trade], losses)
    tags = result[0].rationale_tags
    assert tags["capped_by_per_name"] is True
    assert tags["reason"] == "loss_harvest"
    assert tags["spec_ref"] == "§5.2"


def test_tag_loss_harvest_existing_lot_hints_preserved() -> None:
    """Pre-existing lot_hints keys are preserved; preferred_lot_ids is added."""
    trade = make_trade(
        symbol="BHP",
        side="sell",
        lot_hints={"note": "manual"},
    )
    h = make_snapshot(lot_id=3)
    losses = {"BHP": [h]}

    result = tag_loss_harvest([trade], losses)
    hints = result[0].lot_hints
    assert hints["note"] == "manual"
    assert hints["preferred_lot_ids"] == [3]


def test_tag_loss_harvest_empty_trades() -> None:
    assert tag_loss_harvest([], {"BHP": [make_snapshot()]}) == []


def test_tag_loss_harvest_empty_losses() -> None:
    """No losses → all trades pass through unchanged."""
    trades = [make_trade(symbol="BHP", side="sell")]
    result = tag_loss_harvest(trades, {})
    assert result[0].rationale_tags == {}


def test_tag_loss_harvest_mixed_trades() -> None:
    """Mixed batch: only the sell on a loss symbol gets tagged."""
    sell_loss = make_trade(symbol="BHP", side="sell")
    buy_trade = make_trade(symbol="CBA", side="buy", delta_qty=Decimal("10"), delta_aud=Decimal("1000"))
    hold_trade = make_trade(symbol="RIO", side="hold", delta_qty=Decimal("0"), delta_aud=Decimal("0"))
    sell_no_loss = make_trade(symbol="WBC", side="sell", delta_qty=Decimal("-5"), delta_aud=Decimal("-500"))

    h = make_snapshot(symbol="BHP", lot_id=42)
    losses = {"BHP": [h]}

    result = tag_loss_harvest([sell_loss, buy_trade, hold_trade, sell_no_loss], losses)

    bhp_result = next(t for t in result if t.symbol == "BHP")
    assert bhp_result.rationale_tags["reason"] == "loss_harvest"

    for sym in ("CBA", "RIO", "WBC"):
        t = next(r for r in result if r.symbol == sym)
        assert "reason" not in t.rationale_tags


def test_tag_loss_harvest_multiple_lots_ordered() -> None:
    """Three loss lots on same symbol: sorted largest loss first."""
    # Losses: lot1=-1000, lot2=-500, lot3=-1500 → order: lot3, lot1, lot2
    h1 = make_snapshot(lot_id=1, current_price_aud=Decimal("40"), cost_base_normal=Decimal("5000"))
    # qty=100, price=40 → mv=4000, gain = 4000-5000 = -1000
    h2 = make_snapshot(lot_id=2, current_price_aud=Decimal("45"), cost_base_normal=Decimal("5000"))
    # gain = 4500-5000 = -500
    h3 = make_snapshot(lot_id=3, current_price_aud=Decimal("35"), cost_base_normal=Decimal("5000"))
    # gain = 3500-5000 = -1500
    trade = make_trade(symbol="BHP", side="sell")
    losses = {"BHP": [h1, h2, h3]}

    result = tag_loss_harvest([trade], losses)
    assert result[0].lot_hints["preferred_lot_ids"] == [3, 1, 2]


def test_tag_loss_harvest_delta_qty_unchanged() -> None:
    """delta_qty is not modified by tagging."""
    trade = make_trade(symbol="BHP", side="sell", delta_qty=Decimal("-77"))
    h = make_snapshot(lot_id=1)
    result = tag_loss_harvest([trade], {"BHP": [h]})
    assert result[0].delta_qty == Decimal("-77")
