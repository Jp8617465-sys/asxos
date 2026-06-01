"""
Hidden-risk detection for thesis/underlying divergence — M-Underlyings.

detect_hidden_risk(thesis_status, underlying_score) → warning string | None

Triggers when a thesis is bullish (active, not exited) but underlyings diverge.
"""
from __future__ import annotations

from asxos.domain.underlyings.types import UnderlyingScore

_BULLISH_STATUSES = {"watching", "active"}


def detect_hidden_risk(
    thesis_status: str,
    underlying_score: UnderlyingScore,
) -> str | None:
    """Return a warning string if the thesis is bullish but underlyings diverge.

    Returns None if no hidden risk detected.
    """
    if thesis_status not in _BULLISH_STATUSES:
        return None
    if underlying_score.label != "diverging":
        return None
    return (
        f"Hidden risk: thesis is {thesis_status} but underlyings are diverging "
        f"(weighted move {underlying_score.weighted_movement:+.2f}%). "
        "Review underlying assumptions."
    )
