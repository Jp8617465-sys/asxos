"""Deterministic thesis-discipline evaluator — pure, model-independent.

PR1 of the portfolio-team-visibility lane
(`docs/proposals/portfolio-team-visibility-2026-07-12.md`). This module is the
compute core the `/pm-review` analysis agents' *deterministic* dimensions reduce
to (~80-90% of what "the portfolio team flags"): revisit cadence, trajectory
pace, stop/target, conviction coherence, concentration, unrealised return, and
the unanswered-data-sanity escalation. It takes
already-loaded thesis + portfolio data and returns an ordered list of discipline
findings. It composes the existing pure functions in
`asxos.domain.brief.severity` and `asxos.domain.theses.trajectory`, adds
net-new checks (conviction-unset, data-sanity, and the data-sanity unanswered
escalation), and wraps every check so a check
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

# Escalation threshold for an unanswered data-sanity red: one full revisit
# cadence, so a red that outlives it has — by the system's own cadence
# definition — been ignored for a whole cycle. Strictly-greater-than, matching
# `_timeline`'s strictly-past-deadline red.
#
# This 30 has a RUNTIME TWIN: `asxos/domain/theses/service.py:44`
# `_REVISIT_INTERVAL_DAYS = 30`, which is what actually sets `revisit_due_at` on
# every revisit (migration 0012's DEFAULT only covers the INSERT). The design
# says the two must be equal; they cannot be shared by import, because
# `service.py` pulls in asyncpg and this module is DB-free by contract (see the
# module docstring). `tests/test_thesis_discipline.py` carries the drift guard
# that fails if they diverge — change one, change the other.
_DATA_SANITY_UNANSWERED_ESCALATION_DAYS = 30


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
    # True when the finding describes a WATCHLIST row — a thesis with no capital
    # behind it. Such a finding is real and must be displayed, but it is not
    # evidence that any *holding* was examined, so `BriefData.review` excludes it
    # when deciding whether to raise the "N holding(s) with no discipline
    # evidence" unknown. Without this, one watchlist escalation could make a
    # wholly unchecked portfolio stop reporting that it is unchecked — the same
    # side-door the `info`-level exclusion already closes for CGT facts.
    #
    # Defaulting to False is safe *because the loader is the only producer that
    # can know a row's status*: every other call site here evaluates active
    # theses or portfolio aggregates, which are holding-scoped by construction.
    # A future watchlist-fed check must set this explicitly (and be tested).
    watchlist_only: bool = False


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
    # Date of the latest `thesis_revisions` row whose `revision_type` could
    # plausibly ANSWER a broken-ladder red (target adjusted / reviewed-no-change
    # / status change / terminal) — see `data_sanity_escalation`. ``None`` when
    # no such revision exists (a thesis carrying only its `opened` row), which
    # the check reads as "never answered" and anchors on ``opened_at``.
    #
    # Deliberately NOT defaulted, like every other field here: a caller that
    # omitted it would silently get the most escalation-prone anchor
    # (``opened_at``), i.e. confident false escalations on every old detached
    # thesis. Required means mypy names any new construction site instead.
    last_answering_revision_at: date | None


@dataclass(frozen=True)
class HoldingWeight:
    """One holding's AUD market value, for the concentration check (already AUD)."""

    symbol: str
    market_value_aud: Decimal


@dataclass(frozen=True)
class PortfolioDisciplineInput:
    """Portfolio-level inputs (holdings' AUD market values, for concentration)."""

    holdings: tuple[HoldingWeight, ...]


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


def _fmt_price(value: Decimal) -> str:
    """Render a NUMERIC(18,6) price without its trailing zeros — or its precision.

    ``prices.close`` and the thesis ladder arrive as NUMERIC(18,6), so a raw
    render reads "168.000000". A blanket ``:.2f`` (as ``unrealised_return``
    uses, where the values are always ordinary share prices) would instead
    print a genuinely small figure as "0.00" — a *wrong* number in a message
    whose whole purpose is to show the user his own recorded data. Trim the
    zeros; keep whatever significant digits remain.
    """
    trimmed = value.normalize()
    if trimmed == trimmed.to_integral_value():
        # normalize() renders integral values in exponent form (1.68E+2).
        trimmed = trimmed.quantize(Decimal("1"))
    return f"{trimmed:f}"


