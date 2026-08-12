"""Static contract checks for the Claude Execute GitHub Actions harness."""
from __future__ import annotations

import json
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


def test_claude_settings_matches_validation_workflow_scope() -> None:
    allow = json.loads(SETTINGS.read_text())["permissions"]["allow"]

    for entry in (
        "Bash(git push:*)",
        "Bash(make check:*)",
        "Bash(gh pr create:*)",
        "Bash(gh run watch:*)",
        "Bash(gh workflow run full-check.yml:*)",
        "Bash(gh workflow run targeted-ml-tests.yml:*)",
        "Bash(gh workflow run migration-integration.yml:*)",
    ):
        assert entry in allow

    assert "Bash(gh workflow run:*)" not in allow
    assert "Bash(gh workflow run backup.yml:*)" not in allow
