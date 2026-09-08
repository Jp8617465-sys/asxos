"""Tests for ``.claude/hooks/pr-draft-guard.sh`` — attended/standing PR lifecycle guard.

Pins the ``has()``-over-``//`` fix: ``.tool_input.draft // empty`` treats both ``false`` and
``null``/absent as "missing," so it cannot distinguish "explicitly ready" from "not touching
draft" — which matters for ``update_pull_request`` (a title/body-only edit must not be
denied). This hook reads presence via ``has()`` instead, so ``draft:false``, ``draft:null``,
and absent-``draft`` are each read as their true, distinct state. DENY-only, same rationale
as ``push-guard.sh``: it never attempts to pre-approve draft creation.

Lifecycle policy: draft creation remains available while ATTENDED. Non-draft creation,
readying, state transitions and merge stay denied unless the hook resolves the exact ASXOS
origin and reads remote ``AUTONOMY=STANDING``. Auto-merge remains denied in every state.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "pr-draft-guard.sh"
SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"
REPO_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="pr-draft-guard.sh needs jq on PATH"
)


def run_hook(
    tool_name: str,
    tool_input: dict,
    env_extra: dict | None = None,
    *,
    autonomy: str = "ATTENDED",
) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        gh = Path(tmp) / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            "if [ \"$1 $2 $3\" = \"variable get AUTONOMY\" ]; then\n"
            f"  printf '%s\\n' {autonomy!r}\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        gh.chmod(0o755)
        proc = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
            capture_output=True, text=True,
            env={
                "CLAUDE_PROJECT_DIR": str(REPO_ROOT),
                "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
                **(env_extra or {}),
            },
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


def test_missing_jq_fails_closed() -> None:
    proc = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(HOOK)],
        input=json.dumps(
            {
                "tool_name": "mcp__github__merge_pull_request",
                "tool_input": {"pullNumber": 1, "merge_method": "squash"},
            }
        ),
        capture_output=True,
        text=True,
        env={"PATH": ""},
    )
    assert proc.returncode == 0
    assert _is_deny(json.loads(proc.stdout)["hookSpecificOutput"])


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


def test_allow_create_pull_request_not_draft_when_remote_standing() -> None:
    assert (
        run_hook(
            "mcp__github__create_pull_request",
            {"title": "x", "draft": False},
            autonomy="STANDING",
        )
        == {}
    )


def test_allow_update_pull_request_undraft_when_remote_standing() -> None:
    assert (
        run_hook(
            "mcp__github__update_pull_request",
            {"pullNumber": 1, "draft": False},
            autonomy="STANDING",
        )
        == {}
    )


@pytest.mark.parametrize("state", ["closed", "open"])
def test_deny_update_pull_request_state_transition(state: str) -> None:
    assert _is_deny(
        run_hook("mcp__github__update_pull_request", {"pullNumber": 1, "state": state})
    )


# --- Merge policy: remote standing only; auto-merge always denied --------------------


def test_attended_merge_pull_request_denied() -> None:
    assert _is_deny(run_hook("mcp__github__merge_pull_request", {"pullNumber": 1}))


def test_standing_merge_pull_request_falls_through() -> None:
    assert (
        run_hook(
            "mcp__github__merge_pull_request",
            {"pullNumber": 1, "merge_method": "squash"},
            autonomy="STANDING",
        )
        == {}
    )


def test_standing_merge_exact_payload_repo_falls_through() -> None:
    assert (
        run_hook(
            "mcp__github__merge_pull_request",
            {
                "owner": "Jp8617465-sys",
                "repo": "asxos",
                "pullNumber": 1,
                "merge_method": "squash",
            },
            autonomy="STANDING",
        )
        == {}
    )


@pytest.mark.parametrize(
    "tool_input",
    [
        {
            "owner": "example",
            "repo": "asxos",
            "pullNumber": 1,
            "merge_method": "squash",
        },
        {
            "owner": "Jp8617465-sys",
            "repo": "other",
            "pullNumber": 1,
            "merge_method": "squash",
        },
        {
            "repository": "example/other",
            "pullNumber": 1,
            "merge_method": "squash",
        },
    ],
)
def test_standing_merge_wrong_payload_repo_denied(tool_input: dict) -> None:
    assert _is_deny(
        run_hook(
            "mcp__github__merge_pull_request",
            tool_input,
            autonomy="STANDING",
        )
    )


def test_standing_merge_gh_repo_override_denied() -> None:
    assert _is_deny(
        run_hook(
            "mcp__github__merge_pull_request",
            {"pullNumber": 1, "merge_method": "squash"},
            env_extra={"GH_REPO": "example/other"},
            autonomy="STANDING",
        )
    )


@pytest.mark.parametrize("method", [None, "merge", "rebase", "MERGE"])
def test_standing_merge_requires_explicit_squash(method: str | None) -> None:
    tool_input: dict = {"pullNumber": 1}
    if method is not None:
        tool_input["merge_method"] = method
    assert _is_deny(
        run_hook(
            "mcp__github__merge_pull_request",
            tool_input,
            autonomy="STANDING",
        )
    )


@pytest.mark.parametrize("state", ["", "ATTENDED", "standing", "BROKEN"])
def test_merge_pull_request_denied_without_exact_remote_standing(state: str) -> None:
    assert _is_deny(
        run_hook(
            "mcp__github__merge_pull_request",
            {"pullNumber": 1},
            autonomy=state,
        )
    )


@pytest.mark.parametrize("env_extra", [None, {"ARBI_UNATTENDED": "1"}])
def test_deny_enable_pr_auto_merge_every_mode(env_extra: dict | None) -> None:
    """Auto-merge is forbidden attended AND unattended — it removes the per-PR,
    James-instructed merge decision."""
    assert _is_deny(
        run_hook("mcp__github__enable_pr_auto_merge", {"pullNumber": 1}, env_extra=env_extra)
    )


def test_hook_never_emits_permission_allow() -> None:
    """Regression: the standing path must be hook-SILENCE, never a hook-level
    ``permissionDecision:"allow"``; state and server controls own the grant.

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
    """The state-aware hook and server controls own merge gating; a bare deny would
    make the standing path unreachable."""
    assert "mcp__github__merge_pull_request" not in _settings_deny()


def test_settings_allow_state_gated_pr_lifecycle_tools() -> None:
    allow = json.loads(SETTINGS.read_text())["permissions"]["allow"]
    for tool in (
        "mcp__github__create_pull_request",
        "mcp__github__update_pull_request",
        "mcp__github__merge_pull_request",
    ):
        assert tool in allow
    for rule in (
        "Bash(gh pr ready:*)",
        "Bash(gh pr merge:*)",
    ):
        assert rule in allow


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