def _detached_ladder(
    inp: ThesisDisciplineInput,
) -> tuple[Decimal, Decimal, Decimal] | None:
    """``(current, target, multiple)`` when the ladder is detached, else ``None``.

    The single shared predicate behind both :func:`_data_sanity` (which reports
    it) and :func:`data_sanity_escalation` (which escalates it once unanswered),
    so the threshold and the arithmetic exist once. Returning the operands as
    well as the verdict is what lets both callers format a message without
    re-deriving the multiple or re-declaring the ``None`` guards.

    A live price ≥ ``_DATA_SANITY_TARGET_MULTIPLE`` × target signals a
    stale/broken ladder (data-entry error), not a genuine hit. The comparison
    stays in multiplication form — dividing first and comparing the quotient to
    2 would let ``Decimal`` division rounding decide a boundary case. Both
    prices are native (R10).
    """
    current = inp.current_price_native
    target = inp.target_price_native
    if current is None or target is None or target <= 0:
        return None
    if current < _DATA_SANITY_TARGET_MULTIPLE * target:
        return None
    return current, target, current / target


def _data_sanity(inp: ThesisDisciplineInput) -> DisciplineFinding | None:
    """Red when the live price is an implausible multiple of the recorded target."""
    detached = _detached_ladder(inp)
    if detached is None:
        return None
    current, target, multiple = detached
    return DisciplineFinding(
        check="data_sanity",
        level=DisciplineLevel.red,
        message=(
            f"{inp.symbol}: live price {current} is {multiple:.1f}× the recorded "
            f"target {target} — likely stale/broken thesis data, review"
        ),
        symbol=inp.symbol,
    )


