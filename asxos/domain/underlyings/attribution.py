"""
Underlying attribution scoring — M-Underlyings.

Pure function: score_thesis_underlying(thesis_underlyings, underlying_5d_moves)

Labels:
  confirming — weighted_movement >  +2%  (underlyings support the thesis)
  diverging  — weighted_movement <  -2%  (underlyings contradict the thesis)
  mixed      — weighted_movement in [-2%, +2%]
"""
from __future__ import annotations

from decimal import Decimal

from asxos.domain.underlyings.types import ThesisUnderlying, UnderlyingScore

_CONFIRMING_THRESHOLD = Decimal("2")    # percent
_DIVERGING_THRESHOLD = Decimal("-2")


def score_thesis_underlying(
    thesis_underlyings: list[ThesisUnderlying],
    underlying_5d_moves: dict[int, Decimal | None],  # underlying_id → 5d pct change
) -> UnderlyingScore:
    """Compute a confirming/mixed/diverging score for one thesis.

    thesis_underlyings: all ThesisUnderlying rows for the thesis.
    underlying_5d_moves: 5-day percentage change per underlying_id (may be None if stale).
    """
    if not thesis_underlyings:
        return UnderlyingScore(
            label="mixed",
            weighted_movement=Decimal("0"),
            component_moves=(),
        )

    weighted_sum = Decimal("0")
    components: list[dict] = []

    for tu in thesis_underlyings:
        move = underlying_5d_moves.get(tu.underlying_id)
        if move is None:
            components.append({
                "code": tu.code,
                "exposure": str(tu.exposure),
                "direction": tu.direction.value,
                "move_5d_pct": None,
                "contribution": None,
            })
            continue

        direction_sign = Decimal("1") if tu.direction.value == "positive" else Decimal("-1")
        contribution = tu.exposure * direction_sign * move
        weighted_sum += contribution
        components.append({
            "code": tu.code,
            "exposure": str(tu.exposure),
            "direction": tu.direction.value,
            "move_5d_pct": str(move.quantize(Decimal("0.01"))),
            "contribution": str(contribution.quantize(Decimal("0.000001"))),
        })

    if weighted_sum > _CONFIRMING_THRESHOLD:
        label = "confirming"
    elif weighted_sum < _DIVERGING_THRESHOLD:
        label = "diverging"
    else:
        label = "mixed"

    return UnderlyingScore(
        label=label,
        weighted_movement=weighted_sum.quantize(Decimal("0.000001")),
        component_moves=tuple(components),
    )
