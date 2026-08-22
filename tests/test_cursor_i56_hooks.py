"""Cursor I5/I6 port — native {permission: deny|allow} dialect.

These scripts are the R17 fence. They must not reuse Claude hook JSON and must
deny the global-option `git -C . push origin main` shape that a naive
`git[[:space:]]+push` regex misses (security-engineer, harness-rebuild-2026-08-22).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SHELL = REPO / ".cursor" / "hooks" / "i56-shell-guard.sh"
MCP = REPO / ".cursor" / "hooks" / "i56-mcp-guard.sh"


def _run(hook: Path, payload: dict) -> dict:
    proc = subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert set(out) <= {"permission", "agent_message"}
    assert "hookSpecificOutput" not in out
    return out


def _denied(out: dict, fragment: str) -> None:
    assert out["permission"] == "deny"
    assert fragment in out.get("agent_message", "")


@pytest.mark.parametrize(
    "command,fragment",
    [
        ("git push origin main", "push to main"),
        ("git -C . push origin main", "push to main"),
        ("git --no-pager push origin main", "push to main"),
        ("git push --force origin cursor/x", "force-push"),
        ("git -C . push --force-with-lease origin cursor/x", "force-push"),
        ("gh pr merge 1", "merge/ready"),
        ("gh pr ready 1", "merge/ready"),
        ("gh pr create --title x --body y", "draft required"),
        ("supabase db push", "db mutate"),
    ],
)
def test_i56_shell_denies_i56_shapes(command: str, fragment: str) -> None:
    _denied(_run(SHELL, {"command": command}), fragment)


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git push origin cursor/harness-rebuild-651f",
        "gh pr create --draft --title x --body y",
        "pytest tests/test_cursor_i56_hooks.py",
    ],
)
def test_i56_shell_allows_reversible_shapes(command: str) -> None:
    assert _run(SHELL, {"command": command}) == {"permission": "allow"}


@pytest.mark.parametrize(
    "tool",
    [
        "mcp__github__merge_pull_request",
        "mcp__github__enable_pr_auto_merge",
        "mcp__supabase__apply_migration",
    ],
)
def test_i56_mcp_denies_i56_tools(tool: str) -> None:
    _denied(_run(MCP, {"tool_name": tool}), "I5/I6")


def test_i56_mcp_allows_read_sql() -> None:
    assert _run(MCP, {"tool_name": "mcp__supabase-ro__execute_sql"}) == {
        "permission": "allow"
    }
