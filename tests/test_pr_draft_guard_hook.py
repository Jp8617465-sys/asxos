"""Tests for ``.claude/hooks/pr-draft-guard.sh`` — the always-on draft-PR-ceiling guard.

Pins the ``has()``-over-``//`` fix: ``.tool_input.draft // empty`` treats both ``false`` and
``null``/absent as "missing," so it cannot distinguish "explicitly ready" from "not touching
draft" — which matters for ``update_pull_request`` (a title/body-only edit must not be
denied). This hook reads presence via ``has()`` instead, so ``draft:false``, ``draft:null``,
and absent-``draft`` are each read as their true, distinct state. DENY-only, same rationale
as ``push-guard.sh``: it never attempts to pre-approve draft creation.

Merge policy (2026-07-14 follow-up to PR #39, which overcorrected by denying
``merge_pull_request`` everywhere): **agent-initiated merge is forbidden** as an
instruction-level rule; **James-instructed attended merge execution is allowed** — the hook
stays SILENT for ``merge_pull_request`` in attended sessions (no hook-level allow; the
normal tool-permission / user-instruction flow still applies); **unattended merge**
(``ARBI_UNATTENDED=1``) **and auto-merge** (``enable_pr_auto_merge``, every mode) stay
mechanically denied.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "pr-draft-guard.sh"
SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="pr-draft-guard.sh needs jq on PATH"
)


def run_hook(tool_name: str, tool_input: dict, env_extra: dict | None = None) -> dict:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True, text=True,
        env={"PATH": os.environ.get("PATH", ""), **(env_extra or {})},
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    if not out:
        return {}
    decision = json.loads(out)["hookSpecificOutput"]
    # Structural invariant on EVERY test path: this hook may only deny or stay silent —
    # a hook-level allow would silently suppress the normal permission prompt.
    assert decision.get("permissionDecision") == "deny", f"hook emitted non-deny: {decision}"
    return decision


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


# --- Merge policy: attended silent, unattended denied, auto-merge always denied --------


def test_attended_merge_pull_request_not_denied_by_hook() -> None:
    """James-instructed attended merge execution: the hook stays SILENT (empty output) so
    the normal tool-permission / user-instruction flow decides — it neither denies nor
    emits a hook-level allow."""
    assert run_hook("mcp__github__merge_pull_request", {"pullNumber": 1}) == {}


def test_unattended_merge_pull_request_denied() -> None:
    assert _is_deny(
        run_hook(
            "mcp__github__merge_pull_request",
            {"pullNumber": 1},
            env_extra={"ARBI_UNATTENDED": "1"},
        )
    )


@pytest.mark.parametrize("value", ["0", ""])
def test_merge_pull_request_silent_when_unattended_flag_off(value: str) -> None:
    """Lockout regression: ARBI_UNATTENDED set-but-off ("0" or empty) must read as
    attended — only the exact value "1" arms the unattended deny."""
    assert (
        run_hook(
            "mcp__github__merge_pull_request",
            {"pullNumber": 1},
            env_extra={"ARBI_UNATTENDED": value},
        )
        == {}
    )


@pytest.mark.parametrize("env_extra", [None, {"ARBI_UNATTENDED": "1"}])
def test_deny_enable_pr_auto_merge_every_mode(env_extra: dict | None) -> None:
    """Auto-merge is forbidden attended AND unattended — it removes the per-PR,
    James-instructed merge decision."""
    assert _is_deny(
        run_hook("mcp__github__enable_pr_auto_merge", {"pullNumber": 1}, env_extra=env_extra)
    )


def test_hook_never_emits_permission_allow() -> None:
    """Regression: the attended-merge path must be hook-SILENCE (fall through to the
    normal permission flow), never a hook-level ``permissionDecision:"allow"`` — a
    false-negative on an allow regex would execute silently with zero human check.

    Scans non-comment code only: the hook's header COMMENT legitimately discusses the
    platform's documented allow behavior; what must never exist is code that emits it.
    """
    code = "\n".join(
        line for line in HOOK.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )
    assert re.search(r"permissionDecision[^\n]*allow", code) is None


# --- Settings contract: the deny array matches the corrected merge policy ---------------


def _settings_deny() -> list[str]:
    return json.loads(SETTINGS.read_text())["permissions"]["deny"]


def test_settings_deny_enable_pr_auto_merge_still_present() -> None:
    assert "mcp__github__enable_pr_auto_merge" in _settings_deny()


def test_settings_no_longer_deny_merge_pull_request() -> None:
    """PR #39's bare-tool-name deny of merge_pull_request removed James-instructed
    attended merge execution — the corrected policy handles unattended denial in
    pr-draft-guard.sh instead, so the settings-level bare deny must be gone."""
    assert "mcp__github__merge_pull_request" not in _settings_deny()


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
