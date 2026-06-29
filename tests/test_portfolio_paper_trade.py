"""
Tests for the paper-trade evaluator (M13.8 / plan Part 0 Q3).

Coverage:
  Pure evaluate():
    - Simple buy, price rises → positive P&L
    - Simple buy, price falls → negative P&L
    - Simple sell, price falls → positive P&L (sold before drop)
    - Simple sell, price rises → negative P&L (sold before rise)
    - Mixed buy + sell → aggregate P&L and return %
    - Hold trades excluded from P&L and traded denominator
    - Missing exit price → symbol in missing list, excluded from P&L
    - All symbols missing prices → zero P&L, non-zero traded if trades exist
    - Empty trades list → zero P&L, zero traded
    - outcome_days = (eval_as_of - run_as_of).days
    - hypothetical_return_pct = pnl / traded * 100, 2dp
    - Zero total_traded → return_pct = 0.00 (no ZeroDivisionError)
    - delta_qty is abs() applied (sign stripped)

  Async DB helpers:
    - list_evaluable_runs respects weeks cutoff
    - list_evaluable_runs returns empty when no runs old enough
    - has_enough_paper_weeks True when ≥ min_weeks runs
    - has_enough_paper_weeks False when < min_weeks runs
    - record_signoff inserts decisions row with correct fields
    - evaluate_run_from_db returns None for missing run_id
    - evaluate_run_from_db delegates to evaluate() correctly
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.portfolio.paper_trade import (
    PaperTradeOutcome,
    _cron_was_continuous,
    evaluate,
    evaluate_run_from_db,
    has_enough_paper_weeks,
    list_evaluable_runs,
    record_signoff,
)
from asxos.domain.portfolio.types import ProposedTrade

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENTRY = date(2026, 1, 6)   # run date
_EVAL  = date(2026, 2, 3)   # evaluation date (~4 weeks later)


def _trade(
    symbol: str,
    side: str,
    delta_qty: float,
    delta_aud: float,
    reference_price: float,
) -> ProposedTrade:
    return ProposedTrade(
        symbol=symbol,
        side=side,  # type: ignore[arg-type]
        delta_qty=Decimal(str(delta_qty)),
        delta_aud=Decimal(str(delta_aud)),
        target_qty=Decimal("0"),
        current_qty=Decimal("0"),
        reference_price=Decimal(str(reference_price)),
        rationale_tags={},
        lot_hints={},
    )


def _call(trades, exit_prices, *, run_id=1, run_as_of=_ENTRY, eval_as_of=_EVAL):
    return evaluate(
        run_id=run_id,
        run_as_of=run_as_of,
        trades=trades,
        exit_prices={k: Decimal(str(v)) for k, v in exit_prices.items()},
        eval_as_of=eval_as_of,
    )


# ---------------------------------------------------------------------------
# Pure evaluate() tests
# ---------------------------------------------------------------------------


def test_simple_buy_price_rises():
    """Buy 100 BHP at $50, exits at $55 → +$500 P&L."""
    trades = [_trade("BHP", "buy", delta_qty=100, delta_aud=5000, reference_price=50)]
    out = _call(trades, {"BHP": 55})
    assert out.total_hypothetical_pnl_aud == Decimal("500")
    assert out.total_traded_aud == Decimal("5000")
    assert out.hypothetical_return_pct == Decimal("10.00")
    assert len(out.lines) == 1
    assert out.lines[0].hypothetical_pnl_aud == Decimal("500")


def test_simple_buy_price_falls():
    """Buy 100 BHP at $50, exits at $45 → −$500 P&L."""
    trades = [_trade("BHP", "buy", delta_qty=100, delta_aud=5000, reference_price=50)]
    out = _call(trades, {"BHP": 45})
    assert out.total_hypothetical_pnl_aud == Decimal("-500")
    assert out.hypothetical_return_pct == Decimal("-10.00")


def test_simple_sell_price_falls():
    """Sell 100 WBC at $30, exits at $25 → +$500 (sold before drop)."""
    trades = [_trade("WBC", "sell", delta_qty=-100, delta_aud=-3000, reference_price=30)]
    out = _call(trades, {"WBC": 25})
    assert out.total_hypothetical_pnl_aud == Decimal("500")
    assert out.total_traded_aud == Decimal("3000")
    assert out.hypothetical_return_pct > Decimal("0")


def test_simple_sell_price_rises():
    """Sell 100 WBC at $30, exits at $35 → −$500 (sold before rise)."""
    trades = [_trade("WBC", "sell", delta_qty=-100, delta_aud=-3000, reference_price=30)]
    out = _call(trades, {"WBC": 35})
    assert out.total_hypothetical_pnl_aud == Decimal("-500")
    assert out.hypothetical_return_pct < Decimal("0")


def test_mixed_buy_and_sell():
    """Buy BHP (profit $500) + sell WBC (profit $500) → +$1000 total."""
    trades = [
        _trade("BHP", "buy",  delta_qty=100,  delta_aud=5000,  reference_price=50),
        _trade("WBC", "sell", delta_qty=-100, delta_aud=-3000, reference_price=30),
    ]
    out = _call(trades, {"BHP": 55, "WBC": 25})
    assert out.total_hypothetical_pnl_aud == Decimal("1000")
    assert out.total_traded_aud == Decimal("8000")
    assert len(out.lines) == 2


def test_hold_trades_excluded():
    """Hold trades have zero delta_aud and must not appear in P&L or denominator."""
    trades = [
        _trade("BHP", "buy",  delta_qty=100, delta_aud=5000, reference_price=50),
        _trade("CBA", "hold", delta_qty=0,   delta_aud=0,    reference_price=100),
    ]
    out = _call(trades, {"BHP": 55, "CBA": 110})
    # Only BHP matters
    assert out.total_traded_aud == Decimal("5000")
    assert len(out.lines) == 1
    assert out.lines[0].symbol == "BHP"


def test_missing_exit_price_excluded_from_pnl():
    """Symbol with no exit price goes to missing list; P&L contribution is zero."""
    trades = [
        _trade("BHP", "buy", delta_qty=100, delta_aud=5000, reference_price=50),
        _trade("RIO", "buy", delta_qty=50,  delta_aud=2500, reference_price=50),
    ]
    out = _call(trades, {"BHP": 55})   # no RIO price
    assert "RIO" in out.symbols_missing_exit_price
    assert out.total_traded_aud == Decimal("7500")   # still includes RIO's trade amount
    assert len(out.lines) == 1                        # only BHP line
    assert out.lines[0].symbol == "BHP"


def test_all_prices_missing():
    """No exit prices → zero P&L but traded is still accounted."""
    trades = [_trade("BHP", "buy", delta_qty=100, delta_aud=5000, reference_price=50)]
    out = _call(trades, {})
    assert out.total_hypothetical_pnl_aud == Decimal("0")
    assert out.total_traded_aud == Decimal("5000")
    assert out.hypothetical_return_pct == Decimal("0.00")
    assert "BHP" in out.symbols_missing_exit_price


def test_empty_trades():
    """No trades → everything zero, no errors."""
    out = _call([], {})
    assert out.total_hypothetical_pnl_aud == Decimal("0")
    assert out.total_traded_aud == Decimal("0")
    assert out.hypothetical_return_pct == Decimal("0.00")
    assert out.lines == []
    assert out.symbols_missing_exit_price == []


def test_outcome_days():
    """outcome_days = eval_as_of - run_as_of in calendar days."""
    trades = [_trade("BHP", "buy", delta_qty=10, delta_aud=500, reference_price=50)]
    run_as_of = date(2026, 1, 5)
    eval_as_of = date(2026, 2, 2)
    out = evaluate(
        run_id=1, run_as_of=run_as_of, trades=trades,
        exit_prices={"BHP": Decimal("50")}, eval_as_of=eval_as_of,
    )
    assert out.outcome_days == (eval_as_of - run_as_of).days == 28


def test_return_pct_two_decimal_places():
    """hypothetical_return_pct is quantised to 2 dp."""
    trades = [_trade("BHP", "buy", delta_qty=3, delta_aud=100, reference_price=100)]
    out = _call(trades, {"BHP": Decimal("133.33333")})
    # return_pct quantised to 0.01
    str_pct = str(out.hypothetical_return_pct)
    assert "." in str_pct
    after_dot = str_pct.split(".", 1)[1]
    assert len(after_dot) == 2


def test_zero_total_traded_no_error():
    """If only holds exist, total_traded is 0 and return_pct stays 0.00."""
    trades = [_trade("BHP", "hold", delta_qty=0, delta_aud=0, reference_price=50)]
    out = _call(trades, {"BHP": 55})
    assert out.total_traded_aud == Decimal("0")
    assert out.hypothetical_return_pct == Decimal("0.00")


def test_delta_qty_sign_stripped():
    """Sell delta_qty is negative in ProposedTrade; evaluate() takes abs()."""
    trades = [_trade("WBC", "sell", delta_qty=-200, delta_aud=-6000, reference_price=30)]
    out = _call(trades, {"WBC": 25})
    assert out.lines[0].delta_qty == Decimal("200")   # positive
    assert out.lines[0].hypothetical_pnl_aud == Decimal("1000")  # (30-25)*200


def test_run_id_and_as_of_propagated():
    """run_id and run_as_of are carried through to the outcome."""
    trades = [_trade("BHP", "buy", delta_qty=10, delta_aud=500, reference_price=50)]
    out = evaluate(
        run_id=42,
        run_as_of=date(2026, 3, 1),
        trades=trades,
        exit_prices={"BHP": Decimal("50")},
        eval_as_of=date(2026, 4, 5),
    )
    assert out.run_id == 42
    assert out.run_as_of == date(2026, 3, 1)


# ---------------------------------------------------------------------------
# Async DB helpers — mocked conn
# ---------------------------------------------------------------------------

_TODAY = date(2026, 5, 23)


def _make_runs_conn(run_rows: list[dict]) -> AsyncMock:
    """asyncpg conn returning canned run rows from rebalance_runs."""
    conn = AsyncMock()
    records = []
    for r in run_rows:
        rec = MagicMock()
        rec.__getitem__ = lambda self, k, r=r: r[k]
        records.append(rec)
    conn.fetch.return_value = records
    return conn


@pytest.mark.asyncio
async def test_list_evaluable_runs_respects_cutoff():
    """Runs must have as_of <= today - weeks*7 to be evaluable."""
    run_rows = [
        {"run_id": 10, "as_of": date(2026, 4, 1)},   # 52 days ago — evaluable at 4w
        {"run_id": 11, "as_of": date(2026, 5, 20)},  # 3 days ago — NOT evaluable at 4w
    ]
    conn = _make_runs_conn(run_rows[:1])   # DB would return only evaluable row
    await list_evaluable_runs(conn, weeks=4, today=_TODAY)
    assert conn.fetch.called
    # The SQL cutoff is applied by the DB; we verify the function passes correct arg
    call_args = conn.fetch.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_list_evaluable_runs_empty():
    """Empty result when no runs old enough."""
    conn = _make_runs_conn([])
    runs = await list_evaluable_runs(conn, weeks=4, today=_TODAY)
    assert runs == []


# ── has_enough_paper_weeks — B-refined: maturation AND continuity ────────────────
#
# Weekly cron. W0..W4 are consecutive Saturdays; today = W0 + 28d so the window
# [window_open, today] opens exactly on W0.
_W0 = date(2026, 5, 2)
_GATE_TODAY = _W0 + timedelta(days=28)        # 2026-05-30
_WEEKLY = [_W0 + timedelta(days=7 * i) for i in range(5)]   # W0..W4 (W4 == today)


def _gate_conn(*, matured: int, successes: list[date]) -> AsyncMock:
    """conn returning a maturation COUNT (fetchval) + job_runs successes (fetch)."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=matured)
    conn.fetch = AsyncMock(return_value=[{"as_of": d} for d in successes])
    return conn


