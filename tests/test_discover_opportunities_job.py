"""jobs/discover_opportunities.py — screen, rank, propose at pending_review; plus the service changes."""
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
from asxos.domain.discovery import ranker
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
        return None

    async def fetch(self, query: str, *args: object) -> list[Any]:
        if "FROM valuation_runs" in query:
            return [{"payload": r} for r in self.runs]
        if "FROM theses WHERE closed_at IS NULL" in query:
            return [{"symbol": s} for s in sorted(self.open_symbols)]
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


async def _run_job(conn: FakeConn, *screened: str, top_k: int = 10) -> tuple[dict[str, Any], FakeMonitor]:
    monitor = FakeMonitor()
    patches = _patched(conn, *screened)
    for p in patches:
        p.start()
    try:
        summary = await job_mod.run(monitor=monitor, top_k=top_k)
    finally:
        for p in patches:
            p.stop()
    return summary, monitor


async def test_job_proposes_the_cheap_liquid_name_at_pending_review_with_evidence() -> None:
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8")), _run("DEAR.AU", D("40"))])
    summary, monitor = await _run_job(conn, "CHEAP.AU", "DEAR.AU")
    assert summary["opened"] == [(101, "CHEAP.AU")] and monitor.rows_written == 1
    assert summary["screening_run_id"] == 42 and summary["opportunities"] == 1
    # the thesis row: research, pending_review, the baseline plan
    (args,) = conn.inserted_theses
    assert args[0] == "CHEAP.AU" and args[1] == "research" and args[14] == "pending_review"
    target = D(str(args[6]))
    assert D(str(args[4])) == (target * D("0.80")).quantize(D("0.000001"))
    assert args[7] == 365
    # the 'opened' revision carries the provenance the 0034/0057 constraints require
    (rev,) = [a for q, a in conn.executed if "INSERT INTO thesis_revisions" in q]
    assert rev[5] == "system_screen" and rev[6] == "verified"
    citations = json.loads(str(rev[7]))
    assert citations == ["asxos://valuation_runs/vr-CHEAP.AU-2026-09-19-zero_excess", "asxos://screening_runs/42"]
    # two evidence rows, both verified, with a snapshot hash
    assert [e[1:3] for e in conn.evidence] == [("system_screen", "verified"), ("system_screen", "verified")]
    assert {e[4] for e in conn.evidence} == {"valuation_runs", "screening_runs"}
    assert all(len(str(e[7])) == 64 for e in conn.evidence)
    # the screening rule is ensured before it is read
    assert any("INSERT INTO screening_rules" in q and "ON CONFLICT (name) DO NOTHING" in q for q, _ in conn.executed)


async def test_job_skips_names_that_already_have_an_open_thesis() -> None:
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8"))], open_symbols={"CHEAP.AU"})
    summary, monitor = await _run_job(conn, "CHEAP.AU")
    assert summary["opened"] == [] and monitor.rows_written == 0
    assert monitor.note is not None and "already have an open thesis" in monitor.note
    assert conn.inserted_theses == []


async def test_top_k_bounds_the_proposals_in_rank_order() -> None:
    runs = [_run(f"N{i}.AU", D("8")) for i in range(5)]
    conn = FakeConn(runs=runs)
    summary, _ = await _run_job(conn, *[f"N{i}.AU" for i in range(5)], top_k=2)
    assert [s for _, s in summary["opened"]] == ["N0.AU", "N1.AU"]


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
