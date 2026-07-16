"""Tests for jobs/check_cron_health.py — check #4 (degraded-success surfacing).

A job can record status='success' while a source hard-failed (a partial-success
run that cleared its threshold, e.g. ingest_regulatory with Treasury dead).
JobMonitor stashes that fact in error_message; check #4 must surface it, else the
dead feed stays invisible behind a green cron.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from jobs.check_cron_health import _query_issues


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
async def test_clean_success_rows_produce_no_degraded_issue() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[], [], []])  # nothing stuck / failing / degraded
    conn.fetchrow = AsyncMock(return_value={"last_success": datetime.now(UTC)})

    issues = await _query_issues(conn)

    assert not [i for i in issues if i.startswith("DEGRADED:")]
