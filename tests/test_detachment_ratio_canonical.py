"""The detachment ratio has one definition, and these are its worked examples (E-21).

Five different "×detached" figures for CBA circulated across repo docs — 3.4, 3.5, ~4,
2.449195, 2.471264 — and **none of them was bad data.** Three were different,
arithmetically-correct formulas over the same inputs, and two of those three answer a
question the `price_detached` rule is not asking.

`asxos/domain/decision_engine/challenge/rules.py::detachment_ratio` is the definition;
`challenge_results` and `decision_packets` store that form. This file pins the arithmetic so
the docstring that now states it cannot drift from the code, and so the two rejected forms
stay distinguishable rather than being re-derived by whoever next quotes a figure.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from asxos.domain.decision_engine.challenge.rules import detachment_ratio

# CBA thesis #1's recorded entry band, the worked example every one of those figures came from.
_LOWER = Decimal("42")
_UPPER = Decimal("45")
_MID = Decimal("43.5")  # (42 + 45) / 2


def _canonical(close: str) -> Decimal:
    return detachment_ratio(close=Decimal(close), lower=_LOWER, upper=_UPPER)


@pytest.mark.parametrize(
    ("close", "expected"),
    [
        # The figure the 2026-09-17 dossier reconciled to, on the 09-16 close.
        ("151.54", "2.449195"),
        # The figure the 2026-09-16 register review quoted — same formula, 09-15 close.
        # Its apparent disagreement with the line above is one day, not two formulas.
        ("152.50", "2.471264"),
        # The ~168 close that `portfolio-team-visibility` recorded as "~4× detached".
        ("168", "2.827586"),
        # The close `e2e-run-findings-2026-09-07` quotes, which already used this form.
        ("160.42", "2.653333"),
    ],
)
def test_the_canonical_ratio_on_every_figure_the_docs_quote(close: str, expected: str) -> None:
    assert _canonical(close) == Decimal(expected)


@pytest.mark.parametrize("close", ["42", "43.5", "45", "44.999999"])
def test_anywhere_inside_the_band_is_exactly_zero(close: str) -> None:
    """The property that makes this the right quantity for the rule, and the one both
    rejected forms lack: a close sitting comfortably inside its own entry band is not
    detached at all, so the rule must stay silent. `close / upper` would report 0.93 here
    and `close / midpoint` 1.0 — the latter *at the blocking threshold*, for a thesis whose
    price plan is working exactly as written.
    """
    assert _canonical(close) == Decimal("0")


def test_below_the_band_is_measured_from_the_lower_edge() -> None:
    """Symmetry, which neither rejected form has: detachment is distance from the NEAREST
    edge, so a close below the band is as detached as one the same distance above it."""
    assert _canonical("41") == detachment_ratio(
        close=Decimal("46"), lower=_LOWER, upper=_UPPER
    )
    assert _canonical("41") == Decimal("0.022989")  # 1 / 43.5


@pytest.mark.parametrize(
    ("label", "value", "expected"),
    [
        ("close / upper", Decimal("151.54") / _UPPER, "3.367556"),
        ("close / midpoint", Decimal("151.54") / _MID, "3.483678"),
    ],
)
def test_the_two_rejected_forms_are_reproduced_so_a_stale_figure_is_identifiable(
    label: str, value: Decimal, expected: str
) -> None:
    """Deliberately pins the formulas that are NOT used.

    The point is not to bless them. It is that when someone finds "3.4×" or "3.5×" in a dated
    proposal, the useful question is *which formula produced this*, and that is answerable
    only if the alternatives are written down somewhere executable. Both round to the figures
    the docs actually carry, which is how the five-figure discrepancy was resolved without
    anyone suspecting the data.
    """
    assert round(value, 6) == Decimal(expected), label
    assert value != _canonical("151.54")


def test_the_docstring_states_the_definition_rather_than_pointing_elsewhere() -> None:
    """E-21's pass test is "one definition named in the docs with its formula beside it".

    The definition's home is this function's own docstring, because a definition that lives
    in a dated proposal is one someone has to go looking for — which is how three formulas
    coexisted for months. If a future edit shortens it back to a one-liner, the docs that now
    point here stop resolving, so this fails.
    """
    doc = detachment_ratio.__doc__ or ""

    assert "canonical" in doc.lower()
    assert "midpoint" in doc
    assert "nearest band edge" in doc
    # The two rejected forms must stay named, so a reader can identify a stale quote.
    assert "close / upper" in doc
    assert "close / midpoint" in doc


def test_the_docs_point_at_the_function_rather_than_restating_the_formula() -> None:
    """The corrections are annotations on dated proposals, not rewrites of them — the
    repo's convention for a historical record. What each one must do is name where the
    canonical quantity is defined, so the figure beside it is traceable.
    """
    repo = Path(__file__).resolve().parent.parent
    for rel in (
        "docs/proposals/governor-drafts-2026-09-02.md",
        "docs/proposals/portfolio-team-visibility-2026-07-12.md",
    ):
        text = (repo / rel).read_text(encoding="utf-8")
        assert "E-21" in text, f"{rel} carries no correction marker"
        assert "detachment_ratio" in text, f"{rel} does not name the canonical definition"
