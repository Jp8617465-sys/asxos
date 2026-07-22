"""Tests for jobs/score_macro_theses.py — the macro-thesis learning loop
(Layer A) falsifier/catalyst evaluator.

Pure evaluation logic, no DB: the scoring functions operate on plain
market_context row dicts + machine_conditions dicts, so they are exercised
directly. Covers window aggregation (consecutive/any/majority), predicate
combine (all/any), status precedence, the conservative NULL-value rule, the
unknown-signal guard, insufficient-history, and calendar-horizon expiry.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from jobs.score_macro_theses import (
    _condition_satisfied,
    _predicate_satisfied,
    score_thesis,
)


def _rows(signal: str, values: list) -> list[dict]:
    """market_context history for one signal, oldest-first. None => missing."""
    return [{signal: (None if v is None else Decimal(str(v)))} for v in values]


def _cond(signal="avix", op="lt", threshold="15", window=3, aggregation="consecutive"):  # type: ignore[no-untyped-def]
    return {
        "signal": signal,
        "op": op,
        "threshold": threshold,
        "window": window,
        "aggregation": aggregation,
    }


# --- aggregation: consecutive / any / majority --------------------------------

def test_consecutive_all_satisfy() -> None:
    assert _condition_satisfied(_rows("avix", [14, 14, 14]), _cond()) is True


def test_consecutive_one_break_fails() -> None:
    assert _condition_satisfied(_rows("avix", [14, 16, 14]), _cond()) is False


def test_any_one_satisfies() -> None:
    c = _cond(aggregation="any")
    assert _condition_satisfied(_rows("avix", [16, 16, 14]), c) is True
    assert _condition_satisfied(_rows("avix", [16, 16, 16]), c) is False


def test_majority_strictly_over_half() -> None:
    c = _cond(aggregation="majority")
    assert _condition_satisfied(_rows("avix", [14, 14, 16]), c) is True   # 2/3
    assert _condition_satisfied(_rows("avix", [14, 16, 16]), c) is False  # 1/3


def test_majority_exact_tie_is_not_majority() -> None:
    c = _cond(window=2, aggregation="majority")
    assert _condition_satisfied(_rows("avix", [14, 16]), c) is False  # 1/2 == 50%


# --- window uses only the LAST `window` rows ----------------------------------

def test_only_trailing_window_counts() -> None:
    # First two rows fail the condition, but only the last 3 are inspected.
    c = _cond(window=3, aggregation="consecutive")
    assert _condition_satisfied(_rows("avix", [99, 99, 14, 14, 14]), c) is True


# --- NULL value is conservatively not-satisfied -------------------------------

def test_null_value_in_window_not_satisfied() -> None:
    # A missing value must never let a consecutive condition confirm/falsify.
    assert _condition_satisfied(_rows("avix", [14, None, 14]), _cond()) is False


def test_null_value_still_allows_any_on_a_present_row() -> None:
    c = _cond(aggregation="any")
    assert _condition_satisfied(_rows("avix", [None, None, 14]), c) is True


# --- insufficient history ------------------------------------------------------

def test_fewer_than_window_rows_not_satisfied() -> None:
    assert _condition_satisfied(_rows("avix", [14, 14]), _cond(window=3)) is False


# --- unknown signal guard (raw-SQL / stale-annotation) ------------------------

def test_unknown_signal_raises() -> None:
    with pytest.raises(RuntimeError, match="unknown signal"):
        _condition_satisfied(_rows("avix", [14, 14, 14]), _cond(signal="cpi_yoy"))


# --- operator coverage ---------------------------------------------------------

def test_operators_gt_gte_lt_lte() -> None:
    r = _rows("asx200_close", [8600])
    assert _condition_satisfied(r, _cond(signal="asx200_close", op="gt", threshold="8500", window=1)) is True
    assert _condition_satisfied(r, _cond(signal="asx200_close", op="gt", threshold="8600", window=1)) is False
    assert _condition_satisfied(r, _cond(signal="asx200_close", op="gte", threshold="8600", window=1)) is True
    assert _condition_satisfied(r, _cond(signal="asx200_close", op="lt", threshold="8700", window=1)) is True
    assert _condition_satisfied(r, _cond(signal="asx200_close", op="lte", threshold="8600", window=1)) is True


# --- predicate combine: all vs any --------------------------------------------

def _two_signal_rows(a_vals: list, b_vals: list) -> list[dict]:
    return [
        {"pct_above_200d_ma": Decimal(str(a)), "asx200_close": Decimal(str(b))}
        for a, b in zip(a_vals, b_vals, strict=True)
    ]


def test_combine_all_requires_every_condition() -> None:
    rows = _two_signal_rows([0.6, 0.6], [8700, 8700])
    pred = {
        "combine": "all",
        "conditions": [
            _cond(signal="pct_above_200d_ma", op="gte", threshold="0.50", window=2),
            _cond(signal="asx200_close", op="gt", threshold="8600", window=2),
        ],
    }
    assert _predicate_satisfied(rows, pred) is True

    rows_break = _two_signal_rows([0.6, 0.6], [8500, 8500])  # 2nd condition fails
    assert _predicate_satisfied(rows_break, pred) is False


def test_combine_any_needs_one_condition() -> None:
    rows = _two_signal_rows([0.6, 0.6], [8500, 8500])  # only the first passes
    pred = {
        "combine": "any",
        "conditions": [
            _cond(signal="pct_above_200d_ma", op="gte", threshold="0.50", window=2),
            _cond(signal="asx200_close", op="gt", threshold="8600", window=2),
        ],
    }
    assert _predicate_satisfied(rows, pred) is True


# --- score_thesis: status precedence ------------------------------------------

_JAN1 = date(2026, 1, 1)


def _falsifier(**kw) -> dict:  # type: ignore[no-untyped-def]
    return {"falsifier": {"combine": "all", "conditions": [_cond(**kw)]}}


def _catalyst(**kw) -> dict:  # type: ignore[no-untyped-def]
    return {"catalyst": {"combine": "all", "conditions": [_cond(**kw)]}}


def test_falsified_beats_confirmed() -> None:
    # Both catalyst and falsifier satisfied -> falsified wins.
    mc = {
        "catalyst": {"combine": "all", "conditions": [_cond(op="lt", threshold="15")]},
        "falsifier": {"combine": "all", "conditions": [_cond(op="lt", threshold="15")]},
    }
    out = score_thesis(mc, _rows("avix", [14, 14, 14]), created_at=_JAN1,
                        eval_as_of=date(2026, 1, 10), horizon_months=6)
    assert out["status"] == "falsified"
    assert out["falsifier_triggered"] is True


def test_confirmed_when_catalyst_only() -> None:
    mc = _catalyst(op="lt", threshold="15")
    out = score_thesis(mc, _rows("avix", [14, 14, 14]), created_at=_JAN1,
                       eval_as_of=date(2026, 1, 10), horizon_months=6)
    assert out["status"] == "confirmed"
    assert out["falsifier_triggered"] is False


def test_expired_via_horizon() -> None:
    # Falsifier present but NOT met; past the calendar horizon -> expired.
    mc = _falsifier(op="lt", threshold="15")  # rows are all 20 -> not met
    out = score_thesis(mc, _rows("avix", [20, 20, 20]), created_at=_JAN1,
                       eval_as_of=date(2026, 3, 2), horizon_months=1)
    assert out["status"] == "expired"
    assert out["falsifier_triggered"] is False


def test_open_when_predicate_unmet_and_within_horizon() -> None:
    mc = _falsifier(op="lt", threshold="15")
    out = score_thesis(mc, _rows("avix", [20, 20, 20]), created_at=_JAN1,
                       eval_as_of=date(2026, 1, 15), horizon_months=6)
    assert out["status"] == "open"


def test_open_when_insufficient_history() -> None:
    # window=10 but only 3 rows -> falsifier cannot be met -> open.
    mc = _falsifier(op="lt", threshold="15", window=10)
    out = score_thesis(mc, _rows("avix", [14, 14, 14]), created_at=_JAN1,
                       eval_as_of=date(2026, 1, 6), horizon_months=6)
    assert out["status"] == "open"


def test_no_machine_conditions_is_open_with_reason() -> None:
    out = score_thesis(None, _rows("avix", [14, 14, 14]), created_at=_JAN1,
                       eval_as_of=date(2026, 1, 10), horizon_months=6)
    assert out["status"] == "open"
    assert out["catalyst_progress"] is None
    assert out["falsifier_triggered"] is False
    assert out["evaluation_detail"] == {"reason": "no_machine_conditions"}


def test_empty_machine_conditions_dict_is_open_with_reason() -> None:
    out = score_thesis({}, _rows("avix", [14, 14, 14]), created_at=_JAN1,
                       eval_as_of=date(2026, 1, 10), horizon_months=6)
    assert out["evaluation_detail"] == {"reason": "no_machine_conditions"}


# --- score_thesis: catalyst_progress ------------------------------------------

def test_catalyst_progress_fraction() -> None:
    # Two catalyst conditions, one satisfied -> 0.5.
    mc = {
        "catalyst": {
            "combine": "all",
            "conditions": [
                _cond(signal="pct_above_200d_ma", op="gte", threshold="0.50", window=1),
                _cond(signal="asx200_close", op="gt", threshold="9000", window=1),
            ],
        }
    }
    rows = _two_signal_rows([0.6], [8700])  # breadth passes, index does not
    out = score_thesis(mc, rows, created_at=_JAN1,
                       eval_as_of=date(2026, 1, 10), horizon_months=6)
    assert out["catalyst_progress"] == Decimal("0.5")
    # combine='all' not met (one condition fails), within horizon -> open
    assert out["status"] == "open"


def test_catalyst_progress_full() -> None:
    mc = _catalyst(op="lt", threshold="15", window=1)
    out = score_thesis(mc, _rows("avix", [14]), created_at=_JAN1,
                       eval_as_of=date(2026, 1, 10), horizon_months=6)
    assert out["catalyst_progress"] == Decimal("1")
    assert out["status"] == "confirmed"


def test_no_horizon_never_expires() -> None:
    # horizon_months None -> the expired branch is skipped even far in the future.
    mc = _falsifier(op="lt", threshold="15")
    out = score_thesis(mc, _rows("avix", [20, 20, 20]), created_at=_JAN1,
                       eval_as_of=date(2030, 1, 1), horizon_months=None)
    assert out["status"] == "open"
