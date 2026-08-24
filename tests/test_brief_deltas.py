"""Stage 1: BookDelta is current-minus-prior levels, never a return. No DB."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from asxos.brief.deltas import BookDelta, SnapshotLevels

_PRIOR = SnapshotLevels(
    as_of=date(2026, 5, 21),
    capital_aud=Decimal("100000.000000"),
    holdings_mv_aud=Decimal("80000.000000"),
    cash_aud=Decimal("20000.000000"),
    holdings_count=2,
)
_CURRENT = SnapshotLevels(
    as_of=date(2026, 5, 22),
    capital_aud=Decimal("110000.000000"),
    holdings_mv_aud=Decimal("90000.000000"),
    cash_aud=Decimal("20000.000000"),
    holdings_count=3,
)


def test_snapshot_levels_are_comparable() -> None:
    assert _PRIOR < _CURRENT
    assert _CURRENT > _PRIOR
    same_day_higher = SnapshotLevels(
        as_of=_PRIOR.as_of,
        capital_aud=Decimal("100000.000001"),
        holdings_mv_aud=_PRIOR.holdings_mv_aud,
        cash_aud=_PRIOR.cash_aud,
        holdings_count=_PRIOR.holdings_count,
    )
    assert _PRIOR < same_day_higher


def test_deltas_are_subtraction_not_a_return() -> None:
    delta = BookDelta(current=_CURRENT, prior=_PRIOR)
    assert delta.capital_delta == Decimal("10000.000000")
    assert delta.holdings_mv_delta == Decimal("10000.000000")
    assert delta.cash_delta == Decimal("0.000000")
    assert delta.holdings_count_delta == 1
    # A return would be 0.10 (10%). The property is a level change.
    assert delta.capital_delta != (_CURRENT.capital_aud / _PRIOR.capital_aud - 1)


def test_missing_side_yields_none_deltas() -> None:
    assert BookDelta(current=_CURRENT, prior=None).capital_delta is None
    assert BookDelta(current=None, prior=_PRIOR).holdings_mv_delta is None
    empty = BookDelta()
    assert empty.capital_delta is None
    assert empty.holdings_mv_delta is None
    assert empty.cash_delta is None
    assert empty.holdings_count_delta is None
