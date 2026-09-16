"""Named gaps. A missing primary input blocks the run and says which one.

The rule this encodes (James, 2026-09-08): derive only definitional identities
from primary point-in-time fields in the same period; block with the named gap
when a primary field is NULL; never widen a band to cover an unknown.
"""
from __future__ import annotations

from typing import Final, Literal

NamedGap = Literal[
    # --- inputs absent -------------------------------------------------------
    "pit_row_absent",
    "prior_period_equity_absent",
    "statement_row_absent",
    "net_income_null",
    "shares_outstanding_null_or_zero",
    "goodwill_null",
    "intangibles_null",
    "total_stockholder_equity_null",
    "risk_free_absent",
    "price_absent",
    # --- inputs present but unusable ----------------------------------------
    "tce_non_positive",
    "period_misaligned",
    "pit_row_estimated_tier",
    "currency_null",
    "currency_not_aud",
    # --- universe sweep (F-E2E r2 S1, reported-book base) --------------------
    "book_value_non_positive",
    "roe_null",
    "roe_non_positive",
    "currency_unconvertible",
    "payout_ratio_underivable",
    "roe_definition_unknown",
    "price_stale",
    "risk_free_stale",
    # --- measurement impossible ---------------------------------------------
    "beta_window_insufficient",
    "market_index_absent",
    "price_series_discontinuity",
]

#: Gaps that describe a measurement we cannot make, as opposed to data we lack.
MEASUREMENT_GAPS: Final[frozenset[str]] = frozenset(
    {"beta_window_insufficient", "market_index_absent", "price_series_discontinuity"}
)


class ValuationBlocked(RuntimeError):
    """The run cannot produce a value. Carries EVERY gap, not just the first.

    Collecting them matters: a caller fixing one input at a time would otherwise
    need one run per gap to discover what else is missing.
    """

    def __init__(self, gaps: tuple[Gap, ...]) -> None:
        if not gaps:
            raise ValueError("ValuationBlocked requires at least one gap")
        self.gaps = gaps
        named = ", ".join(g.name for g in gaps)
        super().__init__(f"valuation blocked: {named}")


class Gap:
    """One named, evidenced reason a valuation did not produce a number."""

    __slots__ = ("column", "detail", "name", "observed", "required", "table")

    def __init__(
        self,
        name: NamedGap,
        detail: str,
        *,
        table: str | None = None,
        column: str | None = None,
        observed: str | None = None,
        required: str | None = None,
    ) -> None:
        if not detail.strip():
            raise ValueError(f"gap {name!r} needs a detail")
        self.name = name
        self.detail = detail
        self.table = table
        self.column = column
        self.observed = observed
        self.required = required

    def as_dict(self) -> dict[str, str | None]:
        return {
            "name": self.name,
            "detail": self.detail,
            "table": self.table,
            "column": self.column,
            "observed": self.observed,
            "required": self.required,
        }

    def __repr__(self) -> str:
        return f"Gap({self.name!r}, observed={self.observed!r}, required={self.required!r})"
