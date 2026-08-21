"""Tests for jobs/check_cron_health.py — check #4 (degraded-success surfacing).

A job can record status='success' while a source hard-failed (a partial-success
run that cleared its threshold, e.g. ingest_regulatory with Treasury dead).
JobMonitor stashes that fact in error_message; check #4 must surface it, else the
dead feed stays invisible behind a green cron.
"""
from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from jobs.check_cron_health import _query_issues, _send_alert


def test_send_alert_does_not_shadow_html_module(monkeypatch: pytest.MonkeyPatch) -> None:
    send = MagicMock()
    resend = SimpleNamespace(api_key=None, Emails=SimpleNamespace(send=send))
    monkeypatch.setitem(sys.modules, "resend", resend)
    monkeypatch.setenv("RESEND_API_KEY", "synthetic-resend-key")
    monkeypatch.setenv("BRIEF_TO_EMAIL", "james@example.test")
    monkeypatch.setenv("BRIEF_FROM_EMAIL", "arbi@example.test")

    _send_alert(["DEGRADED: <external error>"])

    send.assert_called_once()
    payload = send.call_args.args[0]
    assert payload["html"] == "<pre>• DEGRADED: &lt;external error&gt;</pre>"


@pytest.mark.asyncio
async def test_degraded_success_row_surfaces_as_issue() -> None:
    conn = MagicMock()
    # fetch() is called in order: (1) stuck rows, (2) all_jobs (empty → no
    # per-job consecutive-failure fetch), (3) degraded-success rows.
    conn.fetch = AsyncMock(
        side_effect=[
            [],  # 1: no stuck 'running' rows
            [],  # 2: no jobs in the 7-day window → no consecutive-failure fetches
            [    # 3: one degraded success row
                {
                    "job_name": "ingest_regulatory",
                    "as_of": date(2026, 7, 15),
                    "error_message": (
                        "degraded: 1/2 source(s) returned no data "
                        "after retry (dead feed): ['Treasury']"
                    ),
                }
            ],
        ]
    )
    # fetchrow drives check #2 (expected-daily); a non-None last_success => no MISSING,
    # deterministic regardless of whether "today" is a weekday.
    conn.fetchrow = AsyncMock(return_value={"last_success": datetime.now(UTC)})

    issues = await _query_issues(conn)

    degraded = [i for i in issues if i.startswith("DEGRADED:")]
    assert len(degraded) == 1
    assert "ingest_regulatory" in degraded[0]
    assert "Treasury" in degraded[0]


@pytest.mark.asyncio
async def test_stuck_age_counts_whole_days_not_the_sub_day_remainder() -> None:
    """A multi-day hang must report its true age, so escalation is possible.

    Regression: the age used ``timedelta.seconds``, which is the sub-day
    REMAINDER — the days component is discarded. Live on 2026-08-18,
    ``sync_financial_statements`` had been running 56.5h and the alert said
    "running for >8h" (56.5h → 30,600s → 8h), identically for three days. The
    number never grows past 23, so a hang can never escalate no matter how long
    it lasts.
    """
    started = datetime.now(UTC) - timedelta(hours=56, minutes=30)
    conn = MagicMock()
    conn.fetch = AsyncMock(
        side_effect=[
            [  # 1: one genuinely stuck row, well past a day old
                {
                    "job_name": "sync_financial_statements",
                    "as_of": date(2026, 8, 15),
                    "started_at": started,
                }
            ],
            [],  # 2: no jobs in the 7-day window
            [],  # 3: no degraded successes
        ]
    )
    conn.fetchrow = AsyncMock(return_value={"last_success": datetime.now(UTC)})

    issues = await _query_issues(conn)

    stuck = [i for i in issues if i.startswith("STUCK:")]
    assert len(stuck) == 1
    assert "sync_financial_statements" in stuck[0]
    # The whole point: 56, not 8.
    assert ">56h" in stuck[0], stuck[0]
    assert ">8h" not in stuck[0], "sub-day remainder leaked into the age"


@pytest.mark.asyncio
async def test_clean_success_rows_produce_no_degraded_issue() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[], [], []])  # nothing stuck / failing / degraded
    conn.fetchrow = AsyncMock(return_value={"last_success": datetime.now(UTC)})

    issues = await _query_issues(conn)

    assert not [i for i in issues if i.startswith("DEGRADED:")]
