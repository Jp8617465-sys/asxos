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

#: `fx_rates` was admitted for the universe sweep (F-E2E r2 S1): USD reporters
#: are converted at the AUDUSD rate on or before the cutoff, the same source
#: `jobs/snapshot_portfolio.py` reads. It carries no Model A surface.
_ADMISSIBLE: Final[frozenset[str]] = frozenset(
    {
        "rs_fundamentals_pit",
        "rs_financial_statements",
        "market_context_current",
        "prices",
        "universe",
        "fx_rates",
        # Security master (EODHD active + delisted). Admitted for the V/P replay,
        # whose membership rule must NOT be `universe.is_active`: that is
        # current-only and silently drops every name delisted since the cutoff.
        # It carries security_type and listing dates, and no Model A surface.
        "rs_security_master",
        # The point-in-time risk-free series (migration 0058, issue #301). It
        # replaces `market_context_current` as the source for ke's risk-free
        # leg: both carry the SAME FRED series (see capm.RISK_FREE_LABEL), but
        # market_context_current carries the monthly value forward into daily
        # rows and only began 2026-07-03, so it cannot answer "what was the rate
        # at a 2025 cutoff". It carries no Model A surface.
        "risk_free_rates",
        # The package's own store (migration 0054) — read back by `repository.py`.
        "valuation_runs",
        "valuation_scenario_preregistrations",
    }
)
_FORBIDDEN: Final[tuple[str, ...]] = (
    r"\bsignals\b", r"\bshap_", r"\bprob_up\b", r"\bsignal_label\b", r"\bmodel_a\b",
    r"\bexpected_return\b", r"\bsignal_outcomes\b",
    r"\bfundamentals\b", r"\bdebt_to_equity\b", r"\bnet_debt\b", r"\bgross_margin\b",
    r"\btotal_revenue\b", r"netinterestincome",
)
_FROM_JOIN = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
#: A common-table-expression name declared in the same statement (`name AS (`).
#: Admissible only for that statement — a CTE can only read what its own
#: FROM/JOIN clauses read, and those are screened by the same pass.
_CTE_NAME = re.compile(r"\b([a-z_][a-z0-9_]*)\s+as\s*\(", re.IGNORECASE)


def assert_valuation_sql_admissible(sql: str) -> None:
    lowered = sql.lower()
    for token in _FORBIDDEN:
        if re.search(token, lowered):
            raise AssertionError(f"valuation SQL names a forbidden token: {token}")
    local_ctes = {name.lower() for name in _CTE_NAME.findall(sql)}
    for table in _FROM_JOIN.findall(sql):
        if table.lower() not in _ADMISSIBLE and table.lower() not in local_ctes:
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
#: The risk-free leg of ke, read as a point-in-time series (migration 0058).
#:
#: It used to read `market_context_current`, which carries the SAME FRED series
#: (capm.RISK_FREE_LABEL) but forward-filled into daily rows and only from
#: 2026-07-03 — so it could not answer "what was the rate at a 2025 cutoff", and
#: the sealed V/P replay hard-failed on exactly that. `risk_free_rates` holds the
#: observations as published, with their true `as_of`.
#:
#: Verified equivalent at the switch, not assumed: on 2026-09-16
#: market_context_current's latest value and risk_free_rates' 2026-08-01
#: observation are both 5.015 — the same number, because one is the other
#: carried forward.
SQL_RISK_FREE: Final[str] = (
    "SELECT as_of, yield_pct AS aus_10y_yield FROM risk_free_rates "
    "WHERE series = $2 AND as_of <= $1 ORDER BY as_of DESC LIMIT 1"
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
