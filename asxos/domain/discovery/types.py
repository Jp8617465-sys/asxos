"""Discovery contracts — a name that passes the value screen, and nothing more.

Demoted 2026-09-16 (#306). The sealed value-to-price test returned `null`
(#304), and the response James pre-committed before any result existed
(`asxos/domain/research/registry/vp.py::RESPONSE_RULE`) demotes the
residual-income model to a discipline device: it must still state a
falsifiable number per thesis, but it stops emitting target prices, entry
bands and ranked "opportunities". `ThesisPlan` — the target, band and stop
this module used to derive from the model value by three constants — and
`Opportunity.plan`, `.score` and `.liquidity_factor` were deleted with it.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from asxos.domain.decision_engine.types import Contract


class Opportunity(Contract):
    """One name that passes the four value-screen gates, with every figure it passed on.

    Not a proposal and not a rank (#306): there is no plan, no score, and no
    order beyond the symbol. The falsifiable number per thesis is stated where
    the challenge reads it — the `valuation_fact` evidence item and the
    `valuation_gap` rule in `decision_engine/builder.py` — for theses a human
    has written and approved.
    """

    symbol: str = Field(min_length=1, max_length=40)
    run_id: str = Field(min_length=1, max_length=200)
    run_content_hash: str = Field(min_length=64, max_length=64)
    as_of: date
    last_close: Decimal = Field(gt=0)
    last_close_dt: date
    value_registered: Decimal = Field(gt=0)
    value_average_roe: Decimal = Field(gt=0)
    value_to_price_registered: Decimal = Field(gt=0)
    value_to_price_average_roe: Decimal = Field(gt=0)
    value_to_price_min: Decimal = Field(gt=0)
    roe_trailing: Decimal
    roe_average: Decimal
    roe_average_is_fallback: bool
    ke_mid: Decimal = Field(gt=0)
    adv_aud: Decimal = Field(ge=0)
    market_cap_aud: Decimal = Field(ge=0)
    flags: tuple[str, ...] = ()
    screening_run_id: int = Field(ge=1)
