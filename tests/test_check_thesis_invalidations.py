"""Tests for jobs/check_thesis_invalidations.py — the 0042 rewrite.

The pre-0042 file tested _normalize_conditions/_parse_price_condition; both
are gone (the JSONB column is dropped in 0042 and the parser moved to
asxos/domain/theses/condition_parser.py, tested in test_condition_parser.py).
This rewrite drives _run() end-to-end with a scripted conn + stubbed
JobMonitor and pins the fixtures from design §9: TR (price-date provenance,
action framing), SP (stale-tape guard), RB no-op/re-arm branches, the
unparseable loud count, the widened active+watching scope, and _send_alert's
hard-fail on missing env (register #20).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.check_thesis_invalidations as job

AS_OF = date(2026, 8, 7)
PRICE_DATE = date(2026, 8, 6)


def _cond(**over) -> dict[str, Any]:
    row = {
        "condition_id": 5,
        "thesis_id": 2,
        "ordinal": 1,
        "condition_text": "Price closes below $230 stop on volume",
        "trigger_semantics": "hard_exit",
        "condition_status": "active",
        "enforcement_kind": "price_below",
        "enforcement_threshold": Decimal("230.000000"),
        "symbol": "HUBS.NYSE",
        "attestation": "underwritten",
    }
    row.update(over)
    return row


class _StubMonitor:
    instances: ClassVar[list[_StubMonitor]] = []

    def __init__(self, *_a, **_k):
        self.rows_written = 0
        self.note: str | None = None
        _StubMonitor.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


@pytest.fixture
def run_env(monkeypatch: pytest.MonkeyPatch):
    """Patch pools, monitor, transitions, locks + alert send; return knobs."""
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    _StubMonitor.instances = []

    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)

    @asynccontextmanager
    async def _acquire():
        yield conn

    sent: list[tuple[str, str]] = []

    with (
        patch.object(job, "init_pool", new=AsyncMock()),
        patch.object(job, "close_pool", new=AsyncMock()),
        patch.object(job, "acquire", side_effect=_acquire),
        patch.object(job, "JobMonitor", _StubMonitor),
        patch.object(job.conditions_svc, "record_trigger", new=AsyncMock(return_value=True)) as trig,
        patch.object(job.conditions_svc, "record_re_arm", new=AsyncMock(return_value=True)) as rearm,
        patch.object(job, "get_disposal_locks", new=AsyncMock(return_value={})) as locks,
        patch.object(job, "_send_alert", side_effect=lambda s, b: sent.append((s, b))),
    ):
        yield {
            "conn": conn, "trigger": trig, "re_arm": rearm,
            "locks": locks, "sent": sent,
        }


def _monitor() -> _StubMonitor:
    assert _StubMonitor.instances
    return _StubMonitor.instances[-1]


# ---------------------------------------------------------------------------
# TR — trigger uses the CLOSE's date, alert action-framed
# ---------------------------------------------------------------------------

async def test_trigger_records_price_date_not_run_date_and_sends_action_alert(run_env):
    run_env["conn"].fetch = AsyncMock(return_value=[_cond()])
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("200.00"), "dt": PRICE_DATE}
    )

    await job._run(AS_OF)

    trig = run_env["trigger"]
    trig.assert_awaited_once()
    kwargs = trig.await_args.kwargs
    assert kwargs["price_date"] == PRICE_DATE  # ≠ AS_OF — register #21
    assert kwargs["price_date"] != AS_OF
    assert kwargs["observed_close"] == Decimal("200.00")
    assert kwargs["source"] == "job"

    assert len(run_env["sent"]) == 1
    subject, body = run_env["sent"][0]
    assert "HUBS.NYSE" in subject
    assert str(PRICE_DATE) in subject
    assert "Run: asx thesis exit HUBS.NYSE" in body  # underwritten+hard_exit+unlocked
    assert _monitor().rows_written == 1


async def test_placeholder_trigger_alert_is_review_framed(run_env):
    run_env["conn"].fetch = AsyncMock(return_value=[_cond(attestation="placeholder")])
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("200.00"), "dt": PRICE_DATE}
    )

    await job._run(AS_OF)

    assert len(run_env["sent"]) == 1
    _subject, body = run_env["sent"][0]
    assert "asx thesis exit" not in body
    assert "PLACEHOLDER — not underwritten" in body


async def test_no_alert_when_transition_already_recorded(run_env):
    """record_trigger returning False (idempotent re-run) → no alert, no
    rows_written — a re-run is quiet."""
    run_env["trigger"].return_value = False
    run_env["conn"].fetch = AsyncMock(return_value=[_cond()])
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("200.00"), "dt": PRICE_DATE}
    )

    await job._run(AS_OF)

    assert run_env["sent"] == []
    assert _monitor().rows_written == 0


# ---------------------------------------------------------------------------
# SP — stale-price guard
# ---------------------------------------------------------------------------

async def test_stale_tape_skips_evaluation_with_loud_note(run_env):
    stale_dt = AS_OF - job.timedelta(days=7)
    run_env["conn"].fetch = AsyncMock(return_value=[_cond()])
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("200.00"), "dt": stale_dt}
    )

    await job._run(AS_OF)

    run_env["trigger"].assert_not_awaited()
    run_env["re_arm"].assert_not_awaited()
    assert run_env["sent"] == []
    note = _monitor().note or ""
    assert "stale tape" in note and str(stale_dt) in note


async def test_missing_price_rows_is_a_loud_note_not_a_silent_skip(run_env):
    run_env["conn"].fetch = AsyncMock(return_value=[_cond()])
    run_env["conn"].fetchrow = AsyncMock(return_value=None)

    await job._run(AS_OF)

    run_env["trigger"].assert_not_awaited()
    assert "NO price rows" in (_monitor().note or "")


# ---------------------------------------------------------------------------
# RB — re-arm and still-breached branches
# ---------------------------------------------------------------------------

async def test_recaptured_close_re_arms_without_alert(run_env):
    run_env["conn"].fetch = AsyncMock(
        return_value=[_cond(condition_status="triggered")]
    )
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("245.00"), "dt": PRICE_DATE}
    )

    await job._run(AS_OF)

    run_env["re_arm"].assert_awaited_once()
    assert run_env["re_arm"].await_args.kwargs["price_date"] == PRICE_DATE
    run_env["trigger"].assert_not_awaited()
    assert run_env["sent"] == []  # a recovery is brief material, not an interrupt
    assert _monitor().rows_written == 1


async def test_still_breached_triggered_condition_is_a_noop(run_env):
    run_env["conn"].fetch = AsyncMock(
        return_value=[_cond(condition_status="triggered")]
    )
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("200.00"), "dt": PRICE_DATE}
    )

    await job._run(AS_OF)

    run_env["trigger"].assert_not_awaited()
    run_env["re_arm"].assert_not_awaited()
    assert _monitor().rows_written == 0


# ---------------------------------------------------------------------------
# Unparseable conditions — counted + surfaced, never silent (register #5)
# ---------------------------------------------------------------------------

async def test_unparseable_conditions_counted_in_note(run_env):
    run_env["conn"].fetch = AsyncMock(return_value=[
        _cond(),
        _cond(
            condition_id=6, ordinal=3,
            condition_text="Macro regime shifts to risk_off_disorderly",
            enforcement_kind="not_machine_checkable",
            enforcement_threshold=None,
        ),
    ])
    run_env["conn"].fetchrow = AsyncMock(
        return_value={"close": Decimal("245.00"), "dt": PRICE_DATE}
    )

    await job._run(AS_OF)

    note = _monitor().note or ""
    assert "1 condition(s) NOT machine-checked" in note
    assert "HUBS.NYSE" in note


# ---------------------------------------------------------------------------
# Scope + query shape
# ---------------------------------------------------------------------------

async def test_query_covers_active_and_watching(run_env):
    """Divergence #3 (register #22): watching theses are in scope."""
    await job._run(AS_OF)
    sql = run_env["conn"].fetch.await_args.args[0]
    assert "'active'" in sql and "'watching'" in sql
    assert "thesis_conditions" in sql


# ---------------------------------------------------------------------------
# _send_alert — hard-fail on missing env (register #20)
# ---------------------------------------------------------------------------

def test_send_alert_raises_on_missing_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("BRIEF_TO_EMAIL", raising=False)
    monkeypatch.delenv("BRIEF_FROM_EMAIL", raising=False)
    with pytest.raises(RuntimeError, match="RESEND_API_KEY"):
        job._send_alert("subject", "body")
