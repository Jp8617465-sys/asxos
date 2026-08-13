"""Adversarial tests for the review-status vocabulary (mission P1-04).

Two properties are load-bearing and neither is self-evident from reading the
module:

1. **The state set is closed.** Exactly four states, and a review surface may not
   invent a fifth by emitting a trade direction (packet P1 required-work item 4).
2. **An unknown can never render as CLEAR** (item 5). This is the failure the
   whole vocabulary exists to prevent: "no problem found" and "could not look"
   must not print the same.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from asxos.domain.review import status as status_module
from asxos.domain.review.status import (
    DIRECTIVE_TERMS,
    ReviewOutcome,
    ReviewStatus,
    classify,
    directive_terms,
)

# ---------------------------------------------------------------------------
# The state set is closed
# ---------------------------------------------------------------------------


def test_exactly_four_states_with_the_packet_s_spellings() -> None:
    assert {s.value for s in ReviewStatus} == {
        "CLEAR",
        "ATTENTION",
        "BLOCKED",
        "EVIDENCE_THIN",
    }


def test_no_state_is_a_trade_direction() -> None:
    """A ranking label must never sneak back in as a fifth state."""
    for state in ReviewStatus:
        assert directive_terms(state.value) == ()


# ---------------------------------------------------------------------------
# classify — deterministic, total, and CLEAR is hard to reach
# ---------------------------------------------------------------------------


def test_clear_only_when_all_three_buckets_are_empty() -> None:
    assert classify().status is ReviewStatus.clear


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"blocking": ["check crashed"]}, ReviewStatus.blocked),
        ({"attention": ["revisit overdue"]}, ReviewStatus.attention),
        ({"unknowns": ["no price"]}, ReviewStatus.evidence_thin),
        (
            {"blocking": ["check crashed"], "attention": ["revisit overdue"]},
            ReviewStatus.blocked,
        ),
        (
            {"blocking": ["check crashed"], "unknowns": ["no price"]},
            ReviewStatus.blocked,
        ),
        (
            {"attention": ["revisit overdue"], "unknowns": ["no price"]},
            ReviewStatus.attention,
        ),
        (
            {
                "blocking": ["check crashed"],
                "attention": ["revisit overdue"],
                "unknowns": ["no price"],
            },
            ReviewStatus.blocked,
        ),
    ],
)
def test_precedence_is_blocked_then_attention_then_thin(kwargs, expected) -> None:
    assert classify(**kwargs).status is expected


def test_an_unknown_can_never_produce_clear() -> None:
    """The core item-5 invariant, asserted directly.

    Anything in `unknowns` forbids CLEAR, no matter what else is present. This is
    what stops a surface with a missing input from looking like a clean bill of
    health.
    """
    assert classify(unknowns=["x"]).status is not ReviewStatus.clear
    assert classify(attention=["a"], unknowns=["x"]).status is not ReviewStatus.clear
    assert classify(blocking=["b"], unknowns=["x"]).status is not ReviewStatus.clear


def test_inputs_are_never_discarded_by_the_reduction() -> None:
    """Collapsing to one status must not lose the evidence behind it."""
    out = classify(blocking=["b"], attention=["a"], unknowns=["u"])
    assert out.reasons == ("b", "a")
    assert out.unknowns == ("u",)


def test_classify_is_deterministic_and_accepts_any_sequence_type() -> None:
    a = classify(attention=["x", "y"], unknowns=("z",))
    b = classify(attention=("x", "y"), unknowns=["z"])
    assert a == b
    assert isinstance(a, ReviewOutcome)


def test_is_clear_matches_the_status() -> None:
    assert classify().is_clear
    assert not classify(unknowns=["x"]).is_clear


# ---------------------------------------------------------------------------
# The directive ban — the mechanical half of "not a synthetic buy/trim signal"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("term", sorted(DIRECTIVE_TERMS))
def test_every_banned_term_is_detected(term: str) -> None:
    assert directive_terms(f"we should {term} this position") == (term,)


@pytest.mark.parametrize(
    "label", ["STRONG_BUY", "BUY", "SELL", "STRONG_SELL", "strong-sell", "Trim"]
)
def test_retired_model_a_labels_trip_the_ban(label: str) -> None:
    """Four of the five ladder rungs are caught by the word-boundary rule without
    needing their own entries — `_` and `-` do not shield a banned word."""
    assert directive_terms(f"signal: {label}") != ()


def test_hold_is_deliberately_not_banned_and_the_gap_is_pinned() -> None:
    """`HOLD` — the fifth rung — does NOT trip the ban, on purpose.

    Banning it would fire on ordinary review prose ("holdings", "hold the thesis
    open"), and alone it directs no trade. Pinned as a test so the limit is a
    known property rather than a surprise: this ban stops directives, it is not a
    detector for a reintroduced ranking model.
    """
    assert directive_terms("signal: HOLD") == ()
    assert directive_terms("Holdings: 3") == ()


@pytest.mark.parametrize(
    "text",
    [
        "Holdings: 3",
        "the buyer of last resort",
        "exited_universe was not reached",  # 'exited' is not the imperative 'exit'
        "Review: EVIDENCE_THIN",
        "CBA.AU: review overdue by 16d (due 2026-06-27)",
        "Underlying: unavailable — no current 5d move to measure",
        "additional context",  # 'add' must not match inside 'additional'
    ],
)
def test_no_false_positives_on_legitimate_review_copy(text: str) -> None:
    assert directive_terms(text) == (), text


def test_detection_is_deduped_and_sorted() -> None:
    assert directive_terms("buy buy TRIM add") == ("add", "buy", "trim")


def test_empty_text_is_clean() -> None:
    assert directive_terms("") == ()


# ---------------------------------------------------------------------------
# Model independence, enforced mechanically
# ---------------------------------------------------------------------------

_SOURCE = Path(status_module.__file__).read_text()


def test_module_imports_are_model_independent() -> None:
    """In the style of test_thesis_discipline.py's import contract (manifest T6).

    A review vocabulary that reaches for a model score would re-open the exact
    laundering path rule #11 closes: a model number entering the written case
    wearing a status label.
    """
    # `line.strip()`, not `line` — an indented import is still an import. Matching
    # only column-0 imports would let a function-local
    # `from asxos.domain.models... import ...` walk past the test whose entire job
    # is to catch it.
    import_lines = [
        line
        for line in _SOURCE.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    banned = (
        "signals",
        "shap",
        "model_a",
        "production_gate",
        "domain.models",
        "asxos.db",
    )
    for line in import_lines:
        for token in banned:
            assert token not in line, f"model-dependent import: {line}"


def test_module_is_pure_no_db_and_no_clock() -> None:
    for token in ("async def", "await ", "datetime.now", "date.today"):
        assert token not in _SOURCE, f"{token!r} makes this module impure"
