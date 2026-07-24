"""Tests for the ThesisProposal keystone schema (Phase B).

Covers the load-bearing validators that make an LLM-invented or uncited
capital-relevant number structurally unrepresentable as trustworthy:
  - ReportFigure provenance (cited needs evidence; derived needs a formula)
  - ReportSection.body is prose-only (capital numbers must be figures)
  - monitor_only (rule #11 Model A) figures barred from basis sections
plus the ThesisProposal shape checks.
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from asxos.domain.theses.schemas import (
    REPORT_SECTION_KINDS,
    ReportFigure,
    ReportSection,
    ThesisProposal,
)

# --- ReportFigure provenance ---------------------------------------------------

def test_cited_figure_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        ReportFigure(label="fair value", value=Decimal("130"), provenance="cited")


def test_cited_figure_with_evidence_ok() -> None:
    f = ReportFigure(
        label="fair value", value=Decimal("130"), provenance="cited",
        evidence_citation_ids=[1],
    )
    assert f.value == Decimal("130")


def test_derived_requires_formula() -> None:
    with pytest.raises(ValidationError):
        ReportFigure(label="fv", value=Decimal("130"), provenance="derived")


def test_derived_with_formula_and_evidence_ok() -> None:
    f = ReportFigure(
        label="fv", value=Decimal("130"), provenance="derived",
        formula="eps_ny * target_multiple", evidence_citation_ids=[1],
    )
    assert f.formula


def test_derived_without_evidence_rejected() -> None:
    # derived must cite its inputs, not just show a formula (a junk-formula
    # derived number with no evidence is a laundering vector)
    with pytest.raises(ValidationError):
        ReportFigure(
            label="fv", value=Decimal("130"), provenance="derived",
            formula="sum of the parts",
        )


def test_formula_rejected_for_non_derived() -> None:
    with pytest.raises(ValidationError):
        ReportFigure(
            label="fv", value=Decimal("130"), provenance="james_input", formula="x",
        )


def test_james_input_needs_no_evidence() -> None:
    f = ReportFigure(label="my target", value=Decimal("130"), provenance="james_input")
    assert f.provenance == "james_input"


def test_value_stays_decimal() -> None:
    f = ReportFigure(label="x", value=Decimal("1.230000"), provenance="james_input")
    assert isinstance(f.value, Decimal)
    assert f.value == Decimal("1.230000")


# --- ReportSection: prose-only body -------------------------------------------

@pytest.mark.parametrize(
    "bad",
    [
        "fair value is $130 per share",
        "gross retention of 99% every year",
        "revenue of 1,234 million this half",
        "trades at 28x forward earnings",
        "operating margin near 12.5 %",
    ],
)
def test_body_rejects_capital_numbers(bad: str) -> None:
    with pytest.raises(ValidationError):
        ReportSection(kind="moat", body=bad)


@pytest.mark.parametrize(
    "ok",
    [
        "a wide moat likely to persist for 20 years",
        "licenses run to 2050 with no renewal before then",
        "the FY26 result is the next catalyst to watch",
        "a 12-month timeline with a clear falsifier",
        "switching costs keep customers locked in year after year",
    ],
)
def test_body_allows_prose_years_and_durations(ok: str) -> None:
    s = ReportSection(kind="moat", body=ok)
    assert s.kind == "moat"


def test_capital_number_belongs_in_a_figure() -> None:
    s = ReportSection(
        kind="moat",
        body="gross retention has stayed remarkably high despite steep price hikes",
        figures=[
            ReportFigure(
                label="gross retention", value=Decimal("0.99"),
                provenance="cited", evidence_citation_ids=[1],
            )
        ],
    )
    assert s.figures[0].value == Decimal("0.99")


# --- monitor_only (rule #11) placement ----------------------------------------

def test_monitor_figure_rejected_in_basis_section() -> None:
    with pytest.raises(ValidationError):
        ReportSection(
            kind="verdict_conviction",
            body="the synthesized point of view",
            figures=[
                ReportFigure(
                    label="Model A prob_up", value=Decimal("0.68"),
                    provenance="cited", evidence_citation_ids=[9], monitor_only=True,
                )
            ],
        )


def test_monitor_figure_allowed_in_evidence_ledger() -> None:
    s = ReportSection(
        kind="evidence_ledger",
        body="monitored, not a basis",
        figures=[
            ReportFigure(
                label="Model A prob_up", value=Decimal("0.68"),
                provenance="cited", evidence_citation_ids=[9], monitor_only=True,
            )
        ],
    )
    assert s.figures[0].monitor_only is True


def test_non_monitor_figure_ok_in_basis() -> None:
    s = ReportSection(
        kind="valuation",
        body="reasoning over the cited external consensus",
        figures=[
            ReportFigure(
                label="analyst consensus target", value=Decimal("7.80"),
                provenance="cited", evidence_citation_ids=[2],
            )
        ],
    )
    assert s.figures[0].monitor_only is False


# --- ThesisProposal shape ------------------------------------------------------

def _fig(v: str, prov: str = "james_input", **kw: object) -> ReportFigure:
    return ReportFigure(label="l", value=Decimal(v), provenance=prov, **kw)  # type: ignore[arg-type]


def test_minimal_valid_proposal() -> None:
    p = ThesisProposal(symbol="CBA.AU", thesis_text="a thesis", evidence_citation_ids=[1])
    assert p.flavour == "individual_equity"


def test_symbol_pattern_enforced() -> None:
    with pytest.raises(ValidationError):
        ThesisProposal(symbol="cba", thesis_text="t", evidence_citation_ids=[1])


def test_evidence_required() -> None:
    with pytest.raises(ValidationError):
        ThesisProposal(symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[])


def test_conviction_range() -> None:
    with pytest.raises(ValidationError):
        ThesisProposal(
            symbol="CBA.AU", thesis_text="t", conviction_level=6, evidence_citation_ids=[1],
        )


def test_entry_band_order_rejected() -> None:
    with pytest.raises(ValidationError):
        ThesisProposal(
            symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[1],
            entry_band_lower=_fig("100"), entry_band_upper=_fig("90"),
        )


def test_entry_band_order_ok() -> None:
    p = ThesisProposal(
        symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[1],
        entry_band_lower=_fig("90"), entry_band_upper=_fig("100"),
    )
    assert p.entry_band_lower is not None
    assert p.entry_band_lower.value == Decimal("90")


def test_duplicate_section_kinds_rejected() -> None:
    with pytest.raises(ValidationError):
        ThesisProposal(
            symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[1],
            sections=[
                ReportSection(kind="moat", body="one point"),
                ReportSection(kind="moat", body="another point"),
            ],
        )


def test_proposed_price_is_a_provenanced_figure() -> None:
    p = ThesisProposal(
        symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[1],
        target_price=ReportFigure(
            label="target", value=Decimal("110"), provenance="james_input",
        ),
    )
    assert p.target_price is not None
    assert p.target_price.value == Decimal("110")


def test_section_kinds_constant_is_the_full_ten() -> None:
    assert "moat" in REPORT_SECTION_KINDS
    assert "evidence_ledger" in REPORT_SECTION_KINDS
    assert len(REPORT_SECTION_KINDS) == 10


# --- security-review hardening (2026-07-18) -----------------------------------

def test_monitor_only_rejected_on_wrapper_prices() -> None:
    # a rule #11 Model A figure may never BE the stop/target/entry lever
    for field in ("target_price", "stop_price", "entry_band_lower", "entry_band_upper"):
        fig = ReportFigure(
            label="Model A implied level", value=Decimal("110"),
            provenance="cited", evidence_citation_ids=[9], monitor_only=True,
        )
        with pytest.raises(ValidationError):
            ThesisProposal(
                symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[1],
                **{field: fig},
            )


def test_float_value_rejected() -> None:
    # a Python float loses precision before Decimal sees it (CLAUDE.md #5)
    with pytest.raises(ValidationError):
        ReportFigure(label="x", value=1.5, provenance="james_input")  # type: ignore[arg-type]


def test_int_value_ok() -> None:
    f = ReportFigure(label="x", value=130, provenance="james_input")  # type: ignore[arg-type]
    assert f.value == Decimal("130")


def test_decimal_precision_via_json() -> None:
    # model_validate_json must not lose precision: a JSON string stays exact,
    # a JSON float is rejected (the CLAUDE.md #5 structural guard).
    ok = '{"label": "x", "value": "123456789012.123456", "provenance": "james_input"}'
    assert ReportFigure.model_validate_json(ok).value == Decimal("123456789012.123456")
    lossy = '{"label": "x", "value": 123456789012.123456, "provenance": "james_input"}'
    with pytest.raises(ValidationError):
        ReportFigure.model_validate_json(lossy)


def test_entry_band_equal_allowed() -> None:
    p = ThesisProposal(
        symbol="CBA.AU", thesis_text="t", evidence_citation_ids=[1],
        entry_band_lower=_fig("100"), entry_band_upper=_fig("100"),
    )
    assert p.entry_band_lower is not None


@pytest.mark.parametrize("bad", ["fair value €130 per share", "a £130 target", "worth ¥13000"])
def test_body_rejects_nondollar_currency(bad: str) -> None:
    with pytest.raises(ValidationError):
        ReportSection(kind="moat", body=bad)


# --- MachineConditions (macro-thesis learning loop, Layer A) -------------------

from asxos.domain.theses.schemas import (  # noqa: E402
    MachineCondition,
    MachineConditions,
    MachinePredicate,
    MacroThesisProposal,
)

_VALID_MC = {
    "falsifier": {
        "combine": "all",
        "conditions": [
            {"signal": "aus_10y_yield", "op": "lt", "threshold": "4.25",
             "window": 5, "aggregation": "consecutive"}
        ],
    }
}


def test_condition_float_threshold_rejected() -> None:
    # A JSON float loses precision before Decimal sees it (CLAUDE.md #5).
    with pytest.raises(ValidationError):
        MachineCondition(signal="avix", op="lt", threshold=15.5)  # type: ignore[arg-type]


def test_condition_decimal_string_threshold_accepted() -> None:
    c = MachineCondition(signal="avix", op="lt", threshold="15.5")
    assert c.threshold == Decimal("15.5")
    assert c.window == 1
    assert c.aggregation == "consecutive"


def test_condition_unknown_signal_rejected() -> None:
    with pytest.raises(ValidationError):
        MachineCondition(signal="cpi_yoy", op="lt", threshold="2.5")  # type: ignore[arg-type]


def test_condition_window_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        MachineCondition(signal="avix", op="lt", threshold="15", window=0)
    with pytest.raises(ValidationError):
        MachineCondition(signal="avix", op="lt", threshold="15", window=61)


def test_predicate_requires_at_least_one_condition() -> None:
    with pytest.raises(ValidationError):
        MachinePredicate(combine="all", conditions=[])


def test_machine_conditions_requires_catalyst_or_falsifier() -> None:
    with pytest.raises(ValidationError):
        MachineConditions()


def test_machine_conditions_falsifier_only_ok() -> None:
    mc = MachineConditions.model_validate(_VALID_MC)
    assert mc.catalyst is None
    assert mc.falsifier is not None
    assert mc.falsifier.conditions[0].threshold == Decimal("4.25")


def test_machine_conditions_serialises_threshold_as_string() -> None:
    # model_dump_json (the service INSERT contract) must never emit a float.
    mc = MachineConditions.model_validate(_VALID_MC)
    dumped = mc.model_dump(mode="json")
    assert isinstance(dumped["falsifier"]["conditions"][0]["threshold"], str)


def test_macro_proposal_backward_compatible_without_machine_conditions() -> None:
    p = MacroThesisProposal(
        title="Sticky AU long end", thesis_text="Yields stay elevated.",
        regime_quadrant="falling_growth_rising_inflation", horizon_months=6,
        catalyst="RBA holds", falsifier="10y closes below 4.25 for 5 sessions",
        evidence_citation_ids=[1],
    )
    assert p.machine_conditions is None


def test_macro_proposal_with_machine_conditions_validates() -> None:
    p = MacroThesisProposal(
        title="Sticky AU long end", thesis_text="Yields stay elevated.",
        regime_quadrant="falling_growth_rising_inflation", horizon_months=6,
        catalyst="RBA holds", falsifier="10y closes below 4.25 for 5 sessions",
        machine_conditions=MachineConditions.model_validate(_VALID_MC),
        evidence_citation_ids=[1],
    )
    assert p.machine_conditions is not None
    assert p.machine_conditions.falsifier is not None
