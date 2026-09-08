"""
Daily pipeline health check — runs at 22:00 UTC after the full pipeline completes.

Scheduled by `.github/workflows/pipeline-health.yml`, deliberately its own
workflow rather than a trailing step of `daily-brief.yml`: a watchdog that only
runs when the thing it watches got far enough to reach it is not a watchdog.

Detects four failure modes:
  1. Jobs stuck in 'running' for >2 hours (process crash, __aexit__ never ran)
  2. Expected-daily jobs with no 'success' row inside their per-job window
     (36 hours by default; 80 hours for weekday-only jobs, see _EXPECTED_DAILY)
  3. Jobs that have recorded 'failure' on their last 2+ consecutive runs
  4. Jobs that recorded 'success' but attached a degraded note — a
     partial-success run that cleared its threshold while a source hard-failed
     (e.g. ingest_regulatory with Treasury dead), which would otherwise hide
     behind a green cron

On any finding: sends an alert email via Resend AND raises RuntimeError
(JobMonitor records 'failure'; Healthchecks.io deadman fires on missed ping).

On clean pipeline: records 'success' and pings Healthchecks.io.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import os
import re
import textwrap
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from asxos import clock
from asxos.control_plane.probe_adapters import (
    PipelineHealthFailure,
    PipelineHealthKind,
    adapt_pipeline_health,
    context_from_github_environment,
    findings_jsonl,
)
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

# Jobs that must have a 'success' row within their window (hours) on weekdays.
# Format: job_name -> max hours since the last 'success' before MISSING fires.
# Jobs excluded (weekly/non-daily) are NOT listed here.
#
# Why a per-job window and not one 36h number: the window has to cover the
# job's own cadence gap, not a generic "daily". `daily-brief.yml` runs Sun–Thu
# UTC (Mon–Fri AEST), so on any weekday-UTC check the last run is < 26h old
# and 36h is right. `us-positions.yml` runs Mon–Fri 21:30 UTC, so on a Monday
# check that fires before 21:30 UTC the last success is Friday's — 50h+ old.
# Measured 2026-08-31 00:17 UTC: "MISSING: check_us_positions has no 'success'
# row in the last 36 hours" with a green Friday run at 2026-08-29 03:14 UTC.
# A structural false positive, self-cleared the next day, and exactly the
# alert-fatigue failure mode this file exists to prevent. 80h covers
# Friday 21:30 → Monday 21:30 (72h) plus GitHub's documented cron drift.
_DEFAULT_WINDOW_HOURS = 36
_WEEKDAY_ONLY_WINDOW_HOURS = 80
_EXPECTED_DAILY: dict[str, int] = {
    "sync_prices": _DEFAULT_WINDOW_HOURS,
    # "generate_signals" — RETIRED 2026-08-08 (governor decision: Model A
    # monitors retired with Render; keeping it here would fire MISSING every
    # weekday forever — the alert-fatigue failure mode this file exists to
    # prevent).
    "ingest_regulatory": _DEFAULT_WINDOW_HOURS,
    "compose_brief": _DEFAULT_WINDOW_HOURS,
    "snapshot_portfolio": _DEFAULT_WINDOW_HOURS,
    "ingest_market_context": _DEFAULT_WINDOW_HOURS,
    "ingest_underlyings": _DEFAULT_WINDOW_HOURS,
    # Mon–Fri 21:30 UTC (`us-positions.yml`) — see the note above.
    "check_us_positions": _WEEKDAY_ONLY_WINDOW_HOURS,
    "check_au_positions": _DEFAULT_WINDOW_HOURS,
    "check_thesis_invalidations": _DEFAULT_WINDOW_HOURS,
    "validate_price_data": _DEFAULT_WINDOW_HOURS,
    # "check_model_staleness" — RETIRED 2026-08-08 (same decision).
}
_SYNC_DATA_ABSENCE = re.compile(
    r"^sync_prices degraded: (?P<as_of>[0-9]{4}-[0-9]{2}-[0-9]{2}) "
    r"(?P<contract>NO_EQUITY_DATA) — ASX=[0-9]+$"
)


def _failure(
    kind: PipelineHealthKind,
    job_name: str,
    message: str,
    *,
    as_of: date | None = None,
) -> PipelineHealthFailure:
    return PipelineHealthFailure(
        kind=kind,
        job_name=job_name,
        as_of=as_of,
        log_excerpt=message,
    )


def _degraded_failure(
    *, job_name: str, as_of: date | None, error_message: str
) -> PipelineHealthFailure:
    match = _SYNC_DATA_ABSENCE.fullmatch(error_message)
    if job_name == "sync_prices" and match is not None:
        return PipelineHealthFailure(
            kind=PipelineHealthKind.DATA_ABSENCE,
            job_name=job_name,
            contract=match.group("contract"),
            market="ASX",
            as_of=date.fromisoformat(match.group("as_of")),
            log_excerpt=(
                f"DEGRADED: {job_name} as_of={as_of} succeeded but reported: "
                f"{error_message}"
            ),
        )
    return _failure(
        PipelineHealthKind.DEGRADED_SUCCESS,
        job_name,
        f"DEGRADED: {job_name} as_of={as_of} succeeded but reported: {error_message}",
        as_of=as_of,
    )


async def _query_issues(conn) -> list[PipelineHealthFailure]:  # type: ignore[type-arg]
    issues: list[PipelineHealthFailure] = []

    # 1 — stuck running rows
    stuck = await conn.fetch(
        """
        SELECT job_name, as_of, started_at
        FROM job_runs
        WHERE status = 'running'
          -- Same 2 hours as JobMonitor's stale-row heal
          -- (asxos/jobs/utils/job_monitor.py) and the brief's stuck branch
          -- (asxos/brief/compose.py::_job_failures). Tightening one alone
          -- reports rows the others still consider live.
          AND started_at < NOW() - INTERVAL '2 hours'
        ORDER BY started_at
        """
    )
    for row in stuck:
        # total_seconds(), not .seconds — the latter is the sub-day REMAINDER, so a
        # multi-day hang reports its hours-past-midnight instead of its true age and
        # can never escalate. Measured 2026-08-18: sync_financial_statements had been
        # running 56.5h and this line reported ">8h", identically, for three days.
        age_h = int((datetime.now(UTC) - row["started_at"]).total_seconds() // 3600)
        issues.append(
            _failure(
                PipelineHealthKind.STUCK_JOB,
                row["job_name"],
                f"STUCK: {row['job_name']} as_of={row['as_of']} "
                f"has been running for >{age_h}h "
                f"(started {row['started_at'].isoformat()})",
                as_of=row["as_of"],
            )
        )

    # 2 — expected-daily jobs missing a success inside their per-job window
    # Only fire this check on weekdays (Mon-Fri AEST ≈ Sun-Thu UTC)
    today_utc = datetime.now(UTC)
    if today_utc.weekday() < 5:  # Mon-Fri UTC (conservative; misses Fri AEST = Sat UTC edge)
        for job_name, window_hours in _EXPECTED_DAILY.items():
            row = await conn.fetchrow(
                """
                SELECT MAX(started_at) AS last_success
                FROM job_runs
                WHERE job_name = $1
                  AND status   = 'success'
                  AND started_at > NOW() - ($2 * INTERVAL '1 hour')
                """,
                job_name,
                window_hours,
            )
            if row["last_success"] is None:
                issues.append(
                    _failure(
                        PipelineHealthKind.MISSING_SUCCESS,
                        job_name,
                        f"MISSING: {job_name} has no 'success' row in the last "
                        f"{window_hours} hours",
                    )
                )

    # 3 — consecutive failures (last 2+ runs all failed, no success between them)
    all_jobs = await conn.fetch(
        "SELECT DISTINCT job_name FROM job_runs WHERE started_at > NOW() - INTERVAL '7 days'"
    )
    for row in all_jobs:
        jn = row["job_name"]
        recent = await conn.fetch(
            """
            SELECT status FROM job_runs
            WHERE job_name = $1
            ORDER BY started_at DESC
            LIMIT 3
            """,
            jn,
        )
        statuses = [r["status"] for r in recent]
        # Two or more consecutive failures with no success in front
        if len(statuses) >= 2 and all(s == "failure" for s in statuses[:2]):
            issues.append(
                _failure(
                    PipelineHealthKind.CONSECUTIVE_FAILURES,
                    jn,
                    f"CONSECUTIVE FAILURES: {jn} last "
                    f"{len([s for s in statuses if s == 'failure'])} "
                    f"runs all failed (statuses: {statuses})",
                )
            )

    # 4 — 'success' runs carrying a degraded note: a partial-success job that
    # cleared its threshold while a source hard-failed, so status='success'
    # hides a dead feed. JobMonitor writes the note into error_message on
    # success; surface it here so it is not invisible (fail-loud, CLAUDE.md #10).
    degraded = await conn.fetch(
        """
        SELECT job_name, as_of, error_message
        FROM job_runs
        WHERE status = 'success'
          AND error_message IS NOT NULL
          AND started_at > NOW() - INTERVAL '36 hours'
        ORDER BY started_at
        """
    )
    for row in degraded:
        issues.append(
            _degraded_failure(
                job_name=row["job_name"],
                as_of=row["as_of"],
                error_message=row["error_message"],
            )
        )

    return issues


def _issue_text(issue: str | PipelineHealthFailure) -> str:
    return issue if isinstance(issue, str) else issue.log_excerpt


def _send_alert(issues: Sequence[str | PipelineHealthFailure]) -> None:
    """Best-effort Resend alert. Never raises — if email fails, the job still
    hard-fails via RuntimeError so Healthchecks.io catches it."""
    try:
        import resend

        api_key = os.environ.get("RESEND_API_KEY", "")
        to = os.environ.get("BRIEF_TO_EMAIL", "")
        sender = os.environ.get("BRIEF_FROM_EMAIL", "")
        if not (api_key and to and sender):
            return

        # html.escape each issue before it enters the unescaped <pre> below:
        # check #4 is the first path routing the free-text job_runs.error_message
        # into this email, so a future note carrying external text can't break
        # out of the markup (defense-in-depth; today all interpolated content is
        # hardcoded). Escaping the controlled #1-#3 lines is a harmless no-op.
        body = "\n".join(f"• {html.escape(_issue_text(i))}" for i in issues)
        html_body = f"<pre>{body}</pre>"
        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": sender,
                "to": to,
                "subject": f"asxos pipeline alert — {clock.today().isoformat()}",
                "html": html_body,
            }
        )
    except Exception:
        pass  # alert failure never masks the primary failure


def _write_finding_artifact(
    *,
    failures: Sequence[PipelineHealthFailure],
    output: Path,
    environment: Mapping[str, str],
    observed_at: datetime,
) -> None:
    context = context_from_github_environment(
        workflow="pipeline_health",
        environment=environment,
        observed_at=observed_at,
    )
    findings = adapt_pipeline_health(context=context, failures=failures)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(findings_jsonl(findings), encoding="utf-8")


async def _run(as_of: date, *, findings_output: Path | None = None) -> None:
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_CHECK_CRON_HEALTH", "")
    await init_pool()
    try:
        async with JobMonitor("check_cron_health", as_of, healthcheck_url):
            async with acquire() as conn:
                issues = await _query_issues(conn)

            if findings_output is not None:
                _write_finding_artifact(
                    failures=issues,
                    output=findings_output,
                    environment=os.environ,
                    observed_at=datetime.now(UTC),
                )
            if issues:
                _send_alert(issues)
                summary = textwrap.indent(
                    "\n".join(_issue_text(issue) for issue in issues), "  "
                )
                raise RuntimeError(f"Pipeline issues detected:\n{summary}")
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--findings-output",
        type=Path,
        default=None,
        help="write canonical Finding JSONL for the Sentinel artifact",
    )
    options = parser.parse_args()
    asyncio.run(_run(clock.today(), findings_output=options.findings_output))
