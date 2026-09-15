"""`ScenarioPreregistration` / `ValuationRun` contracts and the bundled, sealed registration."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib import resources

import pytest

from asxos.domain.decision_engine.types import verify_content_hash
from asxos.domain.valuation.contracts import (
    GapRecord,
    KeBand,
    ScenarioPreregistration,
    ValuationRun,
)
from asxos.domain.valuation.preregistration import (
    BUNDLED_PREREGISTRATION_FILE,
    load_bundled_preregistration,
)

CUTOFF = datetime(2026, 9, 20, 16, 5, tzinfo=UTC)


def _ke() -> KeBand:
    return KeBand(
        risk_free=Decimal("0.048310"),
        risk_free_as_of=date(2026, 9, 15),
        risk_free_series="FRED IRLTLT01AUM156N",
        erp=Decimal("0.055"),
        beta_low=Decimal("0.55"),
        beta_mid=Decimal("0.70"),
        beta_high=Decimal("0.85"),
        beta_provenance="cited",
        ke_low=Decimal("0.078560"),
        ke_mid=Decimal("0.086810"),
        ke_high=Decimal("0.095060"),
    )


def _blocked(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "run_id": "vr-X.AU-2026-09-20-zero_excess",
        "symbol": "X.AU",
        "as_of": date(2026, 9, 20),
        "knowledge_cutoff": CUTOFF,
        "created_at": CUTOFF,
        "method": "residual_income",
        "terminal_convention": "zero_excess",
        "franking_convention": "grossed_up_resident",
        "return_base": "reported_book_equity",
        "horizon_years": 10,
        "outcome": "blocked",
        "data_mode": "real",
        "preregistration_id": "prereg-asx-universe-2026-09-16",
        "ke": _ke(),
        "gaps": (GapRecord(name="pit_row_absent", detail="no row"),),
    }
    base.update(overrides)
    return base


# --- the bundled registration -------------------------------------------------


def test_bundled_preregistration_is_sealed_and_verifies() -> None:
    prereg = load_bundled_preregistration()
    assert prereg.preregistration_id == "prereg-asx-universe-2026-09-16"
    assert prereg.terminal_convention == "zero_excess"
    assert prereg.return_base == "reported_book_equity"
    assert verify_content_hash(prereg)
    assert [lever.label for lever in prereg.levers] == ["bear", "base", "bull"]
    assert sum(lever.probability_pct for lever in prereg.levers) == Decimal("100")
    assert {s.label for s in prereg.sensitivities} == {
        "average_roe",
        "fading_excess_w050",
        "unadjusted_franking",
    }
    assert all(s.registered is False for s in prereg.sensitivities)
    assert prereg.input_rules.price_window_days == 40
    assert prereg.input_rules.roe_average_periods == 3


def test_edited_registration_fails_hash_verification() -> None:
    """An edit after sealing is refused — a changed registration is a NEW id."""
    raw = json.loads(
        resources.files("asxos.domain.valuation")
        .joinpath(BUNDLED_PREREGISTRATION_FILE)
        .read_text(encoding="utf-8")
    )
    raw["levers"][0]["roe_factor"] = "0.80"
    with pytest.raises(ValueError, match="content_hash does not match"):
        ScenarioPreregistration.model_validate(raw)


def test_registration_probabilities_must_sum_to_100() -> None:
    raw = load_bundled_preregistration().model_dump(mode="json")
    raw.pop("content_hash")
    raw["levers"][1]["probability_pct"] = "40"
    with pytest.raises(ValueError, match="sum to exactly 100"):
        ScenarioPreregistration.model_validate(raw)


def test_registration_refuses_an_unregistered_convention() -> None:
    raw = load_bundled_preregistration().model_dump(mode="json")
    raw.pop("content_hash")
    raw["terminal_convention"] = "fading_excess"
    with pytest.raises(ValueError):
        ScenarioPreregistration.model_validate(raw)


# --- ValuationRun shape ------------------------------------------------------


def test_blocked_run_seals_and_round_trips() -> None:
    run = ValuationRun(**_blocked())  # type: ignore[arg-type]
    assert verify_content_hash(run)
    back = ValuationRun.model_validate(run.model_dump(mode="json"))
    assert back == run


def test_blocked_run_cannot_carry_a_value() -> None:
    with pytest.raises(ValueError, match="carries no value"):
        ValuationRun(**_blocked(value_per_share=Decimal("1")))  # type: ignore[arg-type]


def test_blocked_run_needs_a_gap() -> None:
    with pytest.raises(ValueError, match="names at least one gap"):
        ValuationRun(**_blocked(gaps=()))  # type: ignore[arg-type]


def test_valued_run_needs_every_value_field() -> None:
    with pytest.raises(ValueError, match="carries every value field"):
        ValuationRun(**_blocked(outcome="valued", gaps=()))  # type: ignore[arg-type]


def test_as_of_must_be_the_utc_cutoff_date() -> None:
    with pytest.raises(ValueError, match="UTC knowledge_cutoff date"):
        ValuationRun(**_blocked(as_of=date(2026, 9, 21)))  # type: ignore[arg-type]


def test_created_at_cannot_precede_cutoff() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        ValuationRun(  # type: ignore[arg-type]
            **_blocked(created_at=datetime(2026, 9, 20, 15, 0, tzinfo=UTC))
        )


def test_run_refuses_float_input() -> None:
    with pytest.raises(ValueError, match="float input is forbidden"):
        ValuationRun(**_blocked(horizon_years=10, ke=_ke().model_dump() | {"erp": 0.055}))  # type: ignore[arg-type]


def test_run_refuses_an_unregistered_convention() -> None:
    with pytest.raises(ValueError):
        ValuationRun(**_blocked(terminal_convention="fading_excess"))  # type: ignore[arg-type]


def test_ke_band_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="ordered"):
        KeBand(**(_ke().model_dump() | {"ke_low": Decimal("0.2")}))
