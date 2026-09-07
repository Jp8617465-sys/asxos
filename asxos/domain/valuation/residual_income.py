"""Residual income on tangible common equity. Pure functions, no I/O.

    V = B0 + SUM_{t=1..H} (ROE_t - Ke) * B_{t-1} / (1 + Ke)^t

with ROE fading linearly to Ke over H years and terminal value = book.  There is
no continuing-value term in this module — not one set to zero, absent.  Under
clean surplus the discounted-book terminal is already inside the sum above, so
adding a separate terminal discount would double-count.

Ruled by James, 2026-09-08 and recorded in the scenario pre-registration: if this
values a name below its market price, no horizon extension, no growth term and no
terminal excess return may be added to close the gap.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Final

from asxos.domain.valuation.numeric import compound, q6, valuation_context

#: Australian company tax rate used only to gross up franking credits.
COMPANY_TAX_RATE: Final[Decimal] = Decimal("0.30")

#: credit per $1 of fully franked dividend = Tc / (1 - Tc) = 0.30/0.70.
#: Same constant, same derivation, as asxos/domain/research/factor_scores.py.
FRANKING_GROSS_UP: Final[Decimal] = COMPANY_TAX_RATE / (Decimal("1") - COMPANY_TAX_RATE)

DEFAULT_HORIZON_YEARS: Final[int] = 10


def fade_path(roe_start: Decimal, ke: Decimal, horizon_years: int) -> tuple[Decimal, ...]:
    """ROE fading linearly from `roe_start` to exactly `ke` over `horizon_years`.

    The terminal element IS `ke`, by construction rather than by convergence, so
    the excess return is exactly zero in the final year and the terminal value is
    exactly book.
    """
    if horizon_years < 1:
        raise ValueError("horizon_years must be >= 1")
    with valuation_context():
        span = Decimal(horizon_years)
        return tuple(
            roe_start + (ke - roe_start) * Decimal(t) / span
            for t in range(1, horizon_years + 1)
        )


def book_path(
    book_start: Decimal, roe_by_year: tuple[Decimal, ...], payout_ratio: Decimal
) -> tuple[Decimal, ...]:
    """Clean-surplus book roll-forward: B_t = B_{t-1} * (1 + ROE_t * (1 - payout))."""
    if book_start <= 0:
        raise ValueError("book_start must be positive")
    with valuation_context():
        retained = Decimal("1") - payout_ratio
        out: list[Decimal] = []
        book = book_start
        for roe in roe_by_year:
            book = book * (Decimal("1") + roe * retained)
            out.append(book)
        return tuple(out)


def residual_income_series(
    book_start: Decimal, roe_by_year: tuple[Decimal, ...], book_by_year: tuple[Decimal, ...], ke: Decimal
) -> tuple[Decimal, ...]:
    """RI_t = (ROE_t - Ke) * B_{t-1}. Opening book for year 1 is `book_start`."""
    with valuation_context():
        opening = (book_start, *book_by_year[:-1])
        return tuple((roe - ke) * b for roe, b in zip(roe_by_year, opening, strict=True))


def present_value(flows: tuple[Decimal, ...], ke: Decimal) -> Decimal:
    """Discount a 1-indexed annual series at `ke`."""
    with valuation_context():
        rate = Decimal("1") + ke
        return sum(
            (flow / compound(rate, t) for t, flow in enumerate(flows, start=1)),
            Decimal("0"),
        )


def dividend_series(
    book_start: Decimal, roe_by_year: tuple[Decimal, ...], book_by_year: tuple[Decimal, ...], payout_ratio: Decimal
) -> tuple[Decimal, ...]:
    """DPS_t = ROE_t * B_{t-1} * payout — the distributed part of each year's earnings."""
    with valuation_context():
        opening = (book_start, *book_by_year[:-1])
        return tuple(roe * b * payout_ratio for roe, b in zip(roe_by_year, opening, strict=True))


def franking_credit_pv(
    dividends: tuple[Decimal, ...], franking_pct: Decimal, ke: Decimal
) -> Decimal:
    """PV of franking credits attaching to the dividend stream.

    credit_t = DPS_t * (franking_pct/100) * Tc/(1-Tc)

    This needs no franking ACCOUNT BALANCE: `franking_pct` is an assumption input
    cited to the company's dividend disclosure, not a derived capacity, and it is
    run at both 0% and 100% as a sensitivity.  Value to an Australian resident
    holder; worth nothing to a non-resident, which is why the convention has to be
    stated rather than defaulted.
    """
    with valuation_context():
        rate = franking_pct / Decimal("100") * FRANKING_GROSS_UP
        return present_value(tuple(d * rate for d in dividends), ke)


def value_per_share(
    *,
    book_start: Decimal,
    roe_start: Decimal,
    ke: Decimal,
    payout_ratio: Decimal,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    franking_pct: Decimal | None = None,
) -> tuple[Decimal, tuple[Decimal, ...], tuple[Decimal, ...]]:
    """Return (value_per_share, roe_by_year, book_by_year).

    `franking_pct=None` is the unadjusted convention; a value grosses the
    dividend stream up for an Australian resident holder.
    """
    with valuation_context():
        roe_by_year = fade_path(roe_start, ke, horizon_years)
        book_by_year = book_path(book_start, roe_by_year, payout_ratio)
        ri = residual_income_series(book_start, roe_by_year, book_by_year, ke)
        value = book_start + present_value(ri, ke)
        if franking_pct is not None:
            dividends = dividend_series(book_start, roe_by_year, book_by_year, payout_ratio)
            value += franking_credit_pv(dividends, franking_pct, ke)
        return q6(value), roe_by_year, book_by_year
