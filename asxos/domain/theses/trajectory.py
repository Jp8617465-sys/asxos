"""Thesis trajectory math — is a holding on pace to hit its target in time?

Pure Decimal, no DB, no numpy (portfolio conventions). Consumed by the
thesis-milestone-monitor agent, which reads `theses` + `prices` and reports;
the classification logic lives here so it is testable and consistent.

A thesis has an entry anchor (actual_entry_price, or cost_base_normal/quantity),
a target_price, a stop_price, an opened_at date, and a timeline_days budget. The
question is whether price progress toward the target is keeping pace with elapsed
time — distinct from the brief's active_theses collector, which only checks
revisit-overdue and timeline-expiry (the deadline), not mid-timeline pace.
"""
from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class Trajectory(StrEnum):
    """Mid-timeline pace classification (plus the two terminal price states)."""

    ON_TRACK = "ON TRACK"
    BEHIND = "BEHIND"
    STALLED = "STALLED"
    STOP_VIOLATED = "STOP VIOLATED"
    ABOVE_TARGET = "ABOVE TARGET"


def progress_to_target(
    current_price: Decimal, anchor: Decimal, target_price: Decimal
) -> Decimal:
    """Fraction of the anchor→target journey covered, as a Decimal.

    `(current − anchor) / (target − anchor)`. 0 = still at the anchor, 1 = at the
    target, >1 = past it, <0 = moved the wrong way. Raises ``ValueError`` when
    `target == anchor` (no journey to measure — a malformed thesis).
    """
    span = target_price - anchor
    if span == 0:
        raise ValueError("target_price equals the anchor — no journey to measure")
    return (current_price - anchor) / span


def linear_expectation(elapsed_days: int, timeline_days: int) -> Decimal:
    """Where a perfectly-paced thesis would be by now: `elapsed / timeline`.

    Clamped to [0, 1]. Raises ``ValueError`` when `timeline_days <= 0` (a thesis
    with no timeline budget can't have a pace expectation).
    """
    if timeline_days <= 0:
        raise ValueError("timeline_days must be positive")
    frac = Decimal(elapsed_days) / Decimal(timeline_days)
    if frac < 0:
        return Decimal("0")
    if frac > 1:
        return Decimal("1")
    return frac


def classify_trajectory(
    *,
    current_price: Decimal,
    anchor: Decimal,
    target_price: Decimal,
    stop_price: Decimal | None,
    elapsed_days: int,
    timeline_days: int,
) -> Trajectory:
    """Classify a thesis's price trajectory.

    Priority order (highest first): STOP_VIOLATED, ABOVE_TARGET, then the
    pace bands STALLED / BEHIND / ON_TRACK. The terminal price states take
    precedence because they call for action (close/realise or stop-out)
    regardless of pace. A NULL `stop_price` means no stop is set — it simply
    can't be violated (the caller surfaces "no stop set" separately).
    """
    if stop_price is not None and current_price <= stop_price:
        return Trajectory.STOP_VIOLATED
    if current_price >= target_price:
        return Trajectory.ABOVE_TARGET

    progress = progress_to_target(current_price, anchor, target_price)
    expected = linear_expectation(elapsed_days, timeline_days)

    # STALLED: almost no progress well into the timeline.
    if expected > Decimal("0.4") and progress < Decimal("0.05"):
        return Trajectory.STALLED
    # BEHIND: less than half the expected pace, past the timeline midpoint.
    if expected > Decimal("0.5") and progress < expected / 2:
        return Trajectory.BEHIND
    if progress >= expected:
        return Trajectory.ON_TRACK
    # Between half-pace and full-pace, before the midpoint → not yet BEHIND.
    return Trajectory.ON_TRACK if progress >= expected / 2 else Trajectory.BEHIND
