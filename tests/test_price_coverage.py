"""
Tests for asxos.domain.prices.coverage.

Pure classification logic is tested directly; the async DB readers are tested
with a mocked asyncpg connection (no live Postgres), mirroring
tests/test_signals_loader.py.

The scenarios map to the real recovery observations:
  - full trading day      → 2026-06-10 (1852 rows)  → COMPLETE
  - 12/14-row residue day → 2026-06-14/06-15 weekend → NO_EQUITY_DATA
  - gap after latest full → latest_complete stays 2026-06-10
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from asxos.domain.prices.coverage import (
    DEFAULT_MAX_STALE_DAYS,
    MIN_COMPLETE_ROWS,
    PriceDateStatus,
    SyncCompleteness,
    assess_completeness,
    classify_coverage,
    classify_row_count,
    classify_sync_completeness,
    complete_threshold,
    is_stale,
    latest_complete_trading_day,
    latest_observed_price_date,
    select_latest_complete,
    select_sync_target,
    trailing_median_row_count,
)

# --- complete_threshold -------------------------------------------------------


def test_threshold_floor_dominates_at_asx_scale() -> None:
    # 0.8 * 1850 = 1480 < 1500 floor → floor wins
    assert complete_threshold(1850) == MIN_COMPLETE_ROWS


def test_threshold_scales_above_floor_for_larger_universe() -> None:
    # 0.8 * 2400 = 1920 > 1500 floor → scaled value wins
    assert complete_threshold(2400) == 1920


def test_threshold_zero_or_negative_median_falls_back_to_floor() -> None:
    assert complete_threshold(0) == MIN_COMPLETE_ROWS
    assert complete_threshold(-5) == MIN_COMPLETE_ROWS


# --- classify_row_count -------------------------------------------------------


def test_full_trading_day_is_complete() -> None:
    assert classify_row_count(1852, 1850) is PriceDateStatus.COMPLETE


def test_zero_row_weekend_is_no_equity_data() -> None:
    assert classify_row_count(0, 1850) is PriceDateStatus.NO_EQUITY_DATA


def test_twelve_row_residue_is_no_equity_data() -> None:
    # The 12/14-row weekend sync_prices residue must NOT look like a partial day.
    assert classify_row_count(12, 1850) is PriceDateStatus.NO_EQUITY_DATA
    assert classify_row_count(14, 1850) is PriceDateStatus.NO_EQUITY_DATA


def test_partial_provider_response_is_partial() -> None:
    # Above residue band but below the completeness threshold.
    assert classify_row_count(1000, 1850) is PriceDateStatus.PARTIAL


def test_completeness_boundary() -> None:
    # threshold is 1500 when median is 1850 (floor dominates)
    assert classify_row_count(1499, 1850) is PriceDateStatus.PARTIAL
    assert classify_row_count(1500, 1850) is PriceDateStatus.COMPLETE


def test_universe_size_change_shifts_classification() -> None:
    # A 1900-row day is COMPLETE at ASX scale (median 1850, threshold 1500)...
    assert classify_row_count(1900, 1850) is PriceDateStatus.COMPLETE
    # ...but only PARTIAL after the universe grows (median 2400 → threshold 1920).
    assert classify_row_count(1900, 2400) is PriceDateStatus.PARTIAL
    assert classify_row_count(2000, 2400) is PriceDateStatus.COMPLETE


# --- trailing_median_row_count ------------------------------------------------


def test_trailing_median_excludes_residue_and_zero() -> None:
    # 12 (residue) and 0 (weekend) excluded → median of [1845, 1848, 1850]
    assert trailing_median_row_count([1850, 1848, 12, 0, 1845]) == 1848


def test_trailing_median_empty_or_all_residue_is_zero() -> None:
    assert trailing_median_row_count([]) == 0
    assert trailing_median_row_count([0, 5, 12, 14]) == 0


# --- classify_coverage / select_latest_complete -------------------------------


def test_select_latest_complete_skips_gap_after_full_day() -> None:
    # Mirrors reality: newest dates are residue/weekend; last full day is 06-10.
    rows = [
        (date(2026, 6, 15), 14),  # Mon run, Sat target → residue
        (date(2026, 6, 14), 0),  # weekend
        (date(2026, 6, 10), 1852),  # last complete day
        (date(2026, 6, 9), 1848),
    ]
    coverage = classify_coverage(rows)
    # newest-first ordering
    assert [c.dt for c in coverage] == [
        date(2026, 6, 15),
        date(2026, 6, 14),
        date(2026, 6, 10),
        date(2026, 6, 9),
    ]
    statuses = {c.dt: c.status for c in coverage}
    assert statuses[date(2026, 6, 15)] is PriceDateStatus.NO_EQUITY_DATA
    assert statuses[date(2026, 6, 14)] is PriceDateStatus.NO_EQUITY_DATA
    assert statuses[date(2026, 6, 10)] is PriceDateStatus.COMPLETE
    # The latest *complete* day is 06-10, not the 14-row residue date.
    assert select_latest_complete(coverage) == date(2026, 6, 10)


def test_select_latest_complete_none_when_no_complete_days() -> None:
    rows = [(date(2026, 6, 15), 14), (date(2026, 6, 14), 0)]
    assert select_latest_complete(classify_coverage(rows)) is None


def test_classify_coverage_empty() -> None:
    assert classify_coverage([]) == []
    assert select_latest_complete([]) is None


# --- is_stale -----------------------------------------------------------------


def test_is_stale_none_is_stale() -> None:
    assert is_stale(None, date(2026, 6, 16)) is True


def test_is_stale_within_window() -> None:
    # 06-16 vs 06-12 = 4 calendar days <= 5 → fresh
    assert is_stale(date(2026, 6, 12), date(2026, 6, 16)) is False


def test_is_stale_beyond_window() -> None:
    # 06-16 vs 06-10 = 6 calendar days > 5 → stale
    assert is_stale(date(2026, 6, 10), date(2026, 6, 16)) is True
    # explicit ceiling honoured
    assert is_stale(date(2026, 6, 10), date(2026, 6, 16), max_calendar_days=10) is False


def test_default_stale_days_constant() -> None:
    assert DEFAULT_MAX_STALE_DAYS == 5


# --- async readers (mocked conn) ----------------------------------------------


class _Rec(dict):
    """asyncpg.Record-like dict."""


def _conn_with_coverage(pairs: list[tuple[date, int]]) -> Any:
    """Mock conn whose .fetch returns coverage rows (dt, row_count), newest first."""
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[_Rec(dt=d, row_count=c) for d, c in pairs])
    return conn


def test_latest_complete_trading_day_async_returns_last_full_day() -> None:
    conn = _conn_with_coverage(
        [
            (date(2026, 6, 15), 14),
            (date(2026, 6, 14), 0),
            (date(2026, 6, 10), 1852),
            (date(2026, 6, 9), 1848),
        ]
    )
    result = asyncio.run(latest_complete_trading_day(conn))
    assert result == date(2026, 6, 10)
    assert conn.fetch.await_count == 1


def test_latest_complete_trading_day_async_none_when_all_residue() -> None:
    conn = _conn_with_coverage([(date(2026, 6, 15), 14), (date(2026, 6, 14), 0)])
    assert asyncio.run(latest_complete_trading_day(conn)) is None


def test_assess_completeness_report() -> None:
    conn = _conn_with_coverage(
        [
            (date(2026, 6, 15), 14),
            (date(2026, 6, 10), 1852),
            (date(2026, 6, 9), 1848),
        ]
    )
    report = asyncio.run(assess_completeness(conn))
    assert report.latest_observed == date(2026, 6, 15)
    assert report.latest_complete == date(2026, 6, 10)
    assert len(report.coverage) == 3


def test_latest_observed_price_date_async() -> None:
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=date(2026, 6, 15))
    assert asyncio.run(latest_observed_price_date(conn)) == date(2026, 6, 15)


def test_fetch_recent_coverage_passes_lookback() -> None:
    # latest_complete_trading_day should forward lookback_days into the query.
    conn = _conn_with_coverage([(date(2026, 6, 10), 1852)])
    asyncio.run(latest_complete_trading_day(conn, lookback_days=14))
    assert conn.fetch.await_args.args[1] == 14


# --- classify_sync_completeness (sync_prices adapter) -------------------------
#
# Verdict is ASX-equity-only (Phase-1 au_rows); US/FX phase counts are carried
# for context but must never make a non-trading day look ASX-complete. These map
# to the 2026-06-14 residue incident (0 AU equity rows, 12/14 US/FX residue).

_SYNC_TARGET = date(2026, 6, 14)


def test_classify_sync_full_asx_day_is_complete() -> None:
    v = classify_sync_completeness(date(2026, 6, 10), au_rows=1852, us_rows=3, fx_rows=1)
    assert isinstance(v, SyncCompleteness)
    assert v.status is PriceDateStatus.COMPLETE
    assert v.is_complete is True


def test_classify_sync_twelve_row_residue_is_no_equity_data() -> None:
    # The exact incident: 0 ASX equity rows, 12 US/FX residue rows.
    v = classify_sync_completeness(_SYNC_TARGET, au_rows=0, us_rows=12, fx_rows=0)
    assert v.status is PriceDateStatus.NO_EQUITY_DATA
    assert v.is_complete is False


def test_classify_sync_fourteen_row_residue_is_no_equity_data() -> None:
    v = classify_sync_completeness(_SYNC_TARGET, au_rows=0, us_rows=8, fx_rows=6)
    assert v.status is PriceDateStatus.NO_EQUITY_DATA


def test_classify_sync_fx_only_does_not_count_as_asx() -> None:
    # A large FX count must NOT make the day look like ASX coverage.
    v = classify_sync_completeness(_SYNC_TARGET, au_rows=0, us_rows=0, fx_rows=2000)
    assert v.status is PriceDateStatus.NO_EQUITY_DATA
    assert v.is_complete is False


def test_classify_sync_us_only_does_not_count_as_asx() -> None:
    # Thousands of US rows with no ASX session is still no_equity_data.
    v = classify_sync_completeness(_SYNC_TARGET, au_rows=0, us_rows=5000, fx_rows=0)
    assert v.status is PriceDateStatus.NO_EQUITY_DATA
    assert v.is_complete is False


def test_classify_sync_partial_asx_day_is_partial() -> None:
    # Above the residue band but below the ~1800-symbol full-session floor.
    v = classify_sync_completeness(date(2026, 6, 12), au_rows=900, us_rows=3, fx_rows=1)
    assert v.status is PriceDateStatus.PARTIAL
    assert v.is_complete is False


def test_classify_sync_carries_phase_counts_and_target() -> None:
    v = classify_sync_completeness(date(2026, 6, 10), au_rows=1800, us_rows=5, fx_rows=2)
    assert (v.au_rows, v.us_rows, v.fx_rows) == (1800, 5, 2)
    assert v.target == date(2026, 6, 10)


# --- select_sync_target (which fetched day the verdict is about) ----------------
#
# The scenarios map to the 2026-09-03..05 false-positive incident: after #171
# made clock.today() the Sydney date, the 06:30 AEST run fetched yesterday's
# close (2,299 / 2,288 AU rows) plus an empty bulk for today, classified today
# and wrote "NO_EQUITY_DATA — ASX=0" into job_runs.error_message — which
# check_cron_health then surfaced as DEGRADED on three consecutive days.


def test_select_sync_target_pre_open_run_classifies_yesterday() -> None:
    # Thursday 2026-09-03 08:45 AEST: Wednesday's close landed, today is empty.
    counts = {date(2026, 9, 2): 2299, date(2026, 9, 3): 0}
    assert select_sync_target(counts, today=date(2026, 9, 3)) == date(2026, 9, 2)


def test_select_sync_target_after_close_run_classifies_today() -> None:
    # An evening (or next-day manual) run where today's bulk has rows.
    counts = {date(2026, 9, 2): 2299, date(2026, 9, 3): 2288}
    assert select_sync_target(counts, today=date(2026, 9, 3)) == date(2026, 9, 3)


def test_select_sync_target_earlier_zero_day_is_still_flagged() -> None:
    # A holiday (or the 2026-06-14 residue day) BEFORE today keeps its zero: the
    # helper only excuses today, never a past weekday.
    counts = {date(2026, 6, 15): 0, date(2026, 6, 16): 0}
    target = select_sync_target(counts, today=date(2026, 6, 16))
    assert target == date(2026, 6, 15)
    verdict = classify_sync_completeness(target, au_rows=counts[target], us_rows=12, fx_rows=0)
    assert verdict.status is PriceDateStatus.NO_EQUITY_DATA


def test_select_sync_target_monday_run_classifies_friday() -> None:
    # Monday 06:30 AEST: the loop skips the weekend, fetches Friday + empty Monday.
    counts = {date(2026, 9, 4): 2301, date(2026, 9, 7): 0}
    assert select_sync_target(counts, today=date(2026, 9, 7)) == date(2026, 9, 4)


def test_select_sync_target_only_empty_today_is_nothing_to_classify() -> None:
    assert select_sync_target({date(2026, 9, 3): 0}, today=date(2026, 9, 3)) is None
    assert select_sync_target({}, today=date(2026, 9, 3)) is None
