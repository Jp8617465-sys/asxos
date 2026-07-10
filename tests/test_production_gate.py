"""Tests for the contamination-isolation gate (``resolve_production_model``).

The gate is the single source of the 0/>1-approved-model semantics.
``required=True`` (default) hard-fails — the allocator's capital-safety invariant
and rule #11's real enforcement point (``build.py``). ``required=False`` returns
``None`` for display-only brief consumers, so a Model A quarantine does not
hard-fail the model-independent brief (risk-register R9).
"""
from __future__ import annotations

import pytest

from asxos.domain.models.production_gate import resolve_production_model


def test_required_default_raises_on_zero() -> None:
    with pytest.raises(RuntimeError, match="approved_for_allocation"):
        resolve_production_model([])


def test_required_default_raises_on_multiple() -> None:
    with pytest.raises(RuntimeError, match="multiple models"):
        resolve_production_model([{"model": "model_a"}, {"model": "factor_sleeve"}])


def test_required_true_explicit_raises_on_zero() -> None:
    with pytest.raises(RuntimeError, match="approved_for_allocation"):
        resolve_production_model([], required=True)


def test_required_false_returns_none_on_zero() -> None:
    assert resolve_production_model([], required=False) is None


def test_required_false_returns_none_on_multiple() -> None:
    assert (
        resolve_production_model(
            [{"model": "model_a"}, {"model": "factor_sleeve"}], required=False
        )
        is None
    )


def test_returns_name_on_exactly_one_regardless_of_required() -> None:
    rows = [{"model": "model_a"}]
    assert resolve_production_model(rows) == "model_a"
    assert resolve_production_model(rows, required=True) == "model_a"
    assert resolve_production_model(rows, required=False) == "model_a"
