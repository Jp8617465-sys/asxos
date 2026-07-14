"""Deterministic thesis-discipline evaluator — pure, model-independent.

PR1 of the portfolio-team-visibility lane
(`docs/proposals/portfolio-team-visibility-2026-07-12.md`). This module is the
compute core the `/pm-review` analysis agents' *deterministic* dimensions reduce
to (~80-90% of what "the portfolio team flags"): revisit cadence, trajectory
pace, stop/target, conviction coherence, concentration, benchmark lag. It takes
already-loaded thesis + portfolio data and returns an ordered list of discipline
findings. It composes the existing pure functions in
`asxos.domain.brief.severity` and `asxos.domain.theses.trajectory`, adds two
net-new checks (conviction-unset, data-sanity), and wraps every check so a check
that *cannot run* surfaces LOUDLY as an ``error`` finding rather than vanishing.

**No DB, no infra, no email.** A later PR (PR2) wires a loader + a brief section
(or cron) around this; PR1 ships wired to nothing and fully unit-tested.

**Model-independent by construction (CLAUDE.md rule #11).** Reads only
thesis-authored fields (entry/stop/target/timeline/revisit/conviction) and a
current native price. It never reads ``signals`` / ``shap_factors`` /
``prob_up`` / ``expected_return`` / ``signals.regime``, never calls
``resolve_production_model()``, and never invokes ``thesis-coherence-guard``
(whose verdict *is* a Model A read). If a future check needs a model input, it
does not belong here.

**Currency safety (R10, `.claude/rules/portfolio-conventions.md`).** The
trajectory / stop / data-sanity checks anchor on ``entry_price_native`` (the
thesis's own ``actual_entry_price``, in the holding's native currency) and
compare it to ``current_price_native`` (``prices.close``, native) — **both
native, same currency**, so no FX step is needed here and the
``cost_base_normal`` (AUD) ÷ quantity trap that produced the false HUBS "−29%"
is structurally impossible in this module. The loader (PR2) is responsible for
passing native-against-native; portfolio-level figures (concentration, benchmark
lag) arrive already in AUD from ``portfolio_daily_snapshots`` (which are AUD by
construction). This module never mixes the two.

**s766B firewall (`.claude/rules/portfolio-conventions.md`).** Every message is
evidence + arithmetic on the user's own authored data, framed for *his* review.
No trade direction, no recommendation, no opinion on a holding's merit, no
inferred objective. "review overdue", "N× the target", "X% of portfolio" — never
"sell", "trim", "exit", or "overvalued".

Pure ``Decimal`` throughout; no numpy (portfolio conventions).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from asxos.domain.brief import severity
from asxos.domain.brief.types import SeverityItem, SeverityLevel
from asxos.domain.theses.trajectory import Trajectory, classify_trajectory

# A live price at or above this multiple of the target is almost certainly a
# stale/broken thesis ladder (e.g. CBA recorded target 60 vs live ~168 = 2.8×),
# not a genuine "above target" hit. Surfaced as a data-sanity finding and used to
# suppress the spurious ABOVE_TARGET the trajectory check would otherwise emit.
_DATA_SANITY_TARGET_MULTIPLE = Decimal("2")


class DisciplineLevel(StrEnum):
    """Finding severity.

    ``error`` is distinct from ``red``: it means a check *could not be computed*
    (bad/missing data), which must be surfaced loudly — never silently dropped —
    because a silently-skipped check is the exact failure mode
    (findings computed then invisible) this whole lane exists to fix.
    """

    red = "red"
    yellow = "yellow"
    info = "info"
    error = "error"


@dataclass(frozen=True)
class DisciplineFinding:
    """One discipline observation. ``symbol`` is ``None`` for portfolio-level findings."""

    check: str
    level: DisciplineLevel
    message: str
    symbol: str | None = None


@dataclass(frozen=True)
class ThesisDisciplineInput:
    """Per-thesis inputs for the discipline checks.

    All price fields are in ``currency`` (the holding's native currency). The
    loader (PR2) must supply ``entry_price_native`` from the thesis's
    ``actual_entry_price`` and ``current_price_native`` from ``prices.close`` —
    never ``cost_base_normal`` ÷ quantity, which is AUD (R10).
    """

    symbol: str
    # ``currency`` is descriptive metadata only — the evaluator never reads it for
    # arithmetic. Native-consistency across the four price legs is the loader's
    # (PR2's) contract, not something this pure module can enforce (R10).
    currency: str
    revisit_due_at: date
    opened_at: date
    timeline_days: int | None
    entry_price_native: Decimal | None
    current_price_native: Decimal | None
    target_price_native: Decimal | None
    stop_price_native: Decimal | None
    conviction_level: int | None


@dataclass(frozen=True)
class HoldingWeight:
    """One holding's AUD market value, for the concentration check (already AUD)."""

    symbol: str
    market_value_aud: Decimal


@dataclass(frozen=True)
class PortfolioDisciplineInput:
    """Portfolio-level inputs (all AUD, from ``portfolio_daily_snapshots``)."""

    holdings: tuple[HoldingWeight, ...]
    portfolio_tr_aud: Decimal | None
    benchmark_tr_aud: Decimal | None


# Portfolio lags its benchmark by more than this (percentage points of total
# return) → surface it. A starting prior, not a calibrated threshold.
_BENCHMARK_LAG_PP = Decimal("5")


def _err(check: str, symbol: str | None, exc: Exception) -> DisciplineFinding:
    """Build the loud 'this check could not run' finding (never swallow silently)."""
    where = f" for {symbol}" if symbol else ""
    return DisciplineFinding(
        check=check,
        level=DisciplineLevel.error,
        message=f"⚠ {check} could not run{where}: {exc}",
        symbol=symbol,
    )


def _from_severity(
    check: str, item: SeverityItem, symbol: str | None = None
) -> DisciplineFinding:
    """Translate a reused ``SeverityItem`` (red/yellow/green) into a DisciplineFinding.

    ``symbol`` defaults to ``None`` because the severity messages already embed
    their own symbol (revisit, timeline); the concentration check passes it
    explicitly so per-holding findings stay attributable.
    """
    level = (
        DisciplineLevel.red
        if item.level is SeverityLevel.red
        else DisciplineLevel.yellow
    )
    return DisciplineFinding(
        check=check, level=level, message=item.message, symbol=symbol
    )


def _data_sanity(inp: ThesisDisciplineInput) -> DisciplineFinding | None:
    """Red when the live price is an implausible multiple of the recorded target.

    A live price ≥ ``_DATA_SANITY_TARGET_MULTIPLE`` × target signals a stale/broken
    ladder (data-entry error), not a genuine hit. Both prices are native (R10).
    """
    current = inp.current_price_native
    target = inp.target_price_native
    if current is None or target is None or target <= 0:
        return None
    if current >= _DATA_SANITY_TARGET_MULTIPLE * target:
        multiple = current / target
        return DisciplineFinding(
            check="data_sanity",
            level=DisciplineLevel.red,
            message=(
                f"{inp.symbol}: live price {current} is {multiple:.1f}× the recorded "
                f"target {target} — likely stale/broken thesis data, review"
            ),
            symbol=inp.symbol,
        )
    return None


def _trajectory(inp: ThesisDisciplineInput, as_of: date) -> DisciplineFinding | None:
    """Pace / terminal-state finding via ``classify_trajectory`` (all native, R10-safe).

    Requires an anchor, a current price, a target and a positive timeline to
    classify pace. STOP_VIOLATED / STALLED → red; BEHIND / ABOVE_TARGET → yellow;
    ON_TRACK → no finding. Returns ``None`` when inputs are insufficient to
    classify (the missing pieces surface via their own checks / the loader).
    """
    anchor = inp.entry_price_native
    current = inp.current_price_native
    target = inp.target_price_native
    if anchor is None or current is None or target is None:
        return None
    if inp.timeline_days is None or inp.timeline_days <= 0:
        return None
    elapsed = (as_of - inp.opened_at).days
    traj = classify_trajectory(
        current_price=current,
        anchor=anchor,
        target_price=target,
        stop_price=inp.stop_price_native,
        elapsed_days=elapsed,
        timeline_days=inp.timeline_days,
    )
    if traj is Trajectory.ON_TRACK:
        return None
    level = (
        DisciplineLevel.red
        if traj in (Trajectory.STOP_VIOLATED, Trajectory.STALLED)
        else DisciplineLevel.yellow
    )
    return DisciplineFinding(
        check="trajectory",
        level=level,
        message=f"{inp.symbol}: {traj} (current {current}, target {target})",
        symbol=inp.symbol,
    )


def _timeline(inp: ThesisDisciplineInput, as_of: date) -> DisciplineFinding | None:
    """Timeline expiry / near-expiry — evidence-only wording (s766B).

    Deliberately does NOT reuse ``severity.thesis_timeline_expired``'s message:
    that message ends with "— review or close", and "close" reads as a trade
    direction (exit), which the digest firewall (proposal §7) forbids and holds
    *tighter* than the brief's alert wording. We re-derive the same
    classification (red past the deadline, yellow within 14 days) but emit only
    the date arithmetic — no action verb.
    """
    if inp.timeline_days is None:
        return None
    deadline = inp.opened_at + timedelta(days=inp.timeline_days)
    days_remaining = (deadline - as_of).days
    if days_remaining < 0:
        return DisciplineFinding(
            check="timeline",
            level=DisciplineLevel.red,
            message=(
                f"{inp.symbol}: thesis timeline elapsed {-days_remaining}d ago "
                f"(deadline {deadline})"
            ),
            symbol=inp.symbol,
        )
    if days_remaining <= 14:
        return DisciplineFinding(
            check="timeline",
            level=DisciplineLevel.yellow,
            message=f"{inp.symbol}: thesis timeline ends in {days_remaining}d ({deadline})",
            symbol=inp.symbol,
        )
    return None


def _missing_price_legs(inp: ThesisDisciplineInput) -> DisciplineFinding | None:
    """Info finding when a price leg is missing, symmetric with ``no_stop_set``.

    A thesis missing entry/current/target silently no-ops the trajectory and
    data-sanity checks; surface that as an ``info`` finding rather than let an
    incomplete thesis pass as clean (the silent-omission pattern this lane fixes).
    """
    missing = [
        name
        for name, value in (
            ("entry", inp.entry_price_native),
            ("current", inp.current_price_native),
            ("target", inp.target_price_native),
        )
        if value is None
    ]
    if not missing:
        return None
    return DisciplineFinding(
        check="incomplete_price_data",
        level=DisciplineLevel.info,
        message=(
            f"{inp.symbol}: incomplete price data ({', '.join(missing)} missing) — "
            "trajectory/data-sanity checks skipped"
        ),
        symbol=inp.symbol,
    )


def evaluate_thesis(
    inp: ThesisDisciplineInput, as_of: date
) -> list[DisciplineFinding]:
    """All per-thesis discipline findings for one active thesis, in a stable order.

    Every check is independently guarded: a check that raises yields a loud
    ``error`` finding, never a silent omission. A clean thesis yields ``[]``.
    """
    findings: list[DisciplineFinding] = []

    # 1. Revisit cadence (reuses the tested severity function).
    try:
        item = severity.thesis_revisit_overdue(
            inp.symbol, inp.revisit_due_at, as_of
        )
        if item is not None:
            findings.append(_from_severity("revisit_overdue", item))
    except Exception as exc:
        findings.append(_err("revisit_overdue", inp.symbol, exc))

    # 2. Timeline expiry / near-expiry (discipline-owned evidence-only wording).
    #    Broad except: a wrong-typed field must surface as a loud per-check error,
    #    never escape and abort this thesis's other checks (fail-loud isolation).
    try:
        timeline = _timeline(inp, as_of)
        if timeline is not None:
            findings.append(timeline)
    except Exception as exc:
        findings.append(_err("timeline", inp.symbol, exc))

    # 3. Data-sanity (broken ladder) — runs BEFORE trajectory so a broken target
    #    doesn't masquerade as ABOVE_TARGET. Broad except (M2): a mistyped input
    #    from the loader raises TypeError, which a narrow Decimal-only catch would
    #    miss — letting it kill the whole batch instead of this one check.
    broken_ladder = False
    try:
        sanity = _data_sanity(inp)
        if sanity is not None:
            findings.append(sanity)
            broken_ladder = True
    except Exception as exc:
        findings.append(_err("data_sanity", inp.symbol, exc))

    # 4. Trajectory / pace — suppressed when the ladder is already flagged broken.
    if not broken_ladder:
        try:
            traj = _trajectory(inp, as_of)
            if traj is not None:
                findings.append(traj)
        except Exception as exc:
            findings.append(_err("trajectory", inp.symbol, exc))

    # 5. No stop set — a discipline gap worth surfacing (info, not a breach).
    if inp.stop_price_native is None:
        findings.append(
            DisciplineFinding(
                check="no_stop_set",
                level=DisciplineLevel.info,
                message=f"{inp.symbol}: no stop price set on the thesis",
                symbol=inp.symbol,
            )
        )

    # 6. Incomplete price data — surface rather than silently no-op the price
    #    checks (symmetric with no_stop_set; the silent-omission pattern this
    #    lane fixes).
    incomplete = _missing_price_legs(inp)
    if incomplete is not None:
        findings.append(incomplete)

    return findings


def _conviction_summary(
    inputs: tuple[ThesisDisciplineInput, ...],
) -> DisciplineFinding | None:
    """One portfolio-level line when conviction is unset (R11), else ``None``.

    A single summary rather than per-thesis noise: an unset conviction disables
    the size-vs-conviction coherence check portfolio-wide.
    """
    total = len(inputs)
    if total == 0:
        return None
    unset = sum(1 for i in inputs if i.conviction_level is None)
    if unset == 0:
        return None
    return DisciplineFinding(
        check="conviction_unset",
        level=DisciplineLevel.yellow,
        message=(
            f"conviction unset on {unset}/{total} theses — "
            "size-vs-conviction check disabled (R11)"
        ),
    )


def _benchmark_lag(port: PortfolioDisciplineInput) -> DisciplineFinding | None:
    """Yellow when the portfolio lags its benchmark by > ``_BENCHMARK_LAG_PP`` pp.

    Both legs are AUD total-return levels from ``portfolio_daily_snapshots`` —
    no per-lot FX (R10 does not apply at this level)."""
    p = port.portfolio_tr_aud
    b = port.benchmark_tr_aud
    if p is None or b is None:
        return None
    lag = b - p
    if lag > _BENCHMARK_LAG_PP:
        return DisciplineFinding(
            check="benchmark_lag",
            level=DisciplineLevel.yellow,
            message=(
                f"portfolio total return {p:.1f}% vs benchmark {b:.1f}% — "
                f"lagging by {lag:.1f}pp"
            ),
        )
    return None


def evaluate_portfolio(
    inputs: tuple[ThesisDisciplineInput, ...],
    port: PortfolioDisciplineInput,
    as_of: date,
) -> list[DisciplineFinding]:
    """Portfolio-level discipline findings (conviction, concentration, benchmark)."""
    findings: list[DisciplineFinding] = []

    try:
        conv = _conviction_summary(inputs)
        if conv is not None:
            findings.append(conv)
    except Exception as exc:
        findings.append(_err("conviction_unset", None, exc))

    # Concentration per holding (AUD MV — already converted upstream).
    try:
        total_mv = sum((h.market_value_aud for h in port.holdings), Decimal("0"))
        for h in port.holdings:
            item = severity.position_concentration(
                h.symbol, h.market_value_aud, total_mv
            )
            if item is not None:
                findings.append(
                    _from_severity("concentration", item, symbol=h.symbol)
                )
    except Exception as exc:  # broad (M2): isolate a mistyped holding, fail loud
        findings.append(_err("concentration", None, exc))

    try:
        lag = _benchmark_lag(port)
        if lag is not None:
            findings.append(lag)
    except Exception as exc:  # broad (M2): isolate a mistyped input, fail loud
        findings.append(_err("benchmark_lag", None, exc))

    return findings


def evaluate_discipline(
    inputs: tuple[ThesisDisciplineInput, ...],
    port: PortfolioDisciplineInput,
    as_of: date,
) -> list[DisciplineFinding]:
    """Top-level: all per-thesis findings followed by all portfolio-level findings.

    Returns ``[]`` when every thesis is clean and no portfolio-level issue fires
    (quiet-by-default — the surface layer emits nothing on an empty list). An
    ``error``-level finding in the result means a check could not be computed and
    must be shown loudly, not treated as "no finding".
    """
    findings: list[DisciplineFinding] = []
    for inp in inputs:
        findings.extend(evaluate_thesis(inp, as_of))
    findings.extend(evaluate_portfolio(inputs, port, as_of))
    return findings
