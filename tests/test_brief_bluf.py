"""Stage 1: BLUF sentence is evidence-quality copy, never a directive."""

from __future__ import annotations

from asxos.brief.bluf import bluf_sentence
from asxos.domain.review.status import ReviewOutcome, ReviewStatus, directive_terms


def test_clear_is_nothing_to_do() -> None:
    sentence = bluf_sentence(ReviewOutcome(status=ReviewStatus.clear))
    assert sentence == "Nothing to do."
    assert directive_terms(sentence) == ()


def test_attention_lists_reasons() -> None:
    sentence = bluf_sentence(
        ReviewOutcome(
            status=ReviewStatus.attention,
            reasons=("revisit overdue on CBA.AU", "concentration check is loud"),
        )
    )
    assert sentence == "Look at: revisit overdue on CBA.AU; concentration check is loud."
    assert directive_terms(sentence) == ()


def test_attention_without_reasons_points_at_exceptions() -> None:
    sentence = bluf_sentence(ReviewOutcome(status=ReviewStatus.attention))
    assert sentence == "Look at the exceptions below."
    assert directive_terms(sentence) == ()


def test_blocked_cannot_look() -> None:
    sentence = bluf_sentence(
        ReviewOutcome(status=ReviewStatus.blocked, reasons=("discipline section could not run",))
    )
    assert sentence == "Cannot look."
    assert directive_terms(sentence) == ()


def test_evidence_thin_names_thin_evidence() -> None:
    sentence = bluf_sentence(
        ReviewOutcome(
            status=ReviewStatus.evidence_thin,
            unknowns=("3 holding(s) with no discipline evidence",),
        )
    )
    assert sentence == "Cannot look — evidence is thin."
    assert directive_terms(sentence) == ()
