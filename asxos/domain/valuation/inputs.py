"""Every read the valuation makes. Bound parameters only, screened at import.

The screen is modelled on asxos/domain/themes/candidates/measures.py: a FROM/JOIN
allowlist plus a forbidden-token list.  Two of the forbidden tokens matter
specifically here:

  `fundamentals`  — the legacy table whose roe/debt_to_equity/franking_pct/
                    revenue/net_income columns are NULL across all 143,715 rows
                    and have never had a writer (backlog C-18).  Making the name
                    unreadable is what stops a future edit quietly reintroducing
                    it.  `rs_fundamentals_pit` survives the word boundary.

  `debt_to_equity`, `net_debt`, `gross_margin`, `total_revenue`,
  `netInterestIncome` — bank-meaningless or basis-broken (backlog C-19).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Final, Protocol

from asxos.domain.valuation.gaps import Gap
from asxos.domain.valuation.numeric import valuation_context

_ADMISSIBLE: Final[frozenset[str]] = frozenset(
    {"rs_fundamentals_pit", "rs_financial_statements", "market_context_current", "prices", "universe"}
)
_FORBIDDEN: Final[tuple[str, ...]] = (
    r"\bsignals\b", r"\bshap_", r"\bprob_up\b", r"\bsignal_label\b", r"\bmodel_a\b",
    r"\bexpected_return\b", r"\bsignal_outcomes\b",
    r"\bfundamentals\b", r"\bdebt_to_equity\b", r"\bnet_debt\b", r"\bgross_margin\b",
    r"\btotal_revenue\b", r"netinterestincome",
)
_FROM_JOIN = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)


def assert_valuation_sql_admissible(sql: str) -> None:
    lowered = sql.lower()
    for token in _FORBIDDEN:
        if re.search(token, lowered):
            raise AssertionError(f"valuation SQL names a forbidden token: {token}")
    for table in _FROM_JOIN.findall(sql):
        if table.lower() not in _ADMISSIBLE:
            raise AssertionError(f"valuation SQL reads an inadmissible table: {table}")


SQL_PIT: Final[str] = (
    "SELECT as_of, knowledge_date, knowledge_tier, net_income_ttm, total_equity, "
    "shares_outstanding, dividend_ttm, eps_ttm, roe, franking_avg_pct, currency "
    "FROM rs_fundamentals_pit WHERE symbol = $1 AND knowledge_date <= $2 "
    "ORDER BY knowledge_date DESC LIMIT 2"
)
SQL_BALANCE: Final[str] = (
    "SELECT period_end, "
    "(line_items->>'totalStockholderEquity')::numeric AS tse, "
    "(line_items->>'goodWill')::numeric AS goodwill, "
    "(line_items->>'intangibleAssets')::numeric AS intangibles, "
    "(line_items->>'preferredStockTotalEquity') AS preferred, "
    "(line_items->>'minorityInterest') AS minority "
    "FROM rs_financial_statements WHERE symbol = $1 AND period_type = 'yearly' "
    "AND statement_type = 'balance_sheet' AND period_end = ANY($2::date[])"
)
SQL_RISK_FREE: Final[str] = (
    "SELECT as_of, aus_10y_yield FROM market_context_current "
    "WHERE aus_10y_yield IS NOT NULL AND as_of <= $1 ORDER BY as_of DESC LIMIT 1"
)
SQL_CLOSE: Final[str] = (
    "SELECT dt, close FROM prices WHERE symbol = $1 AND dt <= $2 ORDER BY dt DESC LIMIT 1"
)

for _sql in (SQL_PIT, SQL_BALANCE, SQL_RISK_FREE, SQL_CLOSE):
    assert_valuation_sql_admissible(_sql)


class Conn(Protocol):
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...


@dataclass(frozen=True)
class BankInputs:
    """Everything the residual-income model needs for one name, plus its gaps."""

    symbol: str
    period_end: date
    knowledge_date: date
    knowledge_tier: str
    tce: Decimal
    tce_prior: Decimal | None
    tangible_bvps: Decimal
    shares: Decimal
    net_income: Decimal
    rotce_period_end: Decimal
    rotce_average: Decimal | None
    vendor_roe: Decimal | None
    vendor_roe_definition: str
    payout_ratio: Decimal
    franking_avg_pct: Decimal | None
    last_close: Decimal
    last_close_dt: date
    preferred_present: bool
    minority_present: bool
    intangibles_exceed_goodwill: bool
    gaps: tuple[Gap, ...]


def reconcile_roe_definition(
    vendor_roe: Decimal | None, net_income: Decimal, equity_end: Decimal, equity_avg: Decimal | None
) -> str:
    """Name the definition the vendor field actually uses, or refuse to guess.

    James's ruling: recompute on BOTH period-end and average equity, name which
    one the vendor field is, and block if it matches neither.
    """
    if vendor_roe is None:
        return "vendor_roe_absent"
    with valuation_context():
        tolerance = Decimal("0.0001")
        if abs(vendor_roe - net_income / equity_end) <= tolerance:
            return "period_end"
        if equity_avg is not None and abs(vendor_roe - net_income / equity_avg) <= tolerance:
            return "average"
    return "unknown"
