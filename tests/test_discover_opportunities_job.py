"""jobs/discover_opportunities.py — screen and record, open nothing (#306); plus the service changes."""
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


async def test_job_records_the_screen_and_opens_no_thesis() -> None:
    """#306: the passing set is logged; no thesis, revision or evidence row is written."""
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8")), _run("DEAR.AU", D("40"))])
    summary, monitor = await _run_job(conn, "CHEAP.AU", "DEAR.AU")
    assert summary["passing"] == ["CHEAP.AU"] and summary["opened"] == []
    assert summary["screening_run_id"] == 42 and summary["valued_runs"] == 2
    assert monitor.rows_written == 0
    assert monitor.note is not None and "#306" in monitor.note and "1 names pass" in monitor.note
    assert conn.inserted_theses == [] and conn.evidence == []
    assert not any("INSERT INTO thes" in q for q, _ in conn.executed)
    # the screening rule is still ensured before it is read — the audit row is the job's record
    assert any("INSERT INTO screening_rules" in q and "ON CONFLICT (name) DO NOTHING" in q for q, _ in conn.executed)


async def test_job_never_reads_open_theses_because_it_proposes_none() -> None:
    conn = FakeConn(runs=[_run("CHEAP.AU", D("8"))], open_symbols={"CHEAP.AU"})
    summary, _ = await _run_job(conn, "CHEAP.AU")
    assert summary["passing"] == ["CHEAP.AU"] and summary["opened"] == []
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
