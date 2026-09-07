"""Cost of equity. Ke is a RANGE, because beta is not measurable here.

`AXJO.INDX` holds 72 price rows from 2026-05-27 — 71 daily return pairs against a
250-session floor.  Beta therefore BLOCKS (gaps.beta_window_insufficient), and
under James's ruling of 2026-09-08 Ke is carried as a stated range over an
assumed beta band with its sources cited, never as a measured point.  When the
AXJO backfill (backlog E-19) lands, beta is measured and the run is re-run.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Final

from asxos.domain.valuation.numeric import q6, valuation_context

#: One trading year of overlapping observations, the floor for a usable beta.
MIN_BETA_SESSIONS: Final[int] = 250

#: The stated beta band. NOT measured — see the module docstring.
BETA_LOW: Final[Decimal] = Decimal("0.90")
BETA_HIGH: Final[Decimal] = Decimal("1.20")

#: Equity risk premium. James's ruling constrains this to [5%, 6%].
ERP_MIN: Final[Decimal] = Decimal("0.05")
ERP_MAX: Final[Decimal] = Decimal("0.06")

#: What market_context.aus_10y_yield ACTUALLY is. Never label it "10-year ACGB".
RISK_FREE_SERIES: Final[str] = "FRED IRLTLT01AUM156N"
RISK_FREE_LABEL: Final[str] = (
    "OECD/FRED monthly long-term (10-year) government bond yield for Australia, "
    "series IRLTLT01AUM156N — a MONTHLY series carried forward, not a daily "
    "10-year ACGB quote"
)


def cost_of_equity(*, risk_free: Decimal, beta: Decimal, erp: Decimal) -> Decimal:
    """Ke = rf + beta * ERP. No size premium, no country premium, no fudge."""
    if not ERP_MIN <= erp <= ERP_MAX:
        raise ValueError(f"erp {erp} outside the ruled range [{ERP_MIN}, {ERP_MAX}]")
    if beta < 0:
        raise ValueError("beta must be non-negative")
    with valuation_context():
        return q6(risk_free + beta * erp)


def ke_band(*, risk_free: Decimal, erp: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """(ke_low, ke_mid, ke_high) over the stated beta band."""
    with valuation_context():
        beta_mid = (BETA_LOW + BETA_HIGH) / Decimal("2")
        return (
            cost_of_equity(risk_free=risk_free, beta=BETA_LOW, erp=erp),
            cost_of_equity(risk_free=risk_free, beta=beta_mid, erp=erp),
            cost_of_equity(risk_free=risk_free, beta=BETA_HIGH, erp=erp),
        )


def ke_sensitivity(ke_mid: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """The ruled -1% / 0 / +1% table around a Ke."""
    with valuation_context():
        one_pct = Decimal("0.01")
        return (q6(ke_mid - one_pct), q6(ke_mid), q6(ke_mid + one_pct))
