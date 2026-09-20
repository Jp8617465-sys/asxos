"""One universe row → one `ValuationRun`. Pure; no I/O.

Reproduces the `grid`/`rec`/`agg` CTEs of `scripts/research/baseline_inquiry.sql`
(REPORT B is the acceptance test): three pre-registered ROE scenarios at three
Ke points under the registered `zero_excess` convention, plus the three
sensitivities (average ROE, fading excess w = 0.5, unadjusted franking). A row
that cannot be valued becomes a `blocked` run naming every gap — the gate the
Phase 1 lesson demanded ("a gap collected is not a gate").
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Final, TypedDict

from asxos.domain.decision_engine.types import DataMode
from asxos.domain.valuation import capm
from asxos.domain.valuation.absence import is_missing
from asxos.domain.valuation.contracts import (
    FrankingConvention,
    GapRecord,
    KeBand,
    RegisteredTerminalConvention,
    ReturnBase,
    ScenarioPreregistration,
    ScenarioValue,
    Sensitivities,
    ValuationInputs,
    ValuationMethod,
    ValuationRun,
)
from asxos.domain.valuation.gaps import Gap
from asxos.domain.valuation.numeric import q6, valuation_context
from asxos.domain.valuation.residual_income import value_per_share
from asxos.domain.valuation.universe import MarketInputs, UniverseRow

FADING_EXCESS_PERSISTENCE: Final[Decimal] = Decimal("0.5")

#: The currencies convertible with NO rate lookup. AUD needs none; USD is the
#: one pair `MarketInputs` requires, so both are convertible whenever a sweep
#: can run at all.
#:
#: Every OTHER currency is convertible exactly when `fx_rates` carries an
#: AUD-base pair for it at the cutoff — asked of `MarketInputs.is_convertible`,
#: never of a list. The static `frozenset({"AUD", "USD"})` this replaces was a
#: second place the truth lived: widen the ingestion and the frozenset still
#: blocks; stop ingesting a pair and the frozenset still values, on whatever
#: stale rate remained. A predicate over the data cannot drift from the data.
BASE_CONVERTIBLE_CURRENCIES: Final[frozenset[str]] = frozenset({"AUD", "USD"})
FLAG_CURRENCY_UNVERIFIED: Final[str] = "currency_unverified"
FLAG_PAYOUT_CLIPPED: Final[str] = "payout_clipped"
FLAG_ROE_AVERAGE_SHORT: Final[str] = "roe_average_fewer_periods"


class _RunBase(TypedDict):
    """The provenance fields every run carries, valued or blocked."""

    run_id: str
    symbol: str
    as_of: date
    knowledge_cutoff: datetime
    created_at: datetime
    method: ValuationMethod
    terminal_convention: RegisteredTerminalConvention
    franking_convention: FrankingConvention
    return_base: ReturnBase
    horizon_years: int
    data_mode: DataMode
    preregistration_id: str
    ke: KeBand


def run_id_for(symbol: str, as_of: datetime, convention: str) -> str:
    return f"vr-{symbol}-{as_of.date().isoformat()}-{convention}"


def ke_band_for(market: MarketInputs, prereg: ScenarioPreregistration) -> KeBand:
    treatment = prereg.ke_treatment
    low, mid, high = capm.ke_band(risk_free=market.risk_free, erp=treatment.erp)
    return KeBand(
        risk_free=market.risk_free,
        risk_free_as_of=market.risk_free_as_of,
        risk_free_series=capm.RISK_FREE_SERIES,
        erp=treatment.erp,
        beta_low=treatment.beta_low,
        beta_mid=treatment.beta_mid,
        beta_high=treatment.beta_high,
        beta_provenance=treatment.beta_provenance,
        ke_low=low,
        ke_mid=mid,
        ke_high=high,
    )


def _gaps_for(row: UniverseRow, market: MarketInputs | None = None) -> tuple[Gap, ...]:
    """Every reason this row cannot be valued, in the baseline's status order.

    `market` supplies the cutoff's FX map so convertibility is judged against
    the rates that actually exist. It defaults to None for the callers that only
    want the fundamental gaps; with None, convertibility falls back to the two
    currencies that need no lookup (AUD, USD).
    """
    gaps: list[Gap] = []
    if row.pit_as_of is None:
        gaps.append(
            Gap(
                "pit_row_absent",
                "no rs_fundamentals_pit row with knowledge_date at or before the cutoff",
                table="rs_fundamentals_pit",
            )
        )
        # Without a PIT row the remaining fundamental checks are the same absence.
    else:
        if row.book_value_ps is None or row.book_value_ps <= 0:
            gaps.append(
                Gap(
                    "book_value_non_positive",
                    "residual income needs positive opening book per share",
                    table="rs_fundamentals_pit",
                    column="book_value_ps",
                    observed=str(row.book_value_ps),
                    required="> 0",
                )
            )
        if row.roe is None:
            gaps.append(
                Gap(
                    "roe_null",
                    "no trailing ROE on the point-in-time row",
                    table="rs_fundamentals_pit",
                    column="roe",
                )
            )
        elif row.roe <= 0:
            gaps.append(
                Gap(
                    "roe_non_positive",
                    "loss-making on trailing twelve months — no residual-income basis",
                    table="rs_fundamentals_pit",
                    column="roe",
                    observed=str(row.roe),
                    required="> 0",
                )
            )
        currency = None if is_missing(row.currency) else str(row.currency).strip().upper()
        convertible = (
            currency in BASE_CONVERTIBLE_CURRENCIES
            if market is None
            else market.is_convertible(currency)
        )
        if currency is not None and not convertible:
            # `required` names what would actually unblock this row rather than
            # the old fixed "AUD or USD": the answer now depends on which pairs
            # the cutoff carries, so a reader of a blocked run can tell the
            # difference between "we do not convert this currency" and "we do,
            # but not at this date".
            gaps.append(
                Gap(
                    "currency_unconvertible",
                    "reports in a currency with no FX rate at the cutoff",
                    table="rs_fundamentals_pit",
                    column="currency",
                    observed=currency,
                    required=f"an AUD{currency} rate in fx_rates at or before the cutoff",
                )
            )
    if row.last_close is None or row.last_close_dt is None:
        gaps.append(
            Gap(
                "price_absent",
                "no close inside the pre-registered price window before the cutoff",
                table="prices",
                column="close",
            )
        )
    elif row.last_close <= 0:
        gaps.append(
            Gap(
                "price_absent",
                "last close is not positive",
                table="prices",
                column="close",
                observed=str(row.last_close),
                required="> 0",
            )
        )
    return tuple(gaps)


def _payout(row: UniverseRow) -> tuple[Decimal, bool]:
    """dividend_ttm / eps_ttm clipped to [0, 1]; 0 when EPS <= 0 or no dividend."""
    if row.eps_ttm is None or row.eps_ttm <= 0 or row.dividend_ttm is None:
        return Decimal("0"), False
    with valuation_context():
        raw = row.dividend_ttm / row.eps_ttm
    if raw > 1:
        return Decimal("1"), True
    if raw < 0:
        return Decimal("0"), True
    return raw, False


def _weighted(values: list[tuple[Decimal, Decimal]]) -> Decimal:
    with valuation_context():
        return q6(sum((prob * value for prob, value in values), Decimal("0")))


def value_row(
    row: UniverseRow,
    *,
    market: MarketInputs,
    ke: KeBand,
    prereg: ScenarioPreregistration,
    cutoff: datetime,
    created_at: datetime,
    data_mode: DataMode = "real",
) -> ValuationRun:
    """Value one name under the registration, or record why it could not be."""
    base = _RunBase(
        run_id=run_id_for(row.symbol, cutoff, prereg.terminal_convention),
        symbol=row.symbol,
        as_of=cutoff.date(),
        knowledge_cutoff=cutoff,
        created_at=created_at,
        method=prereg.method,
        terminal_convention=prereg.terminal_convention,
        franking_convention=prereg.franking_convention,
        return_base=prereg.return_base,
        horizon_years=prereg.horizon_years,
        data_mode=data_mode,
        preregistration_id=prereg.preregistration_id,
        ke=ke,
    )
    gaps = _gaps_for(row, market)
    if gaps:
        return ValuationRun(
            **base,
            outcome="blocked",
            gaps=tuple(GapRecord.model_validate(g.as_dict()) for g in gaps),
        )

    # Narrowing for the type checker: `_gaps_for` proved each of these present.
    assert row.pit_as_of is not None and row.pit_knowledge_date is not None
    assert row.book_value_ps is not None and row.roe is not None
    assert row.last_close is not None and row.last_close_dt is not None

    flags: list[str] = []
    currency_verified = not is_missing(row.currency)
    currency = str(row.currency).strip().upper() if currency_verified else None
    if not currency_verified:
        flags.append(FLAG_CURRENCY_UNVERIFIED)
    fx_audusd: Decimal | None = None
    fx_as_of = None
    fx_pair: str | None = None
    fx_rate: Decimal | None = None
    with valuation_context():
        quoted = market.fx_for(currency)
        if quoted is None:
            # AUD, or an unverified currency the gaps already let through.
            book_aud = row.book_value_ps
            dividend_aud = row.dividend_ttm
        else:
            fx_rate, fx_as_of = quoted
            fx_pair = f"AUD{currency}"
            # `rate` is the currency's units per one AUD, so native / rate = AUD.
            book_aud = row.book_value_ps / fx_rate
            dividend_aud = None if row.dividend_ttm is None else row.dividend_ttm / fx_rate
            # `fx_audusd` keeps its exact original meaning — the AUDUSD rate,
            # populated only for USD reporters. `valuation_runs.payload` is
            # content-addressed and append-only (0054), so the field is widened
            # BESIDE rather than renamed: every stored USD row keeps its shape,
            # and no consumer reading `fx_audusd` starts silently receiving a
            # NZD rate under a name that says otherwise.
            if currency == "USD":
                fx_audusd = fx_rate
    payout, clipped = _payout(row)
    if clipped:
        flags.append(FLAG_PAYOUT_CLIPPED)
    franking = Decimal("0") if row.franking_avg_pct is None else row.franking_avg_pct
    roe_average = row.roe_average
    roe_periods = max(row.roe_periods, 1)
    if roe_average is not None and roe_periods < prereg.input_rules.roe_average_periods:
        flags.append(FLAG_ROE_AVERAGE_SHORT)

    inputs = ValuationInputs(
        pit_as_of=row.pit_as_of,
        pit_knowledge_date=row.pit_knowledge_date,
        reporting_currency=currency,
        currency_verified=currency_verified,
        fx_audusd=fx_audusd,
        fx_as_of=fx_as_of,
        fx_pair=fx_pair,
        fx_rate=fx_rate,
        book_value_ps_native=row.book_value_ps,
        book_value_ps_aud=q6(book_aud),
        roe_trailing=row.roe,
        roe_average=roe_average,
        roe_periods=roe_periods,
        eps_ttm=row.eps_ttm,
        dividend_ttm_native=row.dividend_ttm,
        dividend_ttm_aud=None if dividend_aud is None else q6(dividend_aud),
        payout_ratio=q6(payout),
        payout_clipped=clipped,
        franking_pct=franking,
        last_close=row.last_close,
        last_close_dt=row.last_close_dt,
    )

    def registered(roe_start: Decimal, ke_point: Decimal, *, franking_pct: Decimal | None) -> Decimal:
        value, _, _ = value_per_share(
            book_start=book_aud,
            roe_start=roe_start,
            ke=ke_point,
            payout_ratio=payout,
            horizon_years=prereg.horizon_years,
            franking_pct=franking_pct,
        )
        return value

    scenarios: list[ScenarioValue] = []
    for lever in prereg.levers:
        with valuation_context():
            prob = lever.probability_pct / Decimal("100")
            roe_start = row.roe * lever.roe_factor
        scenarios.append(
            ScenarioValue(
                label=lever.label,
                probability=prob,
                roe_factor=lever.roe_factor,
                roe_start=q6(roe_start),
                value_ke_low=registered(roe_start, ke.ke_low, franking_pct=franking),
                value_ke_mid=registered(roe_start, ke.ke_mid, franking_pct=franking),
                value_ke_high=registered(roe_start, ke.ke_high, franking_pct=franking),
            )
        )
    pw_mid = _weighted([(s.probability, s.value_ke_mid) for s in scenarios])
    pw_low = _weighted([(s.probability, s.value_ke_low) for s in scenarios])
    pw_high = _weighted([(s.probability, s.value_ke_high) for s in scenarios])

    fading: list[tuple[Decimal, Decimal]] = []
    unadjusted: list[tuple[Decimal, Decimal]] = []
    for lever, scenario in zip(prereg.levers, scenarios, strict=True):
        with valuation_context():
            roe_start = row.roe * lever.roe_factor
        faded, _, _ = value_per_share(
            book_start=book_aud,
            roe_start=roe_start,
            ke=ke.ke_mid,
            payout_ratio=payout,
            horizon_years=prereg.horizon_years,
            franking_pct=franking,
            persistence=FADING_EXCESS_PERSISTENCE,
        )
        fading.append((scenario.probability, faded))
        unadjusted.append((scenario.probability, registered(roe_start, ke.ke_mid, franking_pct=None)))
    average_value = None if roe_average is None else registered(roe_average, ke.ke_mid, franking_pct=franking)

    with valuation_context():
        value_to_price = q6(pw_mid / row.last_close)
    return ValuationRun(
        **base,
        outcome="valued",
        value_per_share=pw_mid,
        value_ke_low=pw_low,
        value_ke_high=pw_high,
        value_to_price=value_to_price,
        inputs=inputs,
        scenarios=tuple(scenarios),
        sensitivities=Sensitivities(
            fading_excess_w050_ke_mid=_weighted(fading),
            average_roe_ke_mid=average_value,
            average_roe_start=None if roe_average is None else q6(roe_average),
            unadjusted_franking_ke_mid=_weighted(unadjusted),
        ),
        flags=tuple(flags),
    )
