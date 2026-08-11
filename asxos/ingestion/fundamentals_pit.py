"""Point-in-time fundamentals derivation — research store `rs_fundamentals_pit`.

The leak-critical transform: reads raw `rs_financial_statements` (+ `rs_corporate_actions`
for dividends/franking) and derives the factor INPUTS, each stamped with a
`knowledge_date` computed by `derive_knowledge_date()` — the guard that drops
future/scheduled disclosure dates. This is where that guard is finally USED.

Pure DB-to-DB (no EODHD): `refresh_fundamentals_pit(conn, ...)`. SEPARATE from
production tables — never touches `universe`/`prices`.

v1 scope: one PIT snapshot per FISCAL YEAR, from yearly statements (for an annual
statement the annual figure IS the trailing-twelve-months at the fiscal year end).
Quarterly-rolling TTM is a v2 refinement. Ratios computed where both operands exist,
else NULL. Absolute-dollar columns are NUMERIC(24,6) (migration 0028) — bank/large-cap
line items exceed NUMERIC(18,6).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, TypedDict, TypeVar

import asyncpg
from dateutil.relativedelta import relativedelta

from asxos.ingestion.financial_statements import derive_knowledge_date

_Q6 = Decimal("0.000001")

# Each source read is scoped to one deterministic symbol page. The conservative
# default avoids whole-universe materialisation without changing the 30-second
# command timeout; the first production run still has to prove the chosen size
# against real row depth and latency. A full ~3,400-symbol run becomes ~68
# resumable pages. The upper bound prevents an operator override from silently
# restoring the original unbounded source fetch.
DEFAULT_PIT_BATCH_SIZE = 50
MAX_PIT_BATCH_SIZE = 200

# A symbol page can contain decades of statements, so bound each UPSERT command
# independently of the symbol read page. This avoids recreating the original
# timeout as one very large ``executemany`` call for history-rich symbols.
DEFAULT_PIT_WRITE_BATCH_SIZE = 250
MAX_PIT_WRITE_BATCH_SIZE = 1_000

_T = TypeVar("_T")

log = logging.getLogger(__name__)


class FundamentalsPitCounts(TypedDict):
    rows: int
    symbols: int
    source_symbols: int
    symbols_without_pit: int
    symbols_scanned: int
    symbols_without_source: int
    batches: int


def _num(x: Any) -> Decimal | None:
    if x is None or x == "":
        return None
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return None


def _div(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None or b == 0:
        return None
    return (a / b).quantize(_Q6)


def _dividend_summary(
    dividends: list[dict[str, Any]],
) -> tuple[Decimal | None, Decimal | None]:
    amounts = [a for d in dividends if (a := _num(d.get("dividend_amount"))) is not None]
    div_sum = sum(amounts, Decimal(0)) if amounts else None
    frks = [f for d in dividends if (f := _num(d.get("franking_pct"))) is not None]
    frank_avg = (sum(frks, Decimal(0)) / len(frks)).quantize(_Q6) if frks else None
    return div_sum, frank_avg


def compute_pit_factors(
    income: dict[str, Any] | None,
    balance: dict[str, Any] | None,
    dividends: list[dict[str, Any]],
    *,
    period_end: date,
    report_date: date | None,
    filing_date: date | None,
    as_of: date,
    lag_days: int = 75,
) -> dict[str, Any] | None:
    """Derive one rs_fundamentals_pit row. `income`/`balance` carry the promoted scalar
    columns plus a `line_items` dict (for grossProfit/operatingIncome/netDebt). Returns
    None if both statements are absent. `knowledge_date` is the guarded PIT key."""
    if not income and not balance:
        return None
    inc_li = (income or {}).get("line_items") or {}
    bal_li = (balance or {}).get("line_items") or {}

    rev = _num((income or {}).get("total_revenue"))
    ni = _num((income or {}).get("net_income"))
    equity = _num((balance or {}).get("total_equity"))
    assets = _num((balance or {}).get("total_assets"))
    shares = _num((balance or {}).get("shares_diluted"))
    gross = _num(inc_li.get("grossProfit"))
    op = _num(inc_li.get("operatingIncome"))
    net_debt = _num(bal_li.get("netDebt"))

    div_sum, frank_avg = _dividend_summary(dividends)

    return {
        "as_of": period_end,
        "knowledge_date": derive_knowledge_date(
            period_end, report_date, filing_date, as_of, lag_days=lag_days
        ),
        "book_value_ps": _div(equity, shares),
        "eps_ttm": _div(ni, shares),
        "revenue_ttm": rev,
        "net_income_ttm": ni,
        "roe": _div(ni, equity),
        "roa": _div(ni, assets),
        "gross_margin": _div(gross, rev),
        "operating_margin": _div(op, rev),
        "net_debt": net_debt,
        "total_equity": equity,
        "shares_outstanding": shares,
        "dividend_ttm": div_sum,
        "franking_avg_pct": frank_avg,
    }


_UPSERT = """
INSERT INTO rs_fundamentals_pit
    (symbol, as_of, knowledge_date, book_value_ps, eps_ttm, revenue_ttm, net_income_ttm,
     roe, roa, gross_margin, operating_margin, net_debt, total_equity, shares_outstanding,
     dividend_ttm, franking_avg_pct, source, computed_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
        'eodhd_derived', now())
