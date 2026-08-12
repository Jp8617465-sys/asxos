"""Static contract checks for the Claude Execute GitHub Actions harness."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "claude-execute.yml"
SETTINGS = ROOT / ".claude" / "settings.json"


def test_claude_execute_workflow_exposes_reversible_execution_tools() -> None:
    text = WORKFLOW.read_text()

    assert "workflow_dispatch:" in text
    assert "Bash(git switch:*)" in text
    assert "Bash(git commit:*)" in text
    assert "Bash(git push:*)" in text
    assert "Bash(make check:*)" in text
    assert "Bash(gh pr create:*)" in text
    assert "Bash(gh run view:*)" in text
    assert "Bash(gh workflow run full-check.yml:*)" in text
    assert "Bash(gh workflow run targeted-ml-tests.yml:*)" in text
    assert "Bash(gh workflow run migration-integration.yml:*)" in text

    assert "Bash(gh workflow run:*)" not in text
    assert "Bash(gh workflow run backup.yml:*)" not in text
    assert "direct push to main" in text
    assert "missing credentials or secret creation" in text
    assert "self-merge not explicitly authorized" in text


def test_claude_settings_dispatch_allowlist_is_named_not_wildcard() -> None:
    """The local attended session's dispatch scope is wider than the in-CI
    harness's (it gained backup.yml and claude-execute.yml in the 2026-08-12
    guard carve-outs) but is still a list of named workflows, never a wildcard.
    The asymmetry is deliberate: a local run is governor-attended, while the
    harness runs unattended inside CI and is held to the narrower validation
    scope asserted above.
    """
    allow = json.loads(SETTINGS.read_text())["permissions"]["allow"]

    for entry in (
        "Bash(git push:*)",
        "Bash(make check:*)",
        "Bash(gh pr create:*)",
        "Bash(gh run watch:*)",
        "Bash(gh workflow run full-check.yml:*)",
        "Bash(gh workflow run targeted-ml-tests.yml:*)",
        "Bash(gh workflow run migration-integration.yml:*)",
        "Bash(gh workflow run backup.yml:*)",
        "Bash(gh workflow run claude-execute.yml:*)",
    ):
        assert entry in allow

    assert "Bash(gh workflow run:*)" not in allow
    assert not any(
        entry.startswith("Bash(gh workflow run ")
        and not entry.endswith(".yml:*)")
        for entry in allow
    )
    # gh run rerun re-executes a prior run with its secrets re-injected, on any
    # workflow — a wider grant than the dispatch allowlist. It must never be a
    # blanket allow rule (security review 2026-08-12, H1).
    assert not any(entry.startswith("Bash(gh run rerun") for entry in allow)


def test_settings_and_push_guard_allow_the_same_workflow_set() -> None:
    """The settings allow-list and the hook's regex are two hand-maintained
    lists that must describe the same closed set; drift between them is silent
    and would let one layer permit what the other denies. Parse both and assert
    equality rather than trusting them to be edited together.
    """
    allow = json.loads(SETTINGS.read_text())["permissions"]["allow"]
    from_settings = {
        entry[len("Bash(gh workflow run ") : -len(":*)")]
        for entry in allow
        if entry.startswith("Bash(gh workflow run ")
    }

    hook = (ROOT / ".claude" / "hooks" / "push-guard.sh").read_text()
    match = re.search(r"run\[\[:space:\]\]\+\(([^)]+)\)\(\[\[:space:\]\]\|\$\)", hook)
    assert match, "could not locate the dispatch allowlist alternation in push-guard.sh"
    from_hook = {alt.replace("\\.", ".") for alt in match.group(1).split("|")}

    assert from_settings == from_hook
