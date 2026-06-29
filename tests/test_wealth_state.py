"""
Tests for the wealth_state brief collector's concentration denominator.

The per-holding concentration % must use the priced per-holding MVs as the
denominator (same source as the numerator), not the snapshot holdings_mv_aud,
which may be derived from a different price date/source.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from asxos.domain.brief.collectors.wealth_state import collect_wealth_state
from asxos.domain.brief.types import SeverityLevel


def _snapshot(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "capital_aud": Decimal("210"),
        # NOTE: snapshot total MV (200) deliberately != priced sum (100) below,
        # so the test distinguishes the two possible denominators.
        "holdings_mv_aud": Decimal("200"),
        "cash_aud": Decimal("10"),
        "us_holdings_mv_aud": None,
        "us_holdings_cost_aud": None,
        "fx_rate_audusd": None,
        "unrealised_fx_pnl_aud": None,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_concentration_uses_priced_sum_not_snapshot_mv() -> None:
    conn = AsyncMock()
    # fetchrow: (1) snapshot row, (2) peak row (None peak → drawdown skipped)
    conn.fetchrow = AsyncMock(side_effect=[_snapshot(), {"peak": None}])
    # fetch: priced holdings summing to 100 (60 + 40), NOT 200
    conn.fetch = AsyncMock(
        return_value=[
            {"symbol": "CBA.AU", "mv_local": Decimal("60")},
            {"symbol": "BHP.AU", "mv_local": Decimal("40")},
        ]
    )

    result = await collect_wealth_state(conn, __import__("datetime").date(2026, 6, 1))

    # CBA is 60/100 = 60% (red) against the priced sum; against the snapshot's 200
    # it would have been only 30% (yellow). A red "concentrated position" item with
    # 60.0% proves the denominator is the priced sum.
    conc = [i for i in result.items if "concentrated position" in i.message]
    assert any("CBA.AU: 60.0%" in i.message and i.level == SeverityLevel.red for i in conc)
