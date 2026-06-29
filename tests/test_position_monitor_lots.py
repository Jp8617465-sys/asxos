"""
Multi-lot aggregation for the position monitor, scoped to the active account_type.

Pins the design contract (Item 1):
  - _build_lot_ladder: weighted-average cost, per-lot CGT ladder, the earliest-
    still-ineligible headline cgt_date, the all_eligible vs empty-ladder distinction,
    and §5.1 calendar eligibility;
  - load_position_context: scopes lots by account_type ($2), uses as_of, dict shape;
  - display._break_even_lot: the break-even uses the earliest-ineligible lot's
    per-share cost (NOT the position weighted-average) — the lot-consistency rule.

Pure Decimal + a mocked asyncpg conn; no live DB.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from asxos.domain.position_monitor.display import _break_even_lot
from asxos.domain.position_monitor.service import (
    _build_lot_ladder,
    load_position_context,
)
from asxos.domain.position_monitor.types import LotCgt, MonitorInput

_AS_OF = date(2026, 6, 28)


def _lot(qty: str, acquired: str, cost: str) -> dict[str, str]:
    return {"quantity": qty, "acquired_at": acquired, "cost_base_normal": cost}


# ---------------------------------------------------------------------------
# _build_lot_ladder
# ---------------------------------------------------------------------------

def test_single_lot_parity() -> None:
    # One lot acquired this year (not yet eligible): weighted-avg == that lot's
    # cost-per-share; cgt_date == acquired + 1yr + 1day (§5.1).
    lots, cost_ps, qty, cgt_date, all_elig = _build_lot_ladder(
        [_lot("100", "2026-01-01", "3000")], Decimal("3000"), Decimal("100"), _AS_OF,
    )
    assert cost_ps == Decimal("30")
    assert qty == Decimal("100")
    assert len(lots) == 1
    assert cgt_date == date(2027, 1, 2)
    assert all_elig is False
    assert lots[0].is_eligible is False


def test_two_lots_weighted_average_and_order() -> None:
    # 100 @ 30/sh (eligible, old) + 100 @ 40/sh (ineligible, recent).
    raw = [_lot("100", "2024-01-01", "3000"), _lot("100", "2026-06-01", "4000")]
    lots, cost_ps, qty, cgt_date, all_elig = _build_lot_ladder(
        raw, Decimal("7000"), Decimal("200"), _AS_OF,
    )
    assert cost_ps == Decimal("35")          # 7000 / 200, exact
    assert qty == Decimal("200")
    assert [lot.acquired_at for lot in lots] == [date(2024, 1, 1), date(2026, 6, 1)]
    # one eligible (2024), one not (2026): headline = the ineligible lot's eligible date
    assert lots[0].is_eligible is True
    assert lots[1].is_eligible is False
    assert cgt_date == date(2027, 6, 2)
    assert all_elig is False


def test_all_lots_eligible_distinct_from_no_lot() -> None:
    raw = [_lot("100", "2023-01-01", "3000"), _lot("50", "2024-02-01", "2000")]
    lots, cost_ps, qty, cgt_date, all_elig = _build_lot_ladder(
        raw, Decimal("5000"), Decimal("150"), _AS_OF,
    )
    assert cgt_date is None
    assert all_elig is True              # non-empty + every lot eligible
    assert all(lot.is_eligible for lot in lots)


def test_no_lots_is_empty_not_all_eligible() -> None:
    lots, cost_ps, qty, cgt_date, all_elig = _build_lot_ladder(
        None, None, None, _AS_OF,
    )
    assert lots == ()
    assert cost_ps is None
    assert qty is None
    assert cgt_date is None
    assert all_elig is False             # empty ladder, NOT "all eligible"


def test_ladder_accepts_jsonb_as_text() -> None:
    # asyncpg may hand jsonb back as a string; the ladder must json.loads it.
    import json
    raw = json.dumps([_lot("10", "2026-01-01", "150")])
    lots, cost_ps, _, cgt_date, _ = _build_lot_ladder(raw, Decimal("150"), Decimal("10"), _AS_OF)
    assert len(lots) == 1
    assert cost_ps == Decimal("15")
    assert cgt_date == date(2027, 1, 2)


# ---------------------------------------------------------------------------
# load_position_context — scoping + shape
# ---------------------------------------------------------------------------

def _ctx_row() -> dict[str, object]:
    return {
        "thesis_id": 7,
        "stop_price": Decimal("90"),
        "target_price": Decimal("150"),
        "analyst_buy_count": 3,
        "analyst_neutral_count": 1,
        "analyst_sell_count": 0,
        "analyst_consensus_target": Decimal("140"),
        "total_cost": Decimal("7000"),
        "total_qty": Decimal("200"),
        "lots": [_lot("100", "2024-01-01", "3000"), _lot("100", "2026-06-01", "4000")],
    }


async def test_load_position_context_scopes_by_account_type() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=_ctx_row())

    ctx = await load_position_context(conn, "BHP.AU", account_type="smsf", as_of=_AS_OF)

    # account_type is bound as $2 (the lot-scoping filter) and echoed back.
    args = conn.fetchrow.await_args.args
    assert args[1] == "BHP.AU"
    assert args[2] == "smsf"
    assert ctx["account_type"] == "smsf"
    assert ctx["cost_usd"] == Decimal("35")
    assert ctx["shares"] == Decimal("200")
    assert ctx["cgt_date"] == date(2027, 6, 2)
    assert ctx["all_eligible"] is False
    assert len(ctx["lots"]) == 2
    # headline `acquired` is the earliest lot
    assert ctx["acquired"] == date(2024, 1, 1)


async def test_load_position_context_no_thesis_returns_empty() -> None:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=None)
    ctx = await load_position_context(conn, "ZZZ.AU", account_type="individual", as_of=_AS_OF)
    assert ctx == {}


# ---------------------------------------------------------------------------
# _break_even_lot — lot-consistency (earliest ineligible, not weighted-average)
# ---------------------------------------------------------------------------

def _input_with_lots(lots: tuple[LotCgt, ...], *, all_eligible: bool) -> MonitorInput:
    return MonitorInput(
        symbol="BHP.AU", as_of=_AS_OF,
        current_price=Decimal("100"), ma_50d=Decimal("95"), ma_200d=Decimal("90"),
        avg_weekly_move=Decimal("2"), vix_5d_move=Decimal("1"), hy_oas_5d_move=Decimal("0.1"),
        retail_ratio=Decimal("1"), news_sentiment=Decimal("0.5"),
        cost_usd=Decimal("35"),  # weighted average — must NOT be what break-even uses
        lots=lots, all_eligible=all_eligible,
    )


def test_break_even_uses_earliest_ineligible_lot_not_weighted_average() -> None:
    eligible = LotCgt(Decimal("100"), date(2024, 1, 1), Decimal("3000"), date(2025, 1, 2), True)
    pending = LotCgt(Decimal("100"), date(2026, 6, 1), Decimal("4000"), date(2027, 6, 2), False)
    inp = _input_with_lots((eligible, pending), all_eligible=False)

    result = _break_even_lot(inp)
    assert result is not None
    lot_cost, lot_acquired = result
    assert lot_cost == Decimal("40")              # the pending lot's 4000/100
    assert lot_cost != inp.cost_usd               # NOT the weighted-average 35
    assert lot_acquired == date(2026, 6, 1)


def test_break_even_lot_none_when_all_eligible() -> None:
    e1 = LotCgt(Decimal("100"), date(2023, 1, 1), Decimal("3000"), date(2024, 1, 2), True)
    inp = _input_with_lots((e1,), all_eligible=True)
    assert _break_even_lot(inp) is None
