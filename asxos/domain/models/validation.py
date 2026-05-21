"""
Model A retraining gates.

Three independent gates per ml-conventions.md and BUILD_GUIDE M9:
  - MIN_ROC_AUC          (default 0.65)
  - MAX_DEGRADATION_PCT  (default 0.05 of the active baseline AUC)
  - MIN_TRAINING_SAMPLES (default 1000)

All three must pass for a new model to be considered for activation. The
ROC AUC values are read from the active row in `model_versions` (the
trainer writes the candidate row with `is_active=FALSE`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_MIN_ROC_AUC = 0.65
DEFAULT_MAX_DEGRADATION_PCT = 0.05
DEFAULT_MIN_TRAINING_SAMPLES = 1000


@dataclass(frozen=True)
class ValidationResult:
    auc: float
    samples: int
    baseline_auc: float | None
    degradation_pct: float | None
    passed: bool
    reasons: list[str] = field(default_factory=list)


def evaluate_gates(
    auc: float,
    samples: int,
    baseline_auc: float | None = None,
    *,
    min_auc: float = DEFAULT_MIN_ROC_AUC,
    max_degradation_pct: float = DEFAULT_MAX_DEGRADATION_PCT,
    min_samples: int = DEFAULT_MIN_TRAINING_SAMPLES,
) -> ValidationResult:
    """Returns a ValidationResult with passed=True iff every gate is satisfied."""
    reasons: list[str] = []

    if auc < min_auc:
        reasons.append(f"AUC {auc:.4f} below floor {min_auc:.4f}")
    if samples < min_samples:
        reasons.append(f"samples {samples} below floor {min_samples}")

    degradation_pct: float | None = None
    if baseline_auc is not None and baseline_auc > 0:
        degradation_pct = (baseline_auc - auc) / baseline_auc
        if degradation_pct > max_degradation_pct:
            reasons.append(
                f"degradation {degradation_pct:.2%} exceeds ceiling "
                f"{max_degradation_pct:.2%}"
            )

    return ValidationResult(
        auc=auc,
        samples=samples,
        baseline_auc=baseline_auc,
        degradation_pct=degradation_pct,
        passed=not reasons,
        reasons=reasons,
    )
