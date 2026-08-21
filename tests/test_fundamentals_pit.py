"""Tests for the rs_fundamentals_pit derivation.

compute_pit_factors is where derive_knowledge_date is finally USED, so the guard is
re-exercised here in context. Ratios are checked on clean synthetic numbers; the
orchestrator is driven with a fake conn. No network, no DB.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from asxos.domain.research.factor_scores import refresh_factor_scores
from asxos.ingestion.fundamentals_pit import (
    MAX_PIT_BATCH_SIZE,
    MAX_PIT_WRITE_BATCH_SIZE,
    compute_pit_factors,
    refresh_fundamentals_pit,
)
from jobs.derive_fundamentals_pit import _refresh_with_monitor

D = date.fromisoformat

_INCOME = {
    "total_revenue": Decimal("1000"), "net_income": Decimal("100"),
    "line_items": {"grossProfit": "600", "operatingIncome": "200"},
}
_BALANCE = {
    "total_assets": Decimal("2000"), "total_equity": Decimal("500"),
    "total_debt": Decimal("300"), "shares_diluted": Decimal("50"),
    "line_items": {"netDebt": "100"},
}
_DIVS = [
    {"dividend_amount": Decimal("1.5"), "franking_pct": Decimal("100")},
    {"dividend_amount": Decimal("1.5"), "franking_pct": Decimal("0")},
]


def _factors(**over):
    kw = {"period_end": D("2025-06-30"), "report_date": D("2025-08-12"),
          "filing_date": D("2025-06-30"), "as_of": D("2026-06-24")}
    kw.update(over)
    return compute_pit_factors(_INCOME, _BALANCE, _DIVS, **kw)


def test_ratios():
    f = _factors()
    assert f["roe"] == Decimal("0.200000")            # 100/500
    assert f["roa"] == Decimal("0.050000")            # 100/2000
    assert f["gross_margin"] == Decimal("0.600000")   # 600/1000
    assert f["operating_margin"] == Decimal("0.200000")
    assert f["book_value_ps"] == Decimal("10.000000") # 500/50
    assert f["eps_ttm"] == Decimal("2.000000")        # 100/50


def test_currency_defaults_to_none_when_absent_from_fixtures():
    """D1 (segment-valuation architecture doc): every monetary column here is
    denominated in the source statement's currency, not necessarily AUD.
    compute_pit_factors must carry it through so a caller can group/convert
    by it rather than assume AUD. The positive carry-through path is covered
    by test_currency_prefers_income_over_balance_sheet below; this only
    pins the absent-key default.
    """
    f = _factors()
    assert f["currency"] is None  # _INCOME/_BALANCE fixtures above carry no currency key


def test_currency_falls_back_to_balance_sheet_when_income_lacks_it():
    f = compute_pit_factors(
        {**_INCOME, "currency": None},
        {**_BALANCE, "currency": "USD"},
        _DIVS,
        period_end=D("2025-06-30"), report_date=D("2025-08-12"),
        filing_date=D("2025-06-30"), as_of=D("2026-06-24"),
    )
    assert f["currency"] == "USD"


def test_currency_prefers_income_over_balance_sheet():
    f = compute_pit_factors(
        {**_INCOME, "currency": "USD"},
        {**_BALANCE, "currency": "AUD"},
        _DIVS,
        period_end=D("2025-06-30"), report_date=D("2025-08-12"),
        filing_date=D("2025-06-30"), as_of=D("2026-06-24"),
    )
    assert f["currency"] == "USD"


def test_absolute_passthrough_and_netdebt():
    f = _factors()
    assert f["revenue_ttm"] == Decimal("1000")
    assert f["net_income_ttm"] == Decimal("100")
    assert f["total_equity"] == Decimal("500")
    assert f["shares_outstanding"] == Decimal("50")
    assert f["net_debt"] == Decimal("100")            # from balance line_items


def test_dividends_and_franking_average():
    f = _factors()
    assert f["dividend_ttm"] == Decimal("3.0")        # 1.5 + 1.5
    assert f["franking_avg_pct"] == Decimal("50.000000")  # avg(100, 0)


def test_knowledge_date_uses_guard_dropping_future_report_date():
    """The whole point: a FUTURE reportDate must not become knowledge_date."""
    f = _factors(period_end=D("2026-03-31"), report_date=D("2026-08-11"),
                 filing_date=D("2026-05-07"), as_of=D("2026-06-24"))
    assert f["knowledge_date"] == D("2026-05-07")     # the real past disclosure
    assert f["as_of"] == D("2026-03-31")              # the period end


def test_division_guards_return_none():
    f = compute_pit_factors(
        {"total_revenue": Decimal("0"), "net_income": Decimal("100"), "line_items": {}},
        {"total_assets": None, "total_equity": Decimal("0"), "shares_diluted": None, "line_items": {}},
        [],
        period_end=D("2025-06-30"), report_date=None, filing_date=None, as_of=D("2026-06-24"),
    )
    assert f["roe"] is None      # equity 0
    assert f["roa"] is None      # assets None
    assert f["gross_margin"] is None
    assert f["book_value_ps"] is None
    assert f["dividend_ttm"] is None
    assert f["franking_avg_pct"] is None


def test_none_when_both_statements_absent():
    assert compute_pit_factors(None, None, [], period_end=D("2025-06-30"),
                               report_date=None, filing_date=None, as_of=D("2026-06-24")) is None


# ---------------------------------------------------------------------------
# orchestrator
# ---------------------------------------------------------------------------


class FakeConn:
    def __init__(self, fin, divs):
        self._fin = fin
        self._divs = divs
        self.fetched: list[tuple[str, tuple[Any, ...]]] = []
        self.executed: list[tuple[str, tuple]] = []
        self.executed_many: list[tuple[str, list[tuple[Any, ...]]]] = []

    async def fetch(self, sql, *args):
        self.fetched.append((sql, args))
        if "SELECT DISTINCT symbol" in sql:
            source_symbols = sorted({row["symbol"] for row in self._fin})
            if "symbol > $1" in sql:
                after, limit = args
                source_symbols = [symbol for symbol in source_symbols if symbol > after]
            else:
                (limit,) = args
            return [{"symbol": symbol} for symbol in source_symbols[:limit]]
        if "rs_financial_statements" in sql:
            selected = set(args[0])
            return sorted(
                (row for row in self._fin if row["symbol"] in selected),
                key=lambda row: (row["symbol"], row["period_end"], row["statement_type"]),
            )
        if "rs_corporate_actions" in sql:
            selected, start, end = args
            return sorted(
                (
                    row
                    for row in self._divs
                    if row["symbol"] in selected and start < row["ex_date"] <= end
                ),
                key=lambda row: (row["symbol"], row["ex_date"]),
            )
        return []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql, args):
        self.executed_many.append((sql, list(args)))


def _finrow(stmt_type, sym="HUBS.US", **over):
    base = {
        "symbol": sym,
        "period_end": D("2025-12-31"),
        "statement_type": stmt_type,
        "filing_date": D("2026-02-11"),
        "report_date": D("2026-02-11"),
        "total_revenue": None,
        "net_income": None,
        "total_assets": None,
        "total_equity": None,
        "total_debt": None,
        "shares_diluted": None,
        "line_items": "{}",
        "currency": "USD",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_orchestrator_derives_and_upserts():
    fin = [
        _finrow(
            "income",
            total_revenue=Decimal("1000"),
            net_income=Decimal("100"),
            line_items=json.dumps({"grossProfit": "600", "operatingIncome": "200"}),
        ),
        _finrow(
            "balance_sheet",
            total_assets=Decimal("2000"),
            total_equity=Decimal("500"),
            total_debt=Decimal("300"),
            shares_diluted=Decimal("50"),
            line_items=json.dumps({"netDebt": "100"}),
        ),
    ]
    divs = [
        {
            "symbol": "HUBS.US",
            "ex_date": D("2025-09-01"),
            "dividend_amount": Decimal("1.5"),
            "franking_pct": Decimal("100"),
        }
    ]
    conn = FakeConn(fin, divs)
    counts = await refresh_fundamentals_pit(conn, as_of=D("2026-06-24"))
    assert counts == {
        "rows": 1,
        "symbols": 1,
        "source_symbols": 1,
        "symbols_without_pit": 0,
        "symbols_scanned": 1,
        "symbols_without_source": 0,
        "batches": 1,
    }
    assert conn.executed == []
    sql, rows = conn.executed_many[0]
    args = rows[0]
    assert "ON CONFLICT (symbol, knowledge_date) DO UPDATE" in sql
    assert args[0] == "HUBS.US"
    assert args[7] == Decimal("0.200000")  # roe in the param list
    assert args[16] == "USD"  # currency, from _finrow's default


@pytest.mark.asyncio
async def test_orchestrator_reads_only_research_store():
    conn = FakeConn([_finrow("income", total_revenue=Decimal("1"))], [])
    await refresh_fundamentals_pit(conn, as_of=D("2026-06-24"))
    all_sql = [sql for sql, _args in conn.fetched]
    all_sql.extend(sql for sql, _rows in conn.executed_many)
    assert all("universe" not in sql.lower() and " prices" not in sql.lower() for sql in all_sql)
    assert all(
        "symbol = ANY($1::text[])" in sql
        for sql, _args in conn.fetched
        if "SELECT symbol, period_end" in sql or "rs_corporate_actions" in sql
    )
    assert all("rs_fundamentals_pit" in sql for sql, _rows in conn.executed_many)
    assert conn.executed == []


@pytest.mark.asyncio
async def test_dividend_window_excludes_out_of_range():
    """Only dividends with ex_date in (period_end - 1y, period_end] count."""
    fin = [
        _finrow("income", total_revenue=Decimal("1000"), net_income=Decimal("100")),
        _finrow("balance_sheet", total_equity=Decimal("500"), shares_diluted=Decimal("50")),
    ]
    divs = [
        {
            "symbol": "HUBS.US",
            "ex_date": D("2025-09-01"),
            "dividend_amount": Decimal("2"),
            "franking_pct": None,
        },
        {
            "symbol": "HUBS.US",
            "ex_date": D("2024-01-01"),
            "dividend_amount": Decimal("9"),
            "franking_pct": None,
        },  # too old
    ]
    conn = FakeConn(fin, divs)
    await refresh_fundamentals_pit(conn, as_of=D("2026-06-24"))
    _sql, rows = conn.executed_many[0]
    args = rows[0]
    assert args[14] == Decimal("2")  # dividend_ttm — only the in-window dividend
    assert args[16] == "USD"  # currency, from _finrow's default


@pytest.mark.asyncio
async def test_large_universe_uses_bounded_deterministic_reads_and_batched_writes():
    symbols = [f"S{index:04d}.AU" for index in range(201)]
    fin = [
        _finrow(
            "income",
            sym=symbol,
            period_end=date(year, 6, 30),
            filing_date=date(year, 8, 20),
            report_date=date(year, 8, 20),
            total_revenue=Decimal("10"),
            net_income=Decimal("1"),
        )
        for symbol in symbols
        for year in range(2013, 2025)
    ]
    conn = FakeConn(fin, [])

    counts = await refresh_fundamentals_pit(
        conn,
        as_of=D("2026-06-24"),
        batch_size=100,
        write_batch_size=128,
    )

    assert counts == {
        "rows": 2412,
        "symbols": 201,
        "source_symbols": 201,
        "symbols_without_pit": 0,
        "symbols_scanned": 201,
        "symbols_without_source": 0,
        "batches": 3,
    }
    statement_batches = [
        args[0] for sql, args in conn.fetched if "SELECT symbol, period_end" in sql
    ]
    assert [symbol for batch in statement_batches for symbol in batch] == symbols
    assert max(map(len, statement_batches)) == 100
    assert len(conn.executed_many) == 21
    assert max(len(rows) for _sql, rows in conn.executed_many) == 128
    assert conn.executed == []  # no per-PIT-row awaited execute
    discovery_sql = [sql for sql, _args in conn.fetched if "SELECT DISTINCT symbol" in sql]
    assert discovery_sql and all("LIMIT" in sql for sql in discovery_sql)


@pytest.mark.asyncio
async def test_explicit_symbols_are_deduplicated_and_fully_accounted(caplog):
    fin = [
        _finrow("income", sym="A.AU", total_revenue=Decimal("1")),
        _finrow("cash_flow", sym="CASH.AU"),
    ]
    conn = FakeConn(fin, [])

    with caplog.at_level("INFO", logger="asxos.ingestion.fundamentals_pit"):
        counts = await refresh_fundamentals_pit(
            conn,
            as_of=D("2026-06-24"),
            symbols=["MISSING.AU", "A.AU", "CASH.AU", "A.AU"],
            batch_size=2,
        )

    assert counts == {
        "rows": 1,
        "symbols": 1,
        "source_symbols": 2,
        "symbols_without_pit": 1,
        "symbols_scanned": 3,
        "symbols_without_source": 1,
        "batches": 2,
    }
    statement_batches = [
        args[0] for sql, args in conn.fetched if "SELECT symbol, period_end" in sql
    ]
    assert statement_batches == [["A.AU", "CASH.AU"], ["MISSING.AU"]]
    assert "fundamentals PIT no-row source symbols=CASH.AU" in caplog.messages
    assert "fundamentals PIT requested symbols without source=MISSING.AU" in caplog.messages


@pytest.mark.asyncio
@pytest.mark.parametrize("batch_size", [0, MAX_PIT_BATCH_SIZE + 1])
async def test_batch_size_is_bounded_before_any_database_call(batch_size):
    conn = FakeConn([], [])

    with pytest.raises(ValueError, match="batch_size must be between"):
        await refresh_fundamentals_pit(
            conn,
            as_of=D("2026-06-24"),
            batch_size=batch_size,
        )

    assert conn.fetched == []


@pytest.mark.asyncio
@pytest.mark.parametrize("write_batch_size", [0, MAX_PIT_WRITE_BATCH_SIZE + 1])
async def test_write_batch_size_is_bounded_before_any_database_call(write_batch_size):
    conn = FakeConn([], [])

    with pytest.raises(ValueError, match="write_batch_size must be between"):
        await refresh_fundamentals_pit(
            conn,
            as_of=D("2026-06-24"),
            write_batch_size=write_batch_size,
        )

    assert conn.fetched == []


class ConvergingConn(FakeConn):
    def __init__(self, fin, *, fail_on_call: int | None) -> None:
        super().__init__(fin, [])
        self.fail_on_call = fail_on_call
        self.executemany_calls = 0
        self.pit_rows: dict[tuple[str, date], tuple[Any, ...]] = {}

    async def executemany(self, sql, args):
        rows = list(args)
        self.executemany_calls += 1
        if self.executemany_calls == self.fail_on_call:
            raise TimeoutError("synthetic batch failure")
        self.executed_many.append((sql, rows))
        for row in rows:
            self.pit_rows[(row[0], row[2])] = row


@pytest.mark.asyncio
async def test_partial_failure_rerun_converges_idempotently():
    symbols = ["A.AU", "B.AU", "C.AU", "D.AU"]
    fin = [_finrow("income", sym=symbol, total_revenue=Decimal("1")) for symbol in symbols]
    conn = ConvergingConn(fin, fail_on_call=2)

    with pytest.raises(TimeoutError, match="synthetic batch failure"):
        await refresh_fundamentals_pit(
            conn,
            as_of=D("2026-06-24"),
            symbols=symbols,
            batch_size=2,
        )
    assert {key[0] for key in conn.pit_rows} == {"A.AU", "B.AU"}

    conn.fail_on_call = None
    conn.executemany_calls = 0
    counts = await refresh_fundamentals_pit(
        conn,
        as_of=D("2026-06-24"),
        symbols=symbols,
        batch_size=2,
    )

    assert counts["rows"] == 4
    assert {key[0] for key in conn.pit_rows} == set(symbols)
    assert len(conn.pit_rows) == 4
    assert conn.executed == []
    assert all(
        "ON CONFLICT (symbol, knowledge_date) DO UPDATE" in sql for sql, _rows in conn.executed_many
    )


class RecordingJobMonitor:
    def __init__(self) -> None:
        self.rows_written = 0
        self.persisted_rows: int | None = None
        self.persisted_status: str | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.persisted_rows = self.rows_written
        self.persisted_status = "failure" if exc_type is not None else "success"
        return False


@pytest.mark.asyncio
async def test_job_monitor_persists_committed_rows_when_later_write_chunk_fails():
    fin = [
        _finrow(
            "income",
            sym="A.AU",
            period_end=date(year, 6, 30),
            filing_date=date(year, 8, 20),
            report_date=date(year, 8, 20),
            total_revenue=Decimal("1"),
        )
        for year in range(2021, 2025)
    ]
    conn = ConvergingConn(fin, fail_on_call=2)
    monitor = RecordingJobMonitor()

    with pytest.raises(TimeoutError, match="synthetic batch failure"):
        async with monitor:
            await _refresh_with_monitor(
                conn,
                monitor=monitor,  # type: ignore[arg-type]
                as_of=D("2026-06-24"),
                symbols=["A.AU"],
                batch_size=1,
                write_batch_size=2,
            )

    assert len(conn.pit_rows) == 2
    assert monitor.persisted_status == "failure"
    assert monitor.persisted_rows == len(conn.pit_rows)


class FactorCompatibilityConn:
    def __init__(self, pit_row: dict[str, Any]) -> None:
        self.pit_row = pit_row
        self.factor_writes: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql, *args):
        if "rs_fundamentals_pit" in sql:
            return [self.pit_row]
        if "FROM prices" in sql:
            return [
                {
                    "symbol": self.pit_row["symbol"],
                    "dt": D("2026-06-24"),
                    "close": Decimal("10"),
                    "adj_close": Decimal("10"),
                }
            ]
        return []

    async def execute(self, sql, *args):
        self.factor_writes.append((sql, args))


@pytest.mark.asyncio
async def test_batched_pit_row_remains_compatible_with_factor_score_consumer():
    derive_conn = FakeConn(
        [
            _finrow(
                "income",
                sym="CBA.AU",
                total_revenue=Decimal("1000"),
                net_income=Decimal("100"),
                line_items=json.dumps({"grossProfit": "600", "operatingIncome": "200"}),
            ),
            _finrow(
                "balance_sheet",
                sym="CBA.AU",
                total_assets=Decimal("2000"),
                total_equity=Decimal("500"),
                shares_diluted=Decimal("50"),
            ),
        ],
        [],
    )
    await refresh_fundamentals_pit(
        derive_conn,
        as_of=D("2026-06-24"),
        symbols=["CBA.AU"],
    )
    args = derive_conn.executed_many[0][1][0]
    pit_row = {
        "symbol": args[0],
        "eps_ttm": args[4],
        "book_value_ps": args[3],
        "roe": args[7],
        "roa": args[8],
        "gross_margin": args[9],
        "operating_margin": args[10],
        "dividend_ttm": args[14],
        "franking_avg_pct": args[15],
        "shares_outstanding": args[13],
        "knowledge_date": args[2],
        "sector": "Financials",
    }
    factor_conn = FactorCompatibilityConn(pit_row)

    counts = await refresh_factor_scores(
        factor_conn,
        as_of=D("2026-06-24"),
        symbols=["CBA.AU"],
    )

    assert counts == {"symbols": 1, "rows": 1}
    assert len(factor_conn.factor_writes) == 1
    _sql, factor_args = factor_conn.factor_writes[0]
    assert factor_args[0] == "CBA.AU"
    assert factor_args[11] == 2  # derived value and quality categories survive
