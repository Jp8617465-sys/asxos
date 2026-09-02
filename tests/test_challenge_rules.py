"""Slice 2.5 challenge layer — campaign node H5-A (ADR §6, §10.4, D12/D13/D14).

Done-when (ADR §6 Slice 2.5): a thesis breaching any ratified register
decision cannot produce `outcome="pass"`; every finding carries an evidence
id; the outside-view pass flags ABSENCE of a base rate only.
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from asxos.domain.decision_engine.challenge import (
    RULE_NAMES,
    BoundaryError,
    ChallengeInput,
    DispositionLog,
    PortfolioState,
    admit_llm_finding,
    challenge_thesis,
    outcome_for,
    rules,
    run_layer1,
)
from asxos.domain.decision_engine.challenge import log as dlog
from asxos.domain.decision_engine.challenge.steelman import (
    OUTSIDE_VIEW_ABSENCE_TEXT,
    falsifiability,
    outside_view,
    text_carries_no_percentage,
)
from asxos.domain.decision_engine.types import ChallengeFinding, ChallengeResult

AS_OF = date(2026, 9, 1)
CUTOFF = datetime(2026, 9, 1, 23, 59, 59, tzinfo=UTC)
PKG = Path(__file__).resolve().parents[1] / "asxos" / "domain" / "decision_engine"


def _state(**kw: Any) -> PortfolioState:
    base: dict[str, Any] = {
        "capital_aud": Decimal("500000"), "cash_pct": Decimal("20"), "gross_exposure_pct": Decimal("80"),
        "borrowing_aud": Decimal("0"), "sector_weights_pct": {"Financials": Decimal("22")},
        "position_weights_pct": {"NAB.AU": Decimal("6")}, "evidence_id": "ev:portfolio",
    }
    base.update(kw)
    return PortfolioState(**base)


def _input(**kw: Any) -> ChallengeInput:
    base: dict[str, Any] = {
        "symbol": "CBA.AU", "sector": "Financials", "as_of": AS_OF, "proposed_weight_pct": Decimal("5"),
        "position_cap_pct": Decimal("10"), "portfolio": _state(),
        "last_close": Decimal("159.15"), "last_close_dt": AS_OF - timedelta(days=1), "price_evidence_id": "ev:price",
        "fundamentals_as_of": date(2026, 6, 30), "fundamentals_evidence_id": "ev:income",
        "thesis_evidence_id": "ev:thesis",
        "entry_band_lower": Decimal("150"), "entry_band_upper": Decimal("165"),
        "target_price": Decimal("185"), "reference_price": Decimal("157"), "horizon_months": 18,
        "invalidation_conditions": ("NIM below 1.80% for two consecutive halves",),
        "last_revisited_at": AS_OF - timedelta(days=10), "revisit_due_at": AS_OF + timedelta(days=80),
        "base_rate_evidence_ids": ("ev:base-rate",),
        "pairwise_correlation_max": Decimal("0.55"), "valuation_percentile": Decimal("60"),
        "adv_aud": Decimal("250000000"), "adv_trend_pct": Decimal("3"), "spread_bps": Decimal("4"),
    }
    base.update(kw)
    return ChallengeInput(**base)


def _challenge(x: ChallengeInput, **kw: Any) -> ChallengeResult:
    return challenge_thesis(x, thesis_version_id="thv-1", evidence_packet_id="evp-1", knowledge_cutoff=CUTOFF, **kw)


def _by_rule(x: ChallengeInput) -> dict[str, rules.RuleOutcome]:
    return {o.rule: o for o in run_layer1(x)}


# --- clean fixture passes; every rule is present in register order -------------------


def test_clean_fixture_passes_with_no_findings_and_all_rules_run() -> None:
    res = _challenge(_input())
    assert res.outcome == "pass" and res.findings == ()
    assert tuple(o.rule for o in run_layer1(_input())) == RULE_NAMES and len(RULE_NAMES) == 15
    assert all(o.evaluated for o in run_layer1(_input()))
    assert res.independent_of_author is True
    assert _challenge(_input()).content_hash == res.content_hash  # deterministic


# --- ratified-register breaches are blocking and cannot pass --------------------------


@pytest.mark.parametrize(
    ("kw", "rule"),
    [
        ({"portfolio": _state(borrowing_aud=Decimal("1"))}, "gross_leverage"),  # D2
        ({"portfolio": _state(gross_exposure_pct=Decimal("96"))}, "gross_leverage"),  # D2 pro-forma > 100
        ({"instrument_kind": "derivative"}, "derivatives_or_shorting"),
        ({"instrument_kind": "short"}, "derivatives_or_shorting"),
        ({"portfolio": _state(cash_pct=Decimal("12"))}, "cash_floor"),  # D1: 12 - 5 = 7 < 7.5
        ({"portfolio": _state(sector_weights_pct={"Financials": Decimal("26")})}, "sector_cap"),  # D8: 31
        ({"sector": None}, "sector_cap"),
        ({"portfolio": _state(position_weights_pct={"CBA.AU": Decimal("6")})}, "position_cap"),  # 11 > 10
        ({"last_close": None, "last_close_dt": None}, "data_integrity"),
        ({"last_close_dt": AS_OF - timedelta(days=11)}, "data_integrity"),
        ({"fundamentals_as_of": None}, "data_integrity"),
        ({"entry_band_lower": Decimal("42"), "entry_band_upper": Decimal("45")}, "price_detached"),  # CBA #1
    ],
)
def test_register_breach_is_blocking_and_forces_abstain(kw: dict[str, Any], rule: str) -> None:
    x = _input(**kw)
    out = _by_rule(x)[rule]
    assert out.finding is not None and out.finding.severity == "blocking"
    assert out.finding.evidence_ids
    res = _challenge(x)
    assert res.outcome == "abstain"
    with pytest.raises(ValidationError, match="blocking finding cannot pass"):
        ChallengeResult.model_validate({**res.model_dump(), "outcome": "pass", "content_hash": ""})


def test_cash_floor_boundary_is_exact_at_seven_point_five() -> None:
    assert _by_rule(_input(portfolio=_state(cash_pct=Decimal("12.5")))).get("cash_floor").finding is None  # type: ignore[union-attr]
    assert _by_rule(_input(portfolio=_state(cash_pct=Decimal("12.499999")))).get("cash_floor").finding is not None  # type: ignore[union-attr]


def test_price_detached_thresholds_and_cba_worked_example() -> None:
    # CBA thesis #1: band 42-45, close 159.15 → distance 114.15 / mid 43.5 = 2.624 ≥ 1.0 → blocking
    assert rules.detachment_ratio(close=Decimal("159.15"), lower=Decimal("42"), upper=Decimal("45")) == Decimal("2.624138")
    assert rules.detachment_ratio(close=Decimal("44"), lower=Decimal("42"), upper=Decimal("45")) == 0
    material = _by_rule(_input(entry_band_lower=Decimal("100"), entry_band_upper=Decimal("110"), last_close=Decimal("140")))
    assert material["price_detached"].finding is not None and material["price_detached"].finding.severity == "material"
    inside = _by_rule(_input())["price_detached"]
    assert inside.finding is None and inside.evaluated
    absent = _by_rule(_input(entry_band_lower=None, entry_band_upper=None))["price_detached"]
    assert not absent.evaluated


# --- material and monitor rules ---------------------------------------------------------


@pytest.mark.parametrize(
    ("kw", "rule", "severity"),
    [
        ({"last_close_dt": AS_OF - timedelta(days=5)}, "data_staleness", "material"),
        ({"fundamentals_as_of": AS_OF - timedelta(days=201)}, "data_staleness", "material"),
        ({"pairwise_correlation_max": Decimal("0.85")}, "correlation", "material"),
        ({"valuation_percentile": Decimal("97")}, "valuation_percentile", "material"),
        ({"valuation_percentile": Decimal("3")}, "valuation_percentile", "material"),
        ({"target_price": Decimal("300"), "horizon_months": 12}, "implied_growth", "material"),
        ({"invalidation_conditions": ()}, "invalidation_field", "material"),
        ({"invalidation_conditions": ("  ",)}, "invalidation_field", "material"),
        ({"adv_aud": Decimal("10000")}, "liquidity", "material"),
        ({"spread_bps": Decimal("150")}, "liquidity", "material"),
        ({"revisit_due_at": AS_OF + timedelta(days=3)}, "thesis_age", "monitor"),
        ({"revisit_due_at": AS_OF - timedelta(days=67)}, "thesis_age", "monitor"),
        ({"adv_trend_pct": Decimal("-40")}, "liquidity_trend", "monitor"),
    ],
)
def test_diagnostic_rules_fire_at_their_thresholds(kw: dict[str, Any], rule: str, severity: str) -> None:
    out = _by_rule(_input(**kw))[rule]
    assert out.finding is not None and out.finding.severity == severity and out.finding.evidence_ids


def test_material_finding_forces_revise_until_james_accepts_it() -> None:
    x = _input(invalidation_conditions=())
    res = _challenge(x)
    assert res.outcome == "revise"
    finding = next(f for f in res.findings if f.severity == "material")
    accepted = dlog.record(DispositionLog(), finding, disposition="accepted", reason="Condition tracked in the revision", at=CUTOFF)
    assert _challenge(x, log=accepted).outcome == "pass"
    overridden = dlog.record(DispositionLog(), finding, disposition="overridden", reason="x", at=CUTOFF)
    assert _challenge(x, log=overridden).outcome == "revise"


def test_overridden_blocking_finding_is_counted_but_still_blocks() -> None:
    x = _input(portfolio=_state(cash_pct=Decimal("10")))
    res = _challenge(x)
    blocking = next(f for f in res.findings if f.severity == "blocking")
    log = dlog.record(DispositionLog(), blocking, disposition="overridden", reason="James override", at=CUTOFF)
    assert _challenge(x, log=log).outcome == "abstain"
    assert log.override_rate_blocking(res.findings) == (1, 1)
    assert outcome_for(res.findings, log) == "abstain"


def test_unmeasured_diagnostics_are_reported_not_guessed() -> None:
    x = _input(pairwise_correlation_max=None, valuation_percentile=None, adv_aud=None, adv_trend_pct=None,
               target_price=None, revisit_due_at=None)
    outs = _by_rule(x)
    for rule in ("correlation", "valuation_percentile", "liquidity", "liquidity_trend", "implied_growth", "thesis_age"):
        assert not outs[rule].evaluated and outs[rule].finding is None
    res = _challenge(x)
    assert res.outcome == "pass" and "could not be evaluated" in res.strongest_bear_case


def test_implied_cagr_arithmetic_is_decimal() -> None:
    cagr = rules.implied_cagr_pct(reference_price=Decimal("100"), target_price=Decimal("121"), horizon_months=24)
    assert cagr == Decimal("10.000000")


# --- Layer 2 shell --------------------------------------------------------------------


def test_outside_view_flags_absence_of_base_rate_only_and_never_asserts_one() -> None:
    found = outside_view(_input(base_rate_evidence_ids=()))
    assert len(found) == 1 and found[0].severity == "material" and found[0].finding == OUTSIDE_VIEW_ABSENCE_TEXT
    assert text_carries_no_percentage(found[0].finding) and text_carries_no_percentage(found[0].required_response)
    assert outside_view(_input()) == ()
    assert _challenge(_input(base_rate_evidence_ids=())).outcome == "revise"


def test_falsifiability_marks_unmeasurable_conditions_as_monitor() -> None:
    found = falsifiability(_input(invalidation_conditions=("management loses credibility", "NIM < 1.80%")))
    assert len(found) == 1 and found[0].severity == "monitor" and "condition 1" in found[0].finding


def test_bear_case_is_template_only_and_never_quotes_the_thesis() -> None:
    narrative = "BUY BUY BUY the best bank in the world"
    x = _input(invalidation_conditions=(narrative,))
    res = _challenge(x)
    assert narrative not in res.strongest_bear_case
    assert all(narrative not in f.finding for f in res.findings)


@pytest.mark.parametrize("text", ["Buy CBA before results", "Price target 200", "We recommend trimming", "Strong sell"])
def test_llm_door_refuses_recommendations_and_unevidenced_or_blocking_findings(text: str) -> None:
    with pytest.raises(BoundaryError, match="recommendation"):
        admit_llm_finding(text=text, required_response="x", evidence_ids=("ev:1",), severity="material")
    with pytest.raises(BoundaryError, match="evidence"):
        admit_llm_finding(text="NIM has compressed", required_response="x", evidence_ids=(), severity="material")
    with pytest.raises(BoundaryError, match="blocking"):
        admit_llm_finding(text="NIM has compressed", required_response="x", evidence_ids=("ev:1",), severity="blocking")  # type: ignore[arg-type]
    ok = admit_llm_finding(text="NIM has compressed for two halves", required_response="Re-underwrite the margin path", evidence_ids=("ev:1",), severity="material")
    assert _challenge(_input(), llm_findings=(ok,)).outcome == "revise"
    with pytest.raises(BoundaryError):
        _challenge(_input(), llm_findings=(ChallengeFinding(severity="blocking", finding="x", required_response="y", evidence_ids=("e",)),))


def test_every_finding_is_unconstructable_without_evidence() -> None:
    with pytest.raises(ValidationError):
        ChallengeFinding(severity="material", finding="x", required_response="y", evidence_ids=())


# --- input hygiene --------------------------------------------------------------------


def test_input_rejects_floats_half_bands_and_future_observations() -> None:
    with pytest.raises(ValidationError, match="float"):
        _input(proposed_weight_pct=5.0)
    with pytest.raises(ValidationError, match="both bounds"):
        _input(entry_band_upper=None)
    with pytest.raises(ValidationError, match="after as_of"):
        _input(last_close_dt=AS_OF + timedelta(days=1))
    with pytest.raises(ValidationError):
        _input(instrument_kind="option")
    with pytest.raises(ValueError, match="knowledge_cutoff"):
        challenge_thesis(_input(), thesis_version_id="t", evidence_packet_id="e", knowledge_cutoff=CUTOFF + timedelta(days=1))


# --- boundaries: rule #11, the firewall, and import isolation ------------------------------


def test_challenge_package_imports_nothing_forbidden_and_carries_no_advice() -> None:
    src = "\n".join(p.read_text() for p in (PKG / "challenge").glob("*.py"))
    assert re.search(r"^\s*(?:from|import)\s+asxos\.domain\.(?:models|portfolio)", src, re.MULTILINE) is None
    assert re.search(r"from\s+signals|join\s+signals|signal_outcomes", src, re.IGNORECASE) is None
    assert "evidence_ids=()" not in src
    templates = re.findall(r'"([^"\n]*)"', src)
    advice = re.compile(r"\b(buy|sell|overweight|underweight|accumulate)\b", re.IGNORECASE)
    offenders = [t for t in templates if advice.search(t) and "recommend" not in t.lower() and "\\b" not in t]
    assert offenders == [], offenders
