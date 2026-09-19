"""
Tests for asxos/domain/regime/classifier.py — M-Market-Context.

Each test corresponds to one of the five regime labels.
Hard-fail and soft-degrade paths are also covered.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from asxos.domain.regime.classifier import classify
from asxos.domain.regime.types import RegimeLabel


def _base() -> dict[str, Decimal | None]:
    """Calm-market baseline indicators."""
    return {
        "avix": Decimal("12"),
        "us_hy_oas": Decimal("3.50"),
        "pct_above_50d_ma": Decimal("0.72"),
        "pct_above_200d_ma": Decimal("0.78"),
        "net_new_highs_lows_10d": Decimal("0.05"),
    }


# ---------------------------------------------------------------------------
# 1. risk_on_broadening
# ---------------------------------------------------------------------------

def test_risk_on_broadening() -> None:
    """avix very calm + wide breadth + net new highs positive."""
    indicators = {
        **_base(),
        "avix": Decimal("13"),
        "pct_above_200d_ma": Decimal("0.74"),
        "net_new_highs_lows_10d": Decimal("0.08"),
    }
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_on_broadening
    fired = {c.name for c in conds if c.fired}
    assert "avix_very_calm" in fired
    assert "breadth_200_bullish" in fired
    assert "net_highs_positive" in fired


# ---------------------------------------------------------------------------
# 2. risk_on_narrowing
# ---------------------------------------------------------------------------

def test_risk_on_narrowing() -> None:
    """avix calm + moderate breadth + net new highs non-positive."""
    indicators = {
        **_base(),
        "avix": Decimal("16"),
        "pct_above_200d_ma": Decimal("0.60"),
        "net_new_highs_lows_10d": Decimal("-0.02"),
    }
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_on_narrowing
    fired = {c.name for c in conds if c.fired}
    assert "avix_calm" in fired
    assert "breadth_200_moderate" in fired
    assert "net_highs_not_positive" in fired


# ---------------------------------------------------------------------------
# 3. neutral_mixed
# ---------------------------------------------------------------------------

def test_neutral_mixed() -> None:
    """avix moderate, moderate breadth, mixed signals → default neutral."""
    indicators = {
        "avix": Decimal("19"),
        "us_hy_oas": Decimal("3.80"),
        "pct_above_200d_ma": Decimal("0.50"),
        "net_new_highs_lows_10d": Decimal("0.01"),
    }
    label, _ = classify(indicators)
    assert label == RegimeLabel.neutral_mixed


def test_neutral_when_optional_breadth_missing() -> None:
    """Missing optional breadth indicators → neutral (not an error)."""
    indicators = {
        "avix": Decimal("19"),
        "us_hy_oas": Decimal("4.00"),
        # all optional breadth indicators absent
    }
    label, _ = classify(indicators)
    assert label == RegimeLabel.neutral_mixed


# ---------------------------------------------------------------------------
# 4. risk_off_orderly
# ---------------------------------------------------------------------------

def test_risk_off_orderly_avix() -> None:
    """AVIX above 22 → risk_off_orderly."""
    indicators = {**_base(), "avix": Decimal("24"), "us_hy_oas": Decimal("4.00")}
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_off_orderly
    assert any(c.name == "avix_elevated" and c.fired for c in conds)


def test_risk_off_orderly_credit() -> None:
    """HY OAS > 4.50 % → risk_off_orderly."""
    indicators = {**_base(), "avix": Decimal("19"), "us_hy_oas": Decimal("5.00")}
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_off_orderly
    assert any(c.name == "hy_oas_elevated" and c.fired for c in conds)


def test_risk_off_orderly_thin_breadth() -> None:
    """pct_above_200d_ma < 0.40 → risk_off_orderly."""
    indicators = {
        **_base(),
        "avix": Decimal("20"),
        "us_hy_oas": Decimal("4.00"),
        "pct_above_200d_ma": Decimal("0.35"),
    }
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_off_orderly
    assert any(c.name == "breadth_200_thin" and c.fired for c in conds)


# ---------------------------------------------------------------------------
# 5. risk_off_disorderly
# ---------------------------------------------------------------------------

def test_risk_off_disorderly_avix() -> None:
    """AVIX > 30 → risk_off_disorderly (takes precedence over all else)."""
    indicators = {**_base(), "avix": Decimal("35"), "us_hy_oas": Decimal("3.00")}
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_off_disorderly
    assert any(c.name == "avix_extreme" and c.fired for c in conds)


def test_risk_off_disorderly_credit() -> None:
    """HY OAS > 6.00 % → risk_off_disorderly."""
    indicators = {**_base(), "avix": Decimal("25"), "us_hy_oas": Decimal("6.50")}
    label, conds = classify(indicators)
    assert label == RegimeLabel.risk_off_disorderly
    assert any(c.name == "hy_oas_stress" and c.fired for c in conds)


# ---------------------------------------------------------------------------
# Hard-fail paths
# ---------------------------------------------------------------------------

def test_missing_avix_raises() -> None:
    """avix=None is a hard-fail — classifier cannot run."""
    with pytest.raises(RuntimeError, match="avix"):
        classify({"avix": None, "us_hy_oas": Decimal("4.00")})


def test_missing_hy_oas_raises() -> None:
    """us_hy_oas=None is a hard-fail."""
    with pytest.raises(RuntimeError, match="us_hy_oas"):
        classify({"avix": Decimal("15"), "us_hy_oas": None})


def test_absent_avix_raises() -> None:
    """avix key absent entirely is also a hard-fail."""
    with pytest.raises(RuntimeError, match="avix"):
        classify({"us_hy_oas": Decimal("4.00")})


# ---------------------------------------------------------------------------
# Condition list completeness
# ---------------------------------------------------------------------------

def test_conditions_always_returned() -> None:
    """Every call returns a non-empty conditions list."""
    _label, conds = classify(_base())
    assert len(conds) > 0
    # All conditions have name strings
    assert all(isinstance(c.name, str) and c.name for c in conds)


# ---------------------------------------------------------------------------
# Unit contract — the defect this file used to hide (capability atlas D-1)
# ---------------------------------------------------------------------------

def test_hy_oas_is_read_in_percent_like_the_stored_fred_series() -> None:
    """The credit legs must fire on the scale the ingest actually stores.

    FRED BAMLH0A0HYM2 is published in percent and stored unscaled, so a live
    reading looks like 2.70, not 270. v1.0's thresholds were 450 / 600 (basis
    points) against that input, which made both credit conditions unfireable
    and left the regime breadth-and-AVIX-only in production. This test is
    mutation-sensitive in the direction that matters: restore the bp scale and
    the stress case below stops firing.
    """
    calm = classify({**_base(), "avix": Decimal("12"), "us_hy_oas": Decimal("2.70")})
    assert calm[0] != RegimeLabel.risk_off_disorderly
    assert not any(c.name.startswith("hy_oas") and c.fired for c in calm[1])

    # A 2008-shaped spread (ICE BofA HY OAS peaked near 20 % in Nov 2008) must
    # read as credit stress on its own, whatever AVIX is doing.
    stress = classify({**_base(), "avix": Decimal("12"), "us_hy_oas": Decimal("20.00")})
    assert stress[0] == RegimeLabel.risk_off_disorderly
    assert any(c.name == "hy_oas_stress" and c.fired for c in stress[1])

    # And every credit threshold the classifier reports must be on that scale.
    for c in stress[1]:
        if c.name.startswith("hy_oas"):
            assert c.threshold is not None and c.threshold < Decimal("100"), c
