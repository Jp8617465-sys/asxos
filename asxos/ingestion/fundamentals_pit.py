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
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import asyncpg
from dateutil.relativedelta import relativedelta

from asxos.ingestion.financial_statements import derive_knowledge_date

_Q6 = Decimal("0.000001")


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


async def refresh_fundamentals_pit(
    conn: asyncpg.Connection,
    *,
    as_of: date,
    symbols: list[str] | None = None,
    lag_days: int = 75,
) -> dict[str, int]:
    """Derive rs_fundamentals_pit from yearly rs_financial_statements + dividends.

    Idempotent UPSERT on (symbol, knowledge_date). Reads only the research store;
    writes only rs_fundamentals_pit.
    """
    filt = " AND symbol = ANY($1)" if symbols else ""
    args: list[Any] = [symbols] if symbols else []

    fin = await conn.fetch(
        f"""
        SELECT symbol, period_end, statement_type, filing_date, report_date,
               total_revenue, net_income, total_assets, total_equity, total_debt,
               shares_diluted, line_items
        FROM rs_financial_statements
        WHERE period_type = 'yearly'{filt}
        ORDER BY symbol, period_end
        """,
        *args,
    )
    groups: dict[tuple[str, date], dict[str, asyncpg.Record]] = {}
    for r in fin:
        groups.setdefault((r["symbol"], r["period_end"]), {})[r["statement_type"]] = r

    divrows = await conn.fetch(
        f"""
        SELECT symbol, ex_date, dividend_amount, franking_pct
        FROM rs_corporate_actions
        WHERE action_type = 'dividend'{filt}
        """,
        *args,
    )
    divs_by_symbol: dict[str, list[asyncpg.Record]] = {}
    for r in divrows:
        divs_by_symbol.setdefault(r["symbol"], []).append(r)

    counts = {"rows": 0, "symbols": 0}
    seen: set[str] = set()
    for (sym, pe), stmts in groups.items():
        anchor = stmts.get("income") or stmts.get("balance_sheet")
        if anchor is None:
            continue
        window_start = pe - relativedelta(years=1)
        window_divs = [
            {"dividend_amount": d["dividend_amount"], "franking_pct": d["franking_pct"]}
            for d in divs_by_symbol.get(sym, [])
            if d["ex_date"] and window_start < d["ex_date"] <= pe
        ]
        factors = compute_pit_factors(
            _stmt_dict(stmts.get("income")),
            _stmt_dict(stmts.get("balance_sheet")),
            window_divs,
            period_end=pe,
            report_date=anchor["report_date"],
            filing_date=anchor["filing_date"],
            as_of=as_of,
            lag_days=lag_days,
        )
        if factors is None:
            continue
        await conn.execute(
            _UPSERT,
            sym, factors["as_of"], factors["knowledge_date"], factors["book_value_ps"],
            factors["eps_ttm"], factors["revenue_ttm"], factors["net_income_ttm"],
            factors["roe"], factors["roa"], factors["gross_margin"], factors["operating_margin"],
            factors["net_debt"], factors["total_equity"], factors["shares_outstanding"],
            factors["dividend_ttm"], factors["franking_avg_pct"],
        )
        counts["rows"] += 1
        seen.add(sym)
    counts["symbols"] = len(seen)
    return counts
