"""Per-lot outcome vs benchmark — pure Decimal, no DB, no numpy.

The north star's literal stated output is a return that is "benchmark-relative and
risk-controlled" (`docs/product/north-star.md:40`). Until this module there was no
production code behind that sentence: `asxos/domain/benchmark/returns.py` had zero
production consumers, and the brief's only benchmark line had been *removed* —
correctly — because it differenced a flow-affected `portfolio_daily_snapshots.capital_aud`
balance as if it were a return index and printed a false −75.7% loss with a bogus
alpha (`asxos/domain/brief/collectors/wealth_state.py:101-108`).

**This module is the structural closure of that defect class.** It never sees
`capital_aud`. Its portfolio leg is anchored on the user's own acquisition record —
`holding_lots.acquired_at` / `cost_base_normal` — against `prices.close` with an
explicit FX step, per open lot. A lot's cost base cannot be moved by a deposit or a
withdrawal, so no flow can contaminate the return, and there is no snapshot balance
to difference.

What it computes, per open lot:

* the lot's own return since acquisition, in AUD;
* the benchmark's return over the *same* window, from `benchmark_tr_level`;
* alpha (portfolio minus benchmark) — only when both legs are real.

Three governor rulings are load-bearing here and are implemented, not interpreted
(`docs/product/roadmap-state.md:252-254`):

* **F1** — the benchmark is the S&P/ASX 200 Accumulation index. `AXJO.INDX` is
  price context only and *must never carry a total-return label*. When
  `benchmark_tr_level` came from the synthetic yield overlay rather than the real
  accumulation index (`jobs/snapshot_portfolio.py:63-92,274-290` —
  `AXJOA.INDX` absent from `prices`, recorded by a non-NULL
  `trailing_div_yield_pct`), this module reports the measurement as
  **unavailable** and names the proxy as the reason. It never silently substitutes.
* **F2** — global exposure is a *separately reported sleeve*. `HUBS.NYSE` is never
  blended into the ASX benchmark comparison; the global sleeve carries no benchmark
  at all, because F1 approved one only for the ASX sleeve.
* **F4** — everything here is reporting-only.

**Currency correctness (R10, `.claude/rules/portfolio-conventions.md` §"`cost_base_normal`
currency — it is the AUD tax base, not native").** `cost_base_normal` is the AUD CGT
cost base, FX-converted at the lot's acquisition rate — it is **not**
`quantity × native_price`. For HUBS.NYSE lot id=1, `cost_base_normal = 6978.23` AUD
= 24 sh × US$187.54 ÷ 0.6450. Dividing it by `quantity` and comparing the result to a
USD `prices.close` is a currency error; it is the error that made the 2026-07-11
`/pm-review` report HUBS at −29% and stop-violated when the lot was ≈ +9.8% in USD.
This module therefore converts **both legs forward into AUD**: the cost leg is already
AUD, and the market leg is `quantity × close ÷ AUDUSD` for a foreign symbol
(AUDUSD = USD per 1 AUD, so USD → AUD divides). It never divides a cost base by a
quantity, in any branch.

**Decimal-only** (`.claude/rules/portfolio-conventions.md` §"Decimal-only arithmetic").
No numpy, no float, no DB handle. Every unavailable outcome is a named state with a
printed reason — never a silent zero, because a rendered 0.0% is indistinguishable
from a measured flat return and that is the same class of lie as the −75.7%.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from asxos.domain.benchmark.returns import alpha, period_return
from asxos.domain.prices.fx import is_foreign_symbol

#: Working precision for money and for return fractions. Matches the NUMERIC(18,6)
#: convention every monetary column in this schema uses (CLAUDE.md #5); on a
#: fraction, 1e-6 is 0.0001% — far finer than anything the brief prints.
_SCALE = Decimal("0.000001")

#: How far a benchmark anchor may sit *before* the date it is anchoring, in calendar
#: days, before the window stops being the same window.
#:
#: The benchmark level comes from `portfolio_daily_snapshots`, which is written only
#: on days the price pipeline ran — so the snapshot nearest an acquisition date is
#: routinely a day or two earlier (weekend, public holiday, a missed cron). Five days
#: absorbs a long weekend plus a holiday. Beyond that the anchor is measuring a
#: materially different window than the lot's, and quietly using it would reintroduce
#: exactly the "compare two things that are not the same thing" failure this module
#: exists to close — so it is reported unavailable instead.
#:
#: Public because the brief's loader bounds its snapshot query by the same number.
#: One constant, so the query window and the acceptance rule cannot drift apart —
#: a loader that fetched a narrower window than this rule accepts would silently
#: downgrade measurable lots to `unavailable_no_series`.
MAX_ANCHOR_LAG_DAYS = 5


class Sleeve(StrEnum):
    """Reporting sleeve. Governor ruling F2 — separately reported, never blended."""

    asx = "asx"
    #: `global` is a Python keyword; the trailing underscore is syntax, not meaning.
    global_ = "global"


class ReturnState(StrEnum):
    """Whether the lot's own return could be measured, and if not, why not.

    The two ``stale`` members are the portfolio leg's half of the window
    guarantee — see :data:`MAX_ANCHOR_LAG_DAYS`. Without them this module
    enforced freshness on the benchmark leg only, and a lot priced to a
    three-month-old close against a benchmark priced to today would have
    produced an alpha spanning two different windows: the exact failure the
    module docstring says it exists to prevent, on the other leg.
    """

    measured = "measured"
    unavailable_no_price = "unavailable_no_price"
    unavailable_stale_price = "unavailable_stale_price"
    unavailable_no_fx = "unavailable_no_fx"
    unavailable_stale_fx = "unavailable_stale_fx"
    unavailable_cost_base = "unavailable_cost_base"
    unavailable_quantity = "unavailable_quantity"


class BenchmarkState(StrEnum):
    """Whether the benchmark leg could be measured, and if not, why not.

    ``unavailable_proxy`` is governor ruling F1 in code: the synthetic accumulation
    overlay is a proxy and is never dressed up as a total-return measurement.
    """

    measured = "measured"
    unavailable_proxy = "unavailable_proxy"
    unavailable_no_series = "unavailable_no_series"
    unavailable_window_mismatch = "unavailable_window_mismatch"
    not_applicable_sleeve = "not_applicable_sleeve"


@dataclass(frozen=True)
class Observation:
    """A market value together with the date it was observed.

    The date is load-bearing, not metadata. A bare ``Decimal`` close cannot be
    checked for staleness, so the type makes "a price with no date" impossible
    to construct — the same reason :class:`BenchmarkAnchor` carries its own
    ``as_of`` rather than being a loose level.
    """

    as_of: date
    value: Decimal


@dataclass(frozen=True)
class BenchmarkAnchor:
    """One endpoint of the benchmark window.

    ``level`` is `portfolio_daily_snapshots.benchmark_tr_level` as at ``as_of``.
    ``is_proxy`` is True when that level came from the documented yield overlay
    rather than the real accumulation index — the loader derives it from a non-NULL
    `trailing_div_yield_pct`, which `jobs/snapshot_portfolio.py:274-290` writes for
    exactly that path and leaves NULL for the real index.
    """

    as_of: date
    level: Decimal
    is_proxy: bool


@dataclass(frozen=True)
class LotInput:
    """One open lot plus the market and benchmark facts needed to measure it.

    ``cost_base_aud`` is `holding_lots.cost_base_normal` — **AUD**, R10. Do not pass
    a native-currency cost here and do not divide it by ``quantity`` anywhere.
    ``close`` is `prices.close` in the symbol's own currency; ``fx_audusd`` is
    USD per 1 AUD and is required only for a foreign symbol. Both are dated
    :class:`Observation`s, because both are checked for staleness against the
    measurement date — see :data:`MAX_ANCHOR_LAG_DAYS`.
    """

    lot_id: int
    symbol: str
    quantity: Decimal
    acquired_at: date
    cost_base_aud: Decimal
    close: Observation | None
    fx_audusd: Observation | None
    benchmark_start: BenchmarkAnchor | None
    benchmark_end: BenchmarkAnchor | None


@dataclass(frozen=True)
class LotOutcome:
    """The measured (or explicitly unmeasurable) outcome for one lot.

    Every ``None`` is paired with a state and a human-readable ``note``. Callers and
    templates must render the note rather than defaulting the ``None`` to zero.
    """

    lot_id: int
    symbol: str
    sleeve: Sleeve
    quantity: Decimal
    acquired_at: date
    cost_base_aud: Decimal
    market_value_aud: Decimal | None
    lot_return: Decimal | None
    return_state: ReturnState
    return_note: str
    #: The `prices.close` date the market leg was valued on. Rendered, so the
    #: reader can see which day the number belongs to instead of assuming today.
    priced_at: date | None
    benchmark_return: Decimal | None
    benchmark_state: BenchmarkState
    benchmark_note: str
    benchmark_window: tuple[date, date] | None
    alpha: Decimal | None

    @property
    def is_foreign(self) -> bool:
        """True when the market leg needed an FX step to reach AUD (R10)."""
        return is_foreign_symbol(self.symbol)


@dataclass(frozen=True)
class SleeveOutcome:
    """One sleeve's lots plus the labels that keep F1/F2 visible on the page."""

    sleeve: Sleeve
    label: str
    benchmark_label: str
    lots: tuple[LotOutcome, ...]
    empty_note: str


