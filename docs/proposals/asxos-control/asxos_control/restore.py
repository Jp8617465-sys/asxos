"""Restore evidence gate. The third restore in seven days is refused."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RestoreEvidence:
    fix_merged: bool
    required_checks_green: bool
    clean_minutes: int
    incident_updated: bool
    restores_in_last_7_days: int
    operational_trip: bool = True


@dataclass(frozen=True)
class RestoreDecision:
    allow: bool
    reason: str
    next_state: str | None


def evaluate_restore(evidence: RestoreEvidence) -> RestoreDecision:
    if evidence.restores_in_last_7_days >= 2:
        return RestoreDecision(False, "third_restore_refused", None)
    if not evidence.operational_trip:
        return RestoreDecision(False, "integrity_trip_owner_only", None)
    if not evidence.fix_merged:
        return RestoreDecision(False, "fix_not_merged", None)
    if not evidence.required_checks_green:
        return RestoreDecision(False, "required_checks_not_green", None)
    if evidence.clean_minutes < 60:
        return RestoreDecision(False, "clean_window_below_60m", None)
    if not evidence.incident_updated:
        return RestoreDecision(False, "incident_not_updated", None)
    return RestoreDecision(True, "restore_evidence_complete", "STANDING")
