"""The deterministic ranker. Pure; no I/O; no LLM.

Inputs: the latest `ValuationRun` per name (S1) and the liquidity screen's
matches (ADV, market cap). Output: `Opportunity` rows in rank order.

Gates, in order (each one is stated so the excluded set is explainable):
  1. the run is `valued` and passed the liquidity screen;
  2. `currency_unverified` names are NOT proposed — a value read in the wrong
     currency is the exact class of error the HUBS incident was
     (portfolio-conventions, cost_base_normal note); they still rank for the
     brief's list, flagged, but never become a thesis;
  3. quality: the 3-period-AVERAGE ROE exceeds Ke mid (trailing ROE falls
     back when no average exists, flagged) — the baseline's answer to
     peak-cycle trailing ROE (Metro Mining 94x on trailing, 0.92x on average);
  4. value: value >= price under BOTH the registered convention and the
     average-ROE sensitivity (the baseline's "robust set", REPORT D).

Rank: score = min(value/price registered, value/price average-ROE)
              x liquidity_factor, liquidity_factor = min(1, ADV / A$1m).
The factor discounts thin names proportionally below A$1m of daily value and
is neutral above it, so a liquid name ranks on value alone. Deterministic
tie-break on symbol.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from asxos.domain.discovery.types import Opportunity, ThesisPlan
from asxos.domain.valuation.contracts import ValuationRun
from asxos.domain.valuation.sweep import FLAG_CURRENCY_UNVERIFIED

_Q6: Final[Decimal] = Decimal("0.000001")

#: Baseline §5 conventions — James can change them (sprint S4).
ENTRY_UPPER_OF_TARGET: Final[Decimal] = Decimal("0.80")
ENTRY_LOWER_OF_TARGET: Final[Decimal] = Decimal("0.65")
STOP_OF_ENTRY_UPPER: Final[Decimal] = Decimal("0.80")
TIMELINE_DAYS: Final[int] = 365
#: The liquidity screen (baseline §4): ADV >= A$250k, market cap >= A$100m.
MIN_ADV_AUD: Final[Decimal] = Decimal("250000")
MIN_MARKET_CAP_AUD: Final[Decimal] = Decimal("100000000")
#: Above this daily value the liquidity factor is 1 (neutral).
LIQUIDITY_NEUTRAL_ADV_AUD: Final[Decimal] = Decimal("1000000")

FLAG_ROE_AVERAGE_FALLBACK: Final[str] = "roe_average_fallback_to_trailing"


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


def plan_for(target: Decimal, last_close: Decimal) -> ThesisPlan:
    """Entry band, stop and horizon from the registered value, by convention."""
    upper = _q(target * ENTRY_UPPER_OF_TARGET)
    lower = _q(target * ENTRY_LOWER_OF_TARGET)
    stop = _q(upper * STOP_OF_ENTRY_UPPER)
    return ThesisPlan(
        target_price=_q(target),
        entry_band_lower=lower,
        entry_band_upper=upper,
        stop_price=stop,
        timeline_days=TIMELINE_DAYS,
        close_inside_band=lower <= last_close <= upper,
    )


def liquidity_factor(adv_aud: Decimal) -> Decimal:
    if adv_aud <= 0:
        return Decimal("0")
    return _q(min(Decimal("1"), adv_aud / LIQUIDITY_NEUTRAL_ADV_AUD))


class Screened:
    """A name that passed the liquidity screen, with the figures it passed on."""

    __slots__ = ("adv_aud", "market_cap_aud", "symbol")

    def __init__(self, symbol: str, *, adv_aud: Decimal, market_cap_aud: Decimal) -> None:
        self.symbol = symbol
        self.adv_aud = adv_aud
        self.market_cap_aud = market_cap_aud


def rank(
    runs: Iterable[ValuationRun],
    screened: Mapping[str, Screened],
    *,
    screening_run_id: int,
    include_currency_unverified: bool = False,
) -> list[Opportunity]:
    """Every name that passes the four gates, best score first."""
    out: list[Opportunity] = []
    for run in runs:
        if run.outcome != "valued" or run.inputs is None or run.sensitivities is None:
            continue
        hit = screened.get(run.symbol)
        if hit is None:
            continue
        if hit.adv_aud < MIN_ADV_AUD or hit.market_cap_aud < MIN_MARKET_CAP_AUD:
            continue
        flags = list(run.flags)
        if FLAG_CURRENCY_UNVERIFIED in flags and not include_currency_unverified:
            continue
        roe_average = run.inputs.roe_average
        fallback = roe_average is None
        if roe_average is None:
            roe_average = run.inputs.roe_trailing
            flags.append(FLAG_ROE_AVERAGE_FALLBACK)
        if roe_average <= run.ke.ke_mid:
            continue
        value_avg = run.sensitivities.average_roe_ke_mid
        if value_avg is None:
            value_avg = run.value_per_share  # no average: the sensitivity equals the registered value
        assert run.value_per_share is not None and value_avg is not None
        close = run.inputs.last_close
        vp_registered = _q(run.value_per_share / close)
        vp_average = _q(value_avg / close)
        if vp_registered < 1 or vp_average < 1:
            continue
        vp_min = min(vp_registered, vp_average)
        factor = liquidity_factor(hit.adv_aud)
        out.append(
            Opportunity(
                symbol=run.symbol,
                run_id=run.run_id,
                run_content_hash=run.content_hash,
                as_of=run.as_of,
                last_close=close,
                last_close_dt=run.inputs.last_close_dt,
                value_registered=run.value_per_share,
                value_average_roe=value_avg,
                value_to_price_registered=vp_registered,
                value_to_price_average_roe=vp_average,
                value_to_price_min=vp_min,
                roe_trailing=run.inputs.roe_trailing,
                roe_average=roe_average,
                roe_average_is_fallback=fallback,
                ke_mid=run.ke.ke_mid,
                adv_aud=hit.adv_aud,
                market_cap_aud=hit.market_cap_aud,
                liquidity_factor=factor,
                score=_q(vp_min * factor),
                flags=tuple(flags),
                plan=plan_for(run.value_per_share, close),
                screening_run_id=screening_run_id,
            )
        )
    out.sort(key=lambda o: (-o.score, o.symbol))
    return out


def thesis_text_for(o: Opportunity) -> str:
    """Template-only prose over the numbers (the G10 defence): nothing free-form."""
    return (
        f"System screen (residual income, {o.as_of.isoformat()}): {o.symbol} is valued at "
        f"{o.value_registered} per share under the registered zero-excess convention "
        f"({o.value_to_price_registered}x the last close of {o.last_close}) and at "
        f"{o.value_average_roe} on the 3-period-average ROE ({o.value_to_price_average_roe}x). "
        f"Average ROE {o.roe_average} exceeds Ke {o.ke_mid}; 90-day ADV A${o.adv_aud:.0f}, "
        f"market cap A${o.market_cap_aud:.0f}. Proposed by jobs/discover_opportunities.py from "
        f"valuation run {o.run_id} — not a recommendation; a human approval is required."
    )


def invalidation_conditions_for(o: Opportunity) -> list[dict[str, str]]:
    """Measurable conditions (each carries a number) the challenger can read."""
    return [
        {
            "condition": f"3-period average ROE falls below Ke mid {o.ke_mid}",
            "status": "open",
        },
        {
            "condition": f"model value at Ke mid falls below the entry band upper {o.plan.entry_band_upper}",
            "status": "open",
        },
        {
            "condition": f"90-day ADV falls below A${MIN_ADV_AUD:.0f}",
            "status": "open",
        },
    ]
