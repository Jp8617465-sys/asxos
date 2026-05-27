"""
Division 775 FX gain/loss calculation for disposed US lots.

Spec: tax-alpha.md §8 (v1.2, 2026-05-27).

Contract (§8.3):
  fx_capital_gain(lot) -> Decimal | None
  - Returns None for ASX lots (no cost_base_usd / FX fields).
  - Returns None if any required FX rate is missing (data gap — flag to user).
  - Returns Decimal for disposed US lots with complete FX data.
    Positive = forex gain (ordinary income under s 775-15).
    Negative = forex loss (deductible under s 775-20).
  - Hard-fails (ValueError) if disposal_fx_rate is zero or negative.

The caller is responsible for displaying the $250 de minimis flag (s 775-30).
This function never applies the election — that is an irrevocable taxpayer choice.

Div 775 and CGT event A1 (equity gain) are independent — §8.4.
Do NOT add fx_capital_gain() to the equity CGT gain from positions.py.
Report them separately on the tax return.
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.tax.types import HoldingLot

_ZERO = Decimal("0")
_DE_MINIMIS = Decimal("250")   # s 775-30 threshold — informational only


def fx_capital_gain(lot: HoldingLot) -> Decimal | None:
    """Compute Div 775 FX gain/loss for a disposed US lot.

    Returns None if:
      - The lot has no cost_base_usd (ASX lot — no FX event).
      - The lot is not yet disposed (disposal_proceeds_usd is None).
      - Any required FX rate is missing (data gap; user must resolve).

    Returns Decimal (may be positive or negative) otherwise.
    Positive = ordinary income (s 775-15). Negative = deductible (s 775-20).

    Spec: tax-alpha.md §8.2.
    """
    # Not a US lot — no forex realisation event.
    if lot.cost_base_usd is None:
        return None

    # Not yet disposed.
    if lot.disposal_proceeds_usd is None:
        return None

    # Data gaps — cannot compute; caller should warn user.
    if lot.acquisition_fx_rate is None or lot.disposal_fx_rate is None:
        return None

    # Hard-fail on nonsensical FX rates (rule #10).
    if lot.disposal_fx_rate <= _ZERO:
        raise ValueError(
            f"lot {lot.lot_id}: disposal_fx_rate={lot.disposal_fx_rate} is not positive "
            "— hard-fail per spec §8.3"
        )
    if lot.acquisition_fx_rate <= _ZERO:
        raise ValueError(
            f"lot {lot.lot_id}: acquisition_fx_rate={lot.acquisition_fx_rate} is not positive "
            "— hard-fail per spec §8.3"
        )

    # §8.2 formula.
    cost_base_aud = lot.cost_base_usd / lot.acquisition_fx_rate
    proceeds_aud = lot.disposal_proceeds_usd / lot.disposal_fx_rate
    return proceeds_aud - cost_base_aud


def is_de_minimis(forex_gain_aud: Decimal) -> bool:
    """Return True if the absolute FX gain/loss is within the §8.1 s 775-30 threshold.

    The $250 de minimis election is available when all forex gains/losses in the
    income year sum to ≤ $250 in absolute value. This function checks per-lot;
    the calling code must aggregate across all lots for the year before applying.
    Informational only — the system never applies the election automatically.
    """
    return abs(forex_gain_aud) <= _DE_MINIMIS
