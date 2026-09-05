"""Slice 2 — the sizer, downstream of the challenge gate (ADR §6, D1/D2).

Re-homes the existing Decimal-only inverse-volatility sizer by IMPORT, not by
move: `asxos.domain.portfolio.allocator.inverse_vol_weights` is called
unchanged for the risk-parity reference weight, and the ratified caps are
applied here for a single proposed position. Nothing under
`asxos/domain/portfolio/` is edited, and the whole-book waterfall
(`constraints.apply_constraints`) is deliberately NOT called: its pre-flight
feasibility check hard-fails whenever `N × per_name_cap < deployable`, which
is every small book, and it sizes a full target list rather than one
position. Its per-name and sector semantics are reproduced below on the
pro-forma book.

Gate: `SizeRange(0, 0)` unless `challenge.outcome == "pass"`. Cash floor
7.5% (D1) and gross leverage 0% (D2) are enforced as hard clamps on the
maximum; sector 30% (D8) and the profile position cap likewise. The result
is a RANGE the decision packet may carry — never an order, never a trade.

`AllocationCandidate` is constructed only to satisfy `inverse_vol_weights`'s
signature; its retired `signal_label` / `prob_up` / `expected_return`
fields are inert placeholders here (`portfolio/types.py` records why they
still exist). Nothing in this module reads `signals` or imports
`asxos.domain.models` (rule #11).
"""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from pydantic import Field

from asxos.domain.decision_engine.challenge.rules import (
    CASH_FLOOR_PCT,
    SECTOR_CAP_PCT,
    PortfolioState,
)
from asxos.domain.decision_engine.types import ChallengeResult, Contract, SizeRange
from asxos.domain.portfolio.allocator import inverse_vol_weights
from asxos.domain.portfolio.types import AllocationCandidate

_Q6: Final[Decimal] = Decimal("0.000001")
_HUNDRED: Final[Decimal] = Decimal("100")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


class VolInput(Contract):
    symbol: str = Field(min_length=1, max_length=40)
    annualised_vol: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)


class ProposedPosition(Contract):
    symbol: str = Field(min_length=1, max_length=40)
    sector: str | None = None
    annualised_vol: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)


class SizingPolicy(Contract):
    """The profile's sizing parameters, in percent of capital. The ratified
    floors/caps are not parameters: cash floor and sector cap come from the
    register constants, and a policy may only be TIGHTER than them."""

    capital_aud: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    position_cap_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("50"), max_digits=18, decimal_places=6)
    min_position_aud: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    cash_floor_pct: Decimal = Field(default=CASH_FLOOR_PCT, ge=CASH_FLOOR_PCT, le=Decimal("100"), max_digits=18, decimal_places=6)
    sector_cap_pct: Decimal = Field(default=SECTOR_CAP_PCT, gt=Decimal("0"), le=SECTOR_CAP_PCT, max_digits=18, decimal_places=6)

    @property
    def deployable_pct(self) -> Decimal:
        return _HUNDRED - self.cash_floor_pct


ZERO_SIZE: Final[SizeRange] = SizeRange(minimum_pct=Decimal("0"), maximum_pct=Decimal("0"))


def _placeholder(symbol: str, sector: str | None, vol: Decimal) -> AllocationCandidate:
    return AllocationCandidate(
        symbol=symbol, sector=sector, market_cap_aud=None,
        signal_label="HOLD", prob_up=Decimal("0"), expected_return=Decimal("0"),
        daily_vol=vol, confidence=0,
    )


def reference_weight_pct(proposed: ProposedPosition, peers: tuple[VolInput, ...], policy: SizingPolicy) -> Decimal:
    """Risk-parity share of the deployable book for the proposed name, via the
    unchanged M13.3 inverse-vol function."""
    candidates = [_placeholder(proposed.symbol, proposed.sector, proposed.annualised_vol)]
    candidates += [_placeholder(p.symbol, None, p.annualised_vol) for p in peers if p.symbol != proposed.symbol]
    weights = inverse_vol_weights(candidates)
    return _q(weights[0] * policy.deployable_pct)


def headroom_max_pct(
    proposed: ProposedPosition,
    peers: tuple[VolInput, ...],
    policy: SizingPolicy,
    state: PortfolioState,
) -> Decimal:
    """The largest weight the ratified caps permit for the proposed name on the
    pro-forma book — the risk-parity reference, then D1 cash, D2 gross, D8
    sector and the profile position cap, whichever binds. Zero on any
    borrowing (D2). This is what a builder PROPOSES; it is not a size until
    the challenge passes."""
    if state.borrowing_aud > 0:
        return Decimal("0")
    headroom = [
        reference_weight_pct(proposed, peers, policy),
        policy.position_cap_pct - state.position_weights_pct.get(proposed.symbol, Decimal("0")),
        state.cash_pct - policy.cash_floor_pct,  # D1: post-trade cash stays at or above the floor
        _HUNDRED - state.gross_exposure_pct,  # D2: gross never above 100%
    ]
    if proposed.sector is not None:
        headroom.append(policy.sector_cap_pct - state.sector_weights_pct.get(proposed.sector, Decimal("0")))
    return _q(max(Decimal("0"), min(headroom)))


def size_from_challenge(
    challenge: ChallengeResult,
    *,
    proposed: ProposedPosition,
    peers: tuple[VolInput, ...],
    policy: SizingPolicy,
    state: PortfolioState,
) -> SizeRange:
    """The only way a non-zero `SizeRange` is produced."""
    if challenge.outcome != "pass":
        return ZERO_SIZE
    if any(f.severity == "blocking" for f in challenge.findings):
        return ZERO_SIZE  # unreachable by contract; belt and braces
    maximum = headroom_max_pct(proposed, peers, policy, state)
    if maximum <= 0:
        return ZERO_SIZE
    minimum = _q(min(maximum, policy.min_position_aud / policy.capital_aud * _HUNDRED))
    return SizeRange(minimum_pct=minimum, maximum_pct=maximum)
