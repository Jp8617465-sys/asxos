"""jobs/discover_opportunities.py — screen, record, and propose at pending_review.

The proposal half was removed by #306 and restored by James on 2026-09-17; the
target/entry-band/rank half stays deleted. Tests below assert both halves.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal as D
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml

import jobs.discover_opportunities as job_mod
from asxos.domain.discovery import proposals, ranker
from asxos.domain.results_review.pit_db import ResultsReviewAdapterError
from asxos.domain.screening.types import ScreenMatch, ScreenRunResult
from asxos.domain.theses import service as thesis_service
from asxos.domain.valuation import sweep
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.universe import MarketInputs, UniverseRow
from tests.test_thesis_service import _make_thesis_row

ROOT = Path(__file__).resolve().parents[1]
PREREG = load_bundled_preregistration()
MARKET = MarketInputs(D("0.04831"), date(2026, 9, 15), D("0.7134"), date(2026, 9, 14))
KE = sweep.ke_band_for(MARKET, PREREG)
CUTOFF = datetime(2026, 9, 19, 16, 0, tzinfo=UTC)
AS_OF = CUTOFF.date()


def _run(symbol: str, close: D) -> dict[str, Any]:
    row = UniverseRow(
        symbol=symbol, pit_as_of=date(2026, 6, 30), pit_knowledge_date=date(2026, 8, 30),
        book_value_ps=D("10"), roe=D("0.20"), eps_ttm=D("1"), dividend_ttm=D("0.5"), franking_avg_pct=D("100"),
        currency="AUD", roe_average=D("0.18"), roe_periods=3, last_close_dt=date(2026, 9, 18), last_close=close,
    )
    return sweep.value_row(row, market=MARKET, ke=KE, prereg=PREREG, cutoff=CUTOFF, created_at=CUTOFF).model_dump(mode="json")


class FakeConn:
    """Enough of asyncpg for the job: screening rule row, valuation payloads, theses, evidence."""

    def __init__(self, *, runs: list[dict[str, Any]], open_symbols: set[str] = frozenset()) -> None:  # type: ignore[assignment]
        self.runs = runs
        self.open_symbols = set(open_symbols)
        self.queue_depth = 0
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.inserted_theses: list[tuple[object, ...]] = []
        self.evidence: list[tuple[object, ...]] = []
        self.next_thesis_id = 100

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return "INSERT 0 1"

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        if "FROM screening_rules" in query:
            return {
                "id": 9, "name": job_mod.SCREEN_RULE_NAME, "source_method": "curated_composite",
                "rule_json_raw": json.dumps(job_mod.SCREEN_RULE_JSON), "is_active": True,
            }
        if "INSERT INTO theses" in query:
            self.inserted_theses.append(args)
            self.next_thesis_id += 1
            return _make_thesis_row(thesis_id=self.next_thesis_id, symbol=str(args[0]), status=str(args[1]), governance_status=str(args[14]))
        if "INSERT INTO thesis_evidence" in query:
            self.evidence.append(args)
            return {"evidence_id": len(self.evidence)}
        if "pending_review" in query and "count(*)" in query:
            return {"n": self.queue_depth}
        return None

    async def fetch(self, query: str, *args: object) -> list[Any]:
        if "FROM valuation_runs" in query:
            return [{"payload": r} for r in self.runs]
        if "FROM theses" in query and "ANY($1::text[])" in query:
            # The suppression predicate. `open_symbols` now means "symbols the
            # predicate would suppress" — queued, on the book, or inside the
            # cooling-off window after a rejection.
            asked = set(args[0]) if args else set()
            return [{"symbol": s} for s in sorted(self.open_symbols & asked)]
        return []

    def transaction(self) -> Any:
        @asynccontextmanager
        async def _tx() -> Any:
            yield

        return _tx()


def _screen_result(*symbols: str) -> ScreenRunResult:
    matches = tuple(
        ScreenMatch(symbol=s, sector="Financials", values={"avg_daily_value_aud_90d": D("2000000"), "market_cap": D("500000000")})
        for s in symbols
    )
    return ScreenRunResult(
        rule_id=9, rule_name=job_mod.SCREEN_RULE_NAME, sector_scope=None, universe_size=1880,
        matches=matches, match_count=len(matches), duration_ms=5, all_symbols=tuple(symbols),
    )


class FakeMonitor:
    def __init__(self) -> None:
        self.rows_written = 0
        self.note: str | None = None


def _patched(conn: FakeConn, *screened: str) -> Any:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    class _Clock:
        @staticmethod
        def today() -> date:
            return AS_OF

    return (
        patch.object(job_mod, "acquire", side_effect=_acquire),
        patch.object(job_mod, "evaluate_rule", AsyncMock(return_value=_screen_result(*screened))),
        patch.object(job_mod, "log_run", AsyncMock(return_value=42)),
        patch.object(job_mod, "clock", _Clock),
    )


async def _run_job(conn: FakeConn, *screened: str) -> tuple[dict[str, Any], FakeMonitor]:
    monitor = FakeMonitor()
    patches = _patched(conn, *screened)
    for p in patches:
        p.start()
    try:
        summary = await job_mod.run(monitor=monitor)
    finally:
        for p in patches:
            p.stop()
    return summary, monitor


async def test_job_proposes_each_survivor_at_pending_review() -> None:
    """The proposal half, restored (James, 2026-09-17) with the target half still deleted.

    #306 demoted this job to recording the screen and opening nothing, because
    the sealed test returned null. What the RESPONSE_RULE actually forbids is
    "target prices, entry bands and ranked 'opportunities'" — not the existence
    of a reviewable queue. So the row is opened with no price plan at all, and
    the demotion holds where it was aimed.
    """
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8")), _run("DEAR.AU", D("40"))])
    summary, monitor = await _run_job(conn, "CHEAP.AU", "DEAR.AU")
    assert summary["passing"] == ["CHEAP.AU"]
    assert summary["opened"] == ["CHEAP.AU#101"]
    assert summary["suppressed_existing"] == [] and summary["breaker"] is None
    assert monitor.rows_written == 1
    # The degraded channel stays empty: a routine weekly outcome written into
    # `note` pages through check_cron_health every Saturday (issue #327).
    assert monitor.note is None
    # No price plan on the inserted row — entry band, stop and target are the
    # 4th/5th/6th/7th bound parameters of open_thesis's INSERT.
    (args,) = conn.inserted_theses
    assert args[3] is None and args[4] is None and args[5] is None and args[6] is None
    assert args[14] == "pending_review"
    # Two thesis_evidence rows, or approve_object hard-fails and James cannot
    # action the proposal at all.
    assert len(conn.evidence) == 2
    # args are 0-indexed against add_thesis_evidence's bind order:
    # thesis_id, source_agent, tier, claim_text, source_table, ...
    assert {str(a[4]) for a in conn.evidence} == {"valuation_runs", "screening_runs"}
    assert any("INSERT INTO screening_rules" in q and "ON CONFLICT (name) DO NOTHING" in q for q, _ in conn.executed)


async def test_a_symbol_already_in_the_queue_is_not_proposed_again() -> None:
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8"))], open_symbols={"CHEAP.AU"})
    summary, monitor = await _run_job(conn, "CHEAP.AU")
    assert summary["passing"] == ["CHEAP.AU"]
    assert summary["opened"] == [] and summary["suppressed_existing"] == ["CHEAP.AU"]
    assert conn.inserted_theses == []
    assert monitor.note is None


async def test_the_queue_depth_breaker_opens_nothing_rather_than_choosing() -> None:
    """It drops the whole week, never a subset.

    Taking the alphabetically-first N of a passing set is a rank pretending not
    to be one: it silently discards names on an alphabetical accident. Refusing
    the run is honest and self-correcting — dispose of a few and the flow
    resumes.
    """
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8"))])
    conn.queue_depth = proposals.MAX_OPEN_QUEUE
    summary, monitor = await _run_job(conn, "CHEAP.AU")
    assert summary["opened"] == []
    assert summary["breaker"] is not None and "awaiting review" in summary["breaker"]
    assert conn.inserted_theses == []
    assert monitor.note is None, "a full queue is James's state, not a job failure"


async def test_a_malformed_vendor_symbol_is_refused_before_any_row_is_written() -> None:
    """Fail-early (rule #10), from the security review of #332.

    `open_thesis` checks only the .AU/.US suffix, and the vendor-namespaced
    regex every packet is built under was otherwise first applied at packet
    time -- after approval. A survivor that would fail it is refused before
    any INSERT, not discovered a week later when the builder raises.
    """
    conn = FakeConn(runs=[_run("BAD-SYM.AU", D("8"))])
    with pytest.raises(ResultsReviewAdapterError, match="not a vendor-namespaced"):
        await _run_job(conn, "BAD-SYM.AU")
    assert conn.inserted_theses == [] and conn.evidence == []


async def test_a_runaway_screen_refuses_loudly_instead_of_flooding_the_queue() -> None:
    """A gate breaking is not a bumper crop of ideas (CLAUDE.md #10)."""
    symbols = [f"S{i:03d}.AU" for i in range(proposals.MAX_OPENS_PER_RUN + 1)]
    conn = FakeConn(runs=[_run(s, D("8")) for s in symbols])
    with pytest.raises(proposals.RunawayScreen, match="runaway guard"):
        await _run_job(conn, *symbols)
    assert conn.inserted_theses == []


async def test_job_refuses_without_a_valuation_run() -> None:
    conn = FakeConn(runs=[])
    with pytest.raises(RuntimeError, match="run_valuation must precede"):
        await _run_job(conn, "CHEAP.AU")


async def test_main_is_behind_the_personal_use_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        await job_mod.main()


# --- the service changes -----------------------------------------------------------


async def test_open_thesis_refuses_a_non_human_source_as_approved() -> None:
    conn = FakeConn(runs=[])
    with pytest.raises(ValueError, match="cannot open as approved"):
        await thesis_service.open_thesis(conn, "X.AU", source="system_screen", governance_status="approved")  # type: ignore[arg-type]


async def test_revision_for_a_non_human_source_needs_evidence() -> None:
    conn = FakeConn(runs=[])
    with pytest.raises(ValueError, match="evidence_confidence"):
        await thesis_service.open_thesis(conn, "X.AU", source="system_screen", governance_status="pending_review")  # type: ignore[arg-type]


async def test_human_open_thesis_is_unchanged_and_opens_approved() -> None:
    conn = FakeConn(runs=[])
    thesis = await thesis_service.open_thesis(conn, "X.AU", reasoning="human")  # type: ignore[arg-type]
    assert thesis.governance_status == "approved"
    (rev,) = [a for q, a in conn.executed if "INSERT INTO thesis_revisions" in q]
    assert rev[5] == "human" and rev[6] is None and json.loads(str(rev[7])) == []


async def test_evidence_hash_is_over_canonical_json() -> None:
    import hashlib

    conn = FakeConn(runs=[])
    data = {"b": D("1.5"), "a": "x"}
    await thesis_service.add_thesis_evidence(
        conn, thesis_id=1, source_agent="system_screen", tier="verified", claim_text="c",  # type: ignore[arg-type]
        source_table="valuation_runs", source_as_of=CUTOFF, snapshot_data=data,
    )
    (args,) = conn.evidence
    canonical = '{"a":"x","b":"1.5"}'
    assert args[6] == canonical and args[7] == hashlib.sha256(canonical.encode()).hexdigest()
    with pytest.raises(ValueError, match="tier"):
        await thesis_service.add_thesis_evidence(
            conn, thesis_id=1, source_agent="x", tier="guess", claim_text="c",  # type: ignore[arg-type]
            source_table="t", source_as_of=CUTOFF, snapshot_data={},
        )


# --- workflow ----------------------------------------------------------------------


def test_weekly_research_discovers_after_the_valuation_with_the_firewall_set() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/weekly-research.yml").read_text())
    job = wf["jobs"]["research"]
    names = [s.get("name") for s in job["steps"]]
    assert names.index("Discover opportunities") == names.index("Run valuation") + 1
    assert job["env"]["ASXOS_PERSONAL_USE"] == "1"


def test_screen_rule_is_the_baseline_liquidity_screen() -> None:
    items = {i["field"]: (i["op"], i["value"]) for i in job_mod.SCREEN_RULE_JSON["conditions"]["items"]}
    assert items == {"avg_daily_value_aud_90d": ("gte", 250000), "market_cap": ("gte", 100000000)}
    assert int(ranker.MIN_ADV_AUD) == 250000 and int(ranker.MIN_MARKET_CAP_AUD) == 100000000
