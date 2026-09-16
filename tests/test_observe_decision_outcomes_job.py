"""jobs/observe_decision_outcomes.py — t0 for every packet, observations at the promised sessions."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml

import jobs.observe_decision_outcomes as job_mod
from asxos.config import settings
from asxos.domain.decision_engine.outcomes import ThesisOutcome, materialise_t0
from asxos.domain.decision_engine.types import DecisionCase
from tests.test_decision_outcomes import _case

ROOT = Path(__file__).resolve().parents[1]


class FakeConn:
    """decision_packets / thesis_outcomes / prices, in memory, append-only like 0052."""

    def __init__(self, *, packets: dict[str, DecisionCase], close: Decimal | None = Decimal("170")) -> None:
        self.packets = packets
        self.outcomes: dict[str, dict[str, Any]] = {}
        self.close = close
        self.price_queries: list[tuple[str, date]] = []

    async def fetch(self, query: str, *args: object) -> list[Any]:
        if "FROM decision_packets p" in query:
            with_t0 = {o["decision_packet_id"] for o in self.outcomes.values() if o["horizon_trading_days"] == 0}
            return [{"decision_packet_id": p} for p in sorted(self.packets) if p not in with_t0]
        if "DISTINCT decision_packet_id FROM thesis_outcomes" in query:
            cutoff = args[0]
            assert isinstance(cutoff, datetime)
            return [
                {"decision_packet_id": p}
                for p in sorted({
                    o["decision_packet_id"] for o in self.outcomes.values()
                    if o["horizon_trading_days"] > 0 and o["observation_state"] == "recorded" and o["due_at"] <= cutoff
                })
            ]
        if "SELECT payload FROM thesis_outcomes" in query:
            rows = [o for o in self.outcomes.values() if o["decision_packet_id"] == args[0]]
            rows.sort(key=lambda o: (o["horizon_trading_days"], o["outcome_id"]))
            return [{"payload": o["payload"]} for o in rows]
        raise AssertionError(query)

    async def fetchrow(self, query: str, *args: object) -> Any:
        assert "FROM prices" in query
        assert isinstance(args[1], date)
        self.price_queries.append((str(args[0]), args[1]))
        return None if self.close is None else {"dt": args[1], "close": self.close}

    async def execute(self, query: str, *args: object) -> str:
        assert "INSERT INTO thesis_outcomes" in query and "ON CONFLICT (outcome_id) DO NOTHING" in query
        outcome_id = str(args[0])
        if outcome_id in self.outcomes:
            return "INSERT 0 0"
        self.outcomes[outcome_id] = {
            "outcome_id": outcome_id, "decision_packet_id": args[2], "horizon_trading_days": args[4],
            "due_at": args[5], "observation_state": args[8], "payload": args[-1],
        }
        return "INSERT 0 1"


class FakeMonitor:
    def __init__(self) -> None:
        self.rows_written = 0
        self.note: str | None = None


async def _run(conn: FakeConn, cutoff: datetime) -> tuple[dict[str, Any], FakeMonitor]:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    monitor = FakeMonitor()
    with (
        patch.object(job_mod, "acquire", side_effect=_acquire),
        patch.object(job_mod.repository, "load_case", AsyncMock(side_effect=lambda pid, *, conn: conn.packets[pid])),
    ):
        summary = await job_mod.run(monitor=monitor, cutoff=cutoff)
    return summary, monitor


def _rows_of(conn: FakeConn, packet_id: str) -> list[ThesisOutcome]:
    return [
        ThesisOutcome.model_validate(json.loads(str(o["payload"])))
        for o in conn.outcomes.values() if o["decision_packet_id"] == packet_id
    ]


async def test_first_run_records_t0_and_the_scheduled_horizons_and_nothing_is_due() -> None:
    case = await _case()
    conn = FakeConn(packets={case.decision.decision_packet_id: case})
    cutoff = case.decision.knowledge_cutoff + timedelta(hours=1)
    summary, monitor = await _run(conn, cutoff)
    expected = materialise_t0(case, created_at=cutoff)
    assert summary["t0_recorded"] == {case.decision.decision_packet_id: len(expected)}
    assert summary["observed"] == {} and summary["failed"] == {}
    assert monitor.rows_written == len(expected) and monitor.note is None
    assert {r.outcome_id for r in _rows_of(conn, case.decision.decision_packet_id)} == {r.outcome_id for r in expected}
    assert conn.price_queries == []


async def test_second_run_is_a_no_op_until_a_horizon_is_due() -> None:
    case = await _case()
    conn = FakeConn(packets={case.decision.decision_packet_id: case})
    cutoff = case.decision.knowledge_cutoff + timedelta(hours=1)
    await _run(conn, cutoff)
    before = dict(conn.outcomes)
    summary, monitor = await _run(conn, cutoff + timedelta(days=1))
    assert conn.outcomes == before and monitor.rows_written == 0
    assert monitor.note == "nothing to record: every packet has its t0 and no horizon is due"
    assert summary["t0_recorded"] == {}


async def test_due_horizons_are_observed_at_their_promised_session_not_the_run_date() -> None:
    case = await _case()
    pid = case.decision.decision_packet_id
    conn = FakeConn(packets={pid: case}, close=Decimal("175.065"))
    await _run(conn, case.decision.knowledge_cutoff + timedelta(hours=1))
    scheduled = [r for r in _rows_of(conn, pid) if r.horizon_trading_days == 21]
    if not scheduled or scheduled[0].observation_state != "recorded":
        pytest.skip("the 21-session horizon is unreachable in this fixture's calendar")
    due_21 = scheduled[0].due_at
    # Run well after the 21-session session, before the 63-session one.
    late = due_21 + timedelta(days=5)
    summary, monitor = await _run(conn, late)
    assert summary["observed"] == {pid: [f"{scheduled[0].outcome_id}-observed"]}
    assert monitor.rows_written == 1
    assert conn.price_queries == [(case.thesis.security_id, due_21.date())]
    observed = next(r for r in _rows_of(conn, pid) if r.outcome_id.endswith("-observed"))
    assert observed.observed_at == due_21.date() and observed.return_state == "measured"
    assert observed.security_return_pct == Decimal("10.000000")  # 159.15 -> 175.065
    assert observed.benchmark_state == "unavailable_no_series" and observed.excess_return_pct is None
    # A third run with the same cutoff observes nothing new.
    again, monitor2 = await _run(conn, late)
    assert again["observed"] == {} and monitor2.rows_written == 0


async def test_a_missing_price_is_recorded_as_named_unavailability_not_skipped() -> None:
    case = await _case()
    pid = case.decision.decision_packet_id
    conn = FakeConn(packets={pid: case}, close=None)
    await _run(conn, case.decision.knowledge_cutoff + timedelta(hours=1))
    scheduled = [r for r in _rows_of(conn, pid) if r.horizon_trading_days == 21 and r.observation_state == "recorded"]
    if not scheduled:
        pytest.skip("the 21-session horizon is unreachable in this fixture's calendar")
    summary, _ = await _run(conn, scheduled[0].due_at + timedelta(days=1))
    assert summary["observed"] == {pid: [f"{scheduled[0].outcome_id}-observed"]}
    observed = next(r for r in _rows_of(conn, pid) if r.outcome_id.endswith("-observed"))
    assert observed.return_state == "unavailable_no_price" and observed.security_return_pct is None


async def test_one_packet_failing_is_noted_and_the_rest_continue() -> None:
    case = await _case()
    pid = case.decision.decision_packet_id
    conn = FakeConn(packets={pid: case, "dpk-broken-9-2026-09-01": case})
    original = job_mod.materialise_t0

    def _t0(c: DecisionCase, *, created_at: datetime) -> Any:
        if _t0.calls == 0:  # type: ignore[attr-defined]
            _t0.calls += 1  # type: ignore[attr-defined]
            raise job_mod.OutcomeError("evidence carries a non-numeric price token")
        return original(c, created_at=created_at)

    _t0.calls = 0  # type: ignore[attr-defined]
    with patch.object(job_mod, "materialise_t0", _t0):
        summary, monitor = await _run(conn, case.decision.knowledge_cutoff + timedelta(hours=1))
    # packets are visited in id order: the broken one first, then the real one continues
    assert list(summary["failed"]) == ["t0:dpk-broken-9-2026-09-01"]
    assert "non-numeric" in summary["failed"]["t0:dpk-broken-9-2026-09-01"]
    assert summary["t0_recorded"] == {pid: len(materialise_t0(case))}
    assert monitor.note is not None and "1 packet pass(es) failed" in monitor.note


async def test_everything_failing_is_a_failed_run() -> None:
    case = await _case()
    conn = FakeConn(packets={case.decision.decision_packet_id: case})
    with (
        patch.object(job_mod, "materialise_t0", side_effect=job_mod.OutcomeError("boom")),
        pytest.raises(RuntimeError, match="no outcome row written"),
    ):
        await _run(conn, case.decision.knowledge_cutoff + timedelta(hours=1))


async def test_main_is_behind_the_personal_use_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        await job_mod.main()


def test_daily_brief_observes_outcomes_right_after_the_packets_are_built() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/daily-brief.yml").read_text())
    job = next(iter(wf["jobs"].values()))
    names = [s.get("name") for s in job["steps"]]
    assert names.index("Observe decision outcomes") == names.index("Build decision packets") + 1
    assert settings.healthcheck_url_observe_decision_outcomes == ""


def test_no_verdict_surface_in_the_job() -> None:
    source = (ROOT / "jobs" / "observe_decision_outcomes.py").read_text()
    for word in ("alpha_claim", "verdict", "promote", "retire", "score"):
        assert word not in source.replace("no verdict", "")
