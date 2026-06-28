"""
Tests for asxos.domain.portfolio.monitor_loader.load_run_inputs end-to-end.

Complements test_monitor_loader.py (which covers only the _position_from_row
row-mapping guards). Here we drive load_run_inputs against a mock asyncpg conn:

- An unknown run_id (fetchrow -> None) returns None without further queries.
- A normal run assembles a MonitorInputs whose forward price panel only contains
  bars with dt <= eval_as_of (the no-lookahead SQL bound), and whose cash, traded
  notional and benchmark are wired through from the fetched rows.

Note: imports asxos.domain.portfolio.monitor (Decimal-only domain, no heavy deps)
so this collects cleanly in the bare sandbox.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from asxos.domain.portfolio.monitor import BenchmarkSeries, CostModel, MonitorInputs
from asxos.domain.portfolio.monitor_loader import XJO_SYMBOL, load_run_inputs

ENTRY = date(2026, 1, 5)
EVAL = date(2026, 1, 12)


def _make_conn(
    *,
    run_row: dict | None,
    position_rows: list[dict] | None = None,
    traded: object = 0,
    price_rows: list[dict] | None = None,
    xjo_rows: list[dict] | None = None,
    proxy_rows: list[dict] | None = None,
) -> MagicMock:
    """A mock conn whose fetch/fetchrow/fetchval replay the loader's call order.

    load_run_inputs issues, in order:
      fetchrow(run) -> fetch(positions) -> fetchval(traded) -> fetch(price panel)
      -> _load_benchmark: fetch(xjo) [-> fetch(proxy) if xjo absent].
    """
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=run_row)
    conn.fetchval = AsyncMock(return_value=traded)

    fetch_returns: list[list[dict]] = []
    if run_row is not None:
        fetch_returns.append(position_rows or [])
        fetch_returns.append(price_rows or [])
        fetch_returns.append(xjo_rows or [])
        if not xjo_rows:
            fetch_returns.append(proxy_rows or [])
    conn.fetch = AsyncMock(side_effect=fetch_returns)
    return conn


def _position_row(symbol: str = "CBA.AU") -> dict:
    return {
        "symbol": symbol,
        "sector": "Financials",
        "target_weight": Decimal("0.2"),
        "target_aud": Decimal("40000"),
        "signal_label": "BUY",
        "prob_up": Decimal("0.62"),
        "expected_return": Decimal("0.04"),
        "target_qty": Decimal("100"),
        "reference_price": Decimal("95.50"),
        "entry_close": Decimal("95.50"),
        "entry_adj_close": Decimal("95.50"),
    }


async def test_unknown_run_returns_none() -> None:
    conn = _make_conn(run_row=None)
    result = await load_run_inputs(conn, run_id=999, eval_as_of=EVAL)
    assert result is None
    # No positions/price/benchmark queries should fire on the None branch.
    conn.fetch.assert_not_awaited()
    conn.fetchval.assert_not_awaited()


async def test_normal_run_assembles_monitor_inputs() -> None:
    run_row = {
        "run_id": 7,
        "as_of": ENTRY,
        "signals_as_of": date(2026, 1, 4),
        "model_version": "model_a_v1_5",
        "capital_aud": Decimal("200000"),
    }
    price_rows = [
        {"dt": ENTRY, "symbol": "CBA.AU", "close": Decimal("95.50"), "adj_close": Decimal("95.50")},
        {"dt": EVAL, "symbol": "CBA.AU", "close": Decimal("99.00"), "adj_close": Decimal("99.00")},
    ]
    xjo_rows = [
        {"dt": ENTRY, "close": Decimal("7800")},
        {"dt": EVAL, "close": Decimal("7900")},
    ]
    conn = _make_conn(
        run_row=run_row,
        position_rows=[_position_row()],
        traded=Decimal("60000"),
        price_rows=price_rows,
        xjo_rows=xjo_rows,
    )

    result = await load_run_inputs(conn, run_id=7, eval_as_of=EVAL)

    assert isinstance(result, MonitorInputs)
    assert result.run_id == 7
    assert result.run_as_of == ENTRY
    assert result.eval_as_of == EVAL
    assert result.capital_aud == Decimal("200000")
    # cash = capital - sum(target_aud) = 200000 - 40000
    assert result.cash_aud == Decimal("160000")
    assert result.total_traded_aud == Decimal("60000")
    assert len(result.positions) == 1
    assert result.positions[0].symbol == "CBA.AU"

    # Forward price panel keyed by dt, both bars present, all dt <= eval_as_of.
    assert set(result.price_panel) == {ENTRY, EVAL}
    assert all(d <= EVAL for d in result.price_panel)
    assert result.price_panel[EVAL]["CBA.AU"].close == Decimal("99.00")

    # Benchmark resolved to the canonical XJO source (entry-anchored).
    assert isinstance(result.benchmark, BenchmarkSeries)
    assert result.benchmark.available is True
    assert XJO_SYMBOL in result.benchmark.source
    assert result.benchmark.levels[ENTRY] == Decimal("7800")

    # The price-panel query must carry the eval_as_of upper bound (no lookahead).
    panel_call = conn.fetch.await_args_list[1]
    assert EVAL in panel_call.args


async def test_no_xjo_falls_back_to_proxy_benchmark() -> None:
    run_row = {
        "run_id": 8,
        "as_of": ENTRY,
        "signals_as_of": ENTRY,
        "model_version": "model_a_v1_5",
        "capital_aud": Decimal("100000"),
    }
    proxy_rows = [
        {"dt": ENTRY, "lvl": Decimal("1.0"), "n": 150},
        {"dt": EVAL, "lvl": Decimal("1.03"), "n": 150},
    ]
    conn = _make_conn(
        run_row=run_row,
        position_rows=[_position_row()],
        traded=Decimal("0"),
        price_rows=[],
        xjo_rows=[],          # XJO not ingested
        proxy_rows=proxy_rows,
    )

    result = await load_run_inputs(conn, run_id=8, eval_as_of=EVAL)
    assert result is not None
    assert result.benchmark.available is True
    assert result.benchmark.source == "equal_weight_universe_proxy"
    assert result.benchmark.levels[ENTRY] == Decimal("1.0")


async def test_cost_model_passthrough_and_default() -> None:
    run_row = {
        "run_id": 9,
        "as_of": ENTRY,
        "signals_as_of": ENTRY,
        "model_version": "m",
        "capital_aud": Decimal("100000"),
    }

    def fresh_conn() -> MagicMock:
        return _make_conn(
            run_row=run_row,
            position_rows=[],
            traded=Decimal("0"),
            price_rows=[],
            xjo_rows=[],
            proxy_rows=[],
        )

    default = await load_run_inputs(fresh_conn(), run_id=9, eval_as_of=EVAL)
    assert default is not None
    assert default.cost_model == CostModel()

    custom = CostModel(commission_bps=Decimal("20"), slippage_bps=Decimal("10"))
    overridden = await load_run_inputs(
        fresh_conn(), run_id=9, eval_as_of=EVAL, cost_model=custom
    )
    assert overridden is not None
    assert overridden.cost_model is custom
