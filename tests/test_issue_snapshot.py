"""Pins on the ADR §5.4 issue snapshot — content assertions, no GitHub calls.

The script runs only in issue-snapshot.yml with GITHUB_TOKEN. These tests pin
the load-bearing shape (schedule of record, --state all, canonical path, cap)
so a silent shrink of the dump fails in the same PR rather than years later
when the clone has no tickets. Analogous to tests/test_backup_script.py.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

_SCRIPT = Path(__file__).parent.parent / "scripts" / "export_github_issues.sh"
_TEXT = _SCRIPT.read_text(encoding="utf-8")
_WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "issue-snapshot.yml"
_WORKFLOW_TEXT = _WORKFLOW.read_text(encoding="utf-8")
_FULL_CHECK = Path(__file__).parent.parent / ".github" / "workflows" / "full-check.yml"
_FULL_CHECK_TEXT = _FULL_CHECK.read_text(encoding="utf-8")
_SNAPSHOT = Path(__file__).parent.parent / "docs" / "ops" / "github-issues-snapshot.json"


def test_script_parses() -> None:
    proc = subprocess.run(
        ["bash", "-n", str(_SCRIPT)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr


def test_script_lists_every_state_with_pinned_json_fields() -> None:
    assert "gh issue list" in _TEXT
    assert "--state all" in _TEXT
    assert "LIMIT=1000" in _TEXT
    assert "--limit" in _TEXT
    # Exact, not substring: `"state" in _TEXT` is satisfied by `stateReason`,
    # by `--state all`, and by the word "state" in a comment, so the loop below
    # cannot on its own catch a field being dropped. The `--json` line is
    # asserted verbatim so a silent shrink of the dump fails here.
    assert (
        "--json number,title,state,stateReason,labels,body,author,"
        "createdAt,updatedAt,closedAt,url" in _TEXT
    )
    for field in (
        "number",
        "title",
        "state",
        "stateReason",
        "labels",
        "body",
        "author",
        "createdAt",
        "updatedAt",
        "closedAt",
        "url",
    ):
        assert field in _TEXT
    assert "docs/ops/github-issues-snapshot.json" in _TEXT
    assert "exported_at" not in _TEXT, (
        "a timestamp in the payload would force an empty commit every run"
    )


def test_script_anchors_gh_to_this_checkout_before_calling_it() -> None:
    """`gh` reads the repo from the CWD's git remote, not from $0's location.

    Without the cd, a manual run from another checkout writes THAT repo's
    issues into this snapshot — wrong evidence rather than absent evidence,
    which is the worse failure for a file that exists to be the evidence.
    Order matters, so it is asserted rather than assumed.
    """
    assert 'cd "${ROOT}"' in _TEXT
    assert _TEXT.index('cd "${ROOT}"') < _TEXT.index("gh issue list")


def test_script_exits_2_when_gh_is_missing() -> None:
    """Content pin only — do not invoke gh. This token 403s on repository.issues."""
    assert "exit 2" in _TEXT
    assert 'command -v gh' in _TEXT


def test_script_refuses_a_truncated_dump() -> None:
    assert "-ge" in _TEXT
    assert "paginate before this is evidence-complete" in _TEXT


def test_workflow_schedule_is_the_load_bearing_trigger() -> None:
    assert 'cron: "0 7 * * *"' in _WORKFLOW_TEXT
    assert "workflow_dispatch:" in _WORKFLOW_TEXT
    assert "pull_request:" not in _WORKFLOW_TEXT
    assert "full-check.yml" in _WORKFLOW_TEXT
    assert "THIS IS NOT A STEP IN full-check.yml" in _WORKFLOW_TEXT


def test_workflow_runs_the_script_and_commits_only_on_change() -> None:
    assert "bash scripts/export_github_issues.sh" in _WORKFLOW_TEXT
    assert "git diff --staged --quiet" in _WORKFLOW_TEXT
    assert "git push" in _WORKFLOW_TEXT
    assert "contents: write" in _WORKFLOW_TEXT
    assert "issues: read" in _WORKFLOW_TEXT
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in _WORKFLOW_TEXT


def _triggers(path: Path) -> dict[str, Any]:
    """Parse a workflow's `on:` block.

    YAML 1.1 resolves the bare key `on` to the boolean True, which is why both
    spellings are looked up rather than indexing "on" directly.
    """
    parsed: dict[Any, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed.get("on", parsed.get(True)) or {}


def test_full_check_ignores_snapshot_pushes_but_never_snapshot_prs() -> None:
    """The paths filter belongs on `push`, and must never reach `pull_request`.

    full-check is a required status check, and a required check SKIPPED by a
    paths filter never reports at all: a PR touching only the snapshot file
    would park on "Expected — waiting for status" and could never merge, a
    deadlock that reads as a hung check rather than a config bug. The original
    pin — the filename appearing somewhere in the file — passes in BOTH the safe
    and the deadlocked configuration, so what is pinned here is the
    trigger-level shape.
    """
    triggers = _triggers(_FULL_CHECK)
    assert triggers["push"]["paths-ignore"] == ["docs/ops/github-issues-snapshot.json"]
    assert "paths-ignore" not in triggers["pull_request"]
    assert "paths" not in triggers["pull_request"]


def test_workflow_pins_its_actions_to_a_sha() -> None:
    """A floating tag opts this workflow out of the repo's pinning regime.

    Every other workflow pins the digest with a trailing version comment, and
    dependabot's github-actions ecosystem is what keeps those pins from
    decaying — it rewrites SHA -> SHA and tag -> tag, so a tag ref would never
    become a pin on its own.
    """
    refs = re.findall(r"uses:\s*(\S+)", _WORKFLOW_TEXT)
    assert refs, "workflow declares no actions — the assertion below would be vacuous"
    for ref in refs:
        assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", ref), f"unpinned action: {ref}"


def test_workflow_rebases_before_pushing() -> None:
    """The branch can move between checkout and push — a merge landing mid-run.

    Without the rebase the job dies non-fast-forward and the day has no
    snapshot at all, which is the same missing-evidence outcome the whole
    workflow exists to prevent.
    """
    assert "git pull --rebase" in _WORKFLOW_TEXT
    assert _WORKFLOW_TEXT.index("git pull --rebase") < _WORKFLOW_TEXT.rindex("git push")


def test_placeholder_snapshot_is_valid_empty_json_array() -> None:
    assert _SNAPSHOT.read_text(encoding="utf-8").strip() == "[]"
