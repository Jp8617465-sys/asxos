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

from asxos.domain.brief.types import SectionStatus, SeverityLevel

_MODULE = "asxos.domain.brief.collectors.active_theses"


def _thesis_row(symbol: str = "BHP.AU", attestation: str = "underwritten") -> dict:
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
        "attestation": attestation,  # migration 0042
    }


def _cond_row(status="active", semantics="alert_review", kind="price_below") -> dict:
    return {
        "thesis_id": 1,
        "status": status,
        "trigger_semantics": semantics,
        "enforcement_kind": kind,
    }


async def _run_collector(
    theses_rows, signal_rows, as_of=date(2026, 6, 1), model_gate_rows=None,
    condition_rows=None, locks=None,
):
    conn = MagicMock()
    # conn.fetch: 1st call = theses query, 2nd = thesis_conditions (0042),
    # 3rd = the contamination-isolation model gate, 4th = signals query
    # (underlyings + disposal locks are patched out, so they don't touch
    # conn.fetch).
    gate_rows = (
        model_gate_rows if model_gate_rows is not None else [{"model": "model_a"}]
    )
    conn.fetch = AsyncMock(
        side_effect=[theses_rows, condition_rows or [], gate_rows, signal_rows]
    )

    score = MagicMock()
    score.label = "confirming"
    score.weighted_movement = Decimal("0.0")

    with (
        patch(f"{_MODULE}.acquire") as mock_acquire,
        patch(f"{_MODULE}.get_disposal_locks", AsyncMock(return_value=locks or {})),
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
async def test_no_approved_model_skips_driver_line():
    # R9: 0 active+approved_for_allocation rows is the EXPECTED state under a
    # Model A quarantine (rule #11), not a misconfig for this display-only
    # path. The card must still render with full discipline severity, just
    # without the cosmetic "Model A:" driver line. The allocator still
    # hard-fails on 0 approved — see tests/test_portfolio_build.py.
    result = await _run_collector([_thesis_row()], [], model_gate_rows=[])
    assert result.status == SectionStatus.ok
    assert "Model A:" not in result.items[0].message


@pytest.mark.asyncio
async def test_multiple_approved_models_skips_driver_line():
    # R9: >1 approved is ambiguous (no single model to display) → skip the
    # driver line rather than hard-fail the discipline section. The allocator
    # still hard-fails on >1 approved — see tests/test_portfolio_build.py.
    result = await _run_collector(
        [_thesis_row()],
        [],
        model_gate_rows=[{"model": "model_a"}, {"model": "factor_sleeve"}],
    )
    assert result.status == SectionStatus.ok
    assert "Model A:" not in result.items[0].message


@pytest.mark.asyncio
async def test_date_typed_earnings_value_does_not_call_date_method():
    row = _thesis_row()
    row["next_earnings_date"] = date(2026, 6, 15)

    result = await _run_collector([row], [], model_gate_rows=[])

    assert result.status == SectionStatus.ok


# ---------------------------------------------------------------------------
# 0042 — attestation tag, lock badge, condition-state line, severity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_placeholder_attestation_tag_on_card():
    result = await _run_collector(
        [_thesis_row(attestation="placeholder")], [], model_gate_rows=[]
    )
    assert "PLACEHOLDER — not underwritten" in result.items[0].message


@pytest.mark.asyncio
async def test_condition_state_line_renders_counts():
    conds = [
        _cond_row(status="triggered"),
        _cond_row(kind="not_machine_checkable"),
        _cond_row(kind="not_machine_checkable"),
        _cond_row(status="active"),
    ]
    result = await _run_collector(
        [_thesis_row(attestation="placeholder")], [], model_gate_rows=[],
        condition_rows=conds,
    )
    msg = result.items[0].message
    assert "conditions: 1 triggered · 2 not machine-checked · 1 active" in msg


@pytest.mark.asyncio
async def test_triggered_hard_exit_underwritten_unlocked_is_red():
    conds = [_cond_row(status="triggered", semantics="hard_exit")]
    result = await _run_collector(
        [_thesis_row(attestation="underwritten")], [], model_gate_rows=[],
        condition_rows=conds,
    )
    assert result.items[0].level == SeverityLevel.red


@pytest.mark.asyncio
async def test_triggered_on_placeholder_is_yellow_not_red():
    conds = [_cond_row(status="triggered", semantics="hard_exit")]
    result = await _run_collector(
        [_thesis_row(attestation="placeholder")], [], model_gate_rows=[],
        condition_rows=conds,
    )
    assert result.items[0].level == SeverityLevel.yellow


@pytest.mark.asyncio
async def test_locked_symbol_demotes_red_and_shows_badge():
    from asxos.domain.portfolio.locks import LockState

    conds = [_cond_row(status="triggered", semantics="hard_exit")]
    lock = LockState(symbol="BHP.AU", lock_end=None, lock_note="ESS window")
    result = await _run_collector(
        [_thesis_row(attestation="underwritten")], [], model_gate_rows=[],
        condition_rows=conds, locks={"BHP.AU": lock},
    )
    assert result.items[0].level == SeverityLevel.yellow
    assert "LOCKED (end unknown)" in result.items[0].message


@pytest.mark.asyncio
async def test_unparseable_conditions_emit_visible_yellow_line():
    conds = [_cond_row(kind="not_machine_checkable")]
    result = await _run_collector(
        [_thesis_row()], [], model_gate_rows=[], condition_rows=conds
    )
    loud = [
        i for i in result.items
        if "NOT MACHINE-CHECKED" in i.message and i.level == SeverityLevel.yellow
    ]
    assert loud, "unparseable conditions must be a visible yellow line, never absent"
