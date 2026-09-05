"""Wave 5 builder generalisation — campaign node H5-C.

`build_decision_case()` runs the Slice 2.5 challenger and the Slice 2 sizer
when a `ChallengeContext` is supplied, merges a Stage 3 `CandidateSnapshot`'s
evidence, and keeps the Slice 1 CBA wrapper's behaviour when no context is
given. The live CBA thesis #1 (entry band 42-45 against a close of 159.15)
stays `abstain` with `price_detached` blocking — that is the governor-drafts
C5 check landing as code, and the readiness criterion, not a failure.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from asxos.domain.decision_engine import builder, repository
from asxos.domain.decision_engine.builder import ChallengeContext
from asxos.domain.decision_engine.challenge import DispositionLog, PortfolioState
from asxos.domain.decision_engine.challenge import log as dlog
from asxos.domain.decision_engine.sizer import SizingPolicy, VolInput
from asxos.domain.decision_engine.types import EvidenceItem, verify_content_hash
from asxos.domain.themes.candidates.builder import cutoff_instant
from asxos.domain.themes.candidates.types import CandidateSnapshot

CUTOFF = datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC)
AS_OF = CUTOFF.date()
REVISITED = datetime(2026, 8, 1, tzinfo=UTC)


class _Conn:
    def __init__(self, *, thesis_row: Mapping[str, object], close: Decimal | None, close_dt: date | None) -> None:
        self.thesis_row, self.close, self.close_dt = thesis_row, close, close_dt
        self.queries: list[str] = []

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, object] | None:
        self.queries.append(query)
        lowered = query.lower()
        if "from theses" in lowered:
            return self.thesis_row
        if "max(period_end)" in lowered:
            return {"period_end": date(2026, 6, 30)}
        if "from rs_financial_statements" in lowered:
            pe = args[1]
            assert isinstance(pe, date)
            return {"symbol": args[0], "period_end": pe, "report_date": date(pe.year, 8, 11), "filing_date": date(pe.year, 8, 11)}
        if "from prices" in lowered:
            return None if self.close is None else {"dt": self.close_dt, "close": self.close}
        raise AssertionError(query)

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, object]]:
        raise AssertionError(query)


def _thesis_row(**kw: Any) -> dict[str, object]:
    row: dict[str, object] = {
        "thesis_id": 1, "symbol": "CBA.AU", "status": "watching",
        "thesis_text": "CBA's deposit franchise supports durable ROE; entry is conditional on the stated band.",
        "entry_band_lower": Decimal("42"), "entry_band_upper": Decimal("45"), "stop_price": Decimal("38"),
        "target_price": Decimal("60"), "timeline_days": 365,
        "invalidation_conditions": json.dumps([{"condition": "NIM below 1.80% for two consecutive halves", "status": "active", "note": None}]),
        "themes": ["big-4-banks"], "actual_entry_price": None, "actual_entry_at": None, "actual_exit_price": None,
        "actual_exit_at": None, "last_revisited_at": REVISITED, "revisit_due_at": REVISITED + timedelta(days=30),
        "opened_at": REVISITED, "closed_at": None, "analyst_buy_count": None, "analyst_neutral_count": None,
        "analyst_sell_count": None, "analyst_consensus_target": None, "analyst_updated_at": None,
        "next_earnings_date": None, "earnings_notes": None, "conviction_level": None, "tax_notes": None,
        "governance_status": "approved", "report_sections": None,
    }
    row.update(kw)
    return row


def _context(**kw: Any) -> ChallengeContext:
    base: dict[str, Any] = {
        "portfolio_state": PortfolioState(
            capital_aud=Decimal("500000"), cash_pct=Decimal("20"), gross_exposure_pct=Decimal("80"),
            borrowing_aud=Decimal("0"), sector_weights_pct={"Financials": Decimal("22")},
            position_weights_pct={}, evidence_id="cba-thesis-narrative",
        ),
        "sizing": SizingPolicy(capital_aud=Decimal("500000"), position_cap_pct=Decimal("10"), min_position_aud=Decimal("5000")),
        "proposed_annualised_vol": Decimal("0.20"),
        "peers": (VolInput(symbol="NAB.AU", annualised_vol=Decimal("0.25")),),
        "base_rate_evidence_ids": ("cba-income-prior",),
    }
    base.update(kw)
    return ChallengeContext(**base)


def _candidate() -> CandidateSnapshot:
    cutoff = cutoff_instant(AS_OF)
    ev = EvidenceItem(
        evidence_id="candidate:price:CBA.AU", evidence_type="market_fact", title="CBA.AU last close",
        claim="prices symbol=CBA.AU dt=2026-09-01 close=159.150000 median_dollar_volume_60d=250000000.000000 sessions=60",
        source_uri="db://prices/CBA.AU/2026-09-01", observed_at=AS_OF, known_at=cutoff, evidence_tier="verified", data_mode="real",
    )
    return CandidateSnapshot(
        candidate_id="cand-big-4-banks-CBA.AU-2026-09-01", symbol="CBA.AU", theme_version_id="tv-big-4-banks-2026-09-01",
        theme_code="big-4-banks", exposure_direction="positive",
        measures={"gics_sector": "Financials", "median_dollar_volume_60d": "250000000.000000", "last_close": "159.150000"},
        quality_checks={"has_sector": "pass"}, as_of=AS_OF, knowledge_cutoff=cutoff,
        expires_at=cutoff + timedelta(days=30), evidence=(ev,), data_mode="real", created_at=cutoff,
    )


async def test_live_cba_thesis_1_stays_abstain_with_price_detached_blocking() -> None:
    conn = _Conn(thesis_row=_thesis_row(), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_cba_decision_case(conn, cutoff=CUTOFF, candidate=_candidate(), context=_context())
    assert case.decision.recommendation_state == "abstain" and case.challenge.outcome == "abstain"
    blocking = [f for f in case.challenge.findings if f.severity == "blocking"]
    assert len(blocking) == 1 and "detached" in blocking[0].finding and "2.624138" in blocking[0].finding
    assert set(blocking[0].evidence_ids) == {"cba-last-close", "cba-thesis-narrative"}
    assert "cba-last-close" in {i.evidence_id for i in case.evidence.items}
    assert "candidate:price:CBA.AU" in {i.evidence_id for i in case.evidence.items}
    assert case.decision.size_range.maximum_pct == 0
    assert verify_content_hash(case.decision)
    assert any("from prices" in q.lower() for q in conn.queries)


async def test_revised_band_passes_the_challenge_and_earns_watch_not_action() -> None:
    row = _thesis_row(entry_band_lower=Decimal("150"), entry_band_upper=Decimal("165"), stop_price=Decimal("140"), target_price=Decimal("185"))
    conn = _Conn(thesis_row=row, close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context())
    assert case.challenge.outcome == "pass" and case.decision.recommendation_state == "watch"
    # the register never lets a non-action state carry size, and tax readiness is unknown (G12)
    assert case.decision.size_range.maximum_pct == 0 and case.decision.tax_assessment_reference.readiness == "unknown"
    assert "8.000000%" in case.portfolio.marginal_risk  # indicative: sector headroom 30 - 22 binds
    assert case.portfolio.constraints[-1].name == "decision_evidence_freshness" and case.portfolio.constraints[-1].status == "pass"
    assert case.challenge.challenge_result_id == "chr-cba-1-2026-09-01"


async def test_material_finding_needs_a_disposition_before_pass() -> None:
    row = _thesis_row(entry_band_lower=Decimal("150"), entry_band_upper=Decimal("165"), stop_price=Decimal("140"), target_price=Decimal("185"))
    conn = _Conn(thesis_row=row, close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context(base_rate_evidence_ids=()))
    assert case.challenge.outcome == "revise" and case.decision.recommendation_state == "abstain"
    material = next(f for f in case.challenge.findings if f.severity == "material")
    log = dlog.record(DispositionLog(), material, disposition="accepted", reason="base rate tracked in Slice 5", at=CUTOFF)
    again = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context(base_rate_evidence_ids=(), dispositions=log))
    assert again.challenge.outcome == "pass"


async def test_no_context_path_is_the_honest_slice1_abstain_and_issues_no_price_query() -> None:
    conn = _Conn(thesis_row=_thesis_row(), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_cba_decision_case(conn, cutoff=CUTOFF)
    assert case.decision.recommendation_state == "abstain"
    assert "did not run" in case.decision.missing_or_uncertain_inputs[1]
    assert not any("from prices" in q.lower() for q in conn.queries)
    assert case.challenge.findings[0].severity == "blocking"


async def test_missing_price_is_a_data_integrity_block() -> None:
    conn = _Conn(thesis_row=_thesis_row(), close=None, close_dt=None)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, context=_context())
    assert case.challenge.outcome == "abstain"
    assert any("missing data" in f.finding for f in case.challenge.findings)
    assert case.portfolio.constraints[-1].status == "fail"


async def test_wrapper_and_candidate_symbol_guards() -> None:
    conn = _Conn(thesis_row=_thesis_row(symbol="NAB.AU"), close=Decimal("40"), close_dt=AS_OF)
    with pytest.raises(ValueError, match=r"scoped to CBA\.AU"):
        await builder.build_cba_decision_case(conn, cutoff=CUTOFF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1)  # generalised: any symbol
    assert case.case_id.startswith("nab-1-")
    with pytest.raises(ValueError, match="not the thesis symbol"):
        await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate())


async def test_challenged_case_round_trips_through_the_repository() -> None:
    from tests.test_decision_engine_persistence import _FakeRepoConn

    conn = _Conn(thesis_row=_thesis_row(), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_cba_decision_case(conn, cutoff=CUTOFF, candidate=_candidate(), context=_context())
    repo = _FakeRepoConn()
    await repository.save(case, conn=repo)
    loaded = await repository.load_case(case.decision.decision_packet_id, conn=repo)
    # the repository reconstructs case_id/label itself (Slice 1 behaviour); the artifacts are identical
    assert loaded.decision == case.decision and loaded.challenge == case.challenge and loaded.evidence == case.evidence
    assert "challenge_results" in repo.tables and len(loaded.challenge.findings) == len(case.challenge.findings)