@dataclass(frozen=True)
class OutcomeSection:
    """Every sleeve, always both, so an empty sleeve is stated rather than absent."""

    as_of: date
    sleeves: tuple[SleeveOutcome, ...]

    @property
    def measured_lot_count(self) -> int:
        return sum(
            1
            for s in self.sleeves
            for lot in s.lots
            if lot.return_state is ReturnState.measured
        )


#: Sleeve presentation. The ASX sleeve names the F1 benchmark; the global sleeve
#: states plainly that it has none, because F1 approved a benchmark for the ASX
#: sleeve only and inventing one for global exposure would be the blend F2 forbids.
_SLEEVE_LABEL: dict[Sleeve, str] = {
    Sleeve.asx: "ASX sleeve",
    Sleeve.global_: "Global sleeve",
}
_SLEEVE_BENCHMARK_LABEL: dict[Sleeve, str] = {
    Sleeve.asx: "S&P/ASX 200 Accumulation (governor ruling F1)",
    Sleeve.global_: (
        "none — governor ruling F1 names a benchmark for the ASX sleeve only, and "
        "ruling F2 keeps this sleeve separate rather than measuring it against one"
    ),
}
_SLEEVE_EMPTY_NOTE: dict[Sleeve, str] = {
    Sleeve.asx: "No open ASX lots — nothing to measure against the ASX benchmark.",
    Sleeve.global_: "No open global lots.",
}


