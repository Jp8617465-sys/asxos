"""
Daily pipeline health check — runs at 22:00 UTC after the full pipeline completes.

Detects three failure modes:
  1. Jobs stuck in 'running' for >2 hours (process crash, __aexit__ never ran)
  2. Expected-daily jobs with no 'success' row in the last 36 hours
  3. Jobs that have recorded 'failure' on their last 2+ consecutive runs

On any finding: sends an alert email via Resend AND raises RuntimeError
(JobMonitor records 'failure'; Healthchecks.io deadman fires on missed ping).

On clean pipeline: records 'success' and pings Healthchecks.io.
"""
from __future__ import annotations

import asyncio
import os
import textwrap
from datetime import UTC, date, datetime

from asxos.db import acquire
from asxos.jobs.utils.job_monitor import JobMonitor

# Jobs that must have a 'success' row within the last 36 hours on weekdays.
# Format: job_name.  Jobs excluded (weekly/non-daily) are NOT listed here.
_EXPECTED_DAILY = [
    "sync_prices",
    "generate_signals",
    "ingest_regulatory",
    "compose_brief",
    "snapshot_portfolio",
    "ingest_market_context",
    "ingest_underlyings",
    "check_us_positions",
    "check_au_positions",
    "check_thesis_invalidations",
    "validate_price_data",
    "check_model_staleness",
]


async def _query_issues(conn) -> list[str]:  # type: ignore[type-arg]
    issues: list[str] = []

    # 1 — stuck running rows
    stuck = await conn.fetch(
        """
        SELECT job_name, as_of, started_at
        FROM job_runs
        WHERE status = 'running'
          AND started_at < NOW() - INTERVAL '2 hours'
        ORDER BY started_at
        """
    )
    for row in stuck:
        age_h = (datetime.now(UTC) - row["started_at"]).seconds // 3600
        issues.append(
            f"STUCK: {row['job_name']} as_of={row['as_of']} "
            f"has been running for >{age_h}h (started {row['started_at'].isoformat()})"
        )

    # 2 — expected-daily jobs missing a success in the last 36 hours
    # Only fire this check on weekdays (Mon-Fri AEST ≈ Sun-Thu UTC)
    today_utc = datetime.now(UTC)
    if today_utc.weekday() < 5:  # Mon-Fri UTC (conservative; misses Fri AEST = Sat UTC edge)
        for job_name in _EXPECTED_DAILY:
            row = await conn.fetchrow(
                """
                SELECT MAX(started_at) AS last_success
                FROM job_runs
                WHERE job_name = $1
                  AND status   = 'success'
                  AND started_at > NOW() - INTERVAL '36 hours'
                """,
                job_name,
            )
            if row["last_success"] is None:
                issues.append(
                    f"MISSING: {job_name} has no 'success' row in the last 36 hours"
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
                f"CONSECUTIVE FAILURES: {jn} last {len([s for s in statuses if s == 'failure'])} "
                f"runs all failed (statuses: {statuses})"
            )

    return issues


def _send_alert(issues: list[str]) -> None:
    """Best-effort Resend alert. Never raises — if email fails, the job still
    hard-fails via RuntimeError so Healthchecks.io catches it."""
    try:
        import resend

        api_key = os.environ.get("RESEND_API_KEY", "")
        to = os.environ.get("BRIEF_TO_EMAIL", "")
        sender = os.environ.get("BRIEF_FROM_EMAIL", "")
        if not (api_key and to and sender):
            return

        body = "\n".join(f"• {i}" for i in issues)
        html = f"<pre>{body}</pre>"
        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": sender,
                "to": to,
                "subject": f"asxos pipeline alert — {date.today().isoformat()}",
                "html": html,
            }
        )
    except Exception:
        pass  # alert failure never masks the primary failure


async def _run(as_of: date) -> None:
    healthcheck_url = os.environ.get("HEALTHCHECK_URL_CHECK_CRON_HEALTH", "")
    async with JobMonitor("check_cron_health", as_of, healthcheck_url):
        async with acquire() as conn:
            issues = await _query_issues(conn)

        if issues:
            _send_alert(issues)
            summary = textwrap.indent("\n".join(issues), "  ")
            raise RuntimeError(f"Pipeline issues detected:\n{summary}")


if __name__ == "__main__":
    asyncio.run(_run(date.today()))
