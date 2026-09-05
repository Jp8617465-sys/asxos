"""ThemeVersion and CandidateSnapshot — evidence, never a recommendation.

Both reuse the decision engine's `ContentAddressedContract` (frozen, float-
free, UTC-only, SHA-256 self-verifying) and its `EvidenceItem`, so a
candidate's evidence can later be lifted into an `EvidencePacket` unchanged.

The Stage 3 gate says "without converting either into a recommendation". That
is enforced here, not promised: `_reject_recommendation_keys` refuses any
measure or quality-check key that names an action, weight, size, target,
score-to-act-on or verdict. There is no field for one either.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from asxos.domain.decision_engine.types import (
    ContentAddressedContract,
    DataMode,
    EvidenceItem,
)

QualityOutcome = Literal["pass", "fail", "unknown"]
MeasureValue = str | int | None  # decimal strings, counts, or absent — never float

_RECOMMENDATION_RE: Final = re.compile(
    r"recommend|verdict|action|\bbuy\b|\bsell\b|overweight|underweight|"
    r"\bweight\b|\bsize\b|position|target_price|price_target|allocation|"
    r"conviction_to_act|signal_label|prob_up",
    re.IGNORECASE,
)
THEME_EXPIRY_DAYS: Final[int] = 30
CANDIDATE_EXPIRY_DAYS: Final[int] = 30
EXPIRY_RULE: Final[str] = (
    "30 calendar days from knowledge_cutoff (Stage 3 draft rule; F3 session-"
    "calendar wiring is the decision engine's, applied when a candidate is lifted)"
)


def _reject_recommendation_keys(mapping: dict[str, object], *, where: str) -> None:
    for key in mapping:
        # underscores are word characters to `re`, so `buy_signal` would slip
        # past `\bbuy\b` unless the key is split into words first
        if _RECOMMENDATION_RE.search(key) or _RECOMMENDATION_RE.search(key.replace("_", " ")):
            raise ValueError(
                f"{where} key {key!r} names a recommendation-shaped quantity; "
                "Stage 3 artifacts are evidence and may not carry one"
            )


def _reject_floats(mapping: dict[str, object], *, where: str) -> None:
    for key, value in mapping.items():
        if isinstance(value, float):
            raise ValueError(f"{where}[{key!r}] is a float; encode as a decimal string")


def default_expiry(cutoff: datetime, *, days: int) -> datetime:
    return cutoff + timedelta(days=days)


class ThemeVersion(ContentAddressedContract):
    """A governed theme, measured at one knowledge cutoff."""

    theme_version_id: str = Field(min_length=1, max_length=200)
    theme_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=10_000)
    conviction_band: Literal["low", "medium", "high"]
    stage: str = Field(min_length=1, max_length=40)
    macro_thesis_id: int | None = None
    regime_quadrant: str | None = None
    members: tuple[str, ...] = Field(min_length=1, max_length=500)
    measures: dict[str, MeasureValue]
    as_of: date
    knowledge_cutoff: datetime
    expires_at: datetime
    expiry_rule: str = EXPIRY_RULE
    evidence: tuple[EvidenceItem, ...] = Field(min_length=1, max_length=500)
    data_mode: DataMode
    source: Literal["governed_theme"] = "governed_theme"
    created_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> Self:
        _reject_recommendation_keys(dict(self.measures), where="ThemeVersion.measures")
        _reject_floats(dict(self.measures), where="ThemeVersion.measures")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("as_of must equal the UTC knowledge_cutoff date")
        if not self.knowledge_cutoff <= self.created_at < self.expires_at:
            raise ValueError("created_at must be within cutoff and expiry")
        late = [e.evidence_id for e in self.evidence if e.known_at > self.knowledge_cutoff]
        if late:
            raise ValueError(f"evidence known after cutoff: {late}")
        if len({e.evidence_id for e in self.evidence}) != len(self.evidence):
            raise ValueError("evidence_id values must be unique")
        if any(e.data_mode != self.data_mode for e in self.evidence):
            raise ValueError("evidence data_mode differs from the theme version")
        return self


class CandidateSnapshot(ContentAddressedContract):
    """One security under one ThemeVersion at one cutoff. Evidence only."""

    candidate_id: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=40)
    theme_version_id: str = Field(min_length=1, max_length=200)
    theme_code: str = Field(min_length=1, max_length=100)
    exposure_direction: Literal["positive", "negative"]
    measures: dict[str, MeasureValue]
    quality_checks: dict[str, QualityOutcome]
    as_of: date
    knowledge_cutoff: datetime
    expires_at: datetime
    expiry_rule: str = EXPIRY_RULE
    evidence: tuple[EvidenceItem, ...] = Field(min_length=1, max_length=500)
    data_mode: DataMode
    created_at: datetime
    not_a_recommendation: Literal[True] = True

    @property
    def quality_passed(self) -> bool:
        return bool(self.quality_checks) and all(v == "pass" for v in self.quality_checks.values())

    @model_validator(mode="after")
    def _validate(self) -> Self:
        _reject_recommendation_keys(dict(self.measures), where="CandidateSnapshot.measures")
        _reject_recommendation_keys(dict(self.quality_checks), where="CandidateSnapshot.quality_checks")
        _reject_floats(dict(self.measures), where="CandidateSnapshot.measures")
        if not self.quality_checks:
            raise ValueError("a candidate must carry at least one quality check")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("as_of must equal the UTC knowledge_cutoff date")
        if not self.knowledge_cutoff <= self.created_at < self.expires_at:
            raise ValueError("created_at must be within cutoff and expiry")
        late = [e.evidence_id for e in self.evidence if e.known_at > self.knowledge_cutoff]
        if late:
            raise ValueError(f"evidence known after cutoff: {late}")
        if len({e.evidence_id for e in self.evidence}) != len(self.evidence):
            raise ValueError("evidence_id values must be unique")
        if any(e.data_mode != self.data_mode for e in self.evidence):
            raise ValueError("evidence data_mode differs from the candidate")
        return self