def sleeve_for(symbol: str) -> Sleeve:
    """Which reporting sleeve a symbol belongs to (governor ruling F2).

    Suffix-based, reusing `asxos.domain.prices.fx.is_foreign_symbol` — the codebase's
    single source of truth for "USD-denominated US-exchange symbol" — rather than a
    second copy of the suffix list that could drift from it.
    """
    return Sleeve.global_ if is_foreign_symbol(symbol) else Sleeve.asx


def _is_adjacent(observed: date, target: date) -> bool:
    """True when ``observed`` sits at, or shortly before, ``target``.

    "Shortly" is :data:`MAX_ANCHOR_LAG_DAYS`. An observation dated *after* the
    target is rejected too — every query feeding this module filters
    ``<= as_of``, so a future-dated observation means the caller wired something
    wrong, and silently accepting it would measure a window that has not
    happened yet.
    """
    return 0 <= (target - observed).days <= MAX_ANCHOR_LAG_DAYS


def _market_value_aud(lot: LotInput, as_of: date) -> tuple[Decimal | None, ReturnState, str]:
    """Market value of the lot in AUD, converting the market leg *forward* (R10).

    Never `cost_base_aud / quantity`. For a foreign symbol the native close is
    divided by AUDUSD (USD per 1 AUD) to reach AUD, matching
    `jobs/snapshot_portfolio.py:193-194` and `asxos/brief/compose.py::_holding_weights`.

    Both dated inputs are staleness-checked against ``as_of`` with the same
    tolerance the benchmark leg uses, so a measured return and a measured
    benchmark always describe the same window (see :data:`MAX_ANCHOR_LAG_DAYS`).
    A halted, delisted or sync-gapped symbol therefore degrades to a named
    unavailable rather than being valued at a months-old close — which would
    read as a real, current number.
    """
    if lot.quantity <= 0:
        # A non-positive quantity against a positive cost base computes a value
        # of 0 and a return of exactly −100.00%, which renders as a real,
        # catastrophic-looking result. It is a data defect, so it is named.
        return (
            None,
            ReturnState.unavailable_quantity,
            f"quantity {lot.quantity} is not positive — the lot cannot be valued",
        )
    if lot.close is None:
        return (
            None,
            ReturnState.unavailable_no_price,
            f"no close for {lot.symbol} on or before this date",
        )
    if not _is_adjacent(lot.close.as_of, as_of):
        return (
            None,
            ReturnState.unavailable_stale_price,
            (
                f"latest close for {lot.symbol} is dated {lot.close.as_of}, more than "
                f"{MAX_ANCHOR_LAG_DAYS} days before {as_of} — too stale to compare "
                "with a benchmark measured to this date"
            ),
        )
    if is_foreign_symbol(lot.symbol):
        if lot.fx_audusd is None or lot.fx_audusd.value <= 0:
            return (
                None,
                ReturnState.unavailable_no_fx,
                f"no AUDUSD rate — {lot.symbol} is priced in USD and cannot be stated in AUD",
            )
        if not _is_adjacent(lot.fx_audusd.as_of, as_of):
            return (
                None,
                ReturnState.unavailable_stale_fx,
                (
                    f"latest AUDUSD rate is dated {lot.fx_audusd.as_of}, more than "
                    f"{MAX_ANCHOR_LAG_DAYS} days before {as_of} — {lot.symbol} cannot "
                    "be stated in AUD at a current rate"
                ),
            )
        value = lot.quantity * lot.close.value / lot.fx_audusd.value
    else:
        value = lot.quantity * lot.close.value
    return value.quantize(_SCALE), ReturnState.measured, ""


