"""The value screen. Pure; no I/O; no LLM. It does not rank (#306).

Demoted 2026-09-16. The sealed value-to-price test returned `null` (#304) and
the pre-committed response (`research/registry/vp.py::RESPONSE_RULE`, ruled by
James before any result existed) demotes the residual-income model to a
discipline device: it "stops emitting target prices, entry bands and ranked
'opportunities'". So this module no longer derives a target, an entry band or
a stop from the model value (the three constants and `plan_for` are gone), no
longer scores or orders names by value (the liquidity factor and `rank` are
gone), and no longer writes thesis prose. What remains is the record: which
names pass four stated gates, every figure they passed on, in symbol order.

Inputs: the latest `ValuationRun` per name (S1) and the liquidity screen's
matches (ADV, market cap). Output: the passing set, symbol-ordered.

Gates, in order (each one is stated so the excluded set is explainable):
  1. the run is `valued` and passed the liquidity screen;
  2. `currency_unverified` names are excluded — a value read in the wrong
     currency is the exact class of error the HUBS incident was
     (portfolio-conventions, cost_base_normal note);
  3. quality: the 3-period-AVERAGE ROE exceeds Ke mid (trailing ROE falls
     back when no average exists, flagged) — the baseline's answer to
     peak-cycle trailing ROE (Metro Mining 94x on trailing, 0.92x on average);
  4. value: value >= price under BOTH the registered convention and the
     average-ROE sensitivity (the baseline's "robust set", REPORT D).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from asxos.domain.discovery.types import Opportunity
from asxos.domain.valuation.contracts import ValuationRun
from asxos.domain.valuation.sweep import FLAG_CURRENCY_UNVERIFIED

_Q6: Final[Decimal] = Decimal("0.000001")

#: The liquidity screen (baseline §4): ADV >= A$250k, market cap >= A$100m.
#: `decision_engine/builder.py` reads MIN_ADV_AUD for the packet's tradeability line.
MIN_ADV_AUD: Final[Decimal] = Decimal("250000")
MIN_MARKET_CAP_AUD: Final[Decimal] = Decimal("100000000")

FLAG_ROE_AVERAGE_FALLBACK: Final[str] = "roe_average_fallback_to_trailing"


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


class Screened:
    """A name that passed the liquidity screen, with the figures it passed on."""

    __slots__ = ("adv_aud", "market_cap_aud", "symbol")

    def __init__(self, symbol: str, *, adv_aud: Decimal, market_cap_aud: Decimal) -> None:
        self.symbol = symbol
        self.adv_aud = adv_aud
        self.market_cap_aud = market_cap_aud


def passing(
    runs: Iterable[ValuationRun],
    screened: Mapping[str, Screened],
    *,
    screening_run_id: int,
    include_currency_unverified: bool = False,
) -> list[Opportunity]:
    """Every name that passes the four gates, in symbol order — a set, not a rank."""
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
                value_to_price_min=min(vp_registered, vp_average),
                roe_trailing=run.inputs.roe_trailing,
                roe_average=roe_average,
                roe_average_is_fallback=fallback,
                ke_mid=run.ke.ke_mid,
                adv_aud=hit.adv_aud,
                market_cap_aud=hit.market_cap_aud,
                flags=tuple(flags),
                screening_run_id=screening_run_id,
            )
        )
    out.sort(key=lambda o: o.symbol)
    return out
