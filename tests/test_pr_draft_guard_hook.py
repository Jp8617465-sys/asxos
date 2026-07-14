"""Tests for ``.claude/hooks/pr-draft-guard.sh`` — the always-on draft-PR-ceiling guard.

Pins the ``has()``-over-``//`` fix: ``.tool_input.draft // empty`` treats both ``false`` and
``null``/absent as "missing," so it cannot distinguish "explicitly ready" from "not touching
draft" — which matters for ``update_pull_request`` (a title/body-only edit must not be
denied). This hook reads presence via ``has()`` instead, so ``draft:false``, ``draft:null``,
and absent-``draft`` are each read as their true, distinct state. DENY-only, same rationale
as ``push-guard.sh``: it never attempts to pre-approve draft creation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "pr-draft-guard.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="pr-draft-guard.sh needs jq on PATH"
)


def run_hook(tool_name: str, tool_input: dict) -> dict:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True, text=True,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


# --- DENY: create/update paths that would exceed the draft ceiling --------------------


@pytest.mark.parametrize(
    "tool_input",
    [
        {"title": "x"},  # draft absent
        {"title": "x", "draft": False},
        {"title": "x", "draft": None},
    ],
)
def test_deny_create_pull_request_not_draft(tool_input: dict) -> None:
    assert _is_deny(run_hook("mcp__github__create_pull_request", tool_input))


def test_deny_update_pull_request_undraft() -> None:
    assert _is_deny(
        run_hook("mcp__github__update_pull_request", {"pullNumber": 1, "draft": False})
    )


@pytest.mark.parametrize("state", ["closed", "open"])
def test_deny_update_pull_request_state_transition(state: str) -> None:
    assert _is_deny(
        run_hook("mcp__github__update_pull_request", {"pullNumber": 1, "state": state})
    )


def test_deny_merge_pull_request() -> None:
    assert _is_deny(run_hook("mcp__github__merge_pull_request", {"pullNumber": 1}))


def test_deny_enable_pr_auto_merge() -> None:
    assert _is_deny(run_hook("mcp__github__enable_pr_auto_merge", {"pullNumber": 1}))


# --- ALLOW (no-op): the actual draft-PR loop must stay frictionless at the hook level --


def test_allow_create_pull_request_draft_true() -> None:
    assert run_hook("mcp__github__create_pull_request", {"title": "x", "draft": True}) == {}


@pytest.mark.parametrize(
    "tool_input",
    [
        {"pullNumber": 1, "draft": True},
        {"pullNumber": 1, "title": "new"},
        {"pullNumber": 1, "body": "x"},
        {"pullNumber": 1, "base": "main"},
        {"pullNumber": 1},
    ],
)
def test_allow_update_pull_request_non_lifecycle_edit(tool_input: dict) -> None:
    assert run_hook("mcp__github__update_pull_request", tool_input) == {}


@pytest.mark.parametrize(
    "tool_name,tool_input",
    [
        ("mcp__github__pull_request_read", {"pullNumber": 1}),
        ("mcp__github__list_pull_requests", {}),
        ("Bash", {"command": "ls"}),
    ],
)
def test_allow_non_pr_write_tools_ignored(tool_name: str, tool_input: dict) -> None:
    assert run_hook(tool_name, tool_input) == {}