ON CONFLICT (symbol, knowledge_date) DO UPDATE SET
    as_of=EXCLUDED.as_of, book_value_ps=EXCLUDED.book_value_ps, eps_ttm=EXCLUDED.eps_ttm,
    revenue_ttm=EXCLUDED.revenue_ttm, net_income_ttm=EXCLUDED.net_income_ttm, roe=EXCLUDED.roe,
    roa=EXCLUDED.roa, gross_margin=EXCLUDED.gross_margin, operating_margin=EXCLUDED.operating_margin,
    net_debt=EXCLUDED.net_debt, total_equity=EXCLUDED.total_equity,
    shares_outstanding=EXCLUDED.shares_outstanding, dividend_ttm=EXCLUDED.dividend_ttm,
    franking_avg_pct=EXCLUDED.franking_avg_pct, source='eodhd_derived', computed_at=now()
"""

_FIRST_SOURCE_SYMBOL_BATCH = """
SELECT DISTINCT symbol
FROM rs_financial_statements
WHERE period_type = 'yearly'
ORDER BY symbol
LIMIT $1
"""

_NEXT_SOURCE_SYMBOL_BATCH = """
SELECT DISTINCT symbol
FROM rs_financial_statements
WHERE period_type = 'yearly' AND symbol > $1
ORDER BY symbol
LIMIT $2
"""

_STATEMENTS_BY_SYMBOL_BATCH = """
SELECT symbol, period_end, statement_type, filing_date, report_date,
       total_revenue, net_income, total_assets, total_equity, total_debt,
       shares_diluted, line_items
FROM rs_financial_statements
WHERE period_type = 'yearly' AND symbol = ANY($1::text[])
ORDER BY symbol, period_end, statement_type
"""

_DIVIDENDS_BY_SYMBOL_BATCH = """
SELECT symbol, ex_date, dividend_amount, franking_pct
FROM rs_corporate_actions
WHERE action_type = 'dividend'
  AND symbol = ANY($1::text[])
  AND ex_date > $2
  AND ex_date <= $3
