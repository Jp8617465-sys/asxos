"""
Cross-layer observations — M-Brief-V2-Sections (spec Part 5.5).

Pure function: no I/O, no DB calls. Takes pre-computed context and
returns 0–3 human-readable observation strings for Section 5.

Rules (applied in order, max 3 returned):
  1. Confirming: risk-on regime + ≥50% of theses have confirming underlyings
  2. Diverging:  bullish theses have diverging underlyings (hidden risk signal)
  3. Contradicting: risk-off regime + any thesis still marked active/watching
  4. Mixed: split confirming/diverging across theses (ambiguous environment)
"""
from __future__ import annotations

from asxos.domain.underlyings.types import UnderlyingScore

_RISK_ON_REGIMES = {"risk_on_broadening", "risk_on_narrowing"}
_RISK_OFF_REGIMES = {"risk_off_orderly", "risk_off_disorderly"}
_BULLISH_STATUSES = {"active", "watching"}


def cross_layer_observations(
    regime_label: str | None,
    thesis_scores: list[tuple[str, str, UnderlyingScore]],
) -> list[str]:
    """Generate cross-layer observations linking regime to underlying evidence.

    Args:
        regime_label: current market regime (from market_context_current)
        thesis_scores: list of (symbol, status, UnderlyingScore) tuples

    Returns:
        0–3 observation strings, ordered from most to least important.
    """
    if not thesis_scores:
        return []

    bullish = [(sym, st, sc) for sym, st, sc in thesis_scores if st in _BULLISH_STATUSES]
    if not bullish:
        return []

    confirming = [t for t in bullish if t[2].label == "confirming"]
    diverging = [t for t in bullish if t[2].label == "diverging"]
    mixed = [t for t in bullish if t[2].label == "mixed"]

    observations: list[str] = []

    # Rule 1: risk-off regime with active bullish theses = red flag
    if regime_label in _RISK_OFF_REGIMES and bullish:
        count = len(bullish)
        symbols = ", ".join(t[0] for t in bullish[:3])
        suffix = f" + {count - 3} more" if count > 3 else ""
        observations.append(
            f"Regime {regime_label}: {count} bullish thesis position(s) exposed "
            f"({symbols}{suffix}) — review stop discipline"
        )

    # Rule 2: diverging underlyings on bullish theses = hidden risk
    if diverging:
        symbols = ", ".join(t[0] for t in diverging[:3])
        suffix = f" + {len(diverging) - 3} more" if len(diverging) > 3 else ""
        observations.append(
            f"Underlying divergence on bullish thesis: {symbols}{suffix} — "
            f"commodity/rate drivers moving against thesis direction"
        )

    # Rule 3: confirming in risk-on = alignment signal (informational)
    if (
        len(observations) < 3
        and regime_label in _RISK_ON_REGIMES
        and confirming
    ):
        pct = int(100 * len(confirming) / len(bullish))
        observations.append(
            f"Regime {regime_label}: {pct}% of bullish theses have confirming "
            f"underlying drivers — environment supportive"
        )

    # Rule 4: split mixed/diverging with no clear direction
    if (
        len(observations) < 3
        and mixed
        and not diverging
        and not confirming
        and regime_label not in _RISK_OFF_REGIMES
    ):
        observations.append(
            f"{len(mixed)} thesis underlying(s) showing mixed signals — "
            f"no clear confirming/diverging direction across drivers"
        )

    return observations[:3]