def data_sanity_escalation(
    inp: ThesisDisciplineInput, as_of: date
) -> DisciplineFinding | None:
    """Escalated red when a data-sanity red has sat unanswered past one revisit cadence.

    The escalation half of James's 2026-07-16 ruling (`docs/product/james-inbox.md`,
    the CBA row): :func:`_data_sanity` already *detects* a detached ladder (live
    price ≥ 2× the recorded target); this check escalates it once it has carried
    for more than ``_DATA_SANITY_UNANSWERED_ESCALATION_DAYS`` days with no
    thesis-revision activity, and names the exact CLI verb that answers it.

    **"Unanswered", derived without a schema change.** Findings are computed
    fresh each run and never persisted, so "when did this red first appear?"
    has no stored answer. The derivable measure is ``thesis_revisions`` (the
    append-only event log): the answers available to James — correcting the
    target, a deliberate ``reviewed_no_change`` hold, a status change, retiring
    the row — each land there as a row, so *days since the latest such row*
    (``last_answering_revision_at``, falling back to ``opened_at``) measures how
    long the thesis has gone without a response.

    **The proxy errs in BOTH directions; neither is silent-by-design.** The
    loader narrows the subquery to answering ``revision_type``s precisely so
    that "a revision acknowledges the red" is true *by construction* — without
    that filter, a ``--tax-notes`` or ``--conviction`` edit (or an appended
    report section) would reset the clock while leaving the ladder untouched,
    and for a ``watching`` row that means TOTAL silence, since the base
    :func:`_data_sanity` red never runs on watchlist rows. Residual error each
    way, stated plainly:

    * *Over-escalation*: a thesis already dormant for > N days escalates on the
      first day the price crosses the 2× line, since the clock predates the red.
    * *Under-escalation*: an answering-type revision that does not actually fix
      the ladder (a ``reviewed_no_change`` hold, say) buys another N days.

    Both are bounded by one property: ``INSERT INTO thesis_revisions`` exists in
    exactly one module (``theses/service.py``), and every **clock reset** is a
    human keystroke — no job, agent or model can suppress this finding. One
    job-authored row type exists (``packet_examined``, migration 0060, written
    by ``jobs/build_decision_packets.py`` through the narrow
    ``record_system_examination`` entry): it records that the system built a
    packet against the thesis, it sits OUTSIDE the answering allowlist the
    brief's ``last_answering_revision_at`` subquery counts, and it never
    touches ``last_revisited_at`` — so it cannot answer a red, cannot reset the
    clock, and cannot suppress this finding. A system examination is not a
    human revisit.

    **s766B.** "Correct or retire" applies to the thesis ROW — a stale
    *record* — never to a holding. Evidence + arithmetic + the maintenance
    verb only; no trade-direction vocabulary (and no "close", per
    :func:`_timeline`'s precedent). The ``--target`` verb stays on the record
    side **only because the message emits the literal placeholder
    ``<corrected>`` and never a computed number**: a price target is the
    canonical form of an opinion about a financial product, so interpolating
    one here would cross s766B(3) no matter how the sentence were framed. The
    wording tests pin both the placeholder and the vocabulary. Pure and
    read-only: this path emits a finding; it never writes ``theses``,
    ``thesis_revisions`` or ``governance_events``. A human acts.

    **Known limitation (reported, not worked around).** ``asx thesis revise``
    addresses a thesis by SYMBOL, resolving via ``get_thesis_by_symbol``
    (``ORDER BY opened_at DESC LIMIT 1``, no status filter), and
    ``open_thesis`` has no duplicate-symbol guard. For a symbol carrying more
    than one thesis row the emitted command can therefore land on a different
    row than the one that fired this finding. This check knows the right row;
    the CLI has no id-addressed ``revise`` to name (``approve``/``reject`` take
    a ``thesis_id``, ``revise`` does not). Naming an id-addressed verb that
    does not exist would be worse than naming the real one — fix belongs in the
    CLI.

    Loader-appended (like :func:`unrealised_return`) rather than folded into
    :func:`evaluate_thesis`: the brief loader runs this over ``watching`` AND
    ``active`` theses (the live CBA example is a ``watching`` row), while
    ``evaluate_thesis``'s full check battery stays active-only.
    """
    detached = _detached_ladder(inp)
    if detached is None:
        return None
    current, target, multiple = detached
    answered_at = inp.last_answering_revision_at or inp.opened_at
    silent_days = (as_of - answered_at).days
    if silent_days <= _DATA_SANITY_UNANSWERED_ESCALATION_DAYS:
        return None
    # `expired` — "thesis invalidated or timeline lapsed without entry"
    # (migration 0012) — is the terminal state for a RECORD that was never
    # acted on. Do not "correct" this to `exited`: that word means a position
    # was closed, which is a trade direction, and the s766B wording test bans
    # it (`exited` is in the banned list; `expired` is not, deliberately).
    return DisciplineFinding(
        check="data_sanity_escalation",
        level=DisciplineLevel.red,
        message=(
            f"{inp.symbol}: detached thesis ladder — no answering revision for "
            # "no answering revision since", NOT "nothing since": the subquery
            # is scoped to answering revision types, so unrelated edits after
            # this date are invisible here and "nothing" would be false.
            f"{silent_days}d (no answering revision since {answered_at}); live price "
            f"{_fmt_price(current)} is {multiple:.1f}× the recorded target "
            f"{_fmt_price(target)}. The thesis record looks stale; correct it: "
            f'asx thesis revise {inp.symbol} --target <corrected> --reason "..." '
            f"— or retire the record: asx thesis revise {inp.symbol} "
            f'--status expired --reason "..."'
        ),
        symbol=inp.symbol,
    )


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
    # Name the leg that actually decided the verdict. The message previously
    # interpolated `target` for EVERY state, so a stop-out read
    # "STOP VIOLATED (current 215.170000, target 318.000000)" — the 230.00 stop
    # that fired was invisible, and the one number shown was the one number the
    # classification had not used. A reader cannot check a stop-out against a
    # target; on the live HUBS.NYSE thesis that is a ~88-point difference
    # between the figure printed and the figure the verdict rested on.
    #
    # ABOVE_TARGET keeps `target` because there the target IS the deciding leg
    # (`current >= target`, trajectory.py:79). The pace bands keep it too — it
    # is the denominator of progress_to_target(). Only the stop-out branch was
    # ever wrong, and it was wrong in the one state that calls for action.
    #
    # stop_price_native is non-None here by construction: STOP_VIOLATED is
    # returned only under `stop_price is not None` (trajectory.py:77). The
    # explicit guard is for the type checker and for the next reader, not a
    # runtime doubt — falling back to `target` would silently reinstate the
    # exact defect this block removes.
    if traj is Trajectory.STOP_VIOLATED and inp.stop_price_native is not None:
        reference = f"stop {_fmt_price(inp.stop_price_native)}"
    else:
        reference = f"target {_fmt_price(target)}"
    return DisciplineFinding(
        check="trajectory",
        level=level,
        # _fmt_price, not raw interpolation: these arrive as NUMERIC(18,6), so
        # the bare Decimal rendered "215.170000". Same helper
        # `data_sanity_escalation` uses, for the reason _fmt_price's docstring
        # gives — trim the zeros, keep the significant digits, never
        # blanket-:.2f a legitimately small price (0.004 would become "0.00").
        #
        # NOT `_data_sanity`, which still interpolates raw Decimals (:249-251)
        # and ships "live price 168.000000 is 2.8× the recorded target
        # 60.000000" into the same email. That is a sibling red finding with
        # the same defect this fixes; routing it through _fmt_price is
        # behaviour-visible, so it needs its own assertion rather than a
        # drive-by here.
        message=f"{inp.symbol}: {traj} (current {_fmt_price(current)}, {reference})",
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


def unrealised_return(inp: ThesisDisciplineInput) -> DisciplineFinding | None:
    """Unrealised return since thesis entry — native price only (R10, s766B).

    ``(current − entry) / entry`` in the holding's native currency (both legs
    native, exactly like the trajectory check — no FX step, so the
    ``cost_base_normal`` ÷ quantity currency trap is structurally impossible).
    This is the local, currency-neutral return a broker headlines: for a USD
    holding it is the USD price return (the FX cancels), which is why it
    reconciles with the brokerage line. It REPLACES the removed portfolio-level
    "total return vs benchmark" line, which differenced a flow-affected
    ``capital_aud`` snapshot balance (a static cash placeholder that later
    vanished) and reported a false −75.7% loss.

    Price-only ``info`` fact: excludes dividends, realised gains, and the AUD/FX
    translation — deliberately NOT a total return and NOT a benchmark comparison,
    and it carries no trade direction (s766B). Emitted for display, so the loader
    appends it rather than folding it into the quiet-by-default per-thesis problem
    checks (mirrors how the CGT-boundary info line is appended, not evaluated).
    """
    entry = inp.entry_price_native
    current = inp.current_price_native
    if entry is None or current is None or entry <= 0:
        return None
    pct = (current - entry) / entry * Decimal("100")
    return DisciplineFinding(
        check="unrealised_return",
        level=DisciplineLevel.info,
        message=(
            f"{inp.symbol}: {pct:+.1f}% unrealised since entry "
            f"({inp.currency} {entry:.2f} → {current:.2f}; price only, "
            f"excludes dividends & FX — not a total return)"
        ),
        symbol=inp.symbol,
    )


def evaluate_portfolio(
    inputs: tuple[ThesisDisciplineInput, ...],
    port: PortfolioDisciplineInput,
    as_of: date,
) -> list[DisciplineFinding]:
    """Portfolio-level discipline findings (conviction, concentration)."""
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

    return findings


def evaluate_discipline(
    inputs: tuple[ThesisDisciplineInput, ...],
    port: PortfolioDisciplineInput,
    as_of: date,
) -> list[DisciplineFinding]:
    """The per-thesis check battery followed by the portfolio-level checks.

    **Not the complete finding set — this entry point is not sufficient on its
    own.** Two checks are deliberately *loader-appended* rather than called from
    here, and a caller that uses only this function will silently drop them:

    * :func:`unrealised_return` — an ``info`` display fact, kept out so this
      function stays quiet-by-default (a clean portfolio returns ``[]``).
    * :func:`data_sanity_escalation` — **a red**, kept out because it applies to
      ``watching`` rows too, while everything here is active-thesis scoped. Miss
      it and a stale-record escalation is computed nowhere and shown nowhere.

    ``asxos/brief/compose.py::_discipline_findings`` is the reference caller and
    runs all three. A new consumer (a ``/pm-review`` feed, an ``asx thesis
    discipline`` CLI) must do the same — dropping a red on the floor is exactly
    the "findings computed then invisible" failure this module exists to fix.

    Returns ``[]`` when every thesis is clean of the checks *it* owns and no
    portfolio-level issue fires. An ``error``-level finding in the result means a
    check could not be computed and must be shown loudly, not treated as "no
    finding".
    """
    findings: list[DisciplineFinding] = []
    for inp in inputs:
        findings.extend(evaluate_thesis(inp, as_of))
    findings.extend(evaluate_portfolio(inputs, port, as_of))
    return findings
