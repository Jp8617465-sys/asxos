"""Tests for jobs/check_cron_health.py — check #4 (degraded-success surfacing).

A job can record status='success' while a source hard-failed (a partial-success
run that cleared its threshold, e.g. ingest_regulatory with Treasury dead).
JobMonitor stashes that fact in error_message; check #4 must surface it, else the
dead feed stays invisible behind a green cron.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.check_cron_health as job_mod
from jobs.check_cron_health import _query_issues

_SATURDAY = datetime(2026, 7, 18, 22, 0, tzinfo=UTC)  # weekday() == 5
_MONDAY = datetime(2026, 7, 20, 22, 0, tzinfo=UTC)  # weekday() == 0


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


# ---------------------------------------------------------------------------
# Check #2b — Saturday weekly-lane coverage (2026-07-19 sprint follow-up).
#
# Before this check existed, a missed/failed Saturday job (sync_universe,
# retrain_model_a, sync_corporate_actions, sync_financial_statements,
# derive_fundamentals_pit, build_portfolio) had NO "missing" detection at
# all -- only the 2+-consecutive-failures check could catch it, meaning a
# single bad Saturday stayed silent for a full week.
# ---------------------------------------------------------------------------


def _weekly_fetchrow(missing: set[str]):
    async def _fetchrow(query, job_name):
        if job_name in missing:
            return {"last_success": None}
        return {"last_success": datetime.now(UTC)}

    return _fetchrow


@pytest.mark.asyncio
async def test_saturday_missing_weekly_job_surfaces_as_issue() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[], [], []])
    conn.fetchrow = AsyncMock(side_effect=_weekly_fetchrow({"derive_fundamentals_pit"}))

    with patch.object(job_mod, "datetime") as mock_dt:
        mock_dt.now.return_value = _SATURDAY
        issues = await _query_issues(conn)

    missing = [i for i in issues if i.startswith("MISSING:") and "weekly Saturday lane" in i]
    assert len(missing) == 1
    assert "derive_fundamentals_pit" in missing[0]


@pytest.mark.asyncio
async def test_saturday_all_weekly_jobs_present_no_weekly_issues() -> None:
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[], [], []])
    conn.fetchrow = AsyncMock(side_effect=_weekly_fetchrow(set()))

    with patch.object(job_mod, "datetime") as mock_dt:
        mock_dt.now.return_value = _SATURDAY
        issues = await _query_issues(conn)

    assert not [i for i in issues if "weekly Saturday lane" in i]


@pytest.mark.asyncio
async def test_saturday_retrain_model_a_excluded_even_when_absent() -> None:
    # Regression (refactoring-expert finding, 2026-07-19): retrain_model_a is
    # SUSPENDED under the Model A shelf (rule #11) and will NEVER have a fresh
    # success row -- it must not be in _EXPECTED_WEEKLY_SATURDAY at all, or
    # this check would alert every single Saturday forever (the exact
    # alert-fatigue pattern check_model_staleness.py already hit and fixed
    # for this identical model-shelf reason).
    assert "retrain_model_a" not in job_mod._EXPECTED_WEEKLY_SATURDAY

    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[], [], []])
    # retrain_model_a has NO success row (as it never will in production) --
    # every OTHER weekly job does.
    conn.fetchrow = AsyncMock(side_effect=_weekly_fetchrow({"retrain_model_a"}))

    with patch.object(job_mod, "datetime") as mock_dt:
        mock_dt.now.return_value = _SATURDAY
        issues = await _query_issues(conn)

    assert not [i for i in issues if "retrain_model_a" in i]


@pytest.mark.asyncio
async def test_non_saturday_skips_weekly_check_entirely() -> None:
    # Monday: even with every weekly job missing, the check must not fire --
    # they aren't expected to have run since last Saturday.
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=[[], [], []])
    conn.fetchrow = AsyncMock(side_effect=_weekly_fetchrow(set(job_mod._EXPECTED_WEEKLY_SATURDAY)))

    with patch.object(job_mod, "datetime") as mock_dt:
        mock_dt.now.return_value = _MONDAY
        issues = await _query_issues(conn)

    assert not [i for i in issues if "weekly Saturday lane" in i]
