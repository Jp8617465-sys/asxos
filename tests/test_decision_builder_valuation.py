"""S2: the residual-income model reaches the challenge through `build_decision_case(valuation=)`.

Before this slice `builder.py` never read `valuation_runs` and `rule_valuation_percentile`
was never fed by the model (code trace 2026-09-16). Now a `ValuationRun` becomes a
`valuation_fact` evidence item citing the persisted run and, when valued, the
`valuation_gap` input the sixteenth rule reads.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from asxos.domain.decision_engine import builder, repository
from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.valuation import sweep
from asxos.domain.valuation.contracts import ValuationRun
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.universe import MarketInputs, UniverseRow
from tests.test_decision_builder_wave5 import (
    AS_OF,
    CUTOFF,
    _candidate,
    _Conn,
    _context,
    _thesis_row,
)

PREREG = load_bundled_preregistration()
MARKET = MarketInputs(D("0.04831"), date(2026, 8, 31), D("0.7134"), date(2026, 8, 31))
KE = sweep.ke_band_for(MARKET, PREREG)
RUN_CUTOFF = CUTOFF - timedelta(hours=1)


def _run(symbol: str = "CBA.AU", *, book: D = D("47.015532"), roe: D | None = D("0.138062")) -> ValuationRun:
    row = UniverseRow(
        symbol=symbol, pit_as_of=date(2026, 6, 30), pit_knowledge_date=date(2026, 8, 12),
        book_value_ps=book, roe=roe, eps_ttm=D("6.491039"), dividend_ttm=D("4.95"),
        franking_avg_pct=D("100"), currency="AUD", roe_average=roe, roe_periods=3,
        last_close_dt=AS_OF, last_close=D("159.15"),
    )
    return sweep.value_row(row, market=MARKET, ke=KE, prereg=PREREG, cutoff=RUN_CUTOFF, created_at=RUN_CUTOFF)


async def _build(cutoff=CUTOFF, **kw: object):  # type: ignore[no-untyped-def]
    conn = _Conn(thesis_row=_thesis_row(), close=D("159.15"), close_dt=AS_OF)
    return await builder.build_decision_case(conn, cutoff=cutoff, thesis_id=1, candidate=_candidate(), **kw)  # type: ignore[arg-type]


async def test_valued_run_becomes_evidence_and_feeds_the_gap_rule() -> None:
    run = _run()  # CBA at the baseline inputs: value 67.496381 against a 60 target
    case = await _build(context=_context(), valuation=run)
    item = next(i for i in case.evidence.items if i.evidence_type == "valuation_fact")
    assert item.evidence_id == "cba-valuation-2026-09-01"
    assert item.source_uri == f"asxos://valuation_runs/{run.run_id}"
    assert run.content_hash in item.claim and "value_per_share=67.496381" in item.claim
    assert item.known_at == RUN_CUTOFF and item.observed_at == AS_OF
    # gap = (60 - 67.496381) / 67.496381 * 100 = -11.106% -> inside the band, evaluated, no finding
    assert not any(f.finding.startswith("The thesis target price sits") for f in case.challenge.findings)
    assert "valuation_gap" not in case.challenge.strongest_bear_case
    assert not any("Model value for the name" in m for m in case.decision.missing_or_uncertain_inputs)
    assert verify_content_hash(case.decision) and verify_content_hash(case.evidence)


async def test_target_far_above_model_value_is_a_material_finding_citing_the_run() -> None:
    run = _run(book=D("5"), roe=D("0.10"))  # a small book: value ~ 6-7 against a 60 target
    case = await _build(context=_context(), valuation=run)
    finding = next(f for f in case.challenge.findings if "above the model's registered value" in f.finding)
    assert finding.severity == "material"
    assert finding.evidence_ids == ("cba-valuation-2026-09-01", "cba-thesis-narrative")
    assert case.challenge.outcome == "abstain"  # price_detached still blocks on the live plan


async def test_blocked_run_is_evidence_but_no_gap() -> None:
    run = _run(roe=D("-0.05"))
    assert run.outcome == "blocked"
    case = await _build(context=_context(), valuation=run)
    item = next(i for i in case.evidence.items if i.evidence_type == "valuation_fact")
    assert "blocked" in item.title and "roe_non_positive" in item.claim
    assert "valuation_gap" in case.challenge.strongest_bear_case  # reported unevaluated
    assert any("Model value for the name" in m for m in case.decision.missing_or_uncertain_inputs)


async def test_no_valuation_is_declared_missing_and_the_rule_is_unevaluated() -> None:
    case = await _build(context=_context())
    assert not any(i.evidence_type == "valuation_fact" for i in case.evidence.items)
    assert any("Model value for the name" in m for m in case.decision.missing_or_uncertain_inputs)
    assert "valuation_gap" in case.challenge.strongest_bear_case


async def test_context_measured_gap_wins_over_the_derived_one() -> None:
    case = await _build(context=_context(valuation_gap_pct=D("80")), valuation=_run())
    finding = next(f for f in case.challenge.findings if "above the model's registered value" in f.finding)
    assert "80" in finding.finding


async def test_no_context_path_still_carries_the_evidence_item() -> None:
    case = await _build(valuation=_run())
    assert any(i.evidence_type == "valuation_fact" for i in case.evidence.items)
    assert case.decision.recommendation_state == "abstain"


async def test_wrong_symbol_is_refused() -> None:
    with pytest.raises(ValueError, match=r"is for NAB\.AU"):
        await _build(context=_context(), valuation=_run("NAB.AU"))


async def test_run_built_after_the_cutoff_is_refused() -> None:
    """A run known after the packet cutoff would be evidence from the future."""
    with pytest.raises(ValueError, match="after the requested knowledge cutoff"):
        await _build(cutoff=RUN_CUTOFF - timedelta(hours=1), context=_context(), valuation=_run())


async def test_case_with_valuation_evidence_round_trips_through_the_repository() -> None:
    from tests.test_decision_engine_persistence import _FakeRepoConn

    case = await _build(context=_context(), valuation=_run())
    repo = _FakeRepoConn()
    await repository.save(case, conn=repo)
    loaded = await repository.load_case(case.decision.decision_packet_id, conn=repo)
    assert loaded.evidence == case.evidence and loaded.challenge == case.challenge
