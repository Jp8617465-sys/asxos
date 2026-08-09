"""Tests for asxos/domain/theses/condition_parser.py (0042, D1/R2).

Pins the cp-1 contract: the four live HUBS strings, the qualifier-narrowing
echo (register #5), the price-like-clause warning, the frozen-embedded-value
labelling, the 6dp threshold quantisation, evaluate() semantics, and — the
load-bearing one — that the migration 0042 backfill's hardcoded baseline rows
are exactly what the parser emits (test_migration_0042_baselines_match_parser).
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from asxos.domain.theses.condition_parser import (
    PARSER_VERSION,
    EmbeddedFigure,
    evaluate,
    lint_echo,
    parse_condition,
)

_MIGRATION = Path(__file__).parent.parent / "migrations" / "0042_rules_integrity.sql"

# The four live HUBS (thesis 2) strings and their cp-1 baselines, exactly as
# hardcoded in migration 0042 section 6.
_HUBS = [
    (
        "Price closes below $230 stop on volume",
        "price_below",
        Decimal("230.000000"),
        "will enforce: close < 230.000000. Qualifier 'on volume' NOT enforced (recorded narrowing).",
    ),
    (
        "50d MA ($243.61) not recaptured within 2 weeks of breach",
        "not_machine_checkable",
        None,
        "NOT MACHINE-CHECKED — manual review only. Contains frozen embedded value "
        "'50d MA ($243.61)' (authoring-time; re-derived by sweep).",
    ),
    (
        "Macro regime shifts to risk_off_disorderly",
        "not_machine_checkable",
        None,
        "NOT MACHINE-CHECKED — manual review only.",
    ),
    (
        "Three or more sell-side downgrades with consensus target below $220",
        "not_machine_checkable",
        None,
        "NOT MACHINE-CHECKED — manual review only. Contains a price-like clause "
        "('below $220') that is NOT enforced.",
    ),
]


# --- HUBS pinning ---


def test_hubs_condition_1_price_below_with_dropped_qualifier():
    p = parse_condition(_HUBS[0][0])
    assert p.kind == "price_below"
    assert p.threshold == Decimal("230.000000")
    assert str(p.threshold) == "230.000000"  # 6dp quantised on storage
    assert p.dropped_qualifiers == ("on volume",)
    assert p.embedded_figures == ()  # the $230 was consumed as the threshold
    assert "NOT enforced" in p.echo  # a narrowing is never silent


def test_hubs_condition_2_frozen_ma_figure():
    p = parse_condition(_HUBS[1][0])
    assert p.kind == "not_machine_checkable"
    assert p.threshold is None
    assert p.dropped_qualifiers == ()  # qualifiers only alongside a matched pattern
    assert p.embedded_figures == (EmbeddedFigure(label="50d MA", value=Decimal("243.61")),)
    assert "50d MA" in p.echo and "re-derived by sweep" in p.echo


def test_hubs_condition_3_plain_unparseable():
    p = parse_condition(_HUBS[2][0])
    assert p.kind == "not_machine_checkable"
    assert p.embedded_figures == ()
    assert p.echo == "NOT MACHINE-CHECKED — manual review only."


def test_hubs_condition_4_price_like_clause_warned():
    p = parse_condition(_HUBS[3][0])
    assert p.kind == "not_machine_checkable"
    assert "price-like clause ('below $220')" in p.echo
    assert "NOT enforced" in p.echo
    # $220 is captured as an unlabelled figure but NOT echoed as frozen value.
    assert p.embedded_figures == (EmbeddedFigure(label="", value=Decimal("220")),)


def test_migration_0042_baselines_match_parser():
    """The migration's hand-transliterated baseline rows must equal the cp-1
    parser output — both directions: (a) parser output matches the pinned
    tuples; (b) each echo appears verbatim (SQL-quote-doubled) in the actual
    migration file, so neither side can drift alone."""
    sql = _MIGRATION.read_text()
    assert PARSER_VERSION == "cp-1"
    assert "'cp-1'" in sql
    for text, kind, threshold, echo in _HUBS:
        p = parse_condition(text)
        assert p.kind == kind, text
        assert p.threshold == threshold, text
        assert p.echo == echo, text
        assert text.replace("'", "''") in sql, f"condition text not in migration: {text}"
        assert echo.replace("'", "''") in sql, f"echo not in migration: {echo}"


# --- parity with the pre-0042 job patterns ---


def test_parse_below_variants():
    assert parse_condition("Price falls below $150").threshold == Decimal("150.000000")
    assert parse_condition("Price falls below $150").kind == "price_below"
    assert parse_condition("Close under 45.50").kind == "price_below"
    assert parse_condition("Close under 45.50").threshold == Decimal("45.500000")


def test_parse_above_variants():
    assert parse_condition("Price above $300").kind == "price_above"
    p = parse_condition("Stock rises above 8.20")
    assert p.kind == "price_above"
    assert p.threshold == Decimal("8.200000")


def test_first_match_wins_below_before_above():
    # Parity with the old job: below is tried first.
    p = parse_condition("Price falls below $10 or price rises above $20")
    assert p.kind == "price_below"
    assert p.threshold == Decimal("10.000000")


def test_unrecognized_is_not_machine_checkable():
    assert parse_condition("Macro regime shifts").kind == "not_machine_checkable"
    assert parse_condition("Three sell-side downgrades").kind == "not_machine_checkable"


# --- qualifiers ---


@pytest.mark.parametrize("qualifier", ["on volume", "with volume", "intraday", "on a weekly close"])
def test_recognised_qualifiers_recorded_and_echoed(qualifier: str):
    p = parse_condition(f"Price closes below $100 {qualifier}")
    assert p.kind == "price_below"
    assert qualifier in p.dropped_qualifiers
    assert f"Qualifier '{qualifier}' NOT enforced" in p.echo


def test_within_n_weeks_qualifier_recorded_alongside_match():
    p = parse_condition("Close below $50 within 2 weeks")
    assert p.dropped_qualifiers == ("within 2 weeks",)
    # The "2" of "within 2 weeks" must NOT become a phantom embedded figure.
    assert p.embedded_figures == ()


# --- evaluate ---


def test_evaluate_price_below_strict():
    assert evaluate("price_below", Decimal("230"), Decimal("229.99")) is True
    assert evaluate("price_below", Decimal("230"), Decimal("230")) is False
    assert evaluate("price_below", Decimal("230"), Decimal("230.01")) is False


def test_evaluate_price_above_strict():
    assert evaluate("price_above", Decimal("300"), Decimal("300.01")) is True
    assert evaluate("price_above", Decimal("300"), Decimal("300")) is False


def test_evaluate_rejects_not_machine_checkable():
    with pytest.raises(ValueError, match="not_machine_checkable"):
        evaluate("not_machine_checkable", Decimal("1"), Decimal("1"))


# --- lint_echo ---


def test_lint_echo_block_shape():
    block = lint_echo([t for t, _k, _th, _e in _HUBS])
    lines = block.split("\n")
    assert lines[0] == (
        "what I will enforce: [1] close < 230.000000 (qualifier 'on volume' NOT enforced)"
    )
    assert lines[1] == "conditions 2-4 NOT machine-checked — manual review only"


def test_lint_echo_no_checkable_conditions():
    block = lint_echo(["Macro regime shifts"])
    assert "nothing — no machine-checkable conditions" in block
    assert "condition 1 NOT machine-checked" in block


def test_lint_echo_non_contiguous_unchecked():
    block = lint_echo([
        "Macro regime shifts",
        "Price below $10",
        "Sentiment collapses",
    ])
    assert "conditions 1, 3 NOT machine-checked" in block
