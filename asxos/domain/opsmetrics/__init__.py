"""Operational timing metrics — trend detection over the durations jobs already emit.

**The gap this closes.** The repo emits per-run timing in three places and reads it
in none: ``job_runs.duration_ms`` (every job x every ``as_of``, since migration
0001), ``brief_runs.section_runs`` (12 brief collectors, each with ``elapsed_ms``),
and ``screening_runs.duration_ms``. Emission was never the problem; aggregation was.
Without it, ``security-perf-mission-loop.md`` §4's requirement that perf findings be
*"measured hot-path impact, never speculative"* had no producer, so the standing perf
lane could only emit silence or speculation.

**Leaf package.** Pure functions over rows — rows in, verdicts out. Imports nothing
from ``asxos.domain.{brief,portfolio,tax,models,theses}``; those may import this,
never the reverse. That keeps it usable from a script, a job, and a future brief
collector without a cycle, and it keeps this module testable with no database.

**Decimal, not float** — repo convention for statistical values (CLAUDE.md
non-negotiable #5), and it keeps threshold comparisons exact rather than
representation-dependent.
"""

from asxos.domain.opsmetrics.trend import (
    DEFAULT_MIN_BASELINE,
    DEFAULT_RATIO_THRESHOLD,
    DEFAULT_RECENT_WINDOW,
    DEFAULT_ROBUST_Z_THRESHOLD,
    Sample,
    TrendResult,
    Verdict,
    duration_trend,
    mad,
    median,
)

__all__ = [
    "DEFAULT_MIN_BASELINE",
    "DEFAULT_RATIO_THRESHOLD",
    "DEFAULT_RECENT_WINDOW",
    "DEFAULT_ROBUST_Z_THRESHOLD",
    "Sample",
    "TrendResult",
    "Verdict",
    "duration_trend",
    "mad",
    "median",
]