def _lot_return(
    lot: LotInput, as_of: date
) -> tuple[Decimal | None, Decimal | None, ReturnState, str]:
    """(market_value_aud, return_fraction, state, note) — both legs in AUD."""
    value, state, note = _market_value_aud(lot, as_of)
    if value is None:
        return None, None, state, note
    if lot.cost_base_aud <= 0:
        return (
            value,
            None,
            ReturnState.unavailable_cost_base,
            (
                f"cost base {lot.cost_base_aud} is not positive — a return has no "
                "meaningful base"
            ),
        )
    return value, period_return(lot.cost_base_aud, value).quantize(_SCALE), state, note


def _benchmark_measurement(
    lot: LotInput, sleeve: Sleeve, as_of: date
) -> tuple[Decimal | None, BenchmarkState, str, tuple[date, date] | None]:
    """(return_fraction, state, note, window) for the benchmark leg.

    Order of checks is deliberate: sleeve first (F2), then availability, then the
    proxy veto (F1), then window identity. Each rejection names itself so the brief
    prints why the comparison is absent instead of an unexplained blank.
    """
    if sleeve is not Sleeve.asx:
        return (
            None,
            BenchmarkState.not_applicable_sleeve,
            "not applicable — this sleeve is reported separately (governor ruling F2)",
            None,
        )
    start, end = lot.benchmark_start, lot.benchmark_end
    if start is None or end is None:
        return (
            None,
            BenchmarkState.unavailable_no_series,
            (
                "benchmark series does not cover this window — no level recorded on "
                f"or before {lot.acquired_at if start is None else as_of}"
            ),
            None,
        )
    if start.is_proxy or end.is_proxy:
        # Governor ruling F1. The synthetic overlay is a yield approximation on a
        # PRICE index; reporting it as the accumulation benchmark would be the
        # silent substitution the ruling forbids by name.
        return (
            None,
            BenchmarkState.unavailable_proxy,
            (
                "unavailable — the recorded level is the synthetic yield "
                "approximation, not the S&P/ASX 200 Accumulation index "
                "(governor ruling F1: never substitute a proxy silently)"
            ),
            None,
        )
    if not (
        _is_adjacent(start.as_of, lot.acquired_at) and _is_adjacent(end.as_of, as_of)
    ):
        return (
            None,
            BenchmarkState.unavailable_window_mismatch,
            (
                f"benchmark window {start.as_of} → {end.as_of} does not match the "
                f"lot's {lot.acquired_at} → {as_of} within {MAX_ANCHOR_LAG_DAYS} days"
            ),
            None,
        )
    # BOTH endpoints, not just the start. A non-positive end level renders a
    # benchmark return below −100%, which is not a number any index can produce
    # and would sit next to a real lot return as if it were comparable.
    for label, anchor in (("start", start), ("end", end)):
        if anchor.level <= 0:
            return (
                None,
                BenchmarkState.unavailable_no_series,
                f"benchmark {label} level {anchor.level} at {anchor.as_of} is not positive",
                None,
            )
    return (
        period_return(start.level, end.level).quantize(_SCALE),
        BenchmarkState.measured,
        "",
        (start.as_of, end.as_of),
    )


