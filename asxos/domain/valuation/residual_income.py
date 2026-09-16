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
from typing import Final, Literal

from asxos.domain.valuation.numeric import compound, q6, valuation_context

#: Australian company tax rate used only to gross up franking credits.
COMPANY_TAX_RATE: Final[Decimal] = Decimal("0.30")



def _franking_gross_up() -> Decimal:
    """Tc / (1 - Tc) under the package's OWN context, not the import-time global one.

    `asxos/domain/portfolio/monitor.py` sets the process-global precision to 40
    at import, so a division evaluated at module import took whichever precision
    happened to be ambient in that import order — 28 or 40 digits — and the
    constant differed between test orders (found 2026-09-16 by the S2 suite).
    """
    with valuation_context():
        return COMPANY_TAX_RATE / (Decimal("1") - COMPANY_TAX_RATE)


#: credit per $1 of fully franked dividend = Tc / (1 - Tc) = 0.30/0.70.
#: Same constant, same derivation, as asxos/domain/research/factor_scores.py.
FRANKING_GROSS_UP: Final[Decimal] = _franking_gross_up()

DEFAULT_HORIZON_YEARS: Final[int] = 10

#: The two terminal-value conventions. Both are ALWAYS run; neither replaces the
#: other (ADR: migration 0054's discriminator exists for exactly this comparison).
#:
#: `zero_excess`   ROE fades to exactly Ke; terminal value = book; no excess
#:                 return survives the horizon. The conservative convention.
#: `fading_excess` A declared fraction of the initial excess return survives to
#:                 the horizon and then decays at that same rate forever
#:                 (Ohlson persistence). At persistence = 0 this reduces EXACTLY
#:                 to `zero_excess` — proven by test, not asserted — so the
#:                 second convention is a strict generalisation of the first and
#:                 the pair cannot silently disagree at the boundary.
TerminalConvention = Literal["zero_excess", "fading_excess"]

#: The base the return and the book must SHARE. If book is tangible common
#: equity the return input is ROTE, never reported-book ROE. Mixing them is worth
#: roughly 1.9x vs 2.35x book on a major bank — most of the spread in any sizing
#: estimate — and it is an error a model carries silently, so the base is a
#: required field on the contract rather than a convention in a docstring.
ReturnBase = Literal["tangible_common_equity", "reported_book_equity"]


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


def terminal_value(
    *, final_residual_income: Decimal, ke: Decimal, persistence: Decimal
) -> Decimal:
    """Continuing value of the residual-income stream beyond the horizon.

        CV = RI_H * w / (1 + Ke - w)      (Ohlson persistence)

    At `persistence = 0` this is exactly zero, which is what makes terminal value
    equal book under `zero_excess`.
    """
    if not (Decimal("0") <= persistence < Decimal("1")):
        raise ValueError("persistence must be in [0, 1)")
    with valuation_context():
        if persistence == 0:
            return Decimal("0")
        return final_residual_income * persistence / (Decimal("1") + ke - persistence)


def value_per_share(
    *,
    book_start: Decimal,
    roe_start: Decimal,
    ke: Decimal,
    payout_ratio: Decimal,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    franking_pct: Decimal | None = None,
    persistence: Decimal = Decimal("0"),
) -> tuple[Decimal, tuple[Decimal, ...], tuple[Decimal, ...]]:
    """Return (value_per_share, roe_by_year, book_by_year).

    `franking_pct=None` is the unadjusted convention; a value grosses the
    dividend stream up for an Australian resident holder.

    `persistence` (w) selects the terminal convention. w = 0 is `zero_excess`:
    ROE fades to exactly Ke and terminal value is book. w > 0 is `fading_excess`:
    ROE fades only to `Ke + w * (roe_start - Ke)`, and that surviving excess then
    decays at w forever. The single parameter governs both the fade endpoint and
    the post-horizon decay, so the conventions cannot drift apart.
    """
    if not (Decimal("0") <= persistence < Decimal("1")):
        raise ValueError("persistence must be in [0, 1)")
    with valuation_context():
        terminal_roe = ke + persistence * (roe_start - ke)
        roe_by_year = fade_path(roe_start, terminal_roe, horizon_years)
        book_by_year = book_path(book_start, roe_by_year, payout_ratio)
        ri = residual_income_series(book_start, roe_by_year, book_by_year, ke)
        value = book_start + present_value(ri, ke)
        cv = terminal_value(final_residual_income=ri[-1], ke=ke, persistence=persistence)
        if cv:
            value += cv / compound(Decimal("1") + ke, horizon_years)
        if franking_pct is not None:
            dividends = dividend_series(book_start, roe_by_year, book_by_year, payout_ratio)
            value += franking_credit_pv(dividends, franking_pct, ke)
        return q6(value), roe_by_year, book_by_year
