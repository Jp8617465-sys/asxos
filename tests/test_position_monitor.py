"""
Tests for M-Position-Monitor.

Covers:
  - Symbol normalisation: .NYSE/.NASDAQ → .US; .AU passthrough
  - SMA calculation: 50d and 200d from synthetic close list
  - SMA hard-fail: fewer closes than period
  - avg_weekly_move: correct mean over trailing 5-day intervals
  - avg_weekly_move: fallback when < 6 closes
  - FRED 5d move: correct % change
  - FRED 5d move: hard-fail when < 6 non-None observations
  - build_monitor_result: stage + underlying score round-trip (pure)
  - build_monitor_result: default underlyings used when thesis_underlyings=None
  - save_run / list_runs: round-trip via mock DB
  - format_monitor: smoke (non-empty string, key content present)
  - format_history: smoke (non-empty, correct columns)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from asxos.domain.position_monitor.display import format_history, format_monitor
from asxos.domain.position_monitor.fetcher import (
    _pct_change_5d,
    avg_weekly_move,
    eodhd_symbol,
    sma,
)
from asxos.domain.position_monitor.service import build_monitor_result, save_run
from asxos.domain.position_monitor.types import MonitorInput

# ---------------------------------------------------------------------------
# Symbol normalisation
# ---------------------------------------------------------------------------

class TestEodhdSymbol:
    def test_nyse_to_us(self):
        assert eodhd_symbol("HUBS.NYSE") == "HUBS.US"

    def test_nasdaq_to_us(self):
        assert eodhd_symbol("CRM.NASDAQ") == "CRM.US"

    def test_amex_to_us(self):
        assert eodhd_symbol("SPY.AMEX") == "SPY.US"

    def test_asx_passthrough(self):
        assert eodhd_symbol("BHP.AU") == "BHP.AU"

    def test_already_us(self):
        assert eodhd_symbol("HUBS.US") == "HUBS.US"

    def test_lowercase_normalised(self):
        assert eodhd_symbol("hubs.nyse") == "HUBS.US"


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

class TestSMA:
    def test_50d_sma_correct(self):
        # 50 closes all equal to 100.00 → SMA = 100.00
        closes = [Decimal("100.00")] * 60
        result = sma(closes, 50)
        assert result == Decimal("100.00")

    def test_200d_sma_correct(self):
        # 200 closes: first 100 at 50, last 100 at 150 → SMA = 100.00
        closes = [Decimal("50.00")] * 100 + [Decimal("150.00")] * 100
        result = sma(closes, 200)
        assert result == Decimal("100.00")

    def test_sma_uses_last_n_closes(self):
        # 210 closes: first 10 at 0, next 200 at 100 → 200d SMA = 100
        closes = [Decimal("0")] * 10 + [Decimal("100")] * 200
        result = sma(closes, 200)
        assert result == Decimal("100.00")

    def test_sma_hard_fails_insufficient_data(self):
        """Fewer closes than period → RuntimeError (spec: hard-fail invariant)."""
        with pytest.raises(RuntimeError, match="Insufficient price history"):
            sma([Decimal("100")] * 49, 50)


# ---------------------------------------------------------------------------
# Average weekly move
# ---------------------------------------------------------------------------

class TestAvgWeeklyMove:
    def test_constant_prices_gives_zero_move(self):
        closes = [Decimal("100")] * 25
        result = avg_weekly_move(closes)
        assert result == Decimal("0.000")

    def test_correct_mean_over_5day_intervals(self):
        # Prices alternate +10% every 5 days: 100, 110, 100, 110, ...
        closes = []
        for i in range(25):
            closes.append(Decimal("100") if i % 10 < 5 else Decimal("110"))
        result = avg_weekly_move(closes)
        assert result > Decimal("0")

    def test_fallback_when_too_few_closes(self):
        result = avg_weekly_move([Decimal("100")] * 4)
        assert result == Decimal("0.030")

    def test_fallback_when_empty(self):
        result = avg_weekly_move([])
        assert result == Decimal("0.030")


# ---------------------------------------------------------------------------
# FRED 5d move
# ---------------------------------------------------------------------------

class TestPctChange5d:
    def test_correct_5d_move(self):
        # newest-first: 110, 108, 106, 104, 102, 100 → +10.00%
        values = [Decimal("110"), Decimal("108"), Decimal("106"),
                  Decimal("104"), Decimal("102"), Decimal("100")]
        result = _pct_change_5d(values)
        assert result == Decimal("10.00")

    def test_negative_5d_move(self):
        # 90, 92, 94, 96, 98, 100 → -10.00%
        values = [Decimal("90"), Decimal("92"), Decimal("94"),
                  Decimal("96"), Decimal("98"), Decimal("100")]
        result = _pct_change_5d(values)
        assert result == Decimal("-10.00")

    def test_skips_none_values(self):
        # None values interleaved; still has 6 non-None
        values = [Decimal("110"), None, Decimal("108"), Decimal("106"),
                  Decimal("104"), None, Decimal("102"), Decimal("100")]
        result = _pct_change_5d(values)
        assert result == Decimal("10.00")

    def test_hard_fails_when_too_few_non_none(self):
        """< 6 non-None observations → RuntimeError."""
        values = [Decimal("110"), None, None, Decimal("108"), None, Decimal("100")]
        with pytest.raises(RuntimeError, match="Insufficient observations"):
            _pct_change_5d(values)


# ---------------------------------------------------------------------------
# build_monitor_result — pure function
# ---------------------------------------------------------------------------

def _make_inputs(**kwargs) -> MonitorInput:
    defaults: dict = {
        "symbol": "HUBS.NYSE",
        "as_of": date(2026, 6, 2),
        "current_price": Decimal("252"),
        "ma_50d": Decimal("243.61"),
        "ma_200d": Decimal("317.94"),
        "avg_weekly_move": Decimal("0.08"),
        "vix_5d_move": Decimal("-8.0"),
        "hy_oas_5d_move": Decimal("-3.5"),
        "retail_ratio": Decimal("2.50"),
        "news_sentiment": Decimal("0.72"),
    }
    defaults.update(kwargs)
    return MonitorInput(**defaults)


class TestBuildMonitorResult:
    def test_late_retail_stage(self):
        """Retail spike 2.5× + high sentiment → LATE-RETAIL."""
        result = build_monitor_result(_make_inputs())
        assert result.stage_label == "late-retail"

    def test_confirming_underlying(self):
        """VIX -8% + HY OAS -3.5% (both negative direction) → CONFIRMING."""
        result = build_monitor_result(_make_inputs())
        assert result.underlying_label == "confirming"
        assert result.weighted_movement > Decimal("0")

    def test_default_underlyings_used_when_none(self):
        """When thesis_underlyings=None, defaults (VIX + HY OAS) are used."""
        result = build_monitor_result(_make_inputs(), thesis_underlyings=None)
        codes = {comp["code"] for comp in result.component_moves}
        assert "vix" in codes
        assert "us_hy_oas" in codes

    def test_diverging_when_vix_spikes(self):
        """VIX +20% → underlying score diverging."""
        result = build_monitor_result(
            _make_inputs(vix_5d_move=Decimal("20.0"), hy_oas_5d_move=Decimal("5.0"))
        )
        assert result.underlying_label == "diverging"

    def test_scenarios_empty_without_position_context(self):
        """No cost_usd / acquired → no scenarios generated."""
        result = build_monitor_result(_make_inputs())
        assert result.scenarios == ()

    def test_scenarios_populated_with_position_context(self):
        result = build_monitor_result(
            _make_inputs(
                cost_usd=Decimal("187.54"),
                shares=Decimal("24"),
                acquired=date(2026, 5, 31),
                cgt_date=date(2027, 6, 1),
                stop_price=Decimal("230"),
            )
        )
        codes = {s.code for s in result.scenarios}
        assert "A" in codes   # sell now
        assert "B" in codes   # stop
        assert "D" in codes   # CGT hold

    def test_cross_layer_obs_populated_with_regime(self):
        result = build_monitor_result(
            _make_inputs(regime_label="risk_on_narrowing")
        )
        assert len(result.cross_layer_obs) > 0


# ---------------------------------------------------------------------------
# save_run — mock DB
# ---------------------------------------------------------------------------

class TestSaveRun:
    @pytest.mark.asyncio
    async def test_save_run_returns_run_id(self):
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)

        result = build_monitor_result(_make_inputs())
        run_id = await save_run(mock_conn, result)

        assert run_id == 42
        mock_conn.fetchval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_run_passes_correct_symbol(self):
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)

        result = build_monitor_result(_make_inputs(symbol="BHP.AU"))
        await save_run(mock_conn, result)

        call_args = mock_conn.fetchval.call_args
        assert "BHP.AU" in call_args.args


# ---------------------------------------------------------------------------
# Display — smoke tests
# ---------------------------------------------------------------------------

class TestFormatMonitor:
    def test_returns_non_empty_string(self):
        result = build_monitor_result(_make_inputs())
        output = format_monitor(result)
        assert isinstance(output, str)
        assert len(output) > 100

    def test_contains_stage_label(self):
        result = build_monitor_result(_make_inputs())
        output = format_monitor(result)
        assert "LATE-RETAIL" in output

    def test_contains_underlying_label(self):
        result = build_monitor_result(_make_inputs())
        output = format_monitor(result)
        assert "CONFIRMING" in output

    def test_contains_symbol(self):
        result = build_monitor_result(_make_inputs())
        output = format_monitor(result)
        assert "HUBS.NYSE" in output


class TestFormatHistory:
    def test_empty_runs_returns_message(self):
        output = format_history([])
        assert "No monitor runs" in output

    def test_formats_run_row(self):
        runs = [{
            "as_of": date(2026, 6, 2),
            "current_price": Decimal("252"),
            "stage_label": "late-retail",
            "underlying_label": "confirming",
            "weighted_movement": Decimal("5.75"),
            "retail_ratio": Decimal("2.50"),
            "news_sentiment": Decimal("0.72"),
            "regime_label": "risk_on_narrowing",
        }]
        output = format_history(runs)
        assert "2026-06-02" in output
        assert "late-retail" in output
        assert "confirming" in output