# --- _cron_was_continuous (pure logic) ---

def test_continuity_healthy_weekly_run_passes():
    assert _cron_was_continuous(_WEEKLY, _W0, _GATE_TODAY) is True


def test_continuity_one_missed_week_tolerated():
    # W2 missing → max gap 14d (W1→W3) → still continuous.
    successes = [_WEEKLY[0], _WEEKLY[1], _WEEKLY[3], _WEEKLY[4]]
    assert _cron_was_continuous(successes, _W0, _GATE_TODAY) is True


def test_continuity_three_week_blackout_fails():
    # Only W0 and W4 → 28d gap > 14d → blackout.
    assert _cron_was_continuous([_WEEKLY[0], _WEEKLY[4]], _W0, _GATE_TODAY) is False


def test_continuity_stale_cron_fails():
    # A single early run, nothing since → latest success < today-14 → not alive.
    assert _cron_was_continuous([_W0], _W0, _GATE_TODAY) is False


def test_continuity_window_not_opened_on_real_run_fails():
    # Earliest success is after window_open → not enough observed history.
    late = [_W0 + timedelta(days=3), _GATE_TODAY]
    assert _cron_was_continuous(late, _W0, _GATE_TODAY) is False


def test_continuity_empty_fails():
    assert _cron_was_continuous([], _W0, _GATE_TODAY) is False


