"""Tests for thesis trajectory math (asxos/domain/theses/trajectory.py).

Pure Decimal. Covers progress/expectation primitives and the full classification
priority order (STOP_VIOLATED > ABOVE_TARGET > pace bands).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from asxos.domain.theses.trajectory import (
    Trajectory,
    classify_trajectory,
    linear_expectation,
    progress_to_target,
)

# --- progress_to_target ----------------------------------------------------

def test_progress_halfway() -> None:
    assert progress_to_target(Decimal("45"), Decimal("40"), Decimal("50")) == Decimal("0.5")


def test_progress_past_target_exceeds_one() -> None:
    assert progress_to_target(Decimal("52"), Decimal("40"), Decimal("50")) > Decimal("1")


def test_progress_wrong_way_is_negative() -> None:
    assert progress_to_target(Decimal("38"), Decimal("40"), Decimal("50")) < Decimal("0")


def test_progress_zero_span_raises() -> None:
    with pytest.raises(ValueError, match="no journey"):
        progress_to_target(Decimal("45"), Decimal("50"), Decimal("50"))


# --- linear_expectation ----------------------------------------------------

def test_linear_expectation_midpoint() -> None:
    assert linear_expectation(180, 360) == Decimal("0.5")


def test_linear_expectation_clamps_over_one() -> None:
    assert linear_expectation(400, 360) == Decimal("1")


def test_linear_expectation_clamps_negative() -> None:
    assert linear_expectation(-10, 360) == Decimal("0")


def test_linear_expectation_zero_timeline_raises() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        linear_expectation(10, 0)


# --- classify_trajectory ---------------------------------------------------

def _classify(current, anchor=Decimal("40"), target=Decimal("50"),
              stop=Decimal("36"), elapsed=180, timeline=360):
    return classify_trajectory(
        current_price=Decimal(str(current)), anchor=anchor, target_price=target,
        stop_price=stop, elapsed_days=elapsed, timeline_days=timeline,
    )


def test_stop_violated_takes_priority() -> None:
    # At/below stop → STOP_VIOLATED even though other conditions could apply.
    assert _classify("36", stop=Decimal("36")) == Trajectory.STOP_VIOLATED
    assert _classify("35", stop=Decimal("36")) == Trajectory.STOP_VIOLATED


def test_above_target() -> None:
    assert _classify("50") == Trajectory.ABOVE_TARGET
    assert _classify("55") == Trajectory.ABOVE_TARGET


def test_on_track_at_pace() -> None:
    # progress 0.6 ≥ expected 0.5 → ON TRACK
    assert _classify("46", elapsed=180, timeline=360) == Trajectory.ON_TRACK


def test_stalled_barely_moved_late() -> None:
    # progress 0.02 < 0.05, expected 0.555 > 0.4 → STALLED
    assert _classify("40.2", elapsed=200, timeline=360) == Trajectory.STALLED


def test_behind_half_pace_past_midpoint() -> None:
    # progress 0.2 < expected/2 (0.416), expected 0.833 > 0.5 → BEHIND
    assert _classify("42", elapsed=300, timeline=360) == Trajectory.BEHIND


def test_null_stop_never_violated() -> None:
    # No stop set → cannot be STOP_VIOLATED; falls through to pace bands.
    assert _classify("45", stop=None, elapsed=180, timeline=360) == Trajectory.ON_TRACK


def test_ahead_of_pace_before_midpoint_on_track() -> None:
    # progress 0.3 ≥ expected 0.277 (early) → ON TRACK
    assert _classify("43", elapsed=100, timeline=360) == Trajectory.ON_TRACK
