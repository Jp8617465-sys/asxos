"""Stage 5 / ADR Slice 4 — outcome materialisation for governed packets.

Replaces the deleted `jobs/track_signal_outcomes.py`, generalising the
`macro_thesis_outcomes` pattern (migration 0041) from macro theses to
decision packets. Two operations, both append-only (migration 0052):

* `materialise_t0(case)` records, at the moment the packet is delivered,
  **what was known and what was claimed** — the reference price, the
  scenario ladder, the recommendation state, the challenge outcome, and
  the hash of the frozen evidence. Nothing about the future is guessed:
  the horizon rows are created `pending` with their due session already
  resolved, so a later observation cannot quietly re-pick its own horizon.
* `observe(packet, horizon, ...)` fills one horizon row when its session
  arrives: the realised return of the security over the window, the
  benchmark's return over the *same* window, and the difference.

Three properties are load-bearing, and each is a rule this repo has broken
before:

1. **Horizons are trading sessions, not weekdays.** Each due date is
   resolved through the packet's own `TradingSessionCalendar`
   (`types.py::TradingSessionCalendar.resolve_expiry`), the same object the
   F3 expiry uses. Weekday arithmetic mislabelled as trading days is the
   defect that calendar exists to prevent.
2. **The benchmark leg is `asxos.domain.benchmark.outcome`, unchanged.**
   Its `BenchmarkState.unavailable_proxy` is governor ruling F1 in code:
   while `AXJOA.INDX` is absent from `prices`, the accumulation comparison
   is reported **unavailable** and never silently replaced by the synthetic
   yield overlay. This module re-exports that state; it does not re-derive
   the rule and cannot soften it.
3. **One observation is never an alpha claim.** An outcome row carries
   measurements and named unavailability states. There is no verdict, no
   score, no promote/retire field, and no aggregate across packets — the
   learning review is a human act on this evidence
   (`target-architecture.md` §15 Stage 5), and its exit gate needs a
   complete episode, which one t0 row is not.

Decimal-only. No DB handle in the pure functions; persistence is at the
bottom of the module behind an explicit `Protocol`, as elsewhere in this
package.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Final, Literal, Protocol, Self

from pydantic import Field, model_validator

from asxos.domain.benchmark.outcome import BenchmarkState
from asxos.domain.benchmark.returns import period_return
from asxos.domain.decision_engine.types import (
    OUTCOME_WINDOWS_TRADING_DAYS,
    ContentAddressedContract,
    DecisionCase,
    DecisionPacket,
    TradingSessionCalendar,
    require_utc,
)

_Q6: Final[Decimal] = Decimal("0.000001")
T0: Final[int] = 0
HORIZONS: Final[tuple[int, ...]] = OUTCOME_WINDOWS_TRADING_DAYS

ObservationState = Literal["recorded", "observed", "unobservable"]
ReturnLeg = Literal["measured", "unavailable_no_price", "unavailable_stale_price", "pending"]


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


class OutcomeError(RuntimeError):
    """An outcome could not be materialised honestly."""


class ClaimRecord(ContentAddressedContract):
    """What the packet claimed at t0 — copied, never recomputed later."""

    recommendation_state: str = Field(min_length=1, max_length=40)
    challenge_outcome: str = Field(min_length=1, max_length=20)
    reference_price: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    scenario_returns_pct: dict[str, str] = Field(default_factory=dict)
    size_range_max_pct: Decimal = Field(ge=Decimal("0"), max_digits=18, decimal_places=6)
    evidence_packet_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    blocking_finding_count: int = Field(ge=0)
    missing_input_count: int = Field(ge=0)


class ThesisOutcome(ContentAddressedContract):
    """One (packet, horizon) row. `horizon_trading_days == 0` is the t0 record."""

    outcome_id: str = Field(min_length=1, max_length=200)
    decision_packet_id: str = Field(min_length=1, max_length=200)
    decision_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    symbol: str = Field(min_length=1, max_length=40)
    horizon_trading_days: int = Field(ge=0, le=126)
    due_at: datetime
    as_of: date
    knowledge_cutoff: datetime
    observation_state: ObservationState
    claim: ClaimRecord
    # Filled only when observed; each None is paired with a state and a note.
    observed_at: date | None = None
    observed_price: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=18, decimal_places=6)
    security_return_pct: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    return_state: ReturnLeg = "pending"
    return_note: str = Field(default="", max_length=2_000)
    benchmark_return_pct: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    benchmark_state: str = Field(min_length=1, max_length=40)
    benchmark_note: str = Field(default="", max_length=2_000)
    excess_return_pct: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    created_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.horizon_trading_days not in (T0, *HORIZONS):
            raise ValueError(f"horizon {self.horizon_trading_days} is not a ratified window")
        if self.as_of != self.knowledge_cutoff.date():
            raise ValueError("as_of must equal the UTC knowledge_cutoff date")
        if self.horizon_trading_days == T0:
            if self.observation_state != "recorded":
                raise ValueError("the t0 row records the claim; it is never an observation")
            if self.due_at != self.knowledge_cutoff:
                raise ValueError("the t0 row is due at its own cutoff")
        elif self.due_at <= self.knowledge_cutoff:
            raise ValueError("a horizon must fall after the knowledge cutoff")
        if self.observation_state == "observed":
            if self.security_return_pct is None and self.return_state == "measured":
                raise ValueError("a measured return must carry a value")
            if self.observed_at is None:
                raise ValueError("an observation must record the date it was taken")
        else:
            if self.security_return_pct is not None or self.benchmark_return_pct is not None:
                raise ValueError("only an observed row may carry returns")
        # Excess is a difference, never a claim: it exists only when BOTH legs do.
        both = self.security_return_pct is not None and self.benchmark_return_pct is not None
        if (self.excess_return_pct is not None) != both:
            raise ValueError("excess return requires both legs measured, and nothing else")
        if both:
            expected = _q(self.security_return_pct - self.benchmark_return_pct)  # type: ignore[operator]
            if self.excess_return_pct != expected:
                raise ValueError("excess return must equal security minus benchmark")
        return self

    @property
    def is_t0(self) -> bool:
        return self.horizon_trading_days == T0


def _scenarios(case: DecisionCase) -> dict[str, str]:
    return {s.label: format(s.return_pct, "f") for s in case.thesis.scenarios}


#: The token `builder.py` writes into the last-close evidence claim, and the
#: only thing this module parses out of prose. Pinned from both sides by
#: tests/test_decision_outcomes.py::test_reference_price_parser_is_pinned_to_the_builders_wording
#: — if the builder's wording drifts, that test fails rather than every
#: horizon silently recording `unavailable_no_price` while looking healthy.
PRICE_CLAIM_TOKEN: Final[str] = "close="


def _reference_price(case: DecisionCase) -> Decimal | None:
    """The price the scenarios were struck from, read out of the packet's own
    evidence — never re-derived from a live query at observation time.

    Recovering a number from prose is a known weakness (`security-engineer`,
    2026-09-03): the structural fix is to carry the price as a typed field on
    the evidence item, which edits the frozen `types.py` and is therefore a
    governor-scoped change. Until then a malformed token raises `OutcomeError`
    loudly instead of `decimal.InvalidOperation` from deep inside a builder.
    """
    for item in case.evidence.items:
        if not item.evidence_id.endswith("-last-close"):
            continue
        for token in item.claim.split():
            if token.startswith(PRICE_CLAIM_TOKEN):
                raw = token.removeprefix(PRICE_CLAIM_TOKEN).rstrip(".")
                try:
                    return Decimal(raw)
                except InvalidOperation as exc:
                    raise OutcomeError(
                        f"evidence {item.evidence_id!r} carries a non-numeric price token {raw!r}; "
                        "the outcome ledger cannot be anchored on it"
                    ) from exc
    return None


def horizon_due_at(packet: DecisionPacket, horizon: int) -> datetime:
    """Resolve a horizon through the packet's OWN trading calendar (never weekdays)."""
    if horizon == T0:
        return packet.knowledge_cutoff
    calendar: TradingSessionCalendar = packet.trading_calendar
    try:
        return calendar.resolve_expiry(packet.knowledge_cutoff, horizon)
    except ValueError as exc:
        raise OutcomeError(
            f"the packet's trading calendar does not reach {horizon} sessions past its cutoff; "
            "a horizon cannot be scheduled on weekday arithmetic"
        ) from exc


