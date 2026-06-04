#!/usr/bin/env python
"""
Daily ML health monitor — runs at 21:05 UTC after the full daily pipeline.

Detects four ML-specific failure modes that check_cron_health cannot see:
  1. Signals are stale (as_of > 3 days ago).
  2. generate_signals has >=2 consecutive failures in last 5 runs.
  3. No successful retrain_model_a in >14 days.
  4. Active model is effectively >60 days old (proxy: last successful retrain).

On any finding: sends a labelled email alert and raises RuntimeError
(JobMonitor records status='failure'; Healthchecks.io deadman fires on missed ping).
On clean: records success and pings Healthchecks.io silently.
"""
from __future__ import annotations

import asyncio
import os
import textwrap
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

JOB_NAME = "check_model_staleness"
_SIGNAL_STALE_DAYS = 3
_RETRAIN_STALE_DAYS = 14
_MODEL_AGE_DAYS = 60
_CONSEC_FAIL_THRESHOLD = 2


def _send_alert(subject: str, body: str) -> None:
    """Best-effort Resend alert. Never raises."""
    try:
        import resend

        api_key = os.environ.get("RESEND_API_KEY", "")
        to = os.environ.get("BRIEF_TO_EMAIL", "")
        sender = os.environ.get("BRIEF_FROM_EMAIL", "")
        if not (api_key and to and sender):
            return

        resend.api_key = api_key
        resend.Emails.send({
            "from": sender,
            "to": to,
            "subject": subject,
            "html": f"<pre>{body}</pre>",
        })
    except Exception:
        pass


async def _query_issues(conn, as_of: date) -> list[tuple[str, str]]:  # type: ignore[type-arg]
    """Returns list of (subject_tag, detail) tuples — one per issue found."""
    issues: list[tuple[str, str]] = []

    # 1. Signal staleness
    row = await conn.fetchrow(
        "SELECT MAX(as_of) AS latest_as_of FROM signals WHERE model = 'model_a'"
    )
    if row["latest_as_of"] is None:
        issues.append((
            "[SIGNALS MISSING] no model_a signals in DB",
            "No rows found in signals table for model_a.",
        ))
    else:
        signal_as_of = row["latest_as_of"]
        age_days = (as_of - signal_as_of).days
        if age_days > _SIGNAL_STALE_DAYS:
            issues.append((
                f"[MODEL STALE] signals are {age_days}d old",
                f"Latest signal as_of={signal_as_of} ({age_days}d ago). "
                f"Expected: within {_SIGNAL_STALE_DAYS}d of today ({as_of}).",
            ))

    # 2. Consecutive generate_signals failures
    recent = await conn.fetch(
        """
        SELECT status FROM job_runs
        WHERE job_name = 'generate_signals'
        ORDER BY started_at DESC
        LIMIT 5
        """
    )
    statuses = [r["status"] for r in recent]
    leading_fails = 0
    for s in statuses:
        if s in ("failure", "blocked"):
            leading_fails += 1
        else:
            break
    if leading_fails >= _CONSEC_FAIL_THRESHOLD:
        issues.append((
            f"[GENERATE FAILING] {leading_fails} consecutive failures",
            f"generate_signals last {len(statuses)} statuses: {statuses}. "
            f"{leading_fails} leading failures/blocks.",
        ))

    # 3. Retrain staleness + 4. Model age proxy
    retrain_row = await conn.fetchrow(
        """
        SELECT MAX(started_at) AS last_retrain
        FROM job_runs
        WHERE job_name = 'retrain_model_a'
          AND status = 'success'
        """
    )
    if retrain_row["last_retrain"] is None:
        issues.append((
            "[RETRAIN NEVER SUCCEEDED] no successful retrain on record",
            "No successful retrain_model_a found in job_runs.",
        ))
    else:
        last_retrain_dt = retrain_row["last_retrain"]
        last_retrain_date = last_retrain_dt.date() if hasattr(last_retrain_dt, "date") else last_retrain_dt
        retrain_age = (as_of - last_retrain_date).days
        if retrain_age > _RETRAIN_STALE_DAYS:
            issues.append((
                f"[RETRAIN STUCK] no successful retrain in {retrain_age}d",
                f"Last successful retrain_model_a: {last_retrain_date} ({retrain_age}d ago). "
                f"Threshold: {_RETRAIN_STALE_DAYS}d.",
            ))
        if retrain_age > _MODEL_AGE_DAYS:
            issues.append((
                f"[MODEL AGED] active model is effectively >{retrain_age}d old",
                f"Last retrain was {retrain_age}d ago (>{_MODEL_AGE_DAYS}d threshold). "
                "Consider manual retrain.",
            ))

    return issues


async def _run(as_of: date) -> None:
    healthcheck_url = settings.healthcheck_url_check_model_staleness
    async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
        await init_pool()
        try:
            async with acquire() as conn:
                issues = await _query_issues(conn, as_of)

            monitor.rows_written = len(issues)

            if not issues:
                return

            primary_subject = issues[0][0]
            all_details = "\n\n".join(
                f"{subject}:\n{detail}" for subject, detail in issues
            )
            _send_alert(
                f"asxos {primary_subject} — {as_of}",
                all_details,
            )
            summary = textwrap.indent("\n".join(subj for subj, _ in issues), "  ")
            raise RuntimeError(f"ML health issues detected:\n{summary}")
        finally:
            await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check ML model staleness and health")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Date override (default: today)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