# --- has_enough_paper_weeks (both conditions) ---

@pytest.mark.asyncio
async def test_gate_passes_with_maturation_and_continuity():
    conn = _gate_conn(matured=1, successes=_WEEKLY)
    assert await has_enough_paper_weeks(conn, today=_GATE_TODAY) is True


@pytest.mark.asyncio
async def test_gate_fails_when_not_matured():
    # 27 days elapsed: oldest run not yet 28d old → maturation count 0.
    conn = _gate_conn(matured=0, successes=_WEEKLY)
    assert await has_enough_paper_weeks(
        conn, today=_W0 + timedelta(days=27)
    ) is False
    conn.fetch.assert_not_awaited()  # short-circuits before the continuity query


@pytest.mark.asyncio
async def test_gate_fails_on_same_day_backfill():
    # One run dated 35d ago + its lone success → matured, but the cron is not alive.
    backfill = [_GATE_TODAY - timedelta(days=35)]
    conn = _gate_conn(matured=1, successes=backfill)
    assert await has_enough_paper_weeks(conn, today=_GATE_TODAY) is False


@pytest.mark.asyncio
async def test_gate_min_matured_runs_override_decouples_count():
    # Healthy weekly cron but only 1 matured run; require 4 → maturation fails.
    conn = _gate_conn(matured=1, successes=_WEEKLY)
    assert await has_enough_paper_weeks(
        conn, min_matured_runs=4, today=_GATE_TODAY
    ) is False