ORDER BY symbol, ex_date
"""


def _stmt_dict(row: asyncpg.Record | None) -> dict[str, Any] | None:
    if row is None:
        return None
    li = row["line_items"]
    if isinstance(li, str):
        li = json.loads(li)
    return {
        "total_revenue": row["total_revenue"],
        "net_income": row["net_income"],
        "total_assets": row["total_assets"],
        "total_equity": row["total_equity"],
        "total_debt": row["total_debt"],
        "shares_diluted": row["shares_diluted"],
        "line_items": li or {},
    }


def _validate_batch_size(name: str, batch_size: int, maximum: int) -> None:
    if not 1 <= batch_size <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")


def _normalise_symbols(symbols: list[str]) -> list[str]:
    normalised = sorted({symbol.strip() for symbol in symbols if symbol.strip()})
    if not normalised:
        raise ValueError("symbols was provided but contained no non-blank symbols")
    return normalised


def _chunks(values: list[_T], batch_size: int) -> Iterator[list[_T]]:
    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]


async def _source_symbol_batches(
    conn: asyncpg.Connection,
    *,
    batch_size: int,
) -> AsyncIterator[list[str]]:
    """Yield all yearly-statement symbols in stable, bounded keyset pages."""
    after: str | None = None
    while True:
        if after is None:
            rows = await conn.fetch(_FIRST_SOURCE_SYMBOL_BATCH, batch_size)
        else:
            rows = await conn.fetch(_NEXT_SOURCE_SYMBOL_BATCH, after, batch_size)
        batch = [row["symbol"] for row in rows]
        if not batch:
            return
        yield batch
        after = batch[-1]


def _pit_upsert_args(symbol: str, factors: dict[str, Any]) -> tuple[Any, ...]:
    return (
        symbol,
        factors["as_of"],
        factors["knowledge_date"],
        factors["book_value_ps"],
        factors["eps_ttm"],
        factors["revenue_ttm"],
        factors["net_income_ttm"],
        factors["roe"],
        factors["roa"],
        factors["gross_margin"],
        factors["operating_margin"],
        factors["net_debt"],
        factors["total_equity"],
        factors["shares_outstanding"],
        factors["dividend_ttm"],
        factors["franking_avg_pct"],
    )


async def _derive_symbol_batch(
    conn: asyncpg.Connection,
    *,
    symbols: list[str],
    as_of: date,
    lag_days: int,
) -> tuple[list[tuple[Any, ...]], set[str], set[str]]:
    """Read and derive one bounded symbol batch without writing it."""
    fin = await conn.fetch(_STATEMENTS_BY_SYMBOL_BATCH, symbols)
    source_symbols = {row["symbol"] for row in fin}

    groups: dict[tuple[str, date], dict[str, asyncpg.Record]] = {}
    for row in fin:
        groups.setdefault((row["symbol"], row["period_end"]), {})[row["statement_type"]] = row

    divs_by_symbol: dict[str, list[asyncpg.Record]] = {}
    if groups:
        period_ends = [period_end for _symbol, period_end in groups]
        dividend_start = min(period_ends) - relativedelta(years=1)
        dividend_end = max(period_ends)
        divrows = await conn.fetch(
            _DIVIDENDS_BY_SYMBOL_BATCH,
            sorted(source_symbols),
            dividend_start,
            dividend_end,
        )
        for row in divrows:
            divs_by_symbol.setdefault(row["symbol"], []).append(row)

    upsert_rows: list[tuple[Any, ...]] = []
    derived_symbols: set[str] = set()
    for (symbol, period_end), statements in groups.items():
        anchor = statements.get("income") or statements.get("balance_sheet")
        if anchor is None:
            continue
        window_start = period_end - relativedelta(years=1)
        window_divs = [
            {
                "dividend_amount": dividend["dividend_amount"],
                "franking_pct": dividend["franking_pct"],
            }
            for dividend in divs_by_symbol.get(symbol, [])
            if dividend["ex_date"] and window_start < dividend["ex_date"] <= period_end
        ]
        factors = compute_pit_factors(
            _stmt_dict(statements.get("income")),
            _stmt_dict(statements.get("balance_sheet")),
            window_divs,
            period_end=period_end,
            report_date=anchor["report_date"],
            filing_date=anchor["filing_date"],
            as_of=as_of,
            lag_days=lag_days,
        )
        if factors is None:
            continue
        upsert_rows.append(_pit_upsert_args(symbol, factors))
        derived_symbols.add(symbol)

    return upsert_rows, source_symbols, derived_symbols


async def refresh_fundamentals_pit(
    conn: asyncpg.Connection,
    *,
    as_of: date,
    symbols: list[str] | None = None,
    lag_days: int = 75,
    batch_size: int = DEFAULT_PIT_BATCH_SIZE,
    write_batch_size: int = DEFAULT_PIT_WRITE_BATCH_SIZE,
    on_rows_committed: Callable[[int], None] | None = None,
) -> FundamentalsPitCounts:
    """Derive rs_fundamentals_pit from yearly rs_financial_statements + dividends.

    Idempotent UPSERT on (symbol, knowledge_date). Reads only the research store;
    writes only rs_fundamentals_pit. Source reads are bounded by a deterministic
    symbol batch and UPSERT commands by an independent PIT-row batch. Each
    successful write command is committed before the next one in the normal job
    path; a rerun converges through the idempotent conflict key. ``on_rows_committed``
    receives the cumulative row count after every successful write command so a
    caller can retain truthful progress if a later command fails.

    Coverage identities:

    - ``symbols_scanned = source_symbols + symbols_without_source``
    - ``source_symbols = symbols + symbols_without_pit``

    ``symbols_without_source`` is normally zero and is useful for an explicit
    ``symbols`` request containing names absent from yearly source statements.
    """
    _validate_batch_size("batch_size", batch_size, MAX_PIT_BATCH_SIZE)
    _validate_batch_size(
        "write_batch_size", write_batch_size, MAX_PIT_WRITE_BATCH_SIZE
    )
    requested = _normalise_symbols(symbols) if symbols is not None else None
    explicit_batches = _chunks(requested, batch_size) if requested is not None else None

    counts = FundamentalsPitCounts(
        rows=0,
        symbols=0,
        source_symbols=0,
        symbols_without_pit=0,
        symbols_scanned=0,
        symbols_without_source=0,
        batches=0,
    )

    async def process_batch(batch: list[str]) -> None:
        upsert_rows, source_symbols, derived_symbols = await _derive_symbol_batch(
            conn,
            symbols=batch,
            as_of=as_of,
            lag_days=lag_days,
        )
        without_pit = sorted(source_symbols - derived_symbols)
        without_source = sorted(set(batch) - source_symbols)

        symbol_batch_number = counts["batches"] + 1
        for write_batch_number, write_batch in enumerate(
            _chunks(upsert_rows, write_batch_size), start=1
        ):
            await conn.executemany(_UPSERT, write_batch)
            counts["rows"] += len(write_batch)
            if on_rows_committed is not None:
                on_rows_committed(counts["rows"])
            log.info(
                "fundamentals PIT write symbol_batch=%d write_batch=%d rows=%d "
                "cumulative_rows=%d",
                symbol_batch_number,
                write_batch_number,
                len(write_batch),
                counts["rows"],
            )

        counts["symbols"] += len(derived_symbols)
        counts["source_symbols"] += len(source_symbols)
        counts["symbols_without_pit"] += len(without_pit)
        counts["symbols_scanned"] += len(batch)
        counts["symbols_without_source"] += len(without_source)
        counts["batches"] += 1

        log.info(
            "fundamentals PIT batch=%d first=%s last=%s scanned=%d source=%d "
            "derived=%d no_pit=%d no_source=%d rows=%d cumulative_source=%d "
            "cumulative_rows=%d",
            counts["batches"],
            batch[0],
            batch[-1],
            len(batch),
            len(source_symbols),
            len(derived_symbols),
            len(without_pit),
            len(without_source),
            len(upsert_rows),
            counts["source_symbols"],
            counts["rows"],
        )
        if without_pit:
            log.info("fundamentals PIT no-row source symbols=%s", ",".join(without_pit))
        if without_source:
            log.info(
                "fundamentals PIT requested symbols without source=%s", ",".join(without_source)
            )

    if explicit_batches is not None:
        for batch in explicit_batches:
            await process_batch(batch)
    else:
        async for batch in _source_symbol_batches(conn, batch_size=batch_size):
            await process_batch(batch)

    return counts
