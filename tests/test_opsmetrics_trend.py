"""Tests for asxos.domain.opsmetrics.trend.

The properties worth pinning are the ones that make this usable as evidence for a
standing perf lane: that a single outlier does NOT move the verdict (the reason for
median/MAD over mean/stddev), that failed runs are excluded (a fast crash must not
read as an improvement), and that a thin baseline returns INSUFFICIENT_DATA rather
than a confident-looking number.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from asxos.domain.opsmetrics import (
    Sample,
    Verdict,
    duration_trend,
    mad,
    median,
)

START = date(2026, 1, 1)


def series(durations: list[int | None], statuses: list[str] | None = None) -> list[Sample]:
    stats = statuses or ["success"] * len(durations)
    return [
        Sample(as_of=START + timedelta(days=i), duration_ms=d, status=s)
        for i, (d, s) in enumerate(zip(durations, stats, strict=True))
    ]


# --- primitives ------------------------------------------------------------


def test_median_odd_and_even() -> None:
    assert median([Decimal(3), Decimal(1), Decimal(2)]) == Decimal(2)
    assert median([Decimal(1), Decimal(2), Decimal(3), Decimal(4)]) == Decimal("2.5")


def test_median_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        median([])


def test_mad_of_constant_series_is_zero() -> None:
    assert mad([Decimal(5)] * 7) == Decimal(0)


def test_mad_is_not_moved_by_one_extreme_value() -> None:
    """The whole reason for MAD: 50% breakdown point."""
    base = [Decimal(10)] * 10
    assert mad([*base, Decimal(100000)]) == Decimal(0)


# --- verdicts --------------------------------------------------------------


def test_insufficient_data_when_baseline_too_thin() -> None:
    got = duration_trend("j", series([100] * 8))
    assert got.verdict is Verdict.INSUFFICIENT_DATA
    assert got.ratio is None
    assert "never patch" in got.note


def test_stable_series_is_ok() -> None:
    got = duration_trend("j", series([100, 105, 95, 100, 102, 98, 101, 99, 103, 97] + [100] * 5))
    assert got.verdict is Verdict.OK
    assert got.ratio is not None and got.ratio < Decimal("1.5")


def test_sustained_slowdown_is_regressed() -> None:
    got = duration_trend("j", series([100, 105, 95, 100, 102, 98, 101, 99, 103, 97] + [300] * 5))
    assert got.verdict is Verdict.REGRESSED
    assert got.is_actionable
    assert got.ratio is not None and got.ratio >= Decimal("1.5")


def test_sustained_speedup_is_improved() -> None:
    got = duration_trend(
        "j", series([300, 310, 290, 300, 305, 295, 302, 298, 301, 299] + [100] * 5)
    )
    assert got.verdict is Verdict.IMPROVED
    assert not got.is_actionable


def test_single_spike_inside_the_recent_window_does_not_regress() -> None:
    """One slow run on shared CI carries no information; the median must absorb it."""
    got = duration_trend(
        "j", series([100, 105, 95, 100, 102, 98, 101, 99, 103, 97, 100, 100, 9000, 100, 100])
    )
    assert got.verdict is Verdict.OK


def test_single_spike_in_the_baseline_does_not_mask_a_real_regression() -> None:
    """A mean/stddev baseline would widen around the spike and hide the shift."""
    got = duration_trend("j", series([100, 105, 95, 100, 9000, 98, 101, 99, 103, 97] + [400] * 5))
    assert got.verdict is Verdict.REGRESSED


# --- data hygiene ----------------------------------------------------------


def test_failed_runs_are_excluded() -> None:
    """A fast crash must never read as a performance improvement."""
    durations = [300] * 10 + [5] * 5
    statuses = ["success"] * 10 + ["failure"] * 5
    got = duration_trend("j", series(durations, statuses))
    assert got.verdict is Verdict.INSUFFICIENT_DATA
    assert got.n_usable == 10
    assert got.verdict is not Verdict.IMPROVED


def test_insufficient_data_reports_no_split() -> None:
    """There is no baseline/recent comparison yet, so those counts must read 0."""
    got = duration_trend("j", series([100] * 8))
    assert (got.n_usable, got.n_baseline, got.n_recent) == (8, 0, 0)


def test_blocked_runs_are_excluded() -> None:
    """'blocked' is upstream-not-ready or the rule #11 model gate — not a timing signal."""
    durations = [300] * 12 + [4] * 5
    statuses = ["success"] * 12 + ["blocked"] * 5
    got = duration_trend("j", series(durations, statuses))
    assert got.verdict is Verdict.INSUFFICIENT_DATA


def test_null_durations_are_skipped() -> None:
    got = duration_trend("j", series([None] * 5 + [100] * 10))
    assert got.verdict is Verdict.INSUFFICIENT_DATA


def test_unordered_input_is_sorted_before_comparison() -> None:
    """A caller's ORDER BY must not be able to invert baseline and recent."""
    ordered = series([100] * 10 + [400] * 5)
    shuffled = [ordered[i] for i in (14, 0, 7, 3, 11, 1, 9, 5, 13, 2, 8, 4, 12, 6, 10)]
    assert duration_trend("j", shuffled).verdict is Verdict.REGRESSED


def test_zero_baseline_median_is_insufficient_not_a_divide_error() -> None:
    got = duration_trend("j", series([0] * 10 + [50] * 5))
    assert got.verdict is Verdict.INSUFFICIENT_DATA
    assert "too fast to time" in got.note


def test_constant_baseline_uses_ratio_gate_without_inventing_a_z() -> None:
    """MAD of 0 makes z undefined, not infinite."""
    got = duration_trend("j", series([100] * 10 + [400] * 5))
    assert got.verdict is Verdict.REGRESSED
    assert got.mad_ms == Decimal(0)
    assert got.robust_z is None


def test_statistically_clean_but_tiny_shift_is_not_flagged() -> None:
    """Both gates must clear; a 3% shift on a very stable job is not actionable."""
    got = duration_trend("j", series([100] * 10 + [103] * 5))
    assert got.verdict is Verdict.OK
