"""Tests for the deterministic thesis-discipline evaluator (PR1).

Covers the acceptance criteria in
`docs/proposals/portfolio-team-visibility-2026-07-12.md` §6: the CBA fixture
(revisit-overdue + data-sanity), the conviction-NULL summary (R11),
quiet-by-default, fail-loud-on-error, model-independence, and the reused
severity/trajectory dimensions.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

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
    last_revised_at: date | None = None,
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
        last_revised_at=last_revised_at,
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
    *, last_revised_at: date | None, opened_at: date = date(2026, 1, 1)
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
        current="168",
        target="60",
        stop="38",
        last_revised_at=last_revised_at,
    )


def test_cba_unanswered_data_sanity_red_escalates() -> None:
    # Last revision 2026-05-01, as_of 2026-07-13 → 73 days of revision silence
    # while the ladder is detached (> the 30-day cadence) → escalated red that
    # names the exact CLI verb.
    f = data_sanity_escalation(_cba_detached(last_revised_at=date(2026, 5, 1)), AS_OF)
    assert f is not None
    assert f.check == "data_sanity_escalation"
    assert f.level is DisciplineLevel.red
    assert f.symbol == "CBA.AU"
    assert "unanswered for 73d" in f.message
    assert "2.8×" in f.message
    assert "asx thesis revise CBA.AU" in f.message


def test_escalation_boundary_exactly_n_days_is_not_yet_escalated() -> None:
    # Exactly N days of silence is NOT yet escalated (strictly-greater-than,
    # matching _timeline's strictly-past-deadline red); N+1 days is.
    n = _DATA_SANITY_UNANSWERED_ESCALATION_DAYS
    at_boundary = _cba_detached(last_revised_at=AS_OF - timedelta(days=n))
    assert data_sanity_escalation(at_boundary, AS_OF) is None

    past_boundary = _cba_detached(last_revised_at=AS_OF - timedelta(days=n + 1))
    f = data_sanity_escalation(past_boundary, AS_OF)
    assert f is not None
    assert f"unanswered for {n + 1}d" in f.message


def test_answered_red_does_not_escalate() -> None:
    # The real logic: a thesis_revisions row AFTER the red first appeared is an
    # answer. The ladder here detached long ago (thesis opened 2026-01-01), but
    # James revised the thesis 5 days before as_of — that revision row resets
    # the unanswered clock, so the still-firing base red does NOT escalate.
    answered = _cba_detached(last_revised_at=AS_OF - timedelta(days=5))
    assert data_sanity_escalation(answered, AS_OF) is None
    # The base data-sanity red itself still fires via evaluate_thesis — the
    # answer suppresses only the escalation, never the evidence.
    assert _by_check(evaluate_thesis(answered, AS_OF), "data_sanity")


def test_no_escalation_without_a_live_data_sanity_red() -> None:
    # A healthy ladder never escalates, no matter how long the revision
    # silence — escalation only ever accompanies a currently-firing red.
    dormant_but_healthy = _thesis(
        opened_at=date(2025, 1, 1), last_revised_at=date(2025, 1, 1)
    )
    assert data_sanity_escalation(dormant_but_healthy, AS_OF) is None


def test_escalation_falls_back_to_opened_at_when_no_revisions() -> None:
    # No thesis_revisions rows → opened_at anchors the clock (it matches the
    # 'opened' revision open_thesis() writes). Opened 2026-01-01 → 193 days.
    f = data_sanity_escalation(_cba_detached(last_revised_at=None), AS_OF)
    assert f is not None
    assert "unanswered for 193d" in f.message
    assert "2026-01-01" in f.message


def test_escalation_wording_carries_no_trade_direction() -> None:
    # s766B: "retire" applies to the thesis ROW (a stale record), never to a
    # position. The banned substrings cover plural/variant forms too
    # ("sells", "exited", "reduces", "allocation"), plus "close" per the
    # _timeline precedent (discipline.py:220-229).
    f = data_sanity_escalation(_cba_detached(last_revised_at=date(2026, 5, 1)), AS_OF)
    assert f is not None
    low = f.message.lower()
    for banned in ("sell", "trim", "exit", "reduce", "alloc", "close", "buy"):
        assert banned not in low, f"trade-direction wording leaked: {banned}"
    # …and it names the record-maintenance verb, applied to the row.
    assert "retire the record" in low
    assert "asx thesis revise" in low


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
