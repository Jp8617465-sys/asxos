"""pr-draft-guard.sh — MCP-surface verdicts AND the settings.json wiring.

Two layers, both pinned, because the 2026-08-21 incident was a WIRING failure,
not a logic failure: the hook's cases matched MCP tool names from day one, but
`.claude/settings.json` registered it only under `matcher: "Bash"` — a matcher
those tool names can never satisfy — so every MCP case was dead code and a PR
was un-drafted through the GitHub MCP server with no deny (independently
recorded by session 01YBEYvVFasrq89XhkncMKRD as a fourth R5/R16/R17 instance:
*the control exists and is not applying in this execution context*).

A test suite that only drove the hook via subprocess would have been GREEN
through that entire incident. Hence ``TestSettingsWiring``: it asserts the
settings file actually routes MCP tool names into the guards. Neither layer can
now regress without a red test.

Follows the ``tests/test_review_gate_hook.py`` pattern: drive the shell hook as
a subprocess with a PreToolUse JSON payload on stdin; a deny is a JSON verdict
on stdout, an allow/fall-through is silence.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "pr-draft-guard.sh"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def run_hook(payload: dict, *, unattended: bool = False) -> str:
    """Run the hook with `payload` on stdin; return raw stdout ('' = silent)."""
    env = dict(os.environ)
    env.pop("ARBI_UNATTENDED", None)
    if unattended:
        env["ARBI_UNATTENDED"] = "1"
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def assert_denied(out: str, *fragments: str) -> None:
    assert out, "expected a deny verdict, hook was silent"
    verdict = json.loads(out)["hookSpecificOutput"]
    assert verdict["permissionDecision"] == "deny"
    for fragment in fragments:
        assert fragment in verdict["permissionDecisionReason"]


class TestPrLifecycle:
    def test_create_without_draft_denied(self):
        out = run_hook(
            {"tool_name": "mcp__github__create_pull_request", "tool_input": {}}
        )
        assert_denied(out, "draft:true")

    def test_create_draft_false_denied(self):
        out = run_hook(
            {
                "tool_name": "mcp__github__create_pull_request",
                "tool_input": {"draft": False},
            }
        )
        assert_denied(out, "draft:true")

    def test_create_draft_true_silent(self):
        out = run_hook(
            {
                "tool_name": "mcp__github__create_pull_request",
                "tool_input": {"draft": True},
            }
        )
        assert out == ""

    def test_undraft_denied(self):
        # The exact 2026-08-21 incident shape.
        out = run_hook(
            {
                "tool_name": "mcp__github__update_pull_request",
                "tool_input": {"pullNumber": 147, "draft": False},
            }
        )
        assert_denied(out, "un-drafts")

    def test_update_without_draft_field_silent(self):
        # An edit not touching `draft` must NOT be denied — the jq has()
        # presence check, not the `// empty` conflation.
        out = run_hook(
            {
                "tool_name": "mcp__github__update_pull_request",
                "tool_input": {"pullNumber": 1, "title": "new title"},
            }
        )
        assert out == ""

    def test_update_state_change_denied(self):
        out = run_hook(
            {
                "tool_name": "mcp__github__update_pull_request",
                "tool_input": {"pullNumber": 1, "state": "closed"},
            }
        )
        assert_denied(out, "lifecycle")

    def test_merge_attended_falls_through_silently(self):
        # Attended: no hook-level allow OR deny — the normal permission
        # prompt / James-instructed flow applies (deny-only contract).
        out = run_hook(
            {
                "tool_name": "mcp__github__merge_pull_request",
                "tool_input": {"pullNumber": 1},
            }
        )
        assert out == ""

    def test_merge_unattended_denied(self):
        out = run_hook(
            {
                "tool_name": "mcp__github__merge_pull_request",
                "tool_input": {"pullNumber": 1},
            },
            unattended=True,
        )
        assert_denied(out, "unattended")

    def test_auto_merge_denied_both_modes(self):
        payload = {
            "tool_name": "mcp__github__enable_pr_auto_merge",
            "tool_input": {"pullNumber": 1},
        }
        assert_denied(run_hook(payload), "every mode")
        assert_denied(run_hook(payload, unattended=True), "every mode")


class TestMainBranchFileWrites:
    """The MCP twin of a `git push` to main — no hook owned this shape before."""

    @pytest.mark.parametrize(
        "tool",
        [
            "mcp__github__create_or_update_file",
            "mcp__github__push_files",
            "mcp__github__delete_file",
        ],
    )
    @pytest.mark.parametrize(
        "branch", ["main", "master", "Main", "refs/heads/main"]
    )
    def test_protected_ref_denied(self, tool, branch):
        out = run_hook(
            {"tool_name": tool, "tool_input": {"branch": branch, "path": "x"}}
        )
        assert_denied(out, "GitHub API")

    def test_claude_branch_silent(self):
        # Branch-side API writes are the SANCTIONED draft route for
        # authority-path changes (authority-guard contract) — never deny them.
        out = run_hook(
            {
                "tool_name": "mcp__github__create_or_update_file",
                "tool_input": {"branch": "claude/some-branch", "path": "x"},
            }
        )
        assert out == ""

    @pytest.mark.parametrize(
        "tool_input",
        [{}, {"branch": ""}, {"branch": None}],
        ids=["absent", "empty", "null"],
    )
    def test_missing_branch_denied(self, tool_input):
        # Security-engineer REQUIRED fix (2026-08-21): the contents API
        # defaults an omitted branch to the repo DEFAULT branch (main), so
        # silence here would be fail-open on a third-party schema staying
        # strict. No legitimate call omits the branch — deny.
        out = run_hook(
            {
                "tool_name": "mcp__github__create_or_update_file",
                "tool_input": {**tool_input, "path": "x"},
            }
        )
        assert_denied(out, "DEFAULT branch")


class TestNonMatchingTools:
    def test_bash_silent(self):
        out = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": "git push"}}
        )
        assert out == ""

    def test_read_tools_silent(self):
        out = run_hook(
            {"tool_name": "mcp__github__pull_request_read", "tool_input": {}}
        )
        assert out == ""


class TestSettingsWiring:
    """The layer the incident actually broke. A hook is only a control if a
    matcher routes the guarded tool names into it."""

    def _pretooluse(self):
        return json.loads(SETTINGS.read_text())["hooks"]["PreToolUse"]

    def _blocks_matching(self, tool_name: str):
        for block in self._pretooluse():
            matcher = block.get("matcher")
            if matcher is None or re.fullmatch(matcher, tool_name):
                yield block

    @pytest.mark.parametrize(
        "tool_name",
        [
            "mcp__github__update_pull_request",
            "mcp__github__merge_pull_request",
            "mcp__github__create_pull_request",
            "mcp__github__create_or_update_file",
        ],
    )
    def test_pr_write_tools_route_into_pr_draft_guard(self, tool_name):
        commands = [
            hook["command"]
            for block in self._blocks_matching(tool_name)
            for hook in block["hooks"]
        ]
        assert any("pr-draft-guard.sh" in c for c in commands), (
            f"{tool_name} matches no PreToolUse block running pr-draft-guard.sh "
            "- the 2026-08-21 dead-wiring hole is open again"
        )

    def test_mcp_tools_route_into_unattended_guard(self):
        commands = [
            hook["command"]
            for block in self._blocks_matching("mcp__Supabase__execute_sql")
            for hook in block["hooks"]
        ]
        assert any("unattended-guard.sh" in c for c in commands), (
            "MCP tools match no PreToolUse block running unattended-guard.sh - "
            "its entire mcp__* case tree (incl. the fail-closed unknown-server "
            "deny) is dead code again"
        )

    @pytest.mark.parametrize(
        ("matcher", "expected_guards"),
        [
            (
                "Bash",
                (
                    "push-guard.sh",
                    "authority-guard.sh",
                    "pr-draft-guard.sh",
                    "unattended-guard.sh",
                ),
            ),
            ("Edit", ("authority-guard.sh", "unattended-guard.sh")),
            ("Write", ("authority-guard.sh", "unattended-guard.sh")),
            ("MultiEdit", ("authority-guard.sh", "unattended-guard.sh")),
            ("NotebookEdit", ("authority-guard.sh", "unattended-guard.sh")),
        ],
    )
    def test_existing_wiring_unchanged(self, matcher, expected_guards):
        # Regression guard across ALL pre-existing blocks, not just Bash —
        # a settings replacement that quietly drops a guard from any block is
        # the same smuggle class the 2026-08-21 review checked for.
        commands = [
            hook["command"]
            for block in self._pretooluse()
            if block.get("matcher") == matcher
            for hook in block["hooks"]
        ]
        assert commands, f"the {matcher} PreToolUse block is gone entirely"
        for guard in expected_guards:
            assert any(guard in c for c in commands), (
                f"{matcher} chain lost {guard}"
            )

    def test_auto_merge_stays_in_permissions_deny(self):
        # The settings-level deny removes the tool from context entirely —
        # the hook's every-mode deny is the second layer, not the only one.
        deny = json.loads(SETTINGS.read_text())["permissions"]["deny"]
        assert "mcp__github__enable_pr_auto_merge" in deny
