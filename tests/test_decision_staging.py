"""Slice 3 order staging — campaign node H5-C. Built only from a passed challenge
and a non-zero size; lots come from the tax module's selectors; nothing executes."""
from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from asxos.domain.decision_engine.staging import StagedOrder, StagingError, stage_order
from asxos.domain.decision_engine.types import ChallengeFinding, ChallengeResult, SizeRange
from asxos.domain.tax.types import HoldingLot

AS_OF = date(2026, 9, 1)
CUTOFF = datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC)
STAGING = Path(__file__).resolve().parents[1] / "asxos" / "domain" / "decision_engine" / "staging.py"


def _challenge(outcome: str, *, blocking: bool = False) -> ChallengeResult:
    findings = (ChallengeFinding(severity="blocking", finding="x", required_response="y", evidence_ids=("e",)),) if blocking else ()
    return ChallengeResult(
        challenge_result_id="chr-1", thesis_version_id="thv-1", evidence_packet_id="evp-1", as_of=AS_OF,
        knowledge_cutoff=CUTOFF, created_at=CUTOFF, outcome=outcome, strongest_bear_case="none",  # type: ignore[arg-type]
        findings=findings, independent_of_author=True,
    )


SIZE = SizeRange(minimum_pct=Decimal("1"), maximum_pct=Decimal("8"))
LOTS = (
    HoldingLot(lot_id=1, symbol="CBA.AU", acquired_at=date(2024, 3, 1), quantity=Decimal("200"), cost_base_normal=Decimal("20000"), cost_base_div296=Decimal("20000")),
    HoldingLot(lot_id=2, symbol="CBA.AU", acquired_at=date(2026, 3, 1), quantity=Decimal("100"), cost_base_normal=Decimal("12000"), cost_base_div296=Decimal("12000")),
    HoldingLot(lot_id=3, symbol="NAB.AU", acquired_at=date(2024, 3, 1), quantity=Decimal("50"), cost_base_normal=Decimal("1500"), cost_base_div296=Decimal("1500")),
)


def _stage(**kw):  # type: ignore[no-untyped-def]
    base = {"symbol": "CBA.AU", "side": "buy", "reference_price": Decimal("159.15"), "capital_aud": Decimal("500000"),
            "as_of": AS_OF, "staged_at": CUTOFF}
    base.update(kw)
    return stage_order(_challenge("pass"), SIZE, **base)


def test_buy_is_staged_from_the_maximum_size_and_is_not_executable() -> None:
    order = _stage()
    assert order.quantity == Decimal("251")  # floor(40000 / 159.15)
    assert order.notional_aud == Decimal("39946.650000") and order.size_pct == Decimal("7.989330")
    assert order.limit_price == Decimal("159.150000") and order.lot_selections == ()
    assert order.not_executable is True and order.execution_venue == "none"
    with pytest.raises(ValueError):
        StagedOrder.model_validate({**order.model_dump(), "not_executable": False})


def test_sell_delegates_lot_selection_to_the_tax_module() -> None:
    order = _stage(side="sell", open_lots=LOTS, reference_price=Decimal("160"))
    assert order.quantity == Decimal("250")  # floor(40000/160); held 300
    assert sum((lot.qty for lot in order.lot_selections), Decimal("0")) == Decimal("250")
    by_id = {lot.lot_id: lot for lot in order.lot_selections}
    # Lot 1: 200 u @ 100, discountable (acquired 2024-03-01, earliest qualifying 2025-03-02 ≤ 2026-09-01):
    #   gain 12,000, post-discount 6,000. Lot 2: 100 u @ 120, NOT discountable (earliest 2027-03-02):
    #   per-unit 40 post-discount vs lot 1's 30, so the true minimum draws lot 1 in full and 50 of lot 2:
    #   6,000 + 2,000 = 8,000 (vs 8,500 the other way). Arithmetic per spec §2 (individual d = 0.5) and §5.1.
    assert by_id[1].discountable is True and by_id[1].qty == Decimal("200") and by_id[1].realised_gain_aud == Decimal("12000")
    assert by_id[2].discountable is False and by_id[2].qty == Decimal("50") and by_id[2].realised_gain_aud == Decimal("2000")
    assert all(lot.provisional is True and lot.eligibility_evaluated_at == AS_OF and lot.gain_priced_at == Decimal("160") for lot in order.lot_selections)
    fifo = _stage(side="sell", open_lots=LOTS, reference_price=Decimal("160"), lot_selector="fifo")
    assert [lot.lot_id for lot in fifo.lot_selections] == [1, 2]


def test_sell_refuses_mixed_account_types_and_the_min_cgt_fallback_bound() -> None:
    smsf = (HoldingLot(lot_id=7, symbol="CBA.AU", acquired_at=date(2024, 1, 1), quantity=Decimal("10"), cost_base_normal=Decimal("1000"), cost_base_div296=Decimal("1000"), account_type="smsf"),)
    with pytest.raises(StagingError, match="account_type"):
        _stage(side="sell", open_lots=LOTS + smsf)
    many = tuple(HoldingLot(lot_id=100 + i, symbol="CBA.AU", acquired_at=date(2024, 1, 1 + i), quantity=Decimal("10"), cost_base_normal=Decimal("1000"), cost_base_div296=Decimal("1000")) for i in range(7))
    with pytest.raises(StagingError, match="min-CGT search bound"):
        _stage(side="sell", open_lots=many)
    assert _stage(side="sell", open_lots=many, lot_selector="fifo").quantity == Decimal("70")


def test_sell_is_capped_at_held_quantity() -> None:
    small = (HoldingLot(lot_id=9, symbol="CBA.AU", acquired_at=date(2024, 1, 1), quantity=Decimal("10"), cost_base_normal=Decimal("1000"), cost_base_div296=Decimal("1000")),)
    order = _stage(side="sell", open_lots=small)
    assert order.quantity == Decimal("10")


@pytest.mark.parametrize(
    ("challenge", "size", "match"),
    [
        (_challenge("revise"), SIZE, "revise"),
        (_challenge("abstain", blocking=True), SIZE, "abstain"),
        (_challenge("pass"), SizeRange(minimum_pct=Decimal("0"), maximum_pct=Decimal("0")), "zero size"),
    ],
)
def test_staging_refuses_anything_but_a_passed_nonzero_gate(challenge: ChallengeResult, size: SizeRange, match: str) -> None:
    with pytest.raises(StagingError, match=match):
        stage_order(challenge, size, symbol="CBA.AU", side="buy", reference_price=Decimal("100"), capital_aud=Decimal("1000"), as_of=AS_OF, staged_at=CUTOFF)


def test_staging_refuses_sub_unit_and_mismatched_dates() -> None:
    with pytest.raises(StagingError, match="fewer than one unit"):
        _stage(capital_aud=Decimal("100"))
    with pytest.raises(StagingError, match="as_of"):
        _stage(as_of=date(2026, 9, 2))


def test_staging_has_no_broker_or_execution_surface() -> None:
    src = STAGING.read_text()
    assert re.search(r"\b(broker|execute|submit_order|place_order|httpx|requests)\b", src.split('"""', 2)[2]) is None
    assert re.search(r"^\s*(?:from|import)\s+asxos\.domain\.models", src, re.MULTILINE) is None and "import jobs" not in src and "from jobs" not in src
    assert "select_min_cgt" in src and "is_discountable" not in src.split('"""', 2)[2]
