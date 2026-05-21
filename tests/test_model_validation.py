"""
Gate-evaluation tests for asxos.domain.models.validation.

Boundaries:
  - AUC must clear MIN_ROC_AUC (default 0.65).
  - samples must clear MIN_TRAINING_SAMPLES (default 1000).
  - degradation vs baseline must not exceed MAX_DEGRADATION_PCT (default 5%).
"""
from __future__ import annotations

from asxos.domain.models.validation import (
    DEFAULT_MAX_DEGRADATION_PCT,
    DEFAULT_MIN_ROC_AUC,
    DEFAULT_MIN_TRAINING_SAMPLES,
    evaluate_gates,
)


def test_passes_when_all_gates_clear() -> None:
    r = evaluate_gates(auc=0.71, samples=10_000, baseline_auc=0.70)
    assert r.passed is True
    assert r.reasons == []
    assert r.degradation_pct is not None
    assert r.degradation_pct < 0  # improvement


def test_fails_when_auc_below_floor() -> None:
    r = evaluate_gates(auc=DEFAULT_MIN_ROC_AUC - 0.01, samples=10_000, baseline_auc=None)
    assert r.passed is False
    assert any("AUC" in reason for reason in r.reasons)


def test_fails_when_samples_below_floor() -> None:
    r = evaluate_gates(auc=0.71, samples=DEFAULT_MIN_TRAINING_SAMPLES - 1, baseline_auc=None)
    assert r.passed is False
    assert any("samples" in reason for reason in r.reasons)


def test_fails_when_degradation_exceeds_ceiling() -> None:
    # baseline 0.70, candidate 0.65 → degradation ~7.1% > 5%
    r = evaluate_gates(auc=0.65, samples=10_000, baseline_auc=0.70)
    assert r.passed is False
    assert any("degradation" in reason for reason in r.reasons)


def test_passes_when_no_baseline_supplied() -> None:
    # First-ever training run: degradation gate is N/A
    r = evaluate_gates(auc=0.66, samples=2_000, baseline_auc=None)
    assert r.passed is True


def test_collects_multiple_reasons() -> None:
    r = evaluate_gates(auc=0.50, samples=10, baseline_auc=0.70)
    assert r.passed is False
    # Three failures: AUC, samples, degradation
    assert len(r.reasons) == 3


def test_boundary_at_min_auc_passes() -> None:
    r = evaluate_gates(auc=DEFAULT_MIN_ROC_AUC, samples=1500, baseline_auc=None)
    assert r.passed is True


def test_boundary_at_min_samples_passes() -> None:
    r = evaluate_gates(auc=0.70, samples=DEFAULT_MIN_TRAINING_SAMPLES, baseline_auc=None)
    assert r.passed is True


def test_boundary_at_max_degradation_passes() -> None:
    # Degradation slightly below the ceiling — must pass (gate is strict `>`).
    # Using a baseline that produces a clean 4.99% degradation in float math.
    r = evaluate_gates(auc=0.66501, samples=10_000, baseline_auc=0.70)
    assert r.passed is True
    assert r.degradation_pct is not None
    assert r.degradation_pct < DEFAULT_MAX_DEGRADATION_PCT


def test_zero_baseline_is_ignored() -> None:
    # Defensive: baseline = 0 shouldn't divide by zero
    r = evaluate_gates(auc=0.70, samples=10_000, baseline_auc=0.0)
    assert r.passed is True
    assert r.degradation_pct is None