def materialise_t0(case: DecisionCase, *, created_at: datetime | None = None) -> tuple[ThesisOutcome, ...]:
    """The t0 record plus one `pending` row per ratified horizon.

    Every horizon whose due session the packet's calendar cannot reach is
    reported `unobservable` with its reason — not silently omitted, because a
    missing row is indistinguishable from an unrun observation.
    """
    packet = case.decision
    created = require_utc(created_at or packet.created_at, field_name="created_at")
    claim = ClaimRecord(
        recommendation_state=packet.recommendation_state,
        challenge_outcome=case.challenge.outcome,
        reference_price=_reference_price(case),
        scenario_returns_pct=_scenarios(case),
        size_range_max_pct=packet.size_range.maximum_pct,
        evidence_packet_hash=case.evidence.content_hash,
        blocking_finding_count=len([f for f in case.challenge.findings if f.severity == "blocking"]),
        missing_input_count=len(packet.missing_or_uncertain_inputs),
    )
    rows: list[ThesisOutcome] = [
        ThesisOutcome(
            outcome_id=f"out-{packet.decision_packet_id}-t0",
            decision_packet_id=packet.decision_packet_id,
            decision_content_hash=packet.content_hash,
            symbol=case.thesis.security_id,
            horizon_trading_days=T0,
            due_at=packet.knowledge_cutoff,
            as_of=packet.as_of,
            knowledge_cutoff=packet.knowledge_cutoff,
            observation_state="recorded",
            claim=claim,
            benchmark_state=BenchmarkState.unavailable_no_series.value,
            benchmark_note="t0 records the claim; no window has elapsed to measure.",
            created_at=created,
        )
    ]
    for horizon in HORIZONS:
        try:
            due = horizon_due_at(packet, horizon)
            state: ObservationState = "recorded"
            note = ""
        except OutcomeError as exc:
            due = packet.expires_at
            state = "unobservable"
            note = str(exc)
        rows.append(
            ThesisOutcome(
                outcome_id=f"out-{packet.decision_packet_id}-{horizon}d",
                decision_packet_id=packet.decision_packet_id,
                decision_content_hash=packet.content_hash,
                symbol=case.thesis.security_id,
                horizon_trading_days=horizon,
                due_at=due,
                as_of=packet.as_of,
                knowledge_cutoff=packet.knowledge_cutoff,
                observation_state=state,
                claim=claim,
                benchmark_state=BenchmarkState.unavailable_no_series.value,
                benchmark_note=note or "not yet due.",
                created_at=created,
            )
        )
    return tuple(rows)


