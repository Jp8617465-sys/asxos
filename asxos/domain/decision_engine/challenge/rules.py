"""Layer 1 challenge rules — deterministic code, never LLM-executed (ADR D12).

The fourteen rules of `docs/product/architecture-decision-record.md` §10.4 are
implemented one function each, run PRO-FORMA (post-proposed-trade) over a
typed `ChallengeInput`, and emit canonical `ChallengeFinding`s. Severity
follows D14: `blocking` is reserved for a breach of a ratified register
decision (D1 cash floor 7.5%, D2 gross leverage 0%, D8 sector cap 30%, the
profile position cap, long-only cash equity) or a certain data-integrity
failure; `material` is a cited diagnostic concern; `monitor` is real but not
actionable now. Nothing here imposes a restriction the register does not
already carry.

A fifteenth rule, `price_detached`, is the governor-drafts C5 item scheduled
here (2026-07-16 ruling, restated 2026-09-02): the entry band on file no
longer describes the security's price. Its thresholds are arbi's draft
constants (`PRICE_DETACHED_*`), recorded as such; James may tighten or loosen
them by ruling. Detachment is a data-integrity failure of the decision basis
(the price plan is stale), which is why the severe tier is `blocking` under
D14 rather than a new restriction.

Every finding cites at least one evidence id — the contract makes an
unevidenced finding unconstructable. Prose is template-only; the only
variable content is code-generated numbers and rule names, so no author or
document text can steer a finding (the results-review G10 defence, reused).
Decimal-only. No DB, no network, no clock: `as_of` comes from the input.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final, Literal, Self

from pydantic import Field, model_validator

from asxos.domain.decision_engine.types import ChallengeFinding, Contract

# --- Ratified register values (ADR §1) ---------------------------------------
CASH_FLOOR_PCT: Final[Decimal] = Decimal("7.5")  # D1
GROSS_LEVERAGE_CAP_PCT: Final[Decimal] = Decimal("0")  # D2 — any borrowing breaches
SECTOR_CAP_PCT: Final[Decimal] = Decimal("30")  # D8

# --- Data-integrity and diagnostic thresholds (arbi draft constants) ----------
PRICE_STALE_BLOCKING_DAYS: Final[int] = 10  # priced on data older than this = integrity failure
PRICE_STALE_MATERIAL_DAYS: Final[int] = 3
FUNDAMENTALS_STALE_MATERIAL_DAYS: Final[int] = 200  # > two half-year cycles
CORRELATION_MATERIAL: Final[Decimal] = Decimal("0.80")  # the register's own co-movement assumption
VALUATION_EXTREME_LOW_PCT: Final[Decimal] = Decimal("5")
VALUATION_EXTREME_HIGH_PCT: Final[Decimal] = Decimal("95")
IMPLIED_CAGR_MATERIAL_PCT: Final[Decimal] = Decimal("30")
LIQUIDITY_PARTICIPATION: Final[Decimal] = Decimal("0.20")  # of ADV per session
LIQUIDITY_DAYS_TO_EXIT_MATERIAL: Final[Decimal] = Decimal("5")
LIQUIDITY_SPREAD_MATERIAL_BPS: Final[Decimal] = Decimal("100")
LIQUIDITY_TREND_MONITOR_PCT: Final[Decimal] = Decimal("-25")
THESIS_AGE_MONITOR_DAYS: Final[int] = 14  # within this many days of revisit_due
PRICE_DETACHED_BLOCKING_RATIO: Final[Decimal] = Decimal("1.0")  # distance ≥ 100% of band midpoint
PRICE_DETACHED_MATERIAL_RATIO: Final[Decimal] = Decimal("0.25")

_Q6: Final[Decimal] = Decimal("0.000001")
_MEASURABLE_RE: Final = re.compile(r"\d")

Severity = Literal["blocking", "material", "monitor"]
InstrumentKind = Literal["cash_equity", "etf", "derivative", "short"]
RuleName = Literal[
    "gross_leverage",
    "derivatives_or_shorting",
    "cash_floor",
    "sector_cap",
    "position_cap",
    "data_integrity",
    "data_staleness",
    "correlation",
    "valuation_percentile",
    "implied_growth",
    "invalidation_field",
    "liquidity",
    "thesis_age",
    "liquidity_trend",
    "price_detached",
]
RULE_NAMES: Final[tuple[RuleName, ...]] = (
    "gross_leverage", "derivatives_or_shorting", "cash_floor", "sector_cap", "position_cap",
    "data_integrity", "data_staleness", "correlation", "valuation_percentile", "implied_growth",
    "invalidation_field", "liquidity", "thesis_age", "liquidity_trend", "price_detached",
)


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


class PortfolioState(Contract):
    """Pre-trade book state, in percent of capital. Every figure is what the
    caller measured; nothing is inferred here."""

    capital_aud: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    cash_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    gross_exposure_pct: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    borrowing_aud: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    sector_weights_pct: dict[str, Decimal] = Field(default_factory=dict)
    position_weights_pct: dict[str, Decimal] = Field(default_factory=dict)
    evidence_id: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        for name, value in {**self.sector_weights_pct, **self.position_weights_pct}.items():
            if value < 0 or value > 100:
                raise ValueError(f"weight for {name!r} outside [0, 100]")
        return self


class ChallengeInput(Contract):
    """Everything the Layer-1 rules read. Pro-forma: the proposed position is
    ADDED to the pre-trade state before each check."""

    symbol: str = Field(min_length=1, max_length=40)
    instrument_kind: InstrumentKind = "cash_equity"
    sector: str | None = None
    as_of: date
    proposed_weight_pct: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    position_cap_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("50"), max_digits=18, decimal_places=6)
    portfolio: PortfolioState
    # price
    last_close: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    last_close_dt: date | None = None
    price_evidence_id: str | None = Field(default=None, min_length=1, max_length=200)
    # fundamentals
    fundamentals_as_of: date | None = None
    fundamentals_evidence_id: str | None = Field(default=None, min_length=1, max_length=200)
    # thesis
    thesis_evidence_id: str = Field(min_length=1, max_length=200)
    entry_band_lower: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    entry_band_upper: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    target_price: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    reference_price: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    horizon_months: int | None = Field(default=None, gt=0, le=120)
    invalidation_conditions: tuple[str, ...] = Field(default=(), max_length=100)
    last_revisited_at: date | None = None
    revisit_due_at: date | None = None
    base_rate_evidence_ids: tuple[str, ...] = Field(default=(), max_length=100)
    # diagnostics (None = not measured; the rule reports "not evaluated")
    pairwise_correlation_max: Decimal | None = Field(default=None, ge=Decimal("-1"), le=Decimal("1"), max_digits=18, decimal_places=6)
    valuation_percentile: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"), max_digits=18, decimal_places=6)
    adv_aud: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=18, decimal_places=6)
    adv_trend_pct: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    spread_bps: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=18, decimal_places=6)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if (self.entry_band_lower is None) != (self.entry_band_upper is None):
            raise ValueError("entry band needs both bounds or neither")
        if self.entry_band_lower is not None and self.entry_band_upper is not None:
            if self.entry_band_lower > self.entry_band_upper:
                raise ValueError("entry_band_lower cannot exceed entry_band_upper")
        if (self.last_close is None) != (self.last_close_dt is None):
            raise ValueError("last_close and last_close_dt travel together")
        if self.last_close_dt is not None and self.last_close_dt > self.as_of:
            raise ValueError("last_close_dt cannot be after as_of")
        if self.fundamentals_as_of is not None and self.fundamentals_as_of > self.as_of:
            raise ValueError("fundamentals_as_of cannot be after as_of")
        return self

    # -- pro-forma helpers (percent of capital) ---------------------------------
    @property
    def intended_size_aud(self) -> Decimal:
        return _q(self.portfolio.capital_aud * self.proposed_weight_pct / Decimal("100"))

    @property
    def post_trade_cash_pct(self) -> Decimal:
        return _q(self.portfolio.cash_pct - self.proposed_weight_pct)

    @property
    def post_trade_gross_pct(self) -> Decimal:
        return _q(self.portfolio.gross_exposure_pct + self.proposed_weight_pct)

    @property
    def post_trade_sector_pct(self) -> Decimal | None:
        if self.sector is None:
            return None
        return _q(self.portfolio.sector_weights_pct.get(self.sector, Decimal("0")) + self.proposed_weight_pct)

    @property
    def post_trade_position_pct(self) -> Decimal:
        return _q(self.portfolio.position_weights_pct.get(self.symbol, Decimal("0")) + self.proposed_weight_pct)

    def _ids(self, *specific: str | None) -> tuple[str, ...]:
        ids = tuple(i for i in specific if i)
        return ids or (self.thesis_evidence_id,)


class RuleOutcome(Contract):
    rule: RuleName
    evaluated: bool
    finding: ChallengeFinding | None = None
    detail: str = Field(min_length=1, max_length=2_000)


def _finding(severity: Severity, text: str, response: str, ids: tuple[str, ...]) -> ChallengeFinding:
    return ChallengeFinding(severity=severity, finding=text, required_response=response, evidence_ids=ids[:100])


# --- the rules ------------------------------------------------------------------


def rule_gross_leverage(x: ChallengeInput) -> RuleOutcome:
    if x.portfolio.borrowing_aud > 0 or x.post_trade_gross_pct > Decimal("100"):
        return RuleOutcome(rule="gross_leverage", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            f"Gross leverage would be non-zero: borrowing {x.portfolio.borrowing_aud} AUD, "
            f"post-trade gross exposure {x.post_trade_gross_pct}% (D2 cap {GROSS_LEVERAGE_CAP_PCT}% LVR).",
            "Fund the position from held capital; no borrowed position can be proposed.",
            x._ids(x.portfolio.evidence_id),
        ))
    return RuleOutcome(rule="gross_leverage", evaluated=True, detail="no borrowing; gross exposure within 100%")


def rule_derivatives_or_shorting(x: ChallengeInput) -> RuleOutcome:
    if x.instrument_kind in ("derivative", "short"):
        return RuleOutcome(rule="derivatives_or_shorting", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            f"Instrument kind {x.instrument_kind!r} is outside long-only cash equity.",
            "Withdraw the proposal; only long-only cash equity is in mandate.",
            x._ids(x.thesis_evidence_id),
        ))
    return RuleOutcome(rule="derivatives_or_shorting", evaluated=True, detail="long-only cash equity")


def rule_cash_floor(x: ChallengeInput) -> RuleOutcome:
    if x.post_trade_cash_pct < CASH_FLOOR_PCT:
        return RuleOutcome(rule="cash_floor", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            f"Post-trade cash {x.post_trade_cash_pct}% is below the D1 floor of {CASH_FLOOR_PCT}%.",
            f"Reduce the proposed size so post-trade cash is at least {CASH_FLOOR_PCT}% of capital.",
            x._ids(x.portfolio.evidence_id),
        ))
    return RuleOutcome(rule="cash_floor", evaluated=True, detail=f"post-trade cash {x.post_trade_cash_pct}%")


def rule_sector_cap(x: ChallengeInput) -> RuleOutcome:
    post = x.post_trade_sector_pct
    if post is None:
        return RuleOutcome(rule="sector_cap", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            "No GICS sector is recorded for the proposed security, so the D8 sector cap cannot be checked.",
            "Record the security's GICS sector before the proposal is re-challenged.",
            x._ids(x.thesis_evidence_id),
        ))
    if post > SECTOR_CAP_PCT:
        return RuleOutcome(rule="sector_cap", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            f"Post-trade sector exposure {post}% exceeds the D8 cap of {SECTOR_CAP_PCT}%.",
            f"Reduce the proposed size so the sector stays at or below {SECTOR_CAP_PCT}%.",
            x._ids(x.portfolio.evidence_id),
        ))
    return RuleOutcome(rule="sector_cap", evaluated=True, detail=f"post-trade sector {post}%")


def rule_position_cap(x: ChallengeInput) -> RuleOutcome:
    post = x.post_trade_position_pct
    if post > x.position_cap_pct:
        return RuleOutcome(rule="position_cap", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            f"Post-trade single position {post}% exceeds the profile cap of {x.position_cap_pct}%.",
            f"Reduce the proposed size so the position stays at or below {x.position_cap_pct}%.",
            x._ids(x.portfolio.evidence_id),
        ))
    return RuleOutcome(rule="position_cap", evaluated=True, detail=f"post-trade position {post}%")


def _price_age(x: ChallengeInput) -> int | None:
    return (x.as_of - x.last_close_dt).days if x.last_close_dt else None


def rule_data_integrity(x: ChallengeInput) -> RuleOutcome:
    age = _price_age(x)
    if age is None:
        return RuleOutcome(rule="data_integrity", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            "No price is available at the knowledge cutoff; the decision would be priced on missing data.",
            "Supply a price observed on or before the cutoff and re-challenge.",
            x._ids(x.price_evidence_id),
        ))
    if age > PRICE_STALE_BLOCKING_DAYS:
        return RuleOutcome(rule="data_integrity", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            f"The last price is {age} days old at the cutoff, beyond the {PRICE_STALE_BLOCKING_DAYS}-day integrity threshold.",
            "Refresh prices before the proposal is re-challenged.",
            x._ids(x.price_evidence_id),
        ))
    if x.instrument_kind == "cash_equity" and x.fundamentals_as_of is None:
        return RuleOutcome(rule="data_integrity", evaluated=True, detail="breach", finding=_finding(
            "blocking",
            "No fundamentals are knowable at the cutoff for a cash-equity proposal.",
            "Supply point-in-time fundamentals knowable at the cutoff and re-challenge.",
            x._ids(x.fundamentals_evidence_id),
        ))
    return RuleOutcome(rule="data_integrity", evaluated=True, detail=f"price age {age}d; fundamentals present")


def rule_data_staleness(x: ChallengeInput) -> RuleOutcome:
    age = _price_age(x)
    notes: list[str] = []
    if age is not None and PRICE_STALE_MATERIAL_DAYS < age <= PRICE_STALE_BLOCKING_DAYS:
        notes.append(f"price {age} days old")
    if x.fundamentals_as_of is not None:
        f_age = (x.as_of - x.fundamentals_as_of).days
        if f_age > FUNDAMENTALS_STALE_MATERIAL_DAYS:
            notes.append(f"fundamentals {f_age} days old")
    if notes:
        return RuleOutcome(rule="data_staleness", evaluated=True, detail="stale", finding=_finding(
            "material",
            "Decision inputs are stale below the integrity threshold: " + "; ".join(notes) + ".",
            "Refresh the stale inputs or record why the staleness is acceptable for this horizon.",
            x._ids(x.price_evidence_id, x.fundamentals_evidence_id),
        ))
    return RuleOutcome(rule="data_staleness", evaluated=age is not None, detail="inputs fresh" if age is not None else "no price to age")


def rule_correlation(x: ChallengeInput) -> RuleOutcome:
    if x.pairwise_correlation_max is None:
        return RuleOutcome(rule="correlation", evaluated=False, detail="pairwise correlation not measured")
    if x.pairwise_correlation_max > CORRELATION_MATERIAL:
        return RuleOutcome(rule="correlation", evaluated=True, detail="above threshold", finding=_finding(
            "material",
            f"Maximum pairwise correlation with the existing book is {x.pairwise_correlation_max}, above {CORRELATION_MATERIAL}.",
            "Record why the position adds exposure the book does not already carry, or reduce it.",
            x._ids(x.portfolio.evidence_id),
        ))
    return RuleOutcome(rule="correlation", evaluated=True, detail=f"max pairwise correlation {x.pairwise_correlation_max}")


def rule_valuation_percentile(x: ChallengeInput) -> RuleOutcome:
    p = x.valuation_percentile
    if p is None:
        return RuleOutcome(rule="valuation_percentile", evaluated=False, detail="sector valuation percentile not measured")
    if p <= VALUATION_EXTREME_LOW_PCT or p >= VALUATION_EXTREME_HIGH_PCT:
        return RuleOutcome(rule="valuation_percentile", evaluated=True, detail="extreme", finding=_finding(
            "material",
            f"Sector valuation percentile {p} is at an extreme (outside {VALUATION_EXTREME_LOW_PCT}-{VALUATION_EXTREME_HIGH_PCT}).",
            "Record the variant view that justifies an extreme valuation, citing evidence.",
            x._ids(x.fundamentals_evidence_id),
        ))
    return RuleOutcome(rule="valuation_percentile", evaluated=True, detail=f"percentile {p}")


def implied_cagr_pct(*, reference_price: Decimal, target_price: Decimal, horizon_months: int) -> Decimal:
    """Annualised growth implied by reaching target from reference over the horizon."""
    ratio = target_price / reference_price
    years = Decimal(horizon_months) / Decimal(12)
    return _q(((ratio.ln() / years).exp() - Decimal(1)) * Decimal(100))


def rule_implied_growth(x: ChallengeInput) -> RuleOutcome:
    if x.target_price is None or x.reference_price is None or x.horizon_months is None:
        return RuleOutcome(rule="implied_growth", evaluated=False, detail="target, reference or horizon absent")
    cagr = implied_cagr_pct(reference_price=x.reference_price, target_price=x.target_price, horizon_months=x.horizon_months)
    if cagr > IMPLIED_CAGR_MATERIAL_PCT:
        return RuleOutcome(rule="implied_growth", evaluated=True, detail=f"implied CAGR {cagr}%", finding=_finding(
            "material",
            f"The target price implies {cagr}% annualised from the reference price over {x.horizon_months} months, above {IMPLIED_CAGR_MATERIAL_PCT}%.",
            "Reconcile the target with the evidence for growth of that magnitude, or revise it.",
            x._ids(x.thesis_evidence_id),
        ))
    return RuleOutcome(rule="implied_growth", evaluated=True, detail=f"implied CAGR {cagr}%")


def rule_invalidation_field(x: ChallengeInput) -> RuleOutcome:
    if not any(c.strip() for c in x.invalidation_conditions):
        return RuleOutcome(rule="invalidation_field", evaluated=True, detail="empty", finding=_finding(
            "material",
            "The thesis records no invalidation condition.",
            "Record at least one condition under which the thesis is wrong before it is re-challenged.",
            x._ids(x.thesis_evidence_id),
        ))
    return RuleOutcome(rule="invalidation_field", evaluated=True, detail=f"{len(x.invalidation_conditions)} condition(s)")


def rule_liquidity(x: ChallengeInput) -> RuleOutcome:
    if x.adv_aud is None:
        return RuleOutcome(rule="liquidity", evaluated=False, detail="average dollar volume not measured")
    notes: list[str] = []
    if x.adv_aud == 0:
        notes.append("no traded volume")
    else:
        days = _q(x.intended_size_aud / (x.adv_aud * LIQUIDITY_PARTICIPATION))
        if days > LIQUIDITY_DAYS_TO_EXIT_MATERIAL:
            notes.append(f"{days} sessions to exit at {LIQUIDITY_PARTICIPATION} participation")
    if x.spread_bps is not None and x.spread_bps > LIQUIDITY_SPREAD_MATERIAL_BPS:
        notes.append(f"spread {x.spread_bps} bps")
    if notes:
        return RuleOutcome(rule="liquidity", evaluated=True, detail="thin", finding=_finding(
            "material",
            "Liquidity is thin for the intended size: " + "; ".join(notes) + ".",
            "Reduce the intended size or record the accepted exit horizon.",
            x._ids(x.price_evidence_id),
        ))
    return RuleOutcome(rule="liquidity", evaluated=True, detail="adequate for the intended size")


def rule_thesis_age(x: ChallengeInput) -> RuleOutcome:
    if x.revisit_due_at is None:
        return RuleOutcome(rule="thesis_age", evaluated=False, detail="no revisit date on file")
    remaining = (x.revisit_due_at - x.as_of).days
    if remaining <= THESIS_AGE_MONITOR_DAYS:
        state = f"{-remaining} days overdue" if remaining < 0 else f"due in {remaining} days"
        return RuleOutcome(rule="thesis_age", evaluated=True, detail=state, finding=_finding(
            "monitor",
            f"The thesis revisit is {state}.",
            "Revisit the thesis and record the revision.",
            x._ids(x.thesis_evidence_id),
        ))
    return RuleOutcome(rule="thesis_age", evaluated=True, detail=f"revisit due in {remaining} days")


def rule_liquidity_trend(x: ChallengeInput) -> RuleOutcome:
    if x.adv_trend_pct is None:
        return RuleOutcome(rule="liquidity_trend", evaluated=False, detail="volume trend not measured")
    if x.adv_trend_pct < LIQUIDITY_TREND_MONITOR_PCT:
        return RuleOutcome(rule="liquidity_trend", evaluated=True, detail="declining", finding=_finding(
            "monitor",
            f"Average dollar volume has changed {x.adv_trend_pct}% against the prior window.",
            "Watch liquidity; re-run the liquidity rule before any size increase.",
            x._ids(x.price_evidence_id),
        ))
    return RuleOutcome(rule="liquidity_trend", evaluated=True, detail=f"volume trend {x.adv_trend_pct}%")


def detachment_ratio(*, close: Decimal, lower: Decimal, upper: Decimal) -> Decimal:
    """Distance from the nearest band edge, as a fraction of the band midpoint. 0 inside the band."""
    mid = (lower + upper) / Decimal(2)
    if lower <= close <= upper:
        return Decimal("0")
    distance = lower - close if close < lower else close - upper
    return _q(distance / mid)


def rule_price_detached(x: ChallengeInput) -> RuleOutcome:
    if x.entry_band_lower is None or x.entry_band_upper is None or x.last_close is None:
        return RuleOutcome(rule="price_detached", evaluated=False, detail="entry band or price absent")
    ratio = detachment_ratio(close=x.last_close, lower=x.entry_band_lower, upper=x.entry_band_upper)
    if ratio >= PRICE_DETACHED_BLOCKING_RATIO:
        return RuleOutcome(rule="price_detached", evaluated=True, detail=f"detached {ratio}", finding=_finding(
            "blocking",
            f"The last close {x.last_close} is detached from the entry band {x.entry_band_lower}-{x.entry_band_upper} "
            f"by {ratio} of the band midpoint; the price plan on file no longer describes the security.",
            "Revise the entry band, stop and target against the current price before the thesis is re-challenged.",
            x._ids(x.price_evidence_id, x.thesis_evidence_id),
        ))
    if ratio >= PRICE_DETACHED_MATERIAL_RATIO:
        return RuleOutcome(rule="price_detached", evaluated=True, detail=f"drifted {ratio}", finding=_finding(
            "material",
            f"The last close {x.last_close} sits outside the entry band {x.entry_band_lower}-{x.entry_band_upper} "
            f"by {ratio} of the band midpoint.",
            "Confirm the entry band still reflects the intended entry, or revise it.",
            x._ids(x.price_evidence_id, x.thesis_evidence_id),
        ))
    return RuleOutcome(rule="price_detached", evaluated=True, detail=f"detachment {ratio}")


RULES: Final[tuple[Callable[[ChallengeInput], RuleOutcome], ...]] = (
    rule_gross_leverage,
    rule_derivatives_or_shorting,
    rule_cash_floor,
    rule_sector_cap,
    rule_position_cap,
    rule_data_integrity,
    rule_data_staleness,
    rule_correlation,
    rule_valuation_percentile,
    rule_implied_growth,
    rule_invalidation_field,
    rule_liquidity,
    rule_thesis_age,
    rule_liquidity_trend,
    rule_price_detached,
)


def run_layer1(x: ChallengeInput) -> tuple[RuleOutcome, ...]:
    """Run every rule, in register order. Deterministic for equal input."""
    outcomes = tuple(rule(x) for rule in RULES)
    assert tuple(o.rule for o in outcomes) == RULE_NAMES
    return outcomes


def findings_of(outcomes: tuple[RuleOutcome, ...]) -> tuple[ChallengeFinding, ...]:
    return tuple(o.finding for o in outcomes if o.finding is not None)


def is_measurable(condition: str) -> bool:
    """A condition is falsifiable in the Layer-1 sense when it carries a number or date."""
    return bool(_MEASURABLE_RE.search(condition))
