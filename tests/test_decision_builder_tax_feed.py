"""The builder with the G12 feed (S9): a real-mode pass earns `watch`, never an action state or size."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from asxos.domain.decision_engine import builder
from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.tax import feed
from tests.test_decision_builder_wave5 import (
    AS_OF,
    CUTOFF,
    _candidate,
    _Conn,
    _context,
    _thesis_row,
)

IN_BAND = {"entry_band_lower": Decimal("150"), "entry_band_upper": Decimal("165"), "stop_price": Decimal("140"), "target_price": Decimal("185")}


def _rec(ex: date, franking: Decimal | None = Decimal("100"), symbol: str = "CBA.AU") -> feed.DividendRecord:
    return feed.DividendRecord(symbol=symbol, ex_date=ex, pay_date=None, dividend_amount=Decimal("2.50"), franking_pct=franking)


def _feed(*records: feed.DividendRecord, cutoff: datetime = CUTOFF, symbol: str = "CBA.AU") -> feed.DividendCharacterisation:
    return feed.characterise_dividends(list(records), symbol=symbol, cutoff=cutoff)


async def test_pass_earns_watch_not_action_and_the_g12_line_disappears() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    dividends = _feed(_rec(AS_OF - timedelta(days=200)), _rec(AS_OF - timedelta(days=20)))
    case = await builder.build_decision_case(
        conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context(), dividends=dividends
    )
    assert case.challenge.outcome == "pass" and case.decision.recommendation_state == "watch"
    ref = case.decision.tax_assessment_reference
    assert (ref.readiness, ref.applicability) == ("pass", "applicable")
    assert case.decision.size_range.maximum_pct == 0
    assert not any("G12" in m for m in case.decision.missing_or_uncertain_inputs)
    item = next(i for i in case.evidence.items if i.evidence_type == "tax_fact")
    assert item.evidence_id == "cba-dividends-2026-09-01" and item.data_mode == "real"
    assert item.known_at == dividends.known_at and "readiness=pass" in item.claim
    assert item.evidence_id in case.thesis.evidence_ids
    assert any("rs_corporate_actions" in m.version for m in case.decision.model_and_prompt_manifest)
    assert verify_content_hash(case.evidence) and verify_content_hash(case.decision)
    assert case.decision.upstream_hashes.tax_assessment_reference == ref.content_hash


async def test_undeclared_franking_keeps_readiness_unknown_and_declares_the_gap() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    dividends = _feed(_rec(AS_OF - timedelta(days=20), franking=None))
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context(), dividends=dividends)
    assert case.decision.tax_assessment_reference.readiness == "unknown"
    gap = next(m for m in case.decision.missing_or_uncertain_inputs if "Dividend characterisation incomplete" in m)
    assert "franking_pct undeclared (NULL, not 0)" in gap
    assert case.decision.recommendation_state == "watch"  # the challenge still passed; tax alone never blocks watch


async def test_without_the_feed_the_packet_is_unchanged_from_before_s9() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context())
    assert case.decision.missing_or_uncertain_inputs[0] == "Real dividend/realised-gains feed for tax readiness (G12)"
    assert case.decision.tax_assessment_reference.readiness == "unknown"
    assert not any(i.evidence_type == "tax_fact" for i in case.evidence.items)
    assert all("rs_corporate_actions" not in m.version for m in case.decision.model_and_prompt_manifest)


async def test_feed_for_another_symbol_or_cutoff_is_refused() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    with pytest.raises(ValueError, match=r"is for NAB\.AU"):
        await builder.build_decision_case(
            conn, cutoff=CUTOFF, thesis_id=1, context=_context(),
            dividends=_feed(_rec(AS_OF - timedelta(days=20), symbol="NAB.AU"), symbol="NAB.AU"),
        )
    earlier = datetime(2026, 8, 31, 23, 59, 59, tzinfo=UTC)
    with pytest.raises(ValueError, match="different knowledge cutoff"):
        await builder.build_decision_case(
            conn, cutoff=CUTOFF, thesis_id=1, context=_context(),
            dividends=_feed(_rec(AS_OF - timedelta(days=20)), cutoff=earlier),
        )


async def test_no_context_path_still_abstains_with_a_pass_on_file() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, dividends=_feed(_rec(AS_OF - timedelta(days=20))))
    assert case.decision.recommendation_state == "abstain"
    assert case.decision.tax_assessment_reference.readiness == "pass"
    assert "did not run" in case.decision.missing_or_uncertain_inputs[0]