def observe(
    pending: ThesisOutcome,
    *,
    observed_at: date,
    observed_price: Decimal | None,
    price_note: str = "",
    benchmark_start_level: Decimal | None = None,
    benchmark_end_level: Decimal | None = None,
    benchmark_is_proxy: bool = False,
    created_at: datetime | None = None,
) -> ThesisOutcome:
    """Fill one horizon row. Both legs are measured over the SAME window, or the
    leg that could not be measured says so by name."""
    if pending.is_t0:
        raise OutcomeError("the t0 row is a record of the claim and is never observed")
    if pending.observation_state == "observed":
        raise OutcomeError(f"{pending.outcome_id} is already observed; rows are append-only")
    if pending.observation_state == "unobservable":
        raise OutcomeError(f"{pending.outcome_id} has no resolvable due session")
    if observed_at < pending.as_of:
        raise OutcomeError("an observation cannot predate the packet")

    reference = pending.claim.reference_price
    security_return: Decimal | None = None
    if observed_price is None:
        return_state: ReturnLeg = "unavailable_no_price"
        return_note = price_note or f"no price for {pending.symbol} at the {pending.horizon_trading_days}-session horizon"
    elif reference is None:
        return_state = "unavailable_no_price"
        return_note = "the packet recorded no reference price, so no return can be measured against it"
    else:
        security_return = _q(period_return(reference, observed_price) * Decimal("100"))
        return_state = "measured"
        return_note = price_note

    # Governor ruling F1: the proxy overlay is never dressed up as the
    # accumulation benchmark. Reuses the benchmark module's own state names.
    benchmark_return: Decimal | None = None
    if benchmark_is_proxy:
        benchmark_state = BenchmarkState.unavailable_proxy.value
        benchmark_note = (
            "unavailable — the recorded level is the synthetic yield approximation, not the "
            "S&P/ASX 200 Accumulation index (governor ruling F1: never substitute a proxy silently)"
        )
    elif benchmark_start_level is None or benchmark_end_level is None:
        benchmark_state = BenchmarkState.unavailable_no_series.value
        benchmark_note = "benchmark series does not cover this window"
    elif benchmark_start_level <= 0 or benchmark_end_level <= 0:
        benchmark_state = BenchmarkState.unavailable_no_series.value
        benchmark_note = "a benchmark level in this window is not positive"
    else:
        benchmark_return = _q(period_return(benchmark_start_level, benchmark_end_level) * Decimal("100"))
        benchmark_state = BenchmarkState.measured.value
        benchmark_note = ""

    excess = (
        _q(security_return - benchmark_return)
        if security_return is not None and benchmark_return is not None
        else None
    )
    return ThesisOutcome(
        # A NEW id beside the scheduled row, not over it: both are facts, and
        # the 0052 trigger refuses the UPDATE that overwriting would need.
        outcome_id=f"{pending.outcome_id}-observed",
        decision_packet_id=pending.decision_packet_id,
        decision_content_hash=pending.decision_content_hash,
        symbol=pending.symbol,
        horizon_trading_days=pending.horizon_trading_days,
        due_at=pending.due_at,
        as_of=pending.as_of,
        knowledge_cutoff=pending.knowledge_cutoff,
        observation_state="observed",
        claim=pending.claim,
        observed_at=observed_at,
        observed_price=observed_price,
        security_return_pct=security_return,
        return_state=return_state,
        return_note=return_note,
        benchmark_return_pct=benchmark_return,
        benchmark_state=benchmark_state,
        benchmark_note=benchmark_note,
        excess_return_pct=excess,
        created_at=require_utc(created_at or pending.created_at, field_name="created_at"),
    )


