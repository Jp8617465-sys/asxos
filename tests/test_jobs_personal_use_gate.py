"""Firewall-gate regression: personal-data jobs hard-fail without ASXOS_PERSONAL_USE=1.

R14 audit follow-up (2026-07-18): snapshot_portfolio, check_au_positions,
check_us_positions and check_thesis_invalidations read/write holdings + theses
(personal-advice data under s766B). Before this change they relied SOLELY on
render.yaml setting the env var -- no in-code backstop like build_portfolio.py
has, so a manual run or render.yaml drift would silently process personal data.

compute_opportunity_cost (sprint follow-up, 2026-07-19) ranks redeployment
candidates against active theses -- same personal-advice-data class -- and had
the same gap: render.yaml-only enforcement, no in-code backstop.

``require_personal_use_job()`` is that backstop. These tests pin (a) the helper's
own behaviour and (b) that each entry point calls it BEFORE any DB access, so a
missing flag fails loud (CLAUDE.md #10) rather than reaching init_pool().

R14-CLOSING DISCOVERY TEST (sprint follow-up, 2026-07-19): the parametrized test
above pins behaviour for jobs already known to need the gate, but nothing
previously caught a *new* job silently missing it -- exactly the gap that let
compute_opportunity_cost run ungated for as long as it did. The section below
makes that class of gap structurally hard to reintroduce: every file in
jobs/*.py must be classified into exactly one of the buckets below, so a brand
new, unclassified job file fails ``test_every_job_is_classified`` until a
human/agent explicitly decides where it belongs.
"""
from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import pytest

from asxos.jobs._helpers import require_personal_use_job

_JOBS_DIR = Path(__file__).resolve().parent.parent / "jobs"

# Every jobs/*.py filename, classified as of 2026-07-19. Discovered, not
# assumed: audited each file's SQL against the personal-data table set
# (theses, holding_lots, current_holdings, profiles, portfolio_daily_snapshots)
# via `grep -noE "FROM +[a-z_]+|INTO +[a-z_]+|UPDATE +[a-z_]+" jobs/*.py`, then
# read the surrounding code for anything the grep could plausibly have missed.
# Honest limit: this is a text-level audit of each job's OWN source, not a full
# call-graph trace through every domain-service function it calls -- a job
# that touches personal data ONLY through an unaudited service indirection
# (the way build_portfolio.py's gate would be invisible to a naive table-name
# grep, since it goes through PortfolioService.build()) could in principle
# still slip past this heuristic. Re-audit if a job's imports change
# significantly, not just when its own SQL text changes.

# Hard-fails via the shared require_personal_use_job() helper.
_GATED_SHARED_HELPER = {
    "check_au_positions.py",
    "check_thesis_invalidations.py",
    "check_us_positions.py",
    "compute_opportunity_cost.py",
    "snapshot_portfolio.py",
}

# Hard-fails via an equivalent inline `os.environ.get("ASXOS_PERSONAL_USE") !=
# "1": raise RuntimeError(...)` check -- predates the shared helper (or was
# never migrated to it). Functionally equivalent fail-loud gate, just not the
# shared code path, so it needs its own assertion below rather than
# test_job_entry_point_gated's shared-helper-specific parametrize list.
_GATED_INLINE = {
    "build_portfolio.py",
    "ingest_news.py",
    "ingest_sentiment.py",
}

# Deliberately NOT hard-gated at the job entry point. compose_brief.py's V1
# path (asxos/brief/compose.py::collect()) delegates to per-SECTION internal
# checks (e.g. _discipline_findings returns [] rather than raising when the
# flag is unset), so the brief can still send its non-personal sections --
# portfolio-conventions.md "Allocator hard-fails; brief is best-effort (R9)".
# Confirmed deliberate design for V1 (compose.py's own docstrings cite R9
# explicitly), not an oversight -- do not "fix" V1 into a hard fail without
# re-reading R9 first.
#
# RESOLVED (was a known gap, security-engineer audit 2026-07-19, risk-register
# R18; fixed same day, backend-architect-designed): jobs/compose_brief.py
# actually calls the V2 path (asxos/domain/brief/composer.py::compose()),
# which is a DIFFERENT tree from V1 above -- its 8 collectors (wealth_state,
# tax_operational, active_theses, watchlist, underlying_drivers, new_ideas,
# theme_dashboard, opportunity_cost) read theses/current_holdings/
# portfolio_daily_snapshots. They previously ran unconditionally with no
# ASXOS_PERSONAL_USE check anywhere, and _persist_brief_run() unconditionally
# INSERTed a personal-data-derived one_thing/health_line into brief_runs
# regardless of the flag -- masked only by render.yaml, and unconditional
# regardless of ASXOS_V2_BRIEF_ENABLED too (the snapshot is built before the
# V1-vs-V2 render branch is chosen).
#
# Fix lives entirely in composer.py, mirroring V1's graceful-degrade
# philosophy (not compute_opportunity_cost.py's hard-fail-the-whole-job
# pattern, which would also kill the non-personal market_context/
# section_health sections): `_gated_collect()` wraps the 8 personal
# collectors so their collect_*() coroutine is never even constructed when
# ASXOS_PERSONAL_USE is unset -- reusing the already-wired
# SectionStatus.suppressed (new_ideas.py already used it for risk-off
# suppression) rather than inventing new status handling. `_persist_brief_run`
# separately redacts one_thing/health_line as defense-in-depth, independent
# of the collector gate. See tests/test_brief_composer.py's
# test_compose_suppresses_all_personal_collectors_when_gate_off and siblings
# for the real (not mocked-away) end-to-end proof.
_GATED_INTERNAL_GRACEFUL = {
    "compose_brief.py",
}

