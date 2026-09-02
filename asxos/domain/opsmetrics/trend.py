"""Robust duration-trend detection: trailing median + MAD.

**Why median and MAD rather than mean and stddev.** The duration series here is
short, right-skewed, and outlier-heavy: one retry doubles a run, one cold cache
triples it, and jobs run at most once per ``as_of``. A mean is dragged by a single
bad run and a stddev computed from that same run then widens until nothing looks
anomalous — the estimator hides the very event it should flag. Median and MAD both
have a 50% breakdown point, so half the sample can be garbage before the estimate
moves.

**What this can and cannot detect.** It detects *sustained* shifts — a job that got
slower and stayed slower. It deliberately cannot detect a single slow run, because on
shared CI infrastructure a single slow run carries no information. Anyone wanting a
5% regression gate on ephemeral runners is building a noise generator; the thresholds
here are coarse on purpose.

**Only successful runs are compared.** A ``failure`` or ``blocked`` run's duration is
however long it took to crash or to notice upstream was not ready — including it
would let a fast failure read as a performance improvement. ``duration_trend``
filters on status, so callers can pass rows straight from the table.

**Scope honesty.** ``job_runs.duration_ms`` measures the job body (what ``JobMonitor``
wraps), not the workflow — so it excludes ``pip install``, which dominates CI
wall-clock. For ingestion jobs it is mostly upstream network I/O, so a regression here
often means *the API got slower*, not *our code got slower*. That is still worth
knowing, but it is not by itself a reason to optimise anything.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

SUCCESS_STATUS = "success"

#: Scales MAD to be comparable with a standard deviation under normality. Durations
#: are not normal, so treat the resulting z as an ordering heuristic, not a p-value.
#: The ratio gate below is the primary signal; z only suppresses noise on jobs whose
#: durations are naturally jumpy.
MAD_TO_SIGMA = Decimal("1.4826")

DEFAULT_RECENT_WINDOW = 5
DEFAULT_MIN_BASELINE = 10
#: 1.5x slower. Coarse because CI runners vary 20-50% run to run.
DEFAULT_RATIO_THRESHOLD = Decimal("1.5")
DEFAULT_ROBUST_Z_THRESHOLD = Decimal("3")


class Verdict(str, Enum):
    OK = "ok"
    REGRESSED = "regressed"
    IMPROVED = "improved"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class Sample:
    """One recorded run. ``duration_ms`` may be NULL in the table, hence optional."""

    as_of: date
    duration_ms: int | None
    status: str = SUCCESS_STATUS


@dataclass(frozen=True)
class TrendResult:
    job_name: str
    verdict: Verdict
    #: Successful runs with a recorded duration. Reported separately from the
    #: baseline/recent split because on INSUFFICIENT_DATA there is no split yet,
    #: and reusing those two fields to mean "what the split would have been" reads
    #: as a real comparison that never happened.
    n_usable: int
    n_baseline: int
    n_recent: int
    baseline_median_ms: Decimal | None = None
    recent_median_ms: Decimal | None = None
    mad_ms: Decimal | None = None
    ratio: Decimal | None = None
    robust_z: Decimal | None = None
    note: str = ""

    @property
    def is_actionable(self) -> bool:
        """True only for a REGRESSED verdict — the one a perf lane may act on."""
        return self.verdict is Verdict.REGRESSED


def median(values: Sequence[Decimal]) -> Decimal:
    """Median of a non-empty sequence. Even counts average the middle pair."""
    if not values:
        raise ValueError("median of empty sequence")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal(2)


def mad(values: Sequence[Decimal], center: Decimal | None = None) -> Decimal:
    """Median absolute deviation about ``center`` (default: the sample median).

    Zero is a legitimate result — it means over half the sample is identical, which
    happens for fast deterministic jobs. Callers must not divide by it blindly;
    ``duration_trend`` falls back to the ratio gate alone in that case.
    """
    if not values:
        raise ValueError("mad of empty sequence")
    mid = median(values) if center is None else center
    return median([abs(v - mid) for v in values])


def _usable(samples: Iterable[Sample]) -> list[Sample]:
    return [s for s in samples if s.status == SUCCESS_STATUS and s.duration_ms is not None]


def duration_trend(
    job_name: str,
    samples: Iterable[Sample],
    *,
    recent_window: int = DEFAULT_RECENT_WINDOW,
    min_baseline: int = DEFAULT_MIN_BASELINE,
    ratio_threshold: Decimal = DEFAULT_RATIO_THRESHOLD,
    z_threshold: Decimal = DEFAULT_ROBUST_Z_THRESHOLD,
) -> TrendResult:
    """Compare the most recent ``recent_window`` successful runs against the rest.

    Samples may arrive in any order; they are sorted by ``as_of`` internally so a
    caller's ``ORDER BY`` cannot silently invert the comparison.

    A REGRESSED verdict requires **both** gates: the median ratio clears
    ``ratio_threshold`` *and* the shift clears ``z_threshold`` in MAD units. The ratio
    alone would flag jobs that are naturally jumpy; the z alone would flag a
    statistically clean but operationally irrelevant 3% shift on a very stable job.
    Requiring both is what keeps the output small enough to be read.
    """
    usable = sorted(_usable(samples), key=lambda s: s.as_of)

    if len(usable) < min_baseline + recent_window:
        return TrendResult(
            job_name=job_name,
            verdict=Verdict.INSUFFICIENT_DATA,
            n_usable=len(usable),
            n_baseline=0,
            n_recent=0,
            note=(
                f"need {min_baseline + recent_window} successful runs, have {len(usable)}. "
                "Report and stop — never patch on a baseline this thin."
            ),
        )

    # `_usable` has already dropped None durations. Do NOT re-filter on truthiness
    # here: a legitimately 0 ms run is falsy, and dropping it silently shrinks the
    # sample — which then reads as a smaller-but-confident baseline rather than as
    # missing data.
    baseline_vals = [
        Decimal(s.duration_ms) for s in usable[:-recent_window] if s.duration_ms is not None
    ]
    recent_vals = [
        Decimal(s.duration_ms) for s in usable[-recent_window:] if s.duration_ms is not None
    ]

    base_med = median(baseline_vals)
    recent_med = median(recent_vals)
    dispersion = mad(baseline_vals, base_med)

    if base_med == 0:
        return TrendResult(
            job_name=job_name,
            verdict=Verdict.INSUFFICIENT_DATA,
            n_usable=len(usable),
            n_baseline=len(baseline_vals),
            n_recent=len(recent_vals),
            baseline_median_ms=base_med,
            recent_median_ms=recent_med,
            mad_ms=dispersion,
            note="baseline median is 0 ms — ratio undefined; the job is too fast to time here.",
        )

    ratio = recent_med / base_med

    robust_z: Decimal | None = None
    if dispersion > 0:
        robust_z = (recent_med - base_med) / (MAD_TO_SIGMA * dispersion)

    # MAD of 0 means the baseline is essentially constant, so z is undefined
    # (not infinite). Fall back to the ratio gate rather than inventing a z.
    z_ok_slower = robust_z is None or robust_z >= z_threshold
    z_ok_faster = robust_z is None or robust_z <= -z_threshold

    if ratio >= ratio_threshold and z_ok_slower:
        verdict = Verdict.REGRESSED
        note = f"median {base_med} ms -> {recent_med} ms ({ratio:.2f}x) over {recent_window} runs"
    elif ratio_threshold > 1 and ratio <= (Decimal(1) / ratio_threshold) and z_ok_faster:
        verdict = Verdict.IMPROVED
        note = f"median {base_med} ms -> {recent_med} ms ({ratio:.2f}x) over {recent_window} runs"
    else:
        verdict = Verdict.OK
        note = f"within tolerance ({ratio:.2f}x)"

    return TrendResult(
        job_name=job_name,
        verdict=verdict,
        n_usable=len(usable),
        n_baseline=len(baseline_vals),
        n_recent=len(recent_vals),
        baseline_median_ms=base_med,
        recent_median_ms=recent_med,
        mad_ms=dispersion,
        ratio=ratio,
        robust_z=robust_z,
        note=note,
    )
