"""Pins the session-dispatch scope rule in `.claude/rules/job-conventions.md`.

The previous rule was a prose allowlist of five workflows. By 2026-09-16 four more had
been added (`vp-register`, `vp-research`, `risk-free-backfill`, `nightly-check`) that it
did not name, and it denied "secret-bearing" jobs while `backup.yml` — two secrets,
dispatched every §8 migration — sat on its allowlist. A list that has to be edited by hand
every time a workflow lands is a prose control wearing a test's clothes.

What the rule actually protects is James: an out-of-schedule run that puts an email in
his inbox or a paid pull against the §2 spend cap. That is a property of the workflow
file — a `schedule:` plus `RESEND_API_KEY` or `EODHD_API_KEY` in `env:` — so it is
computed here and pinned to the four jobs the rule names. If a new workflow acquires
both properties, this test names it and the rule's prose must be updated deliberately.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))

#: Secrets whose use in a scheduled run has a side effect James experiences directly.
SIDE_EFFECT_SECRETS = ("RESEND_API_KEY", "EODHD_API_KEY")

RESERVED_TO_JAMES = frozenset(
    {"daily-brief.yml", "us-positions.yml", "pipeline-health.yml", "weekly-research.yml"}
)

#: Lanes arbi built for deliberate execution: dispatch-only, and a default that writes
#: nothing. Add a new lane here when it lands, so the persist-default pin covers it.
DISPATCH_ONLY_LANES = (
    "vp-register.yml",
    "vp-research.yml",
    "risk-free-backfill.yml",
    "factor-probe.yml",
)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _triggers(doc: dict) -> dict:
    # PyYAML parses a bare `on:` key as boolean True.
    return doc.get("on") or doc.get(True) or {}


def _has_schedule(doc: dict) -> bool:
    return "schedule" in _triggers(doc)


def _secret_names(text: str) -> set[str]:
    return set(re.findall(r"\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}", text))


def _reserved(path: Path) -> bool:
    doc = _load(path)
    return _has_schedule(doc) and bool(_secret_names(path.read_text()) & set(SIDE_EFFECT_SECRETS))


def test_the_reserved_set_is_computed_and_matches_the_four_named() -> None:
    """The rule's list is derived, not typed. Drift fails here, by name."""
    computed = {p.name for p in WORKFLOWS if _reserved(p)}
    assert computed == RESERVED_TO_JAMES, (
        f"reserved-to-James set drifted: computed {sorted(computed)}, "
        f"rule names {sorted(RESERVED_TO_JAMES)} — update the rule prose deliberately"
    )


def test_backup_is_scheduled_and_secret_bearing_but_not_reserved() -> None:
    """The counter-example that shows 'secret-bearing' was never the principle."""
    backup = ROOT / ".github/workflows/backup.yml"
    assert _has_schedule(_load(backup))
    assert _secret_names(backup.read_text()), "backup.yml carries secrets"
    assert not _reserved(backup)


def test_dispatch_only_lanes_have_no_schedule() -> None:
    for name in DISPATCH_ONLY_LANES:
        doc = _load(ROOT / ".github/workflows" / name)
        assert "workflow_dispatch" in _triggers(doc), name
        assert not _has_schedule(doc), f"{name} must never be scheduled"


def test_dispatch_only_lanes_default_to_writing_nothing() -> None:
    """The default dispatch is a read-through. persist defaults false; dry_run defaults true."""
    for name in DISPATCH_ONLY_LANES:
        inputs = _triggers(_load(ROOT / ".github/workflows" / name))["workflow_dispatch"]["inputs"]
        if "persist" in inputs:
            assert inputs["persist"]["default"] is False, f"{name}: persist must default false"
        if "dry_run" in inputs:
            assert inputs["dry_run"]["default"] is True, f"{name}: dry_run must default true"
        assert "persist" in inputs or "dry_run" in inputs, (
            f"{name}: a dispatch-only lane that writes must expose persist or dry_run"
        )


def test_dispatch_only_lanes_check_out_main() -> None:
    """A production secret never runs at a PR head (AGENTS.md §8)."""
    for name in DISPATCH_ONLY_LANES:
        assert "ref: refs/heads/main" in (ROOT / ".github/workflows" / name).read_text(), name


def test_factor_probe_only_writes_behind_the_persist_flag() -> None:
    """The probe's write-nothing default is enforced by SKIPPING the step, not by a flag.

    `jobs/compute_factor_scores.py` has no `--dry-run` of its own — it upserts
    rs_factor_scores unconditionally. So the only thing standing between a default
    dispatch and a write is the `if:` guard on that step. The generic persist-default
    pin above cannot see that, which is exactly why this lane gets its own assertion:
    delete the guard and the default dispatch silently starts writing.
    """
    doc = _load(ROOT / ".github/workflows/factor-probe.yml")
    steps = doc["jobs"]["probe"]["steps"]

    writers = [s for s in steps if "compute_factor_scores.py" in s.get("run", "")]
    assert len(writers) == 1, "expected exactly one step to invoke the writer"
    assert writers[0].get("if") == "${{ inputs.persist }}", (
        "the recompute step must be gated on inputs.persist — without it the default "
        "dispatch writes rs_factor_scores"
    )

    # The evaluator is read-only and therefore deliberately NOT gated.
    readers = [s for s in steps if "eval_alpha_factors.py" in s.get("run", "")]
    assert len(readers) == 1 and "if" not in readers[0], (
        "the read-only evaluator should run on every dispatch"
    )


def test_factor_probe_touches_no_paid_api_and_no_capital_surface() -> None:
    """A$0 by construction, and it cannot reach a rule-#11 or capital table.

    The lane's cost claim rests on compute_factor_scores being pure DB-to-DB and
    eval_alpha_factors being read-only; the secret list is what makes that checkable
    from outside the jobs.
    """
    text = (ROOT / ".github/workflows/factor-probe.yml").read_text()
    assert _secret_names(text) == {"DATABASE_URL"}, (
        "factor-probe must carry DATABASE_URL and nothing else — a paid-API secret here "
        "would both cost money and move the lane toward the James-reserved set"
    )
    for job in ("run_vp_test.py", "generate_signals.py", "snapshot_portfolio.py"):
        assert job not in text, f"factor-probe must not invoke {job}"
