"""Pins on the Amendment H auto-merge workflow — content assertions, no GitHub calls.

Amendment H (`docs/product/roadmap-state.md`, James 2026-08-25) reversed
Amendment G ruling 3 and made `full-check` the only gate on `main`. That puts a
lot of weight on this one workflow file, so the properties that make it safe to
run unattended are pinned here rather than left to a reviewer's memory:

* it must never check out PR head code (a PR could otherwise influence the job
  that merges it), and must never move to `pull_request_target`;
* it must fail, not no-op, when the repo-level auto-merge setting is off;
* the `no-auto-merge` brake must stay wired.

Analogous to tests/test_issue_snapshot.py and tests/test_backup_script.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "auto-merge.yml"
_TEXT = _WORKFLOW.read_text(encoding="utf-8")


def _parsed() -> dict[Any, Any]:
    """Key type is `Any`, not `str`: YAML 1.1 folds the bare key `on` to True."""
    doc: dict[Any, Any] = yaml.safe_load(_TEXT)
    return doc


def _triggers() -> dict[str, Any]:
    doc = _parsed()
    # `True` is a legitimate key here (YAML 1.1 folds bare `on` to a bool), but
    # dict.get's stubs only accept the declared key type — index explicitly.
    if "on" in doc:
        return doc["on"] or {}
    return doc[True] or {}


def test_workflow_never_checks_out_pr_code() -> None:
    """The job that merges a PR must not run anything the PR can change.

    With Amendment H there is no human read between opening a PR and it landing
    on `main`, so a checkout here would let a PR's own contents influence its
    merge. Asserted on the file, not on review discipline.
    """
    steps = _parsed()["jobs"]["arm"]["steps"]
    # Structural, not textual: the file's own header NAMES actions/checkout in
    # order to forbid it, so a substring check would fail on the warning itself.
    assert all("uses" not in step for step in steps), (
        "this workflow runs no actions at all by design — nothing to check out with"
    )
    assert all("checkout" not in str(step.get("run", "")) for step in steps)


def test_trigger_is_pull_request_not_pull_request_target() -> None:
    """`pull_request_target` runs with a privileged token in the base context.

    Combined with a checkout that is the Comment-and-Control class the App
    runbook says to refuse; this workflow already holds `contents: write`.
    """
    triggers = _triggers()
    assert "pull_request" in triggers
    # Key-level, not textual — the header comment names the forbidden trigger.
    assert "pull_request_target" not in triggers


def test_arming_reacts_to_label_changes_as_well_as_pushes() -> None:
    types = _triggers()["pull_request"]["types"]
    for event in ("opened", "reopened", "synchronize", "ready_for_review"):
        assert event in types
    # Without the label events the brake could never be re-evaluated.
    assert "labeled" in types
    assert "unlabeled" in types


def test_no_auto_merge_label_is_the_brake() -> None:
    guard = _parsed()["jobs"]["arm"]["if"]
    assert "no-auto-merge" in guard
    assert guard.strip().startswith("${{ !contains(")


def test_permissions_are_exactly_what_arming_needs() -> None:
    """`contents: write` is required to merge; nothing wider is."""
    assert _parsed()["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
    }


def test_missing_repo_setting_fails_loudly_rather_than_skipping() -> None:
    """A silent skip here is indistinguishable from a working merge gate."""
    run = _parsed()["jobs"]["arm"]["steps"][0]["run"]
    assert "allow_auto_merge" in run
    assert "::error::" in run
    assert "exit 1" in run
    assert "set -euo pipefail" in run


def test_arming_is_idempotent_and_skips_closed_prs() -> None:
    run = _parsed()["jobs"]["arm"]["steps"][0]["run"]
    assert ".autoMergeRequest != null" in run, "re-arming an armed PR must be a no-op"
    assert "!= \"OPEN\"" in run


def test_amendment_h_is_cited_in_the_file() -> None:
    """The reversal is contested enough that the file must name its authority."""
    assert "Amendment H" in _TEXT
    assert "roadmap-state.md" in _TEXT
