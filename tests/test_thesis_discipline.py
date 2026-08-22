"""Tests for the deterministic thesis-discipline evaluator (PR1).

Covers the acceptance criteria in
`docs/proposals/portfolio-team-visibility-2026-07-12.md` §6: the CBA fixture
(revisit-overdue + data-sanity), the conviction-NULL summary (R11),
quiet-by-default, fail-loud-on-error, model-independence, and the reused
severity/trajectory dimensions.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from asxos.domain.review.status import directive_terms
from asxos.domain.theses.discipline import (
    _DATA_SANITY_UNANSWERED_ESCALATION_DAYS,
    DisciplineLevel,
    HoldingWeight,
    PortfolioDisciplineInput,
    ThesisDisciplineInput,
    data_sanity_escalation,
    evaluate_discipline,
    evaluate_portfolio,
    evaluate_thesis,
    unrealised_return,
)

AS_OF = date(2026, 7, 13)


def _thesis(
    symbol: str = "TST.AU",
    *,
    currency: str = "AUD",
    revisit_due_at: date = date(2026, 8, 1),
    opened_at: date = date(2026, 6, 1),
    timeline_days: int | None = 180,
    entry: str | None = "10",
    current: str | None = "11",
    target: str | None = "15",
    stop: str | None = "9",
    conviction_level: int | None = 3,
    last_answering_revision_at: date | None = None,
) -> ThesisDisciplineInput:
    def _d(v: str | None) -> Decimal | None:
        return None if v is None else Decimal(v)

    return ThesisDisciplineInput(
        symbol=symbol,
        currency=currency,
        revisit_due_at=revisit_due_at,
        opened_at=opened_at,
        timeline_days=timeline_days,
        entry_price_native=_d(entry),
        current_price_native=_d(current),
        target_price_native=_d(target),
        stop_price_native=_d(stop),
        conviction_level=conviction_level,
        last_answering_revision_at=last_answering_revision_at,
    )


_EMPTY_PORT = PortfolioDisciplineInput(holdings=())


def _checks(findings: list) -> set[str]:
    return {f.check for f in findings}


def _by_check(findings: list, check: str) -> list:
    return [f for f in findings if f.check == check]


# --- Quiet-by-default -------------------------------------------------------


def test_clean_thesis_yields_no_findings() -> None:
    # On-track, not overdue, stop set, conviction set → nothing to flag.
    findings = evaluate_thesis(_thesis(), AS_OF)
    assert findings == []


def test_evaluate_discipline_all_clean_is_empty() -> None:
    assert evaluate_discipline((_thesis(),), _EMPTY_PORT, AS_OF) == []


# --- The CBA fixture (acceptance §6) ----------------------------------------


def test_cba_revisit_overdue_and_data_sanity() -> None:
    # CBA-like: revisit due 2026-06-27 (overdue), live 168 vs target 60 (2.8×).
    cba = _thesis(
        symbol="CBA.AU",
        revisit_due_at=date(2026, 6, 27),
        opened_at=date(2026, 1, 1),
        timeline_days=365,
        entry="42",
        current="168",
        target="60",
        stop="38",
        conviction_level=None,
    )
    findings = evaluate_thesis(cba, AS_OF)
    checks = _checks(findings)
    assert "revisit_overdue" in checks
    assert "data_sanity" in checks
    # The broken ladder must SUPPRESS a spurious ABOVE_TARGET trajectory finding.
    assert "trajectory" not in checks
    # Both are red-level.
    by_check = {f.check: f for f in findings}
    assert by_check["revisit_overdue"].level is DisciplineLevel.red
    assert by_check["data_sanity"].level is DisciplineLevel.red
    assert "2.8×" in by_check["data_sanity"].message


# --- Conviction-NULL summary (R11) ------------------------------------------


def test_conviction_summary_when_all_null() -> None:
    theses = tuple(
        _thesis(symbol=f"S{i}.AU", conviction_level=None) for i in range(13)
    )
    findings = evaluate_portfolio(theses, _EMPTY_PORT, AS_OF)
    conv = _by_check(findings, "conviction_unset")
    assert len(conv) == 1
    assert "13/13" in conv[0].message
    assert conv[0].level is DisciplineLevel.yellow
    assert conv[0].symbol is None  # portfolio-level


def test_conviction_no_finding_when_all_set() -> None:
    theses = (_thesis(conviction_level=4), _thesis(symbol="X.AU", conviction_level=2))
    findings = evaluate_portfolio(theses, _EMPTY_PORT, AS_OF)
    assert not _by_check(findings, "conviction_unset")


def test_conviction_partial_null_counts_correctly() -> None:
    theses = (
        _thesis(conviction_level=None),
        _thesis(symbol="X.AU", conviction_level=5),
        _thesis(symbol="Y.AU", conviction_level=None),
    )
    conv = _by_check(
        evaluate_portfolio(theses, _EMPTY_PORT, AS_OF), "conviction_unset"
    )
    assert conv and "2/3" in conv[0].message


# --- Fail-loud on a check that cannot run -----------------------------------


def test_trajectory_error_is_loud_not_silent() -> None:
    # target == anchor makes progress_to_target raise ValueError; it must surface
    # as a loud error finding, never a silent omission.
    broken = _thesis(entry="10", target="10", current="9.5", stop=None)
    findings = evaluate_thesis(broken, AS_OF)
    errs = [f for f in findings if f.level is DisciplineLevel.error]
    assert len(errs) == 1
    assert errs[0].check == "trajectory"
    assert "could not run" in errs[0].message


# --- Reused trajectory / severity dimensions --------------------------------


def test_stop_violated_is_red() -> None:
    t = _thesis(entry="10", current="8.5", target="15", stop="9")
    traj = _by_check(evaluate_thesis(t, AS_OF), "trajectory")
    assert traj and traj[0].level is DisciplineLevel.red
    assert "STOP VIOLATED" in traj[0].message


def test_stop_violated_names_the_stop_not_the_target() -> None:
    """A stop-out must print the stop that fired — it previously printed the target.

    The message interpolated `target` for every trajectory state, so the one
    number shown in a STOP_VIOLATED finding was the one number the
    classification had NOT used (`trajectory.py` decides the stop-out on
    `current_price <= stop_price` and never looks at the target). On the live
    HUBS.NYSE thesis that printed "STOP VIOLATED (current 215.17, target
    318.00)" while the 230.00 stop that fired stayed invisible — an ~88-point
    gap between the figure rendered and the figure the verdict rested on.

    Both halves are asserted: the stop appears AND the target does not. Without
    the negative half a message naming both would pass while still burying the
    stop among numbers the reader has to disambiguate.

    The s766B floor is asserted here too, and this is the place for it: a
    stop-out is the most action-adjacent string the module emits, and until now
    it was the only red-level message with no vocabulary guard at all — the two
    existing guards cover `data_sanity_escalation` and `_timeline` only. `stop`
    is correctly absent from DIRECTIVE_TERMS (it names a field the user himself
    recorded, and the token already shipped inside "STOP VIOLATED" before this
    change), but "correct today" and "pinned" are different things.
    """

    t = _thesis(entry="10", current="8.5", target="15", stop="9")
    traj = _by_check(evaluate_thesis(t, AS_OF), "trajectory")
    assert traj, "expected a trajectory finding"
    assert "STOP VIOLATED" in traj[0].message
    assert "stop 9" in traj[0].message
    assert "target" not in traj[0].message

    assert directive_terms(traj[0].message) == (), (
        f"canonical directive term leaked into a stop-out: "
        f"{directive_terms(traj[0].message)!r}"
    )
    assert _EXTRA_BANNED_FOR_THIS_SURFACE.search(traj[0].message.lower()) is None


def test_above_target_still_names_the_target() -> None:
    """The sibling state keeps `target` — there it IS the deciding leg.

    Guards against over-correcting Unit 5 into "always show the stop". ABOVE
    TARGET is decided by `current >= target`, so naming the stop there would
    reintroduce the same defect in mirror image.
    """

    # Sub-cent, NUMERIC(18,6) target, so this doubles as the only pin on the
    # `target` leg's formatting — every other fixture uses a target that renders
    # identically however it is formatted, leaving that leg unmeasured. At
    # 0.015000 the three candidates diverge: `_fmt_price` gives "0.015", a bare
    # interpolation "0.015000", and a blanket `:.2f` "0.01" — a *different
    # number*. Only the first satisfies both assertions below.
    t = _thesis(entry="0.010", current="0.020", target="0.015000", stop="0.008")
    traj = _by_check(evaluate_thesis(t, AS_OF), "trajectory")
    assert traj and "ABOVE TARGET" in traj[0].message
    assert "target 0.015" in traj[0].message and "0.015000" not in traj[0].message
    assert "stop" not in traj[0].message


def test_trajectory_prices_are_trimmed_not_raw_numeric() -> None:
    """NUMERIC(18,6) must not reach the reader as "8.500000".

    `_fmt_price` already existed for exactly this and was used by
    `_data_sanity`, but the trajectory message interpolated the bare `Decimal`.
    The sub-cent case is the half that matters: a blanket `:.2f` would render a
    legitimately small stop as "0.00" — a *wrong* number in a message whose
    entire purpose is to show the user his own recorded data. Above a cent the
    two formatters agree, so only sub-cent inputs discriminate between them.
    """

    t = _thesis(entry="10", current="8.500000", target="15", stop="9.000000")
    msg = _by_check(evaluate_thesis(t, AS_OF), "trajectory")[0].message
    assert "8.5" in msg and "8.500000" not in msg
    assert "stop 9" in msg and "9.000000" not in msg

    # Sub-cent, because that is the ONLY band where `_fmt_price` and a blanket
    # `:.2f` disagree — and the small-price half of this test is the reason it
    # exists. MEASURED: at 0.01/0.02 (this test's first draft) `:.2f` renders
    # "0.01"/"0.02", byte-identical to `_fmt_price`, so the whole half was
    # vacuous — mutating `_fmt_price(current)` to `{current:.2f}` passed all 32
    # tests. At 0.004/0.005 `:.2f` collapses both to "0.00", printing a stop-out
    # as though the stop sat at zero.
    #
    # Asserted positively (the exact rendered tail), not as `"0.00" not in msg`:
    # "0.004" itself CONTAINS the substring "0.00", so the negative form cannot
    # express this property at any price where it actually bites.
    tiny = _thesis(entry="0.38", current="0.004", target="0.60", stop="0.005")
    tiny_msg = _by_check(evaluate_thesis(tiny, AS_OF), "trajectory")[0].message
    assert tiny_msg.endswith("(current 0.004, stop 0.005)"), tiny_msg


def test_behind_pace_is_yellow() -> None:
    # Well into the timeline but only ~20% of the journey covered → below half the
    # expected linear pace (but clear of the STALLED floor) → BEHIND (yellow).
    t = _thesis(
        opened_at=date(2026, 1, 1),
        timeline_days=200,
        entry="10",
        current="12",  # progress 0.2: not stalled (≥0.05), below pace (<0.48)
        target="20",
        stop="8",
    )
    traj = _by_check(evaluate_thesis(t, AS_OF), "trajectory")
    assert traj and traj[0].level is DisciplineLevel.yellow
    assert "BEHIND" in traj[0].message


def test_no_stop_set_is_info() -> None:
    t = _thesis(stop=None)
    no_stop = _by_check(evaluate_thesis(t, AS_OF), "no_stop_set")
    assert no_stop and no_stop[0].level is DisciplineLevel.info


def test_timeline_expired_is_evidence_only_no_trade_direction() -> None:
    # s766B (M1): the timeline finding must NOT inherit severity.py's "review or
    # close" tail ("close" = exit = a trade direction the digest forbids).
    t = _thesis(opened_at=date(2026, 1, 1), timeline_days=30)  # deadline 2026-01-31
    tl = _by_check(evaluate_thesis(t, AS_OF), "timeline")
    assert tl and tl[0].level is DisciplineLevel.red
    msg = tl[0].message.lower()
    assert "elapsed" in msg and "deadline" in msg
    for banned in ("close", "sell", "trim", "exit", "review or"):
        assert banned not in msg, f"trade-direction wording leaked: {banned}"


def test_incomplete_price_data_is_surfaced_not_silent() -> None:
    # L1: a thesis missing entry/target must not pass as clean — the price checks
    # silently no-op, so surface the gap as an info finding.
    t = _thesis(entry=None, target=None, stop="9")
    incomplete = _by_check(evaluate_thesis(t, AS_OF), "incomplete_price_data")
    assert incomplete and incomplete[0].level is DisciplineLevel.info
    assert "entry" in incomplete[0].message and "target" in incomplete[0].message
    # and the trajectory/data-sanity checks did NOT fire (nothing to compute)
    assert not _by_check(evaluate_thesis(t, AS_OF), "trajectory")
    assert not _by_check(evaluate_thesis(t, AS_OF), "data_sanity")


def test_complete_thesis_has_no_incomplete_finding() -> None:
    assert not _by_check(evaluate_thesis(_thesis(), AS_OF), "incomplete_price_data")


def test_revisit_overdue_message_has_days() -> None:
    t = _thesis(revisit_due_at=date(2026, 6, 27))
    r = _by_check(evaluate_thesis(t, AS_OF), "revisit_overdue")
    assert r and "16d" in r[0].message


# --- Portfolio-level: concentration -----------------------------------------


def test_concentration_red_over_20pct() -> None:
    port = PortfolioDisciplineInput(
        holdings=(
            HoldingWeight("HUBS.NYSE", Decimal("9000")),
            HoldingWeight("VAS.AU", Decimal("1000")),
        ),
    )
    findings = evaluate_portfolio((), port, AS_OF)
    conc = _by_check(findings, "concentration")
    assert conc and conc[0].symbol == "HUBS.NYSE"
    assert conc[0].level is DisciplineLevel.red


# --- Unrealised return (broker-matching, native price only) -----------------


def test_unrealised_return_native_matches_broker() -> None:
    # HUBS-like: USD entry 187.54 → current 224.57 = +19.7% local (the broker's
    # FX-neutral headline). Native-against-native, no cost base, no FX.
    hubs = _thesis(
        symbol="HUBS.NYSE",
        currency="USD",
        entry="187.54",
        current="224.57",
        target="318",
        stop="150",
    )
    f = unrealised_return(hubs)
    assert f is not None
    assert f.check == "unrealised_return"
    assert f.level is DisciplineLevel.info
    assert "+19.7% unrealised since entry" in f.message
    assert "USD 187.54 → 224.57" in f.message
    assert "not a total return" in f.message
    # s766B: evidence-only — no trade direction, no benchmark/alpha framing.
    low = f.message.lower()
    for banned in ("sell", "trim", "exit", "benchmark", "alpha", "lagging"):
        assert banned not in low


def test_unrealised_return_none_without_prices() -> None:
    # Missing entry/current, or a non-positive base → no line (the loader's
    # incomplete-price info finding covers the gap separately).
    assert unrealised_return(_thesis(entry=None)) is None
    assert unrealised_return(_thesis(current=None)) is None
    assert unrealised_return(_thesis(entry="0")) is None


# --- Data-sanity escalation (James's 2026-07-16 CBA ruling) ------------------


def _cba_detached(
    *,
    last_answering_revision_at: date | None,
    opened_at: date = date(2026, 1, 1),
    target: str = "60",
    current: str = "168",
) -> ThesisDisciplineInput:
    """The live worked example's shape: recorded ladder ~60 vs live 168 (2.8×).

    The thesis row is `watching` status in production — status lives at the
    loader level (`_discipline_findings` feeds watching + active theses to this
    check); the pure function sees only the row's dates and prices.
    """
    return _thesis(
        symbol="CBA.AU",
        opened_at=opened_at,
        entry="42",
        current=current,
        target=target,
        stop="38",
        last_answering_revision_at=last_answering_revision_at,
    )


# The load-bearing s766B property (S1): the emitted `--target` flag must carry a
# literal placeholder and NEVER a computed number. A price target is the
# canonical form of an opinion about a financial product — interpolating one
# would cross s766B(3) regardless of the surrounding framing — so this is the
# single assertion keeping the message on the record-maintenance side.
#
# `[\s=]*` NOT `\s+`: typer/click accept `--target=84.00` identically to the
# space form, and a `\s+` guard is blind to it. Verified evadable — a message
# keeping the `<corrected>` placeholder AND appending `(e.g. --target=84.00)`
# passed the whole suite, shipping a computed price target. The companion
# placeholder assertion below does not close this: both hold at once.
_TARGET_FLAG_WITH_A_NUMBER = re.compile(r"--target[\s=]*\S*\d")


def test_escalation_never_emits_a_numeric_price_target() -> None:
    # Across an ordinary ladder, the exact 2.0× boundary, and a sub-cent target
    # (where a naive formatter is most tempted to interpolate) the flag is
    # constant: `--target <corrected>`.
    cases = (
        _cba_detached(last_answering_revision_at=date(2026, 5, 1)),
        _cba_detached(
            last_answering_revision_at=date(2026, 5, 1), target="60", current="120"
        ),
        _cba_detached(
            last_answering_revision_at=date(2026, 5, 1),
            target="0.000001",
            current="168",
        ),
    )
    for inp in cases:
        f = data_sanity_escalation(inp, AS_OF)
        assert f is not None
        assert "--target <corrected>" in f.message
        assert not _TARGET_FLAG_WITH_A_NUMBER.search(f.message), (
            f"a numeric price target leaked into the CLI verb: {f.message}"
        )


def test_cba_unanswered_data_sanity_red_escalates() -> None:
    # Last answering revision 2026-05-01, as_of 2026-07-13 → 73 days of silence
    # while the ladder is detached (> the 30-day cadence) → escalated red that
    # names the exact CLI verbs.
    f = data_sanity_escalation(
        _cba_detached(last_answering_revision_at=date(2026, 5, 1)), AS_OF
    )
    assert f is not None
    assert f.check == "data_sanity_escalation"
    assert f.level is DisciplineLevel.red
    assert f.symbol == "CBA.AU"
    assert "no answering revision for 73d" in f.message
    assert "2.8×" in f.message
    assert "asx thesis revise CBA.AU --target <corrected>" in f.message
    assert "asx thesis revise CBA.AU --status expired" in f.message
    # The pure function never marks watchlist provenance — only the loader,
    # which is the sole holder of the row's status, may set that.
    assert f.watchlist_only is False


def test_escalation_message_leads_with_what_is_measured() -> None:
    # B: the message may claim only revision silence. For a `watching` row the
    # base red was never surfaced (active-only battery), so calling it an
    # "unanswered red" would overstate what is known.
    f = data_sanity_escalation(
        _cba_detached(last_answering_revision_at=date(2026, 5, 1)), AS_OF
    )
    assert f is not None
    assert f.message.startswith("CBA.AU: detached thesis ladder — no answering revision")
    assert "unanswered" not in f.message.lower()


def test_escalation_trims_numeric_price_noise() -> None:
    # NUMERIC(18,6) renders "168.000000" raw; trim to the significant digits…
    f = data_sanity_escalation(
        _cba_detached(last_answering_revision_at=date(2026, 5, 1)), AS_OF
    )
    assert f is not None
    assert "live price 168 is" in f.message
    assert "recorded target 60. The thesis record" in f.message  # 60, not 60.000000
    assert "000000" not in f.message
    # …without rounding a genuinely small figure away to "0.00" (which would be
    # a wrong number about the user's own recorded data).
    small = data_sanity_escalation(
        _cba_detached(last_answering_revision_at=date(2026, 5, 1), target="0.000001"),
        AS_OF,
    )
    assert small is not None
    assert "recorded target 0.000001" in small.message


def test_escalation_boundary_exactly_n_days_is_not_yet_escalated() -> None:
    # Exactly N days of silence is NOT yet escalated (strictly-greater-than,
    # matching _timeline's strictly-past-deadline red); N+1 days is.
    n = _DATA_SANITY_UNANSWERED_ESCALATION_DAYS
    at_boundary = _cba_detached(
        last_answering_revision_at=AS_OF - timedelta(days=n)
    )
    assert data_sanity_escalation(at_boundary, AS_OF) is None

    past_boundary = _cba_detached(
        last_answering_revision_at=AS_OF - timedelta(days=n + 1)
    )
    f = data_sanity_escalation(past_boundary, AS_OF)
    assert f is not None
    assert f"no answering revision for {n + 1}d" in f.message


def test_escalation_window_matches_the_runtime_revisit_interval() -> None:
    """H: the escalation window and the revisit cadence are two independent
    30s the design says must be equal — and nothing else pins either.

    `service.py` (not migration 0012's DEFAULT) is the runtime source: every
    revisit reset goes through Python. It cannot be imported at module scope
    here — it pulls in asyncpg, and `discipline.py` is DB-free by contract — so
    the guard is a test-level equality instead.
    """
    from asxos.domain.theses.service import _REVISIT_INTERVAL_DAYS

    assert _DATA_SANITY_UNANSWERED_ESCALATION_DAYS == _REVISIT_INTERVAL_DAYS


def test_answered_red_does_not_escalate() -> None:
    # The real logic: an answering thesis_revisions row AFTER the red first
    # appeared is a response. The ladder here detached long ago (thesis opened
    # 2026-01-01), but James answered 5 days before as_of — that row resets the
    # clock, so the still-firing base red does NOT escalate.
    answered = _cba_detached(last_answering_revision_at=AS_OF - timedelta(days=5))
    assert data_sanity_escalation(answered, AS_OF) is None
    # The base data-sanity red itself still fires via evaluate_thesis — the
    # answer suppresses only the escalation, never the evidence. (Non-vacuous:
    # the same input escalates once the answer ages past the window.)
    assert _by_check(evaluate_thesis(answered, AS_OF), "data_sanity")
    stale_answer = _cba_detached(
        last_answering_revision_at=AS_OF - timedelta(days=90)
    )
    assert data_sanity_escalation(stale_answer, AS_OF) is not None


def test_no_escalation_without_a_live_data_sanity_red() -> None:
    # A healthy ladder never escalates, no matter how long the revision
    # silence — escalation only ever accompanies a currently-firing red.
    dormant_but_healthy = _thesis(
        opened_at=date(2025, 1, 1), last_answering_revision_at=date(2025, 1, 1)
    )
    assert data_sanity_escalation(dormant_but_healthy, AS_OF) is None


def test_escalation_falls_back_to_opened_at_when_no_answering_revision() -> None:
    # No answering revision → opened_at anchors the clock (a thesis carrying
    # only its 'opened' row has never been answered). Opened 2026-01-01 → 193d.
    f = data_sanity_escalation(
        _cba_detached(last_answering_revision_at=None), AS_OF
    )
    assert f is not None
    assert "no answering revision for 193d" in f.message
    assert "2026-01-01" in f.message


# s766B vocabulary guard.
#
# The CANONICAL list is `asxos/domain/review/status.py::DIRECTIVE_TERMS` /
# `directive_terms()` — production code, pure, importable, exhaustively
# parametrised in tests/test_review_status.py. Assert it as the FLOOR so this
# surface inherits every future addition to it.
#
# An earlier version of this test hand-rolled a regex and claimed to be
# "widened past" the repo's strongest assertion. It was NARROWER on six
# canonical directive terms (accumulate, add, divest, overweight, short,
# underweight) and simultaneously WIDER on `hold`/`holdings`, which
# status.py:64-66 refuses to ban with a documented reason and a pinned test
# (test_review_status.py::test_hold_is_deliberately_not_banned_and_the_gap_is
# _pinned). The suite was asserting both positions ~500 lines apart, each
# unaware of the other. Extras below are what THIS surface additionally
# forbids — they must never contradict the canonical list.
#
# MEASURED (2026-08-17): the canonical guard matches EXACT terms, so
# inflections escape it — `exit`/`sell`/`trim`/`reduce` are caught,
# `exited`/`sold`/`trimmed`/`reduction` are not, and `dispose`/`disposal`
# are absent entirely. The extras below are therefore NOT redundant with the
# canonical list; they are the inflection and nominalisation layer over it.
# Together: canonical = base directive terms (incl. accumulate/add/divest/
# overweight/short/underweight, all six of which the previous hand-rolled
# regex omitted); extras = the forms exact matching cannot reach.
_EXTRA_BANNED_FOR_THIS_SURFACE = re.compile(
    r"\b("
    # Inflections and nominalisations the canonical exact-match guard misses.
    r"sold|selling|bought|buying|trimmed|trimming|"
    r"exited|exiting|reduced|reducing|reduction|"
    r"dispose|disposes|disposed|disposal|"
    r"liquidated|liquidation|allocated|allocation|"
    # Surface-specific: `close` is a trade direction here (the `_timeline`
    # precedent rejected "review or close" for exactly this reason), and the
    # valuation adjectives are opinions about the security, not the record.
    r"close|closes|closed|overvalued|undervalued|cheap|expensive"
    r")\b"
)


def test_escalation_wording_carries_no_trade_direction() -> None:
    # s766B: "retire" applies to the thesis ROW (a stale record), never to a
    # position. Note `expired` (the status the message names) survives this
    # guard while `exited` does NOT — that is the whole reason the retire verb
    # is `--status expired`; see the comment in data_sanity_escalation().
    f = data_sanity_escalation(
        _cba_detached(last_answering_revision_at=date(2026, 5, 1)), AS_OF
    )
    assert f is not None
    low = f.message.lower()
    # The canonical production guard is the floor.
    assert directive_terms(f.message) == (), (
        f"canonical directive term leaked: {directive_terms(f.message)!r}"
    )
    leaked = _EXTRA_BANNED_FOR_THIS_SURFACE.search(low)
    assert leaked is None, f"trade-direction wording leaked: {leaked!r}"
    # Stems too, for forms the word list cannot anticipate.
    for stem in ("sell", "trim", "alloc", "liquidat", "dispos", "recommend"):
        assert stem not in low, f"trade-direction stem leaked: {stem}"
    # …and it names the record-maintenance verbs, applied to the row.
    assert "retire the record" in low
    assert "asx thesis revise" in low
    # The guard is non-vacuous: the banned form this message most nearly emits
    # is caught — and by the CANONICAL guard, not just the local extras. This is
    # exactly why the retire verb is `--status expired` and not `--status
    # exited`; see the comment in data_sanity_escalation().
    # `exited` is an INFLECTION, so the canonical exact-match guard returns ()
    # for it — measured, not assumed. The extras layer is what catches it, and
    # that division of labour is the whole reason both exist.
    assert directive_terms("or retire the record: --status exited") == ()
    assert _EXTRA_BANNED_FOR_THIS_SURFACE.search("--status exited") is not None
    # And the canonical guard is live on this surface: a base directive term
    # would be caught by it even though the extras list omits it.
    assert directive_terms("divest the record") != ()


# --- Ordering + composition -------------------------------------------------


def test_evaluate_discipline_orders_thesis_then_portfolio() -> None:
    cba = _thesis(
        symbol="CBA.AU",
        revisit_due_at=date(2026, 6, 27),
        current="168",
        target="60",
        conviction_level=None,
    )
    port = PortfolioDisciplineInput(
        holdings=(HoldingWeight("CBA.AU", Decimal("5000")),),
    )
    findings = evaluate_discipline((cba,), port, AS_OF)
    checks = [f.check for f in findings]
    # per-thesis checks precede portfolio-level ones
    assert checks.index("revisit_overdue") < checks.index("conviction_unset")
    # benchmark_lag is removed; concentration is the portfolio-level check that
    # fires for the single 100%-weighted holding.
    assert "concentration" in checks


# --- Structural guard: model-independence (rule #11) ------------------------


def test_module_imports_are_model_independent() -> None:
    """The evaluator must not IMPORT the Model A / signals namespace (rule #11).

    Checked at the import level, not raw text: the module docstring legitimately
    *mentions* these tokens to explain the exclusion. What matters for rule #11 is
    that no model/signal code is imported — you cannot call what you do not import,
    and this pure module has no DB handle to run raw SQL either.
    """
    src = Path("asxos/domain/theses/discipline.py").read_text()
    import_lines = [
        ln
        for ln in src.splitlines()
        if ln.strip().startswith(("import ", "from "))
    ]
    joined = "\n".join(import_lines).lower()
    # `models` catches a future `from asxos.domain.models import ...`; the rest
    # catch the signal/SHAP/cache surface. Direct-import scan only — the real
    # backstop is that this module holds no DB handle, so even a transitive
    # dependency could not be *queried* here (security review L3).
    for tok in (
        "signals",
        "models",
        "model_a",
        "production_gate",
        "shap",
        "predict",
        "cache",
    ):
        assert tok not in joined, f"model-dependent import: {tok}"
