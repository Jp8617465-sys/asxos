"""The two terminal-value conventions, and the absence predicate.

Both conventions are always run; neither replaces the other. The property that
makes them safe to compare is that `fading_excess` at persistence 0 reduces
EXACTLY to `zero_excess` — proven here rather than asserted in a comment.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from asxos.domain.valuation import residual_income as ri
from asxos.domain.valuation.absence import is_missing, is_present

WBC = {
    "book_start": Decimal("16.883740"),
    "roe_start": Decimal("0.112121"),
    "ke": Decimal("0.086810"),
    "payout_ratio": Decimal("0.811696"),
}


# --- the absence predicate ---------------------------------------------------

@pytest.mark.parametrize("value", [None, "", " ", "   ", "\t", "\n", "  \t\n "])
def test_missing_covers_null_empty_and_whitespace(value: object) -> None:
    """`is None` alone passes 2,511 empty-string rows in rs_financial_statements."""
    assert is_missing(value) is True
    assert is_present(value) is False


@pytest.mark.parametrize("value", ["AUD", "USD", " AUD ", 0, Decimal("0")])
def test_present_values_are_present_including_falsy_numbers(value: object) -> None:
    """A zero is a value. Only text absence and None count as missing."""
    assert is_missing(value) is False


# --- the degeneracy proof ----------------------------------------------------

def test_fading_excess_at_zero_persistence_is_exactly_zero_excess() -> None:
    """The two conventions agree at the boundary, to the last digit.

    This is what makes a cross-convention comparison meaningful: any difference
    between them is the persistence assumption, never a formulation difference.
    """
    zero, roe_z, book_z = ri.value_per_share(**WBC)  # type: ignore[arg-type]
    faded, roe_f, book_f = ri.value_per_share(**WBC, persistence=Decimal("0"))  # type: ignore[arg-type]
    assert faded == zero
    assert roe_f == roe_z
    assert book_f == book_z


def test_terminal_value_is_zero_at_zero_persistence() -> None:
    assert ri.terminal_value(
        final_residual_income=Decimal("1.5"), ke=Decimal("0.0868"), persistence=Decimal("0")
    ) == Decimal("0")


# --- the second convention behaves ------------------------------------------

def test_persistence_raises_value_monotonically() -> None:
    values = [
        ri.value_per_share(**WBC, persistence=Decimal(p))[0]  # type: ignore[arg-type]
        for p in ("0", "0.2", "0.4", "0.6", "0.8")
    ]
    assert values == sorted(values), "more surviving excess cannot be worth less"
    assert values[-1] > values[0]


def test_zero_excess_still_fades_to_exactly_ke() -> None:
    _, roe_by_year, _ = ri.value_per_share(**WBC)  # type: ignore[arg-type]
    assert roe_by_year[-1] == WBC["ke"]


def test_fading_excess_stops_the_fade_above_ke_by_the_persistence_fraction() -> None:
    """Terminal ROE = Ke + w*(ROE0 - Ke). One parameter governs fade end AND decay."""
    w = Decimal("0.5")
    _, roe_by_year, _ = ri.value_per_share(**WBC, persistence=w)  # type: ignore[arg-type]
    expected = WBC["ke"] + w * (WBC["roe_start"] - WBC["ke"])
    assert roe_by_year[-1] == expected
    assert roe_by_year[-1] > WBC["ke"]


@pytest.mark.parametrize("bad", [Decimal("1"), Decimal("1.5"), Decimal("-0.1")])
def test_persistence_outside_zero_to_one_is_refused(bad: Decimal) -> None:
    with pytest.raises(ValueError, match=r"persistence must be in \[0, 1\)"):
        ri.value_per_share(**WBC, persistence=bad)  # type: ignore[arg-type]


def test_a_name_earning_no_excess_is_worth_book_under_both_conventions() -> None:
    """Persistence cannot manufacture value where there is no excess to persist."""
    flat = {**WBC, "roe_start": WBC["ke"]}
    zero, _, _ = ri.value_per_share(**flat)  # type: ignore[arg-type]
    faded, _, _ = ri.value_per_share(**flat, persistence=Decimal("0.8"))  # type: ignore[arg-type]
    assert zero == faded == WBC["book_start"]


def test_the_return_base_vocabulary_names_tangible_equity_first() -> None:
    """If book is tangible, the return input is ROTE. The contract must say which."""
    assert ri.ReturnBase.__args__ == ("tangible_common_equity", "reported_book_equity")  # type: ignore[attr-defined]
    assert ri.TerminalConvention.__args__ == ("zero_excess", "fading_excess")  # type: ignore[attr-defined]
