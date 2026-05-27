"""
Tests for asxos/domain/tax/fx_gain.py — Division 775 FX gain/loss.

Spec: tax-alpha.md §8 (v1.2, 2026-05-27).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asxos.domain.tax.fx_gain import fx_capital_gain, is_de_minimis
from asxos.domain.tax.types import HoldingLot


def _us_lot(
    *,
    cost_base_usd: Decimal | None = Decimal("10000"),
    disposal_proceeds_usd: Decimal | None = Decimal("12000"),
    acquisition_fx_rate: Decimal | None = Decimal("0.70"),  # USD per AUD (1 AUD buys 0.70 USD)
    disposal_fx_rate: Decimal | None = Decimal("0.65"),
) -> HoldingLot:
    """Return a US lot with sane defaults for FX tests."""
    return HoldingLot(
        lot_id=1,
        symbol="AAPL.US",
        acquired_at=date(2023, 1, 15),
        quantity=Decimal("50"),
        cost_base_normal=Decimal("14285.71"),  # 10000 / 0.70
        cost_base_div296=Decimal("14285.71"),
        account_type="individual",
        disposed_at=date(2024, 6, 20),
        disposal_proceeds=Decimal("18461.54"),
        cost_base_usd=cost_base_usd,
        disposal_proceeds_usd=disposal_proceeds_usd,
        acquisition_fx_rate=acquisition_fx_rate,
        disposal_fx_rate=disposal_fx_rate,
    )


def _asx_lot() -> HoldingLot:
    """Return an ASX lot — no FX fields."""
    return HoldingLot(
        lot_id=2,
        symbol="BHP.AU",
        acquired_at=date(2023, 3, 10),
        quantity=Decimal("100"),
        cost_base_normal=Decimal("4500"),
        cost_base_div296=Decimal("4500"),
    )


# ---------------------------------------------------------------------------
# None-return cases — spec §8.3 contract
# ---------------------------------------------------------------------------

def test_returns_none_for_asx_lot() -> None:
    """No cost_base_usd → not a US lot → None (no forex realisation event)."""
    assert fx_capital_gain(_asx_lot()) is None


def test_returns_none_for_undisposed_lot() -> None:
    """disposal_proceeds_usd=None means lot not yet disposed → None."""
    lot = _us_lot(disposal_proceeds_usd=None)
    assert fx_capital_gain(lot) is None


def test_returns_none_for_missing_acquisition_fx_rate() -> None:
    """Missing acquisition FX rate is a data gap → None (caller must warn)."""
    lot = _us_lot(acquisition_fx_rate=None)
    assert fx_capital_gain(lot) is None


def test_returns_none_for_missing_disposal_fx_rate() -> None:
    """Missing disposal FX rate is a data gap → None (caller must warn)."""
    lot = _us_lot(disposal_fx_rate=None)
    assert fx_capital_gain(lot) is None


def test_returns_none_when_both_fx_rates_missing() -> None:
    lot = _us_lot(acquisition_fx_rate=None, disposal_fx_rate=None)
    assert fx_capital_gain(lot) is None


# ---------------------------------------------------------------------------
# Hard-fail cases — spec §8.3 rule #10
# ---------------------------------------------------------------------------

def test_hard_fails_on_zero_disposal_fx_rate() -> None:
    with pytest.raises(ValueError, match="disposal_fx_rate"):
        fx_capital_gain(_us_lot(disposal_fx_rate=Decimal("0")))


def test_hard_fails_on_negative_disposal_fx_rate() -> None:
    with pytest.raises(ValueError, match="disposal_fx_rate"):
        fx_capital_gain(_us_lot(disposal_fx_rate=Decimal("-0.5")))


def test_hard_fails_on_zero_acquisition_fx_rate() -> None:
    with pytest.raises(ValueError, match="acquisition_fx_rate"):
        fx_capital_gain(_us_lot(acquisition_fx_rate=Decimal("0")))


def test_hard_fails_on_negative_acquisition_fx_rate() -> None:
    with pytest.raises(ValueError, match="acquisition_fx_rate"):
        fx_capital_gain(_us_lot(acquisition_fx_rate=Decimal("-0.1")))


# ---------------------------------------------------------------------------
# Formula correctness — spec §8.2
# formula: (disposal_proceeds_usd / disposal_fx_rate) - (cost_base_usd / acquisition_fx_rate)
# ---------------------------------------------------------------------------

def test_fx_gain_formula_matches_spec() -> None:
    """Explicit worked example.

    ESPP grant: 100 shares × $10 USD = $1,000 USD cost
    Acquisition rate: 0.70 (1 AUD = 0.70 USD)  → AUD cost = 1000 / 0.70 = 1428.57...
    Disposal proceeds: $1,200 USD
    Disposal rate: 0.65 (1 AUD = 0.65 USD) → AUD proceeds = 1200 / 0.65 = 1846.15...

    FX gain = 1846.15... - 1428.57... = 417.58... (positive → ordinary income s 775-15)
    """
    lot = _us_lot(
        cost_base_usd=Decimal("1000"),
        disposal_proceeds_usd=Decimal("1200"),
        acquisition_fx_rate=Decimal("0.70"),
        disposal_fx_rate=Decimal("0.65"),
    )
    result = fx_capital_gain(lot)
    assert result is not None
    expected = Decimal("1200") / Decimal("0.65") - Decimal("1000") / Decimal("0.70")
    assert result == expected


def test_returns_positive_gain_when_aud_weakens() -> None:
    """AUD weakens (rate falls) → same USD proceeds are worth more AUD → FX gain."""
    # Buy when AUD = 0.80 USD; sell when AUD = 0.60 USD
    lot = _us_lot(
        cost_base_usd=Decimal("8000"),
        disposal_proceeds_usd=Decimal("8000"),  # flat USD — no equity gain
        acquisition_fx_rate=Decimal("0.80"),
        disposal_fx_rate=Decimal("0.60"),
    )
    result = fx_capital_gain(lot)
    assert result is not None
    assert result > Decimal("0"), "AUD weakening should produce a positive FX gain"


def test_returns_negative_loss_when_aud_strengthens() -> None:
    """AUD strengthens (rate rises) → same USD proceeds are worth less AUD → FX loss."""
    # Buy when AUD = 0.60 USD; sell when AUD = 0.80 USD
    lot = _us_lot(
        cost_base_usd=Decimal("6000"),
        disposal_proceeds_usd=Decimal("6000"),  # flat USD — no equity gain
        acquisition_fx_rate=Decimal("0.60"),
        disposal_fx_rate=Decimal("0.80"),
    )
    result = fx_capital_gain(lot)
    assert result is not None
    assert result < Decimal("0"), "AUD strengthening with flat USD should produce a FX loss"


def test_returns_zero_when_fx_rate_unchanged_and_flat_usd() -> None:
    """Same rate both ends, same USD proceeds → zero FX gain."""
    lot = _us_lot(
        cost_base_usd=Decimal("5000"),
        disposal_proceeds_usd=Decimal("5000"),
        acquisition_fx_rate=Decimal("0.75"),
        disposal_fx_rate=Decimal("0.75"),
    )
    result = fx_capital_gain(lot)
    assert result == Decimal("0")


def test_result_is_decimal_not_float() -> None:
    """Monetary arithmetic must use Decimal throughout — no float leakage."""
    lot = _us_lot()
    result = fx_capital_gain(lot)
    assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# is_de_minimis — spec §8.1 s 775-30 threshold ($250 AUD)
# ---------------------------------------------------------------------------

def test_is_de_minimis_below_threshold() -> None:
    assert is_de_minimis(Decimal("100.00")) is True


def test_is_de_minimis_at_exact_boundary() -> None:
    """$250 exactly is within the threshold (≤ 250)."""
    assert is_de_minimis(Decimal("250")) is True


def test_is_de_minimis_above_threshold() -> None:
    assert is_de_minimis(Decimal("250.01")) is False


def test_is_de_minimis_negative_loss_within_threshold() -> None:
    """Threshold applies to absolute value — a $200 loss is de minimis."""
    assert is_de_minimis(Decimal("-200")) is True


def test_is_de_minimis_negative_loss_above_threshold() -> None:
    """A $300 FX loss exceeds the threshold."""
    assert is_de_minimis(Decimal("-300")) is False


def test_is_de_minimis_zero_gain() -> None:
    assert is_de_minimis(Decimal("0")) is True
