"""Slice 3 — order STAGING, to the broker's door and no further (ADR §6).

A `StagedOrder` is a typed, non-executable description of what a passed
challenge and a non-zero `SizeRange` would permit: quantity, limit price,
notional, and — for a sell — the tax lots the tax module selects. It is
built only from a `ChallengeResult` whose outcome is `pass` and a
`SizeRange` whose maximum is non-zero; anything else is refused.

Lot selection is DELEGATED to `asxos.domain.tax.lots` (`select_min_cgt`,
`select_fifo`, `select_lifo`) — the sanctioned selectors, which apply the
spec §5.1 calendar rule through `cgt.is_discountable` and the account-type
discount of spec §2 through `cgt.cgt_discount_rate` — never re-implemented
here. The default is `min_cgt`. `account_type` is threaded to the selector
because the discount differs by account type (§2); every lot staged must
carry that same account type, or staging refuses.

**Projection, not a CGT event.** Spec §5.1 (line 110) and §10 (line 371)
fix the disposal date as the CONTRACT date. A staged order has none: the
`discountable` flag and `realised_gain_aud` on each `StagedLot` are §5.1
projections evaluated at the packet `as_of` and at `reference_price`, and
are marked `provisional`. Both MUST be re-evaluated at the contract date
and fill price before any tax figure is relied on; eligibility can only
improve with time, so a lot projected non-discountable may be discountable
at fill.

`select_min_cgt` falls back to FIFO above six lots; staging refuses rather
than record a selector that was not the one applied. The spec carries no
section for lot selection itself — min-CGT's objective is
implementation-defined (`lots.py`) — so a spec amendment (§5.5 + a numeric
test case) is required before a staged sell's lot choice is relied on for
capital; recorded as a James item, not fixed here.

There is no broker, no venue, no credential, no network and no write in this
module. `not_executable` is a `Literal[True]` on every order, and no function
here can be called with anything that would change that.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from asxos.domain.decision_engine.types import ChallengeResult, Contract, SizeRange, require_utc
from asxos.domain.tax.lots import select_fifo, select_lifo, select_min_cgt
from asxos.domain.tax.types import AccountType, HoldingLot, LotSelection

_Q6: Final[Decimal] = Decimal("0.000001")
_HUNDRED: Final[Decimal] = Decimal("100")
MAX_LIMIT_OFFSET_PCT: Final[Decimal] = Decimal("100")

Side = Literal["buy", "sell"]
LotSelector = Literal["min_cgt", "fifo", "lifo"]


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


class StagingError(ValueError):
    """The inputs do not permit a staged order."""


MIN_CGT_MAX_LOTS: Final[int] = 6  # above this `select_min_cgt` silently falls back to FIFO


class StagedLot(Contract):
    lot_id: int
    qty: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    realised_gain_aud: Decimal = Field(max_digits=18, decimal_places=6)
    holding_period_days: int
    discountable: bool
    eligibility_evaluated_at: date
    gain_priced_at: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    provisional: Literal[True] = True


class StagedOrder(Contract):
    staged_order_id: str = Field(min_length=1, max_length=200)
    challenge_result_id: str = Field(min_length=1, max_length=200)
    symbol: str = Field(min_length=1, max_length=40)
    side: Side
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    limit_price: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    notional_aud: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    size_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    lot_selector: LotSelector
    lot_selections: tuple[StagedLot, ...] = Field(default=(), max_length=500)
    as_of: date
    staged_at: datetime
    not_executable: Literal[True] = True
    execution_venue: Literal["none"] = "none"

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.side == "sell" and not self.lot_selections:
            raise ValueError("a staged sell must name the tax lots it draws on")
        if self.side == "buy" and self.lot_selections:
            raise ValueError("a staged buy selects no tax lots")
        if self.side == "sell":
            drawn = sum((lot.qty for lot in self.lot_selections), Decimal("0"))
            if drawn != self.quantity:
                raise ValueError("lot selections must sum to the staged quantity")
        return self


def _select(selector: LotSelector, lots: list[HoldingLot], qty: Decimal, price: Decimal, sale_date: date, account_type: AccountType) -> list[LotSelection]:
    if selector == "min_cgt":
        return select_min_cgt(lots, qty, price, sale_date, account_type=account_type)
    if selector == "fifo":
        return select_fifo(lots, qty, price, sale_date)
    return select_lifo(lots, qty, price, sale_date)


def stage_order(
    challenge: ChallengeResult,
    size: SizeRange,
    *,
    symbol: str,
    side: Side,
    reference_price: Decimal,
    capital_aud: Decimal,
    as_of: date,
    staged_at: datetime,
    open_lots: tuple[HoldingLot, ...] = (),
    account_type: AccountType = "individual",
    lot_selector: LotSelector = "min_cgt",
    limit_offset_pct: Decimal = Decimal("0"),
) -> StagedOrder:
    """Stage one order from a PASSED challenge and a NON-ZERO size range."""
    if challenge.outcome != "pass":
        raise StagingError(f"cannot stage on a {challenge.outcome!r} challenge")
    if any(f.severity == "blocking" for f in challenge.findings):
        raise StagingError("cannot stage against a blocking finding")
    if size.maximum_pct <= 0:
        raise StagingError("cannot stage a zero size range")
    if reference_price <= 0 or capital_aud <= 0:
        raise StagingError("reference price and capital must be positive")
    if limit_offset_pct < 0 or limit_offset_pct >= MAX_LIMIT_OFFSET_PCT:
        raise StagingError(
            f"limit offset must be at least 0 and below {MAX_LIMIT_OFFSET_PCT}%"
        )
    if challenge.as_of != as_of:
        raise StagingError("staging as_of must equal the challenge as_of")
    staged_at = require_utc(staged_at, field_name="staged_at")

    offset = reference_price * limit_offset_pct / _HUNDRED
    limit_price = _q(reference_price + offset if side == "buy" else reference_price - offset)
    notional_cap = capital_aud * size.maximum_pct / _HUNDRED
    # A buy can fill up to its limit, so sizing it at the lower reference
    # price would let the notional at the limit exceed the challenged cap.
    sizing_price = limit_price if side == "buy" else reference_price
    quantity = (notional_cap / sizing_price).quantize(Decimal("1"), rounding=ROUND_DOWN)
    if side == "sell":
        symbol_lots = [lot for lot in open_lots if lot.symbol == symbol and lot.disposed_at is None]
        mismatched = sorted(lot.lot_id for lot in symbol_lots if lot.account_type != account_type)
        if mismatched:
            raise StagingError(
                f"lots {mismatched} carry a different account_type from {account_type!r}; the §2 discount would be wrong"
            )
        if lot_selector == "min_cgt" and len(symbol_lots) > MIN_CGT_MAX_LOTS:
            raise StagingError(
                f"{len(symbol_lots)} open lots exceed the min-CGT search bound ({MIN_CGT_MAX_LOTS}); "
                "the selector would silently fall back to FIFO — choose fifo/lifo explicitly or pre-filter the lots"
            )
        held = sum((lot.quantity for lot in symbol_lots), Decimal("0"))
        quantity = min(quantity, held)
    if quantity <= 0:
        raise StagingError("the permitted size buys or sells fewer than one unit")

    selections: tuple[StagedLot, ...] = ()
    if side == "sell":
        chosen = _select(lot_selector, symbol_lots, quantity, reference_price, as_of, account_type)
        selections = tuple(
            StagedLot(
                lot_id=s.lot_id, qty=_q(s.qty_sold), realised_gain_aud=_q(s.realised_gain_aud),
                holding_period_days=s.holding_period_days, discountable=s.discountable,
                eligibility_evaluated_at=as_of, gain_priced_at=_q(reference_price),
            )
            for s in chosen
        )
    notional = _q(quantity * limit_price)
    return StagedOrder(
        staged_order_id=f"stg-{challenge.challenge_result_id}-{side}",
        challenge_result_id=challenge.challenge_result_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        limit_price=limit_price,
        notional_aud=notional,
        size_pct=_q(notional / capital_aud * _HUNDRED),
        lot_selector=lot_selector,
        lot_selections=selections,
        as_of=as_of,
        staged_at=staged_at,
    )
