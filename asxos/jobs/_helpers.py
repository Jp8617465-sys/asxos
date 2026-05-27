"""
Job-level helpers — infra plumbing for cron entry points.

The leading underscore signals "not domain code." Imported by jobs/*.py only.

Currently exports:
  - assert_partial_success: aggregate failure threshold for gather-pattern jobs
  - UpstreamBlocked: exception class mapped to job_runs.status='blocked' by
    JobMonitor (distinct from 'failure' to avoid alert fatigue on upstream waits)
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


class UpstreamBlocked(RuntimeError):
    """Raised when an upstream job has not succeeded.

    JobMonitor.__aexit__ inspects exc_type.__name__ and maps this to
    status='blocked' in job_runs, distinct from 'failure'. Healthchecks
    are NOT pinged for blocked runs — the deadman should miss so the
    "upstream stuck" pattern surfaces.
    """


def assert_partial_success(
    results: Sequence[Any],
    *,
    is_ok: Callable[[Any], bool],
    threshold: float,
    label: str,
    identifiers: Sequence[Any] | None = None,
    allow_empty: bool = False,
) -> int:
    """Hard-fail if fewer than ``threshold`` of ``results`` satisfy ``is_ok``.

    Args:
        results: outputs from ``asyncio.gather`` (may include exceptions if
            the caller used ``return_exceptions=True``).
        is_ok: per-result success predicate. Examples:
            - sync_fundamentals: ``lambda r: r is True``
            - ingest_regulatory: ``lambda r: r is not None``
            - ingest_news: ``lambda r: isinstance(r, int) and r >= 0``
        threshold: required success ratio (``>=`` comparison). NO DEFAULT —
            each callsite picks deliberately so a copy-paste with the wrong
            threshold becomes obvious in code review.
        label: job name for the diagnostic.
        identifiers: optional same-length sequence (e.g. the list of symbols
            passed to gather). When provided, the RuntimeError lists the
            first 10 entries whose corresponding result failed ``is_ok``.
            Without this, operators must grep stdout for which items failed.
        allow_empty: if False (default), an empty ``results`` raises
            RuntimeError. This closes the silent-empty-input failure mode
            where e.g. an upstream query returning empty silently records
            "success" with zero work done.

    Returns:
        The count of successful results.

    Raises:
        RuntimeError on threshold breach or (when ``allow_empty=False``) on
        empty input.
    """
    n_total = len(results)

    if n_total == 0:
        if not allow_empty:
            raise RuntimeError(
                f"{label}: empty input — refusing to record a silent no-op. "
                "If empty is legitimate here, pass allow_empty=True."
            )
        return 0

    n_ok = sum(1 for r in results if is_ok(r))
    ratio = n_ok / n_total

    if ratio < threshold:
        failing_summary = ""
        if identifiers is not None:
            # Defensive: identifiers may be shorter than results (e.g. caller
            # passed the wrong sequence). Truncate to whatever is available.
            paired = list(zip(identifiers, results, strict=False))
            failing = [str(ident) for ident, r in paired if not is_ok(r)]
            shown = failing[:10]
            failing_summary = (
                f" — first failing: {shown}"
                + (f" (+{len(failing) - 10} more)" if len(failing) > 10 else "")
            )
        raise RuntimeError(
            f"{label}: only {n_ok}/{n_total} succeeded "
            f"({ratio:.1%} < {threshold:.0%} threshold){failing_summary}"
        )

    return n_ok
