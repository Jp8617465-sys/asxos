"""
DB loader for the paper-portfolio monitor (M13.8+).

Thin async I/O that assembles a pure ``MonitorInputs`` from persisted run data
and the prices table. All analytics live in ``monitor.py``; this file only
fetches and shapes typed data, so the maths stays unit-testable without a DB.

No-lookahead is enforced at the SQL boundary: the forward price panel only
selects ``dt <= eval_as_of``. The benchmark resolves to ``AXJO.INDX`` from the
prices table (the same symbol the snapshot job uses); when that is not yet
ingested it falls back to a clearly-labelled equal-weight universe-breadth
proxy, and if that is also unavailable it reports the gap rather than inventing
a comparison.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg

from asxos.domain.portfolio.monitor import (
    BenchmarkSeries,
    CostModel,
    MonitorInputs,
    Position,
    PriceBar,
)

# Same index symbol as jobs/snapshot_portfolio.py. Not yet ingested by
# sync_prices, so the primary benchmark is expected to be empty for now.
XJO_SYMBOL = "AXJO.INDX"


def _dec(v: object) -> Decimal:
    return Decimal(str(v))


def _position_from_row(r: asyncpg.Record) -> Position:
    """Map a target_allocations⋈proposed_trades⋈prices row to a Position.

    Nullable numeric columns are guarded: a NULL prob_up / expected_return (or a
    missing trade/price row from the LEFT JOINs) becomes Decimal('0') rather than
    crashing the whole load with Decimal(str(None)) -> InvalidOperation.
    """
    ref = r["reference_price"]
    entry_close = _dec(ref) if ref is not None else (
        _dec(r["entry_close"]) if r["entry_close"] is not None else Decimal("0")
    )
    adj = r["entry_adj_close"]
    entry_adj = _dec(adj) if adj is not None else entry_close
    qty = _dec(r["target_qty"]) if r["target_qty"] is not None else Decimal("0")
    return Position(
        symbol=r["symbol"],
        sector=r["sector"],
        qty=qty,
        entry_close=entry_close,
        entry_adj_close=entry_adj,
        target_weight=_dec(r["target_weight"]),
        target_aud=_dec(r["target_aud"]),
        signal_label=r["signal_label"],
        prob_up=_dec(r["prob_up"]) if r["prob_up"] is not None else Decimal("0"),
        expected_return=(
            _dec(r["expected_return"]) if r["expected_return"] is not None else Decimal("0")
        ),
    )


async def load_run_inputs(
    conn: asyncpg.Connection,
    run_id: int,
    eval_as_of: date,
    *,
    cost_model: CostModel | None = None,
    forward_fill: bool = False,
) -> MonitorInputs | None:
    """Load one run into a MonitorInputs, or None if run_id is unknown."""
    run = await conn.fetchrow(
        """
        SELECT run_id, as_of, signals_as_of, model_version, capital_aud
        FROM rebalance_runs WHERE run_id = $1
        """,
        run_id,
    )
    if run is None:
        return None

    run_as_of: date = run["as_of"]
    capital = _dec(run["capital_aud"])

    # Positions: target_allocations is authoritative for weight/signal/sector;
    # proposed_trades supplies the entered quantity and the entry (reference) price.
    rows = await conn.fetch(
        """
        SELECT ta.symbol, ta.sector, ta.target_weight, ta.target_aud,
               ta.signal_label, ta.prob_up, ta.expected_return,
               pt.target_qty, pt.reference_price,
               p.close AS entry_close, p.adj_close AS entry_adj_close
        FROM target_allocations ta
        LEFT JOIN proposed_trades pt
               ON pt.run_id = ta.run_id AND pt.symbol = ta.symbol
        LEFT JOIN prices p
               ON p.symbol = ta.symbol AND p.dt = $2
        WHERE ta.run_id = $1
        ORDER BY ta.target_weight DESC, ta.symbol
        """,
        run_id,
        run_as_of,
    )

    positions: list[Position] = []
    symbols: list[str] = []
    for r in rows:
        positions.append(_position_from_row(r))
        symbols.append(r["symbol"])

    invested = sum((p.target_aud for p in positions), Decimal("0"))
    cash = capital - invested

    # Traded notional (denominator for turnover + costs): sum abs(delta_aud)
    # over buy/sell trades — matches paper_trade.evaluate's convention.
    traded = await conn.fetchval(
        """
        SELECT COALESCE(SUM(ABS(delta_aud)), 0)
        FROM proposed_trades
        WHERE run_id = $1 AND side IN ('buy', 'sell')
        """,
        run_id,
    )
    total_traded = _dec(traded)

    # Forward price panel: every bar for held symbols with dt in [entry, eval].
    # The <= eval_as_of bound is the no-lookahead guarantee.
    panel: dict[date, dict[str, PriceBar]] = {}
    if symbols:
        price_rows = await conn.fetch(
            """
            SELECT dt, symbol, close, adj_close
            FROM prices
            WHERE symbol = ANY($1::text[]) AND dt >= $2 AND dt <= $3
            ORDER BY dt
            """,
            symbols,
            run_as_of,
            eval_as_of,
        )
        for pr in price_rows:
            d: date = pr["dt"]
            bar = PriceBar(
                close=_dec(pr["close"]),
                adj_close=_dec(pr["adj_close"]) if pr["adj_close"] is not None else None,
            )
            panel.setdefault(d, {})[pr["symbol"]] = bar

    benchmark = await _load_benchmark(conn, run_as_of, eval_as_of)

    return MonitorInputs(
        run_id=run_id,
        run_as_of=run_as_of,
        signals_as_of=run["signals_as_of"],
        eval_as_of=eval_as_of,
        model_version=run["model_version"],
        capital_aud=capital,
        cash_aud=cash,
        positions=positions,
        price_panel=panel,
        benchmark=benchmark,
        total_traded_aud=total_traded,
        cost_model=cost_model or CostModel(),
        forward_fill=forward_fill,
    )


async def _load_benchmark(
    conn: asyncpg.Connection, entry: date, eval_as_of: date
) -> BenchmarkSeries:
    """Resolve the benchmark series with explicit provenance.

    1. AXJO.INDX from prices (the canonical source). Used if present.
    2. Equal-weight universe-breadth proxy (the 'average active ASX stock').
    3. Otherwise: unavailable, gap reported.
    """
    xjo = await conn.fetch(
        "SELECT dt, close FROM prices WHERE symbol = $1 AND dt >= $2 AND dt <= $3 ORDER BY dt",
        XJO_SYMBOL,
        entry,
        eval_as_of,
    )
    if xjo and any(r["dt"] == entry for r in xjo):
        return BenchmarkSeries(
            available=True,
            source=f"{XJO_SYMBOL} (prices.close)",
            note="ASX 200 index close, anchored at entry date.",
            levels={r["dt"]: _dec(r["close"]) for r in xjo},
        )

    # Fallback: equal-weight breadth proxy over active AU equities, expressed as
    # a growth index (1.0 at entry). Honest 'average stock' comparator.
    proxy = await conn.fetch(
        """
        WITH uni AS (
            SELECT symbol FROM universe
            WHERE is_active AND security_kind = 'au_equity' AND currency = 'AUD' AND symbol LIKE '%.AU'
        ),
        entry_px AS (
            SELECT p.symbol, p.adj_close
            FROM prices p JOIN uni USING (symbol)
            WHERE p.dt = $1 AND p.adj_close IS NOT NULL AND p.adj_close > 0
        )
        SELECT p.dt, AVG(p.adj_close / e.adj_close) AS lvl, COUNT(*) AS n
        FROM prices p JOIN entry_px e USING (symbol)
        WHERE p.dt >= $1 AND p.dt <= $2 AND p.adj_close IS NOT NULL
        GROUP BY p.dt ORDER BY p.dt
        """,
        entry,
        eval_as_of,
    )
    if proxy and any(r["dt"] == entry for r in proxy):
        n_entry = next((r["n"] for r in proxy if r["dt"] == entry), 0)
        return BenchmarkSeries(
            available=True,
            source="equal_weight_universe_proxy",
            note=(
                f"PROXY (XJO not ingested): equal-weight total-return index of "
                f"{n_entry} active AU equities, anchored at entry. Not the official "
                f"S&P/ASX 200 — wire AXJO.INDX into sync_prices for the real benchmark."
            ),
            levels={r["dt"]: _dec(r["lvl"]) for r in proxy},
        )

    return BenchmarkSeries(
        available=False,
        source=XJO_SYMBOL,
        note=(
            "Benchmark UNAVAILABLE: AXJO.INDX not in prices and no breadth proxy "
            "computable for this window. Add AXJO.INDX to sync_prices ingestion."
        ),
        levels={},
    )


async def list_persisted_runs(conn: asyncpg.Connection) -> list[dict[str, Any]]:
    """All persisted runs, most recent first (for --all)."""
    rows = await conn.fetch(
        "SELECT run_id, as_of, signals_as_of, model_version FROM rebalance_runs ORDER BY as_of DESC, run_id DESC"
    )
    return [
        {
            "run_id": r["run_id"],
            "as_of": r["as_of"],
            "signals_as_of": r["signals_as_of"],
            "model_version": r["model_version"],
        }
        for r in rows
    ]