def build_lot_outcome(lot: LotInput, as_of: date) -> LotOutcome:
    """Measure one lot. Pure; the caller supplies every fact."""
    sleeve = sleeve_for(lot.symbol)
    value, lot_return, return_state, return_note = _lot_return(lot, as_of)
    bench_return, bench_state, bench_note, window = _benchmark_measurement(lot, sleeve, as_of)
    priced_at = lot.close.as_of if lot.close is not None else None

    # No separate cross-leg window check, deliberately — one would be dead code.
    # Both ends are already pinned to `as_of` by `_is_adjacent`: the close in
    # `_market_value_aud`, the benchmark end in `_benchmark_measurement`. Neither
    # may be after `as_of` and neither more than MAX_ANCHOR_LAG_DAYS before it,
    # so whenever both legs are measured their end dates are at most
    # MAX_ANCHOR_LAG_DAYS apart *by construction*. A further check on that gap
    # could never fire, and a check that cannot fire is worse than none: it
    # invites a later reader to relax a per-leg check believing this one backs
    # it up. `test_the_two_legs_can_never_diverge_by_more_than_the_tolerance`
    # asserts the implication instead.
    #
    # The residual, stated rather than hidden: up to MAX_ANCHOR_LAG_DAYS of
    # divergence between the two legs' end dates survives, so alpha carries up
    # to that much benchmark drift. Both dates are rendered on the row
    # ("Valued to X. Window Y → Z."), so the reader can see the gap they are
    # being asked to accept.
    excess = (
        alpha(lot_return, bench_return)
        if lot_return is not None and bench_return is not None
        else None
    )
    return LotOutcome(
        lot_id=lot.lot_id,
        symbol=lot.symbol,
        sleeve=sleeve,
        quantity=lot.quantity,
        acquired_at=lot.acquired_at,
        cost_base_aud=lot.cost_base_aud,
        market_value_aud=value,
        lot_return=lot_return,
        return_state=return_state,
        return_note=return_note,
        priced_at=priced_at,
        benchmark_return=bench_return,
        benchmark_state=bench_state,
        benchmark_note=bench_note,
        benchmark_window=window,
        alpha=excess,
    )


def build_outcome_section(lots: Sequence[LotInput], as_of: date) -> OutcomeSection:
    """Split the lots into sleeves (F2) and measure each one.

    Both sleeves are always present in the result, even when empty: an absent sleeve
    reads as "there is nothing there" and an empty one reads as "we looked and there
    is nothing there". Only the second is true, and only the second survives a lot
    being added tomorrow without anyone noticing the section changed shape.
    """
    by_sleeve: dict[Sleeve, list[LotOutcome]] = {Sleeve.asx: [], Sleeve.global_: []}
    for lot in lots:
        outcome = build_lot_outcome(lot, as_of)
        by_sleeve[outcome.sleeve].append(outcome)
    return OutcomeSection(
        as_of=as_of,
        sleeves=tuple(
            SleeveOutcome(
                sleeve=sleeve,
                label=_SLEEVE_LABEL[sleeve],
                benchmark_label=_SLEEVE_BENCHMARK_LABEL[sleeve],
                lots=tuple(sorted(outcomes, key=lambda o: (o.acquired_at, o.symbol, o.lot_id))),
                empty_note="" if outcomes else _SLEEVE_EMPTY_NOTE[sleeve],
            )
            for sleeve, outcomes in by_sleeve.items()
        ),
    )
