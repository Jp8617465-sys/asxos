"""Breaker registry evaluation. Missing or stale telemetry trips."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_DEFAULT = Path(__file__).resolve().parents[1] / "registries" / "breaker-registry.json"


@dataclass(frozen=True)
class BreakerRule:
    workflow: str
    metric: str
    threshold: str
    window: str
    evidence_query: str


@dataclass(frozen=True)
class TelemetryPoint:
    workflow: str
    metric: str
    value: float
    stale: bool
    missing: bool = False


@dataclass(frozen=True)
class BreakerDecision:
    trip: bool
    reason: str
    workflow: str | None
    next_state: str


def load_registry(path: Path | None = None) -> tuple[BreakerRule, ...]:
    raw = json.loads((path or _DEFAULT).read_text(encoding="utf-8"))
    rules = []
    for item in raw["workflows"]:
        required = ("workflow", "metric", "threshold", "window", "evidence_query")
        if any(not item.get(key) for key in required):
            raise ValueError(f"malformed breaker rule: {item!r}")
        rules.append(
            BreakerRule(
                workflow=item["workflow"],
                metric=item["metric"],
                threshold=item["threshold"],
                window=item["window"],
                evidence_query=item["evidence_query"],
            )
        )
    if not rules:
        raise ValueError("breaker registry is empty")
    return tuple(rules)


def _threshold_breached(rule: BreakerRule, point: TelemetryPoint) -> bool:
    if rule.metric != point.metric:
        return True
    if rule.threshold.startswith(">="):
        return point.value >= float(rule.threshold[2:])
    if rule.threshold.startswith(">"):
        return point.value > float(rule.threshold[1:])
    if rule.threshold == "nonzero":
        return point.value != 0
    raise ValueError(f"unsupported threshold {rule.threshold!r}")


def evaluate_breaker(
    registry: tuple[BreakerRule, ...],
    telemetry: dict[str, TelemetryPoint],
) -> BreakerDecision:
    for rule in registry:
        point = telemetry.get(rule.workflow)
        if point is None or point.missing:
            return BreakerDecision(True, "missing_telemetry", rule.workflow, "ATTENDED")
        if point.stale:
            return BreakerDecision(True, "stale_telemetry", rule.workflow, "ATTENDED")
        if _threshold_breached(rule, point):
            return BreakerDecision(True, "threshold_exceeded", rule.workflow, "ATTENDED")
    return BreakerDecision(False, "clean", None, "STANDING")
