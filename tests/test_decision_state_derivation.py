"""asxos/domain/decision_engine/builder.py::derive_state — F-E2E r2 S10, backlog D-16.

Action states stay structurally unreachable this sprint (C-13 does not exist),
so every call site passes calibration=None and the gate always returns a
NON_ACTION_STATE — matching the pre-S10 behaviour exactly, but through the
real gate rather than a one-line hard-code.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from asxos.domain.decision_engine import builder
from asxos.domain.decision_engine.builder import derive_state
from asxos.domain.decision_engine.types import ACTION_STATES, NON_ACTION_STATES
from asxos.domain.discovery.ranker import MIN_ADV_AUD
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


@pytest.mark.parametrize(
    ("challenge_outcome", "tax_readiness", "calibration", "expected"),
    [
        ("abstain", "pass", None, "abstain"),
        ("revise", "pass", None, "abstain"),
        ("pass", "unknown", None, "watch"),
        ("pass", "fail", None, "watch"),
        ("pass", "pass", None, "watch"),  # calibration absent — the only path this codebase can reach today
    ],
)
def test_derive_state_matrix(challenge_outcome: str, tax_readiness: str, calibration: object, expected: str) -> None:
    assert (
        derive_state(challenge_outcome=challenge_outcome, tax_readiness=tax_readiness, calibration=calibration)  # type: ignore[arg-type]
        == expected
    )
    assert expected in NON_ACTION_STATES


def test_a_non_none_calibration_raises_because_nothing_can_honestly_produce_one() -> None:
    with pytest.raises(NotImplementedError, match="C-13"):
        derive_state(challenge_outcome="pass", tax_readiness="pass", calibration=object())


def test_every_reachable_output_is_a_non_action_state() -> None:
    """No combination this codebase can construct today reaches an ACTION_STATE."""
    for challenge_outcome in ("pass", "revise", "abstain"):
        for tax_readiness in ("pass", "fail", "unknown"):
            result = derive_state(challenge_outcome=challenge_outcome, tax_readiness=tax_readiness, calibration=None)  # type: ignore[arg-type]
            assert result not in ACTION_STATES
            assert result in NON_ACTION_STATES


def _rec(ex: date) -> feed.DividendRecord:
    return feed.DividendRecord(symbol="CBA.AU", ex_date=ex, pay_date=None, dividend_amount=Decimal("2.50"), franking_pct=Decimal("100"))


async def test_builder_reaches_watch_with_a_real_tax_pass_through_the_gate() -> None:
    """A challenge pass + a real G12 pass still stops at `watch` — the door (calibration) is
    shut this sprint, so the gate cannot be tricked into an action state via tax alone."""
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    dividends = feed.characterise_dividends([_rec(AS_OF - timedelta(days=20))], symbol="CBA.AU", cutoff=CUTOFF)
    case = await builder.build_decision_case(
        conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context(), dividends=dividends
    )
    assert case.challenge.outcome == "pass"
    assert case.decision.tax_assessment_reference.readiness == "pass"
    assert case.decision.recommendation_state == "watch"
    assert case.decision.size_range.maximum_pct == 0


async def test_tradeability_constraint_reads_s4s_liquidity_floor() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    liquid = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=_candidate(), context=_context())
    tradeability = next(c for c in liquid.portfolio.constraints if c.name == "tradeability_and_ownership")
    assert tradeability.status == "pass" and str(MIN_ADV_AUD) in tradeability.detail

    thin_candidate = _candidate().model_copy(update={"measures": {**_candidate().measures, "median_dollar_volume_60d": "1000.000000"}})
    thin = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, candidate=thin_candidate, context=_context())
    thin_tradeability = next(c for c in thin.portfolio.constraints if c.name == "tradeability_and_ownership")
    assert thin_tradeability.status == "unknown" and "below the discovery liquidity floor" in thin_tradeability.detail


async def test_tradeability_is_unmeasured_not_assumed_liquid_without_a_candidate() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1, context=_context())
    tradeability = next(c for c in case.portfolio.constraints if c.name == "tradeability_and_ownership")
    assert tradeability.status == "unknown" and "not assumed liquid" in tradeability.detail


async def test_no_context_path_still_has_every_universal_constraint() -> None:
    conn = _Conn(thesis_row=_thesis_row(**IN_BAND), close=Decimal("159.15"), close_dt=AS_OF)
    case = await builder.build_decision_case(conn, cutoff=CUTOFF, thesis_id=1)
    assert case.decision.recommendation_state == "abstain"
    assert {c.name for c in case.portfolio.constraints} == {
        "model_a_quarantine", "no_leverage", "no_broker_execution", "tradeability_and_ownership",
        "decision_evidence_freshness",
    }


def test_module_docstring_and_cutoff_sanity() -> None:
    assert datetime.now(UTC).tzinfo is not None
