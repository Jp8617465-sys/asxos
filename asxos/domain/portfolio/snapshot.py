"""Daily-snapshot valuation arithmetic — pure functions, no I/O.

Extracted 2026-09-18 from `jobs/snapshot_portfolio.py::_compute_holdings_mv`,
where the FX conversion, the market-value accumulation and the FX-component
decomposition of unrealised P&L were interleaved with three `conn.fetch` calls.
That made the portfolio's **headline numbers** — `holdings_mv_aud`,
`us_mv_aud`, `unrealised_fx_pnl_aud`, the columns the brief and every
performance read are built on — untestable without a fake connection, which is
the one thing `.claude/rules/portfolio-conventions.md` says the M13 domain layer
must never be. `asxos/domain/portfolio/monitor.py` + `monitor_loader.py` already
hold the analogous split (pure compute over a typed input, loading in its own
module); this brings the snapshot job onto the same footing. Rationale:
`docs/proposals/hybrid-tdd-assessment-2026-09-17.md` §6 and §7 action 3.

The job still owns every query. It maps rows to the frozen inputs below and
calls these two functions, in this order, because the second query is
conditional on the first result (no foreign holding priced today → no lot
query at all). Keeping that conditional in the job is what makes this
extraction behaviour-preserving rather than merely tidy.

**Decimal context: deliberately the ambient one.** These functions divide
(`close / audusd_rate`, `1 / fx`), so their results depend on context
precision, and every figure they return is persisted to
`portfolio_daily_snapshots`. Wrapping them in a wider local context would
silently shift stored history at the 28th digit. They therefore run under
whatever context the caller has — in practice the interpreter default of 28 —
exactly as the job did before the extraction. Do not add a `localcontext`
here without a migration plan for the values already stored.

**Currency, per risk R10** (`.claude/rules/portfolio-conventions.md`):
`holding_lots.cost_base_normal` is already **AUD** (the CGT cost base,
FX-converted at the lot's acquisition rate), while `prices.close` is
**native**. `ForeignLot` carries both, and the only place they meet is the FX
decomposition below, which converts the native leg explicitly. Never divide
`cost_base_normal` by quantity and compare it to a USD close.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from asxos.domain.prices.fx import is_foreign_symbol

_ZERO = Decimal("0")
_ONE = Decimal("1")

#: NUMERIC(18,6) is the storage type for every monetary column (CLAUDE.md #5),
#: so stored figures quantise to six places. `us_cost_aud` is the documented
#: exception — see `ForeignCostBasis.us_cost_aud`.
_Q6 = Decimal("0.000001")


@dataclass(frozen=True)
class HoldingPrice:
    """One open holding with its close on the snapshot date.

    `close` is in the symbol's **native** currency: AUD for an ASX symbol, USD
    for any of the foreign suffixes `asxos/domain/prices/fx.py` recognises.
    """

    symbol: str
    quantity: Decimal
    close: Decimal


@dataclass(frozen=True)
class ForeignLot:
    """One open foreign lot: AUD cost base, native close, acquisition FX.

    `acquisition_fx_rate` is nullable because migration 0009 added it after
    lots existed; a lot missing it suppresses the FX decomposition rather than
    failing the snapshot (see `compute_foreign_cost_basis`).
    """

    quantity: Decimal
    cost_base_normal: Decimal  # AUD — the CGT cost base, not native (R10)
    acquisition_fx_rate: Decimal | None
    close: Decimal  # native (USD)


@dataclass(frozen=True)
class HoldingsMarketValue:
    """Market value of the held book on one date, all AUD."""

    total_mv_aud: Decimal
    holdings_count: int
    #: AUD market value of the foreign sleeve only; None when nothing foreign
    #: was priced on the date, which is also the signal that no lot query is
    #: needed.
    us_mv_aud: Decimal | None


@dataclass(frozen=True)
class ForeignCostBasis:
    """Cost base and the currency slice of unrealised P&L for the foreign sleeve."""

    #: Sum of AUD cost bases. **Not quantised** — it is a sum of values already
    #: stored at NUMERIC(18,6), so it carries no extra precision to shed, and
    #: the pre-extraction job did not quantise it either.
    us_cost_aud: Decimal | None
    #: The CURRENCY component of unrealised P&L only — today's native market
    #: value revalued at the acquisition rate versus today's rate. NOT total
    #: unrealised P&L, which is `us_mv_aud - us_cost_aud`. None when any lot
    #: lacks an acquisition rate.
    us_fx_pnl_aud: Decimal | None
    #: How many lots lacked `acquisition_fx_rate`. Returned rather than logged:
    #: these functions take no side effects, so the caller owns the warning.
    lots_missing_acquisition_fx: int


def compute_holdings_mv(
    holdings: list[HoldingPrice],
    audusd_rate: Decimal | None,
    as_of: date,
) -> HoldingsMarketValue:
    """Total the held book in AUD, converting foreign closes at `audusd_rate`.

    `audusd_rate` is USD per 1 AUD, so a native USD price becomes AUD by
    DIVIDING by it. It may be None only while nothing foreign is held: a
    foreign holding with no rate raises, because silently valuing a US
    position at its USD number would overstate the book by roughly a third
    (CLAUDE.md #10 — fail loudly, never degrade a capital figure).

    `as_of` is used only to name the date in that error message.
    """
    if not holdings:
        return HoldingsMarketValue(
            total_mv_aud=_ZERO.quantize(_Q6), holdings_count=0, us_mv_aud=None
        )

    total_mv = _ZERO
    us_mv_aud: Decimal | None = None

    for h in holdings:
        if is_foreign_symbol(h.symbol):
            if audusd_rate is None:
                raise RuntimeError(
                    f"No AUDUSD FX rate on or before {as_of} — "
                    "cannot convert US holdings to AUD. Run sync_prices first."
                )
            price_aud = h.close / audusd_rate
            us_mv_aud = (us_mv_aud or _ZERO) + h.quantity * price_aud
        else:
            price_aud = h.close
        total_mv += h.quantity * price_aud

    return HoldingsMarketValue(
        total_mv_aud=total_mv.quantize(_Q6),
        holdings_count=len(holdings),
        us_mv_aud=None if us_mv_aud is None else us_mv_aud.quantize(_Q6),
    )


def compute_foreign_cost_basis(
    lots: list[ForeignLot],
    audusd_rate: Decimal,
) -> ForeignCostBasis:
    """Sum the foreign AUD cost base and decompose the currency slice of P&L.

    Per lot the currency effect is today's native market value revalued at two
    rates: `qty × close × (1/fx_now − 1/fx_acq)`. It is reported only when
    EVERY lot carries an acquisition rate — a partial sum would read as a
    complete one, and this is a display-only analytic column, so a data gap
    suppresses it rather than failing the run.

    `lots` is the set of open foreign lots that also had a price row on the
    date, so cost and market value cover the same lots. Called only when
    `compute_holdings_mv` reported a foreign sleeve, hence `audusd_rate` is
    known non-None here.
    """
    if not lots:
        return ForeignCostBasis(
            us_cost_aud=None, us_fx_pnl_aud=None, lots_missing_acquisition_fx=0
        )

    us_cost_aud = sum((lot.cost_base_normal for lot in lots), _ZERO)
    missing = sum(1 for lot in lots if lot.acquisition_fx_rate is None)

    us_fx_pnl_aud: Decimal | None = None
    if missing == 0:
        us_fx_pnl_aud = sum(
            (
                lot.quantity
                * lot.close
                * (_ONE / audusd_rate - _ONE / lot.acquisition_fx_rate)
                for lot in lots
                if lot.acquisition_fx_rate is not None  # narrowing; missing == 0
            ),
            _ZERO,
        ).quantize(_Q6)

    return ForeignCostBasis(
        us_cost_aud=us_cost_aud,
        us_fx_pnl_aud=us_fx_pnl_aud,
        lots_missing_acquisition_fx=missing,
    )