# Touches a personal-data table (holding_lots) ONLY to scope a generic fetch
# of EXTERNAL MARKET data (which symbols/date-range to pull prices for) --
# output is shared market data, never personalised advice. Currently NOT
# gated by any mechanism, in either render.yaml or in-code. Deliberately left
# here as an open, judgment-requiring question rather than silently exempted
# OR mechanically gated: sync_prices.py is the most foundational daily job in
# the pipeline (many others gate on its success -- job-conventions.md) and
# hard-failing its entire entry point over a personal-use flag would also
# block its core AU-bulk phase, which touches no personal data at all and
# has nothing to do with s766B. A correct fix likely needs a narrower,
# phase-scoped gate (or a `security_kind`-style split), not the mechanical
# "add require_personal_use_job() as the first line of main()" pattern used
# elsewhere -- see risk-register.md and system-architect before changing
# either of these two files' gating. Listed here (rather than omitted) so
# this test's classification stays honest about the gap instead of hiding it.
_TOUCHES_PERSONAL_DATA_UNGATED_NEEDS_REVIEW = {
    "ingest_underlyings.py",
    "sync_prices.py",
}

# Every remaining jobs/*.py file: audited 2026-07-19, touches none of
# theses/holding_lots/current_holdings/profiles/portfolio_daily_snapshots.
_CLEAN_NO_PERSONAL_DATA = {
    "check_cron_health.py",
    "check_model_staleness.py",
    "compute_factor_scores.py",
    "derive_fundamentals_pit.py",
    "detect_theme_stages.py",
    "eval_alpha_factors.py",
    "generate_signals.py",
    "ingest_market_context.py",
    "ingest_regulatory.py",
    "retrain_model_a.py",
    "sync_corporate_actions.py",
    "sync_financial_statements.py",
    "sync_fundamentals.py",
    "sync_security_master.py",
    "sync_universe.py",
    "track_signal_outcomes.py",
    "validate_price_data.py",
}


def test_every_job_is_classified() -> None:
    """A new jobs/*.py file must be explicitly added to one of the buckets
    above before this test passes -- makes silently forgetting to consider
    the firewall gate for a new job structurally impossible, closing R14."""
    on_disk = {p.name for p in _JOBS_DIR.glob("*.py") if p.name != "__init__.py"}
    classified = (
        _GATED_SHARED_HELPER
        | _GATED_INLINE
        | _GATED_INTERNAL_GRACEFUL
        | _TOUCHES_PERSONAL_DATA_UNGATED_NEEDS_REVIEW
        | _CLEAN_NO_PERSONAL_DATA
    )
    unclassified = on_disk - classified
    assert not unclassified, (
        f"New job file(s) not classified in {__file__}: {sorted(unclassified)}. "
        "Read the file, decide whether it touches theses/holding_lots/"
        "current_holdings/profiles/portfolio_daily_snapshots, and add it to "
        "the correct bucket (see the module docstring for what each means)."
    )
    stale = classified - on_disk
    assert not stale, (
        f"Classified job(s) no longer exist in jobs/: {sorted(stale)} -- "
        "remove them from this file's buckets (renamed or deleted job)."
    )
    # No file may be double-classified -- would silently mask which gate
    # mechanism actually applies.
    buckets = [
        _GATED_SHARED_HELPER,
        _GATED_INLINE,
        _GATED_INTERNAL_GRACEFUL,
        _TOUCHES_PERSONAL_DATA_UNGATED_NEEDS_REVIEW,
        _CLEAN_NO_PERSONAL_DATA,
    ]
    seen: set[str] = set()
    for bucket in buckets:
        overlap = seen & bucket
        assert not overlap, f"Job(s) listed in more than one bucket: {sorted(overlap)}"
        seen |= bucket


def test_gated_shared_helper_jobs_actually_call_it() -> None:
    for fname in sorted(_GATED_SHARED_HELPER):
        src = (_JOBS_DIR / fname).read_text()
        assert "require_personal_use_job()" in src, (
            f"{fname} is classified under _GATED_SHARED_HELPER but its source "
            "no longer calls require_personal_use_job() -- either restore the "
            "call or move it to a different bucket in this file."
        )


def test_gated_inline_jobs_actually_check_the_env_var() -> None:
    for fname in sorted(_GATED_INLINE):
        src = (_JOBS_DIR / fname).read_text()
        assert 'os.environ.get("ASXOS_PERSONAL_USE")' in src, (
            f"{fname} is classified under _GATED_INLINE but its source no "
            "longer checks ASXOS_PERSONAL_USE -- either restore the check or "
            "move it to a different bucket in this file."
        )


def test_helper_raises_when_flag_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        require_personal_use_job()


def test_helper_raises_when_flag_not_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # Any value other than exactly "1" must fail closed.
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "0")
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        require_personal_use_job()


def test_helper_passes_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    require_personal_use_job()  # must not raise


@pytest.mark.parametrize(
    "module_name, entry",
    [
        ("jobs.snapshot_portfolio", lambda m: m.main(None, None)),
        ("jobs.check_au_positions", lambda m: m._run(date(2026, 7, 18))),
        ("jobs.check_us_positions", lambda m: m._run(date(2026, 7, 18))),
        ("jobs.check_thesis_invalidations", lambda m: m._run(date(2026, 7, 18))),
        ("jobs.compute_opportunity_cost", lambda m: m.main()),
    ],
)
def test_job_entry_point_gated(
    monkeypatch: pytest.MonkeyPatch, module_name: str, entry: object
) -> None:
    # The gate is the first statement of each entry point (before init_pool),
    # so a missing flag raises RuntimeError without ever touching the DB.
    import importlib

    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    module = importlib.import_module(module_name)
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        asyncio.run(entry(module))  # type: ignore[operator]
