"""jobs/build_decision_packets.py — every approved thesis, challenged on the paper book, daily."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml

import jobs.build_decision_packets as job_mod
from asxos.config import settings
from asxos.domain.decision_engine.challenge.rules import PortfolioState
from asxos.domain.decision_engine.sizer import SizingPolicy

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = datetime(2026, 9, 17, 20, 40, tzinfo=UTC)


class FakeConn:
    #: A thesis WITH a price plan, which is what every pre-existing test here
    #: assumes. `planless` names the subset that has none, so the partition
    #: added for issue #327 can be exercised without reshaping every fixture.
    def __init__(self, *, theses: list[tuple[int, str]], existing: set[str] = frozenset(), paper: str | None = "paper-daily-2026-09-17", planless: set[str] = frozenset(), uncovered: set[str] = frozenset()) -> None:  # type: ignore[assignment]
        self.theses = theses
        self.planless = set(planless)
        #: Symbols the data layer has NEVER held a statement for. Default empty,
        #: so every pre-existing fixture keeps its coverage and the second
        #: partition added for #327 is opt-in per test.
        self.uncovered = set(uncovered)
        self.existing = set(existing)
        self.paper = paper

    async def fetch(self, query: str, *args: object) -> list[Any]:
        if "FROM theses" in query:
            assert "governance_status = 'approved'" in query and "closed_at IS NULL" in query
            return [
                {
                    "thesis_id": t,
                    "symbol": s,
                    "entry_band_lower": None if s in self.planless else D("40"),
                    "entry_band_upper": None if s in self.planless else D("42"),
                    "stop_price": None if s in self.planless else D("36"),
                    "target_price": None if s in self.planless else D("55"),
                    "actual_entry_price": None,
                }
                for t, s in self.theses
            ]
        return []

    async def fetchrow(self, query: str, *args: object) -> Any:
        if "FROM decision_packets" in query:
            return {"?column?": 1} if args[0] in self.existing else None
        if "FROM paper_book_snapshots" in query:
            return None if self.paper is None else {"snapshot_id": self.paper}
        if "FROM rs_financial_statements" in query:
            return None if args[0] in self.uncovered else {"?column?": 1}
        return None


class FakeMonitor:
    def __init__(self) -> None:
        self.rows_written = 0
        self.note: str | None = None


def _state() -> PortfolioState:
    return PortfolioState(
        capital_aud=D("25000"), cash_pct=D("100"), gross_exposure_pct=D("0"), borrowing_aud=D("0"),
        sector_weights_pct={}, position_weights_pct={}, evidence_id="paper-book-paper-daily-2026-09-17",
    )


def _case(packet_id: str) -> Any:
    return SimpleNamespace(decision=SimpleNamespace(decision_packet_id=packet_id))


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


def _patches(conn: FakeConn, build: Any, save: Any) -> list[Any]:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    return [
        patch.object(job_mod, "acquire", side_effect=_acquire),
        patch.object(job_mod, "load_paper_book_state", AsyncMock(return_value=_state())),
        patch.object(job_mod, "load_sizing_policy", AsyncMock(return_value=SizingPolicy(capital_aud=D("25000"), position_cap_pct=D("10"), min_position_aud=D("1000")))),
        patch.object(job_mod, "load_annualised_vol", AsyncMock(return_value=D("0.2"))),
        patch.object(job_mod, "load_peer_vols", AsyncMock(return_value=())),
        patch.object(job_mod, "latest_run_for_symbol", AsyncMock(return_value=None)),
        patch.object(job_mod, "build_decision_case", build),
        patch.object(job_mod.repository, "save", save),
        # A-47: the writeback is a collaborator like the rest; its own behaviour is
        # pinned in tests/test_decision_writeback.py, not re-tested through the job.
        patch.object(job_mod, "record_packet_examination", AsyncMock(return_value=True)),
    ]


async def _run(conn: FakeConn, build: Any, save: Any | None = None) -> tuple[dict[str, Any], FakeMonitor]:
    monitor = FakeMonitor()
    save = save or AsyncMock()
    patches = _patches(conn, build, save)
    for p in patches:
        p.start()
    try:
        summary = await job_mod.run(monitor=monitor, cutoff=CUTOFF)
    finally:
        for p in patches:
            p.stop()
    return summary, monitor


async def test_builds_and_persists_one_packet_per_approved_thesis_on_the_paper_book() -> None:
    conn = FakeConn(theses=[(1, "CBA.AU"), (7, "HLI.AU")])
    build = AsyncMock(side_effect=lambda conn, **kw: _case(job_mod.packet_id_for("X.AU", kw["thesis_id"], kw["cutoff"])))
    save = AsyncMock()
    summary, monitor = await _run(conn, build, save)
    assert len(summary["built"]) == 2 and monitor.rows_written == 2 and summary["failed"] == {}
    assert save.await_count == 2
    kwargs = build.await_args_list[0].kwargs
    assert kwargs["cutoff"] == CUTOFF and kwargs["thesis_id"] == 1
    assert kwargs["context"].portfolio_state.evidence_id.startswith("paper-book-")
    assert "valuation" in kwargs
    assert summary["paper_snapshot_id"] == "paper-daily-2026-09-17"


async def test_same_day_packet_is_skipped_not_rebuilt() -> None:
    existing = job_mod.packet_id_for("CBA.AU", 1, CUTOFF)
    conn = FakeConn(theses=[(1, "CBA.AU")], existing={existing})
    build = AsyncMock()
    summary, monitor = await _run(conn, build)
    assert summary["skipped_same_day"] == [existing] and summary["built"] == []
    build.assert_not_awaited()
    assert monitor.rows_written == 0


async def test_one_failing_thesis_does_not_stop_the_others_and_is_noted() -> None:
    conn = FakeConn(theses=[(1, "CBA.AU"), (2, "BAD.AU"), (3, "HLI.AU")])

    async def build(conn: Any, **kw: Any) -> Any:
        if kw["thesis_id"] == 2:
            raise ValueError("thesis_id=2 has no entry/target/stop price plan on file")
        return _case(job_mod.packet_id_for("X.AU", kw["thesis_id"], kw["cutoff"]))

    summary, monitor = await _run(conn, build)
    assert len(summary["built"]) == 2 and list(summary["failed"]) == ["BAD.AU#2"]
    assert monitor.note is not None and "1 of 3 approved theses did not build" in monitor.note


async def test_everything_failing_is_a_failed_run() -> None:
    conn = FakeConn(theses=[(1, "CBA.AU")])
    build = AsyncMock(side_effect=RuntimeError("portfolio state is available only for the latest exact snapshot"))
    with pytest.raises(RuntimeError, match="no packet built"):
        await _run(conn, build)


async def test_no_paper_book_is_a_hard_fail_never_the_live_book() -> None:
    conn = FakeConn(theses=[(1, "CBA.AU")], paper=None)
    with pytest.raises(RuntimeError, match="paper_book_snapshots"):
        await _run(conn, AsyncMock())


async def test_no_approved_theses_is_a_noted_success() -> None:
    summary, monitor = await _run(FakeConn(theses=[]), AsyncMock())
    assert summary["built"] == [] and monitor.note == "no approved theses — nothing to challenge"


def test_packet_id_matches_the_builder_shape() -> None:
    assert job_mod.packet_id_for("CBA.AU", 1, CUTOFF) == "dpk-cba-1-2026-09-17"
    assert job_mod.packet_id_for("HUBS.NYSE", 13, CUTOFF) == "dpk-hubs-13-2026-09-17"


async def test_main_is_behind_the_personal_use_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE")
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        await job_mod.main()


def test_daily_brief_builds_packets_after_the_brief_is_sent() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/daily-brief.yml").read_text())
    job = next(iter(wf["jobs"].values()))
    names = [s.get("name") for s in job["steps"]]
    assert names.index("Build decision packets") == names.index("Compose and send brief") + 1
    assert job["env"]["ASXOS_PERSONAL_USE"] == "1"
    assert settings.healthcheck_url_build_decision_packets == ""


async def test_a_planless_approved_thesis_is_partitioned_out_not_failed() -> None:
    """Issue #327's shape, pinned.

    An approved thesis with no entry band, stop or target used to reach
    `build_decision_case`, raise, land in `failed`, and therefore in
    `monitor.note` — which `check_cron_health` turns into a nightly alert. It
    did that for eleven rows for 84 days (migration 0059) and for HUBS.NYSE
    until its statements land.

    It is now partitioned out before the builder is called: reported in the
    summary, absent from `failed`, and — the load-bearing half — silent in
    `monitor.note`.
    """
    conn = FakeConn(theses=[(1, "CBA.AU"), (9, "PLAN.AU")], planless={"PLAN.AU"})

    async def build(conn: Any, **kw: Any) -> Any:
        assert kw["thesis_id"] != 9, "the builder must never be called for a planless thesis"
        return _case(job_mod.packet_id_for("CBA.AU", kw["thesis_id"], kw["cutoff"]))

    summary, monitor = await _run(conn, build)
    assert summary["awaiting_plan"] == ["PLAN.AU#9"]
    assert summary["failed"] == {}
    assert len(summary["built"]) == 1
    assert monitor.note is None, (
        "a row waiting on James is not a job-health problem; a note here pages "
        "through check_cron_health every night until he acts"
    )


async def test_every_approved_thesis_awaiting_a_plan_is_a_quiet_success() -> None:
    """The degenerate case the candidates feature makes reachable.

    Right after James approves a batch of machine proposals and before he has
    written any plans, EVERY approved thesis is planless. Nothing is built and
    nothing failed — which must not trip the "no packet built" invariant, whose
    job is to catch a genuinely broken run.
    """
    conn = FakeConn(theses=[(1, "A.AU"), (2, "B.AU")], planless={"A.AU", "B.AU"})

    async def build(conn: Any, **kw: Any) -> Any:
        raise AssertionError("the builder must not be called at all")

    summary, monitor = await _run(conn, build)
    assert summary["built"] == [] and summary["failed"] == {}
    assert summary["awaiting_plan"] == ["A.AU#1", "B.AU#2"]
    assert monitor.note is None


async def test_a_symbol_the_vendor_has_never_covered_is_set_aside_not_failed() -> None:
    """Issue #327, the second structural precondition.

    `build_decision_case` needs an admissible yearly income row. When the data
    layer has NEVER held a statement for the symbol, no run will ever produce
    one — so calling the builder re-raises the same ValueError every night into
    `monitor.note`, which pages through check_cron_health forever.

    Measured 2026-09-19: after the first weekly-research run carrying #328's
    held-US-name union concluded `success` and wrote 437,031 statement rows,
    HUBS.NYSE still had zero — as did every non-.AU symbol, 0 of 3,379 distinct.
    The vendor does not serve them. Coverage is not this job's health.
    """
    conn = FakeConn(theses=[(1, "CBA.AU"), (2, "HUBS.NYSE")], uncovered={"HUBS.NYSE"})

    async def build(conn: Any, **kw: Any) -> Any:
        assert kw["thesis_id"] != 2, "the builder must not be called for an uncovered name"
        return _case(job_mod.packet_id_for("CBA.AU", kw["thesis_id"], kw["cutoff"]))

    summary, monitor = await _run(conn, build)
    assert summary["no_data_coverage"] == ["HUBS.NYSE#2"]
    assert summary["failed"] == {}
    assert len(summary["built"]) == 1
    assert monitor.note is None, (
        "a name the vendor does not cover is not a job-health problem; a note "
        "here pages nightly on a condition nobody can fix"
    )


async def test_a_covered_symbol_that_fails_at_the_cutoff_still_fails_loudly() -> None:
    """The safety property of the partition, and the reason it tests EVER not AT-CUTOFF.

    A symbol WITH statement history whose cutoff yields nothing admissible is a
    regression — vendor gap, ingestion break, a bad cutoff — and must keep
    paging. If this test ever goes green while the one above does too on the
    same input, the partition has become a mute button.
    """
    conn = FakeConn(theses=[(1, "CBA.AU"), (2, "HLI.AU")])  # both covered

    async def build(conn: Any, **kw: Any) -> Any:
        if kw["thesis_id"] == 2:
            raise ValueError("no admissible yearly income row for HLI.AU at knowledge cutoff")
        return _case(job_mod.packet_id_for("CBA.AU", kw["thesis_id"], kw["cutoff"]))

    summary, monitor = await _run(conn, build)
    assert summary["no_data_coverage"] == [], "a covered name must never land in the quiet bucket"
    assert "HLI.AU#2" in summary["failed"]
    assert monitor.note is not None and "1 of 2" in monitor.note


async def test_coverage_is_checked_before_the_builder_not_after() -> None:
    """Checking after would still raise, still land in `failed`, still page.

    The partition only works because it happens BEFORE `build_one` is called —
    the same shape as the price-plan partition above it.
    """
    conn = FakeConn(theses=[(1, "HUBS.NYSE")], uncovered={"HUBS.NYSE"})

    async def build(conn: Any, **kw: Any) -> Any:
        raise AssertionError("the builder must not be called at all")

    summary, monitor = await _run(conn, build)
    assert summary["built"] == [] and summary["failed"] == {}
    assert summary["no_data_coverage"] == ["HUBS.NYSE#1"]
    assert monitor.note is None
