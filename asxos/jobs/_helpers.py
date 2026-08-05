"""
Job-level helpers — infra plumbing for cron entry points.

The leading underscore signals "not domain code." Imported by jobs/*.py only.

Currently exports:
  - assert_partial_success: aggregate failure threshold for gather-pattern jobs
  - UpstreamBlocked: exception class mapped to job_runs.status='blocked' by
    JobMonitor (distinct from 'failure' to avoid alert fatigue on upstream waits)
  - require_personal_use_job: personal-use firewall gate for job entry points
"""
from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any


def require_personal_use_job() -> None:
    """Hard-fail a job entry point if the personal-use firewall flag isn't set.

    Jobs analog of ``asxos.cli._common._require_personal_use``. Part 0 Q1 /
    CLAUDE.md non-negotiable #10: any job that reads or writes portfolio /
    thesis / tax data generates personal-advice output under s766B
    (Corporations Act 2001) and must run only in single-user mode.

    Raising ``RuntimeError`` (not a silent ``log.warning``) means a missing
    flag fails loud rather than relying on ``render.yaml`` setting the env var
    externally — the env-only-protection gap the R14 audit surfaced across the
    position/snapshot/thesis-check jobs. Call this as the first statement of the
    job's entry point, before ``init_pool()`` / ``JobMonitor`` opens.
    """
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise RuntimeError(
            "ASXOS_PERSONAL_USE is not set to '1'. This job generates "
            "personal-advice outputs under s766B (Corporations Act 2001) and "
            "must only run in single-user mode. Set ASXOS_PERSONAL_USE=1."
        )


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
            - ingest_news: ``lambda r: isinstance(r, int)``

            The predicate MUST be able to return False for a failed unit of
            work. Before shipping one, name a value the worker can actually
            produce that fails it; if you cannot, the guard is a no-op that
            still reports a healthy ratio. This is not hypothetical:
            ingest_news previously used ``lambda r: isinstance(r, int) and
            r >= 0`` against a worker that returned ``0`` on caught exceptions
            — every int satisfies ``r >= 0``, so the guard could not fail, and
            a run in which every symbol errored scored 100% healthy. 22
            consecutive runs recorded ``status='success'`` with
            ``rows_written=0`` against an empty target table
            (``docs/market-trends-report-2026-08-05.md`` §1). When the worker
            signals failure with a sentinel, make the sentinel a different
            *type* (``None``) rather than an in-range value, so the predicate
            can tell them apart.

            Scope limit: a type-distinct sentinel only covers failures the
            worker *catches*. An upstream that returns an empty or malformed
            payload without raising still yields a legitimate-looking success
            value, and no predicate here can see it — that class needs a
            row-count check downstream of the write (e.g.
            ``asxos/brief/compose.py::_news_ingest_fresh``), not a wider ratio.
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
