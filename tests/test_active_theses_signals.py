"""Tests for the steady-state ML driver line in the active_theses collector.

The collector joins the latest Model A signal per active-thesis symbol and appends
a "Model A: <label> | Top drivers: …" line to each card. Helper functions
(underlyings, severity) are patched so the test isolates the new signal join.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asxos.domain.brief.types import SectionStatus

_MODULE = "asxos.domain.brief.collectors.active_theses"


def _thesis_row(symbol: str = "BHP.AU") -> dict:
    return {
        "thesis_id": 1,
        "symbol": symbol,
        "status": "active",
        "opened_at": datetime(2026, 1, 1),
        "stop_price": Decimal("38.00"),
        "target_price": Decimal("55.00"),
        "timeline_days": 360,
        "entry_band_lower": Decimal("40.00"),
        "entry_band_upper": Decimal("44.00"),
        "revisit_due_at": datetime(2026, 12, 1),  # far future → green
        "analyst_buy_count": 0,
        "analyst_neutral_count": 0,
        "analyst_sell_count": 0,
        "analyst_consensus_target": None,
        "next_earnings_date": None,
        "earnings_notes": None,
    }


async def _run_collector(
    theses_rows, signal_rows, as_of=date(2026, 6, 1), model_gate_rows=None
):
    conn = MagicMock()
    # conn.fetch: 1st call = theses query, 2nd = the contamination-isolation
    # model gate, 3rd = signals query (underlyings are patched out, so they
    # don't touch conn.fetch).
    gate_rows = (
        model_gate_rows if model_gate_rows is not None else [{"model": "model_a"}]
    )
    conn.fetch = AsyncMock(side_effect=[theses_rows, gate_rows, signal_rows])

    score = MagicMock()
    score.label = "confirming"
    score.weighted_movement = Decimal("0.0")

    with (
        patch(f"{_MODULE}.acquire") as mock_acquire,
        patch(f"{_MODULE}.bulk_list_thesis_underlyings", AsyncMock(return_value={})),
        patch(f"{_MODULE}.get_5d_moves", AsyncMock(return_value={})),
        patch(f"{_MODULE}.score_thesis_underlying", return_value=score),
        patch(f"{_MODULE}.thesis_revisit_overdue", return_value=None),
        patch(f"{_MODULE}.thesis_timeline_expired", return_value=None),
        patch(f"{_MODULE}.earnings_risk", return_value=None),
        patch(f"{_MODULE}.detect_hidden_risk", return_value=None),
    ):
        mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        from asxos.domain.brief.collectors.active_theses import collect_active_theses
        return await collect_active_theses(as_of)


@pytest.mark.asyncio
async def test_driver_line_appended_when_signal_present():
    signal = {
        "symbol": "BHP.AU",
        "signal_label": "BUY",
        "shap_factors": {"earnings_yield": 0.31, "mom_12_1": 0.18, "bias": 0.9},
    }
    result = await _run_collector([_thesis_row()], [signal])
    assert result.status == SectionStatus.ok
    msg = result.items[0].message
    assert "Model A: BUY" in msg
    assert "Top drivers: earnings_yield+0.310, mom_12_1+0.180" in msg
    assert "bias" not in msg  # intercept excluded


@pytest.mark.asyncio
async def test_no_driver_line_when_no_signal_for_symbol():
    # Signal is for a different symbol → the BHP card carries no Model A line.
    signal = {"symbol": "CBA.AU", "signal_label": "SELL", "shap_factors": {"x": 0.5}}
    result = await _run_collector([_thesis_row("BHP.AU")], [signal])
    assert "Model A:" not in result.items[0].message


@pytest.mark.asyncio
async def test_driver_line_label_only_when_shap_empty():
    # Signal present but shap empty → label shows, no drivers suffix.
    signal = {"symbol": "BHP.AU", "signal_label": "HOLD", "shap_factors": {}}
    result = await _run_collector([_thesis_row()], [signal])
    msg = result.items[0].message
    assert "Model A: HOLD" in msg
    assert "Top drivers" not in msg


@pytest.mark.asyncio
async def test_no_approved_model_raises():
    # Contamination-isolation gate: zero active+approved_for_allocation rows
    # is a configuration invariant violation — must fail loudly, not
    # silently omit the Model A driver line.
    with pytest.raises(RuntimeError, match="approved_for_allocation"):
        await _run_collector([_thesis_row()], [], model_gate_rows=[])


@pytest.mark.asyncio
async def test_multiple_approved_models_raises():
    # Multi-sleeve blending is out of v1 scope — more than one eligible
    # model is a hard-fail, not a silent arbitrary pick.
    with pytest.raises(RuntimeError, match="multiple models"):
        await _run_collector(
            [_thesis_row()],
            [],
            model_gate_rows=[{"model": "model_a"}, {"model": "factor_sleeve"}],
        )