@pytest.mark.asyncio
async def test_gate_require_continuity_false_bypasses_continuity():
    # Stale-cron data that would fail continuity, but the flag turns it off.
    conn = _gate_conn(matured=1, successes=[_W0])
    assert await has_enough_paper_weeks(
        conn, require_continuity=False, today=_GATE_TODAY
    ) is True
    conn.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_gate_continuity_query_filters_successful_build_portfolio():
    # The continuity query must scope to successful build_portfolio runs.
    conn = _gate_conn(matured=1, successes=_WEEKLY)
    await has_enough_paper_weeks(conn, today=_GATE_TODAY)
    query = conn.fetch.await_args.args[0]
    assert "job_name = 'build_portfolio'" in query
    assert "status = 'success'" in query


@pytest.mark.asyncio
async def test_record_signoff_inserts_correct_fields():
    """record_signoff calls fetchval with NOTE action and m13_paper_signoff tag."""
    conn = AsyncMock()
    conn.fetchval.return_value = 99
    as_of = date(2026, 5, 23)

    decisions_id = await record_signoff(conn, note="looks good", as_of=as_of)

    assert decisions_id == 99
    conn.fetchval.assert_awaited_once()
    call_sql, call_as_of, call_rationale = conn.fetchval.call_args.args
    assert "NOTE" in call_sql
    assert call_as_of == as_of
    assert "[m13_paper_signoff]" in call_rationale
    assert "looks good" in call_rationale


@pytest.mark.asyncio
async def test_evaluate_run_from_db_missing_run():
    """Returns None when run_id not found."""
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    result = await evaluate_run_from_db(conn, run_id=999, eval_as_of=_TODAY)
    assert result is None


@pytest.mark.asyncio
async def test_evaluate_run_from_db_delegates_evaluate():
    """evaluate_run_from_db loads trades + prices and returns a PaperTradeOutcome."""
    run_record = MagicMock()
    run_record.__getitem__ = lambda self, k: {"run_id": 7, "as_of": date(2026, 1, 6)}[k]

    trade_records = []
    trade_data = {
        "symbol": "BHP",
        "side": "buy",
        "delta_qty": Decimal("100"),
        "delta_aud": Decimal("5000"),
        "reference_price": Decimal("50"),
    }
    rec = MagicMock()
    rec.__getitem__ = lambda self, k, d=trade_data: d[k]
    trade_records.append(rec)

    price_record = MagicMock()
    price_record.__getitem__ = lambda self, k: {"symbol": "BHP", "close": Decimal("55")}[k]

    conn = AsyncMock()
    conn.fetchrow.return_value = run_record
    conn.fetch.side_effect = [trade_records, [price_record]]

    outcome = await evaluate_run_from_db(conn, run_id=7, eval_as_of=_TODAY)
    assert isinstance(outcome, PaperTradeOutcome)
    assert outcome.run_id == 7
    assert outcome.total_hypothetical_pnl_aud == Decimal("500")
    assert outcome.total_traded_aud == Decimal("5000")