def due_horizons(rows: tuple[ThesisOutcome, ...], at: datetime) -> tuple[ThesisOutcome, ...]:
    """Rows whose session has arrived and which have not been observed."""
    at = require_utc(at, field_name="at")
    return tuple(
        r for r in rows
        if not r.is_t0 and r.observation_state == "recorded" and r.due_at <= at
    )


# --- persistence (migration 0052) ------------------------------------------------


class OutcomeConn(Protocol):
    async def execute(self, query: str, *args: object) -> str: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...


SQL_INSERT_OUTCOME: Final[str] = (
    "INSERT INTO thesis_outcomes (outcome_id, content_hash, decision_packet_id, symbol, "
    "horizon_trading_days, due_at, as_of, knowledge_cutoff, observation_state, benchmark_state, "
    "created_at, payload) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb) "
    "ON CONFLICT (outcome_id) DO NOTHING"
)
SQL_LOAD_OUTCOMES: Final[str] = (
    "SELECT payload FROM thesis_outcomes WHERE decision_packet_id = $1 "
    "ORDER BY horizon_trading_days, created_at, outcome_id"
)


def _payload(row: Mapping[str, object]) -> dict[str, Any]:
    raw = row["payload"]
    if isinstance(raw, str):
        return dict(json.loads(raw))
    if isinstance(raw, Mapping):
        return dict(raw)
    raise TypeError(f"unexpected payload column type: {type(raw)!r}")


async def save_outcome(conn: OutcomeConn, outcome: ThesisOutcome) -> None:
    """Append one row. An observation carries its own `outcome_id` and lands
    beside the row that scheduled it — never over it. The 0052 trigger refuses
    the UPDATE that overwriting would require, and the scheduled row stays as
    the record of what was promised and when."""
    await conn.execute(
        SQL_INSERT_OUTCOME,
        outcome.outcome_id, outcome.content_hash, outcome.decision_packet_id, outcome.symbol,
        outcome.horizon_trading_days, outcome.due_at, outcome.as_of, outcome.knowledge_cutoff,
        outcome.observation_state, outcome.benchmark_state, outcome.created_at,
        json.dumps(outcome.model_dump(mode="json")),
    )


async def load_outcomes(conn: OutcomeConn, decision_packet_id: str) -> tuple[ThesisOutcome, ...]:
    rows = await conn.fetch(SQL_LOAD_OUTCOMES, decision_packet_id)
    return tuple(ThesisOutcome.model_validate(_payload(r)) for r in rows)
