"""Bottom-line-up-front sentence for the live daily brief (Stage 1).

One sentence, derived only from a :class:`~asxos.domain.review.status.ReviewOutcome`.
It is a statement about whether the governor needs to look, never a trade
instruction. :func:`asxos.domain.review.status.directive_terms` is the testable ban.

This module does not import :class:`~asxos.brief.compose.BriefData` and does not
import ``asxos.domain.brief``.
"""

from __future__ import annotations

from asxos.domain.review.status import ReviewOutcome, ReviewStatus


def bluf_sentence(review: ReviewOutcome) -> str:
    """One BLUF sentence for ``review.status``.

    * ``CLEAR`` — ``"Nothing to do."``
    * ``ATTENTION`` — ``"Look at: {reasons}."`` when reasons exist, otherwise
      ``"Look at the exceptions below."``
    * ``BLOCKED`` — ``"Cannot look."``
    * ``EVIDENCE_THIN`` — ``"Cannot look — evidence is thin."``
    """
    match review.status:
        case ReviewStatus.clear:
            return "Nothing to do."
        case ReviewStatus.attention:
            if review.reasons:
                return f"Look at: {'; '.join(review.reasons)}."
            return "Look at the exceptions below."
        case ReviewStatus.blocked:
            return "Cannot look."
        case ReviewStatus.evidence_thin:
            return "Cannot look — evidence is thin."
    raise ValueError(f"unhandled review status: {review.status!r}")
