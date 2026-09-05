"""Slice 2 sizer — campaign node H5-B. `SizeRange` is non-zero only on a passed
challenge; cash ≥ 7.5% and gross ≤ 100% post-trade always (D1/D2)."""
from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from asxos.domain.decision_engine.challenge import PortfolioState
from asxos.domain.decision_engine.sizer import (
    ZERO_SIZE,
    ProposedPosition,
    SizingPolicy,
    VolInput,
    reference_weight_pct,
    size_from_challenge,
)
from asxos.domain.decision_engine.types import ChallengeFinding, ChallengeResult

AS_OF = date(2026, 9, 1)
CUTOFF = datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC)
SIZER = Path(__file__).resolve().parents[1] / "asxos" / "domain" / "decision_engine" / "sizer.py"


def _challenge(outcome: str, *, blocking: bool = False) -> ChallengeResult:
    findings = (
        (ChallengeFinding(severity="blocking", finding="x", required_response="y", evidence_ids=("e",)),) if blocking else ()
    )
    return ChallengeResult(
        challenge_result_id="chr-1", thesis_version_id="thv-1", evidence_packet_id="evp-1", as_of=AS_OF,
        knowledge_cutoff=CUTOFF, created_at=CUTOFF, outcome=outcome, strongest_bear_case="none",  # type: ignore[arg-type]
        findings=findings, independent_of_author=True,
    )


PROPOSED = ProposedPosition(symbol="CBA.AU", sector="Financials", annualised_vol=Decimal("0.20"))
PEERS = (VolInput(symbol="NAB.AU", annualised_vol=Decimal("0.25")), VolInput(symbol="BHP.AU", annualised_vol=Decimal("0.30")))
POLICY = SizingPolicy(capital_aud=Decimal("500000"), position_cap_pct=Decimal("10"), min_position_aud=Decimal("5000"))


def _state(**kw: Any) -> PortfolioState:
    base: dict[str, Any] = {
        "capital_aud": Decimal("500000"), "cash_pct": Decimal("20"), "gross_exposure_pct": Decimal("80"),
        "borrowing_aud": Decimal("0"), "sector_weights_pct": {"Financials": Decimal("22")},
        "position_weights_pct": {}, "evidence_id": "ev:portfolio",
    }
    base.update(kw)
    return PortfolioState(**base)


def test_size_is_zero_unless_the_challenge_passed() -> None:
    for outcome, blocking in (("revise", False), ("abstain", False), ("abstain", True)):
        assert size_from_challenge(_challenge(outcome, blocking=blocking), proposed=PROPOSED, peers=PEERS, policy=POLICY, state=_state()) == ZERO_SIZE
    size = size_from_challenge(_challenge("pass"), proposed=PROPOSED, peers=PEERS, policy=POLICY, state=_state())
    assert size.maximum_pct > 0 and 0 < size.minimum_pct <= size.maximum_pct


def test_reference_weight_reuses_inverse_vol_and_caps_bind() -> None:
    ref = reference_weight_pct(PROPOSED, PEERS, POLICY)
    # 1/0.2 : 1/0.25 : 1/0.3 = 5 : 4 : 3.333 → 0.405405 × 92.5 deployable
    assert ref == Decimal("37.500000")
    size = size_from_challenge(_challenge("pass"), proposed=PROPOSED, peers=PEERS, policy=POLICY, state=_state())
    assert size.maximum_pct == Decimal("8")  # sector headroom 30 - 22 binds before the 10% position cap
    assert size.minimum_pct == Decimal("1")  # 5000 / 500000


def test_leverage_and_exhausted_headroom_give_zero() -> None:
    assert size_from_challenge(_challenge("pass"), proposed=PROPOSED, peers=PEERS, policy=POLICY, state=_state(borrowing_aud=Decimal("1"))) == ZERO_SIZE
    assert size_from_challenge(_challenge("pass"), proposed=PROPOSED, peers=PEERS, policy=POLICY, state=_state(cash_pct=Decimal("7.5"), gross_exposure_pct=Decimal("92.5"))) == ZERO_SIZE
    assert size_from_challenge(_challenge("pass"), proposed=PROPOSED, peers=PEERS, policy=POLICY, state=_state(sector_weights_pct={"Financials": Decimal("30")})) == ZERO_SIZE


def test_policy_cannot_loosen_the_register() -> None:
    with pytest.raises(ValueError):
        SizingPolicy(capital_aud=Decimal("1"), position_cap_pct=Decimal("10"), min_position_aud=Decimal("0"), cash_floor_pct=Decimal("5"))
    with pytest.raises(ValueError):
        SizingPolicy(capital_aud=Decimal("1"), position_cap_pct=Decimal("10"), min_position_aud=Decimal("0"), sector_cap_pct=Decimal("35"))


_GRID = [Decimal(v) for v in ("0", "7.499999", "12.5", "30", "92.5", "100")]


@pytest.mark.parametrize("cash", _GRID)
@pytest.mark.parametrize("sector", _GRID)
@pytest.mark.parametrize("gross", _GRID)
@pytest.mark.parametrize("position", [Decimal("0"), Decimal("9.999999"), Decimal("25")])
@pytest.mark.parametrize("vol", [Decimal("0.01"), Decimal("2")])
def test_grid_post_trade_cash_never_below_floor_and_gross_never_above_100(
    cash: Decimal, sector: Decimal, gross: Decimal, position: Decimal, vol: Decimal
) -> None:
    """A deterministic grid rather than a property-based search: `hypothesis` is not a
    declared dependency and adding one is a `tech-stack-researcher` question, not a test."""
    state = _state(cash_pct=cash, gross_exposure_pct=gross, sector_weights_pct={"Financials": sector}, position_weights_pct={"CBA.AU": position})
    proposed = ProposedPosition(symbol="CBA.AU", sector="Financials", annualised_vol=vol)
    size = size_from_challenge(_challenge("pass"), proposed=proposed, peers=PEERS, policy=POLICY, state=state)
    assert size.minimum_pct <= size.maximum_pct
    assert cash - size.maximum_pct >= Decimal("7.5") or size == ZERO_SIZE
    assert gross + size.maximum_pct <= Decimal("100")
    assert sector + size.maximum_pct <= Decimal("30") or size == ZERO_SIZE
    assert position + size.maximum_pct <= Decimal("10") or size == ZERO_SIZE


def test_sizer_imports_no_model_a_surface() -> None:
    src = SIZER.read_text()
    assert re.search(r"^\s*(?:from|import)\s+asxos\.domain\.models", src, re.MULTILINE) is None
    assert re.search(r"from\s+signals|join\s+signals|signal_outcomes", src, re.IGNORECASE) is None
    assert "inverse_vol_weights" in src and "apply_constraints(" not in src
