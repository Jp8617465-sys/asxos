"""Pins on the agent-lane harness after the 2026-09-10 chief-of-staff rollout.

Four lanes (``claude-execute``, ``nightly-triage``, ``weekly-toolwatch``,
``backlog-roll``) run Claude Code in Actions. This file pins the shape they now share:
``--permission-mode auto`` instead of an ``--allowedTools`` fence, the repo-scoped PAT as
BOTH ``GH_TOKEN`` and the checkout credential, and a step that installs the user-level
auto-mode settings the classifier will actually read.

**What these tests do and do not prove.** Asserting that ``--permission-mode auto`` appears
in ``claude_args`` proves the flag is *passed*. It does NOT prove the session actually got
auto mode — if auto is unavailable the CLI falls back to Manual, where in a headless run
every unlisted action is denied with no prompt and the run looks successful having merged
nothing. That can only be confirmed from a real run log, and it is listed as a
first-dispatch check in ``docs/session-handoff-2026-09-10.md``. The same caveat applies to
``CLAUDE_PROJECT_DIR`` resolving on the runner so ``secrets-guard.sh`` runs rather than
exiting 127.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_SETTINGS = _ROOT / ".claude" / "settings.json"
_RUNNER_SETTINGS = _ROOT / ".github" / "runner" / "claude-user-settings.json"
_SECRETS_GUARD = _ROOT / ".claude" / "hooks" / "secrets-guard.sh"

AGENT_LANES = [
    "claude-execute.yml",
    "nightly-triage.yml",
    "weekly-toolwatch.yml",
    "backlog-roll.yml",
]


def _lane_text(name: str) -> str:
    return (_WORKFLOWS / name).read_text(encoding="utf-8")


# --- the four agent lanes ---------------------------------------------------------------


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_runs_in_auto_mode_without_an_allowedtools_fence(lane: str) -> None:
    """Auto mode replaced the per-lane allowlist; the fence must be gone, not both."""
    text = _lane_text(lane)
    assert "--permission-mode auto" in text, f"{lane} does not pass --permission-mode auto"
    assert "--allowedTools" not in text, f"{lane} still carries an --allowedTools fence"
    assert "--mcp-config" in text, f"{lane} does not pass --mcp-config"


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_has_no_unattended_arming(lane: str) -> None:
    """``ARBI_UNATTENDED`` armed a guard hook that no longer exists."""
    assert "ARBI_UNATTENDED" not in _lane_text(lane)


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_checks_out_with_the_pat(lane: str) -> None:
    """The PAT is the checkout credential, not just ``GH_TOKEN``.

    ``persist-credentials: true`` alone persists ``GITHUB_TOKEN``, and a push made with
    ``GITHUB_TOKEN`` deliberately does not trigger other workflows — so ``full-check``
    would never fire on the PR the lane opens, and arbi would wait forever or merge on
    nothing green.
    """
    text = _lane_text(lane)
    assert "token: ${{ secrets.ARBI_GITHUB_TOKEN }}" in text, f"{lane} checkout lacks the PAT"
    assert "persist-credentials: true" in text, f"{lane} does not persist credentials"
    assert "GH_TOKEN: ${{ secrets.ARBI_GITHUB_TOKEN }}" in text, f"{lane} GH_TOKEN is not the PAT"


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_installs_user_level_auto_mode_settings(lane: str) -> None:
    """The classifier ignores ``autoMode`` in project settings, so it must be user-level."""
    text = _lane_text(lane)
    assert ".github/runner/claude-user-settings.json" in text, f"{lane} does not install them"
    assert "~/.claude/settings.json" in text, f"{lane} does not write the user-level path"


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_yaml_parses(lane: str) -> None:
    assert yaml.safe_load(_lane_text(lane)) is not None


# --- project settings -------------------------------------------------------------------


def _settings() -> dict:
    return json.loads(_SETTINGS.read_text(encoding="utf-8"))


def test_settings_allow_covers_the_dev_loop() -> None:
    allow = _settings()["permissions"]["allow"]
    for rule in ("Bash(git:*)", "Bash(gh:*)", "mcp__github__*", "mcp__supabase__*"):
        assert rule in allow, f"{rule} missing from permissions.allow"


def test_settings_deny_is_exactly_the_two_env_rules() -> None:
    """Deny is two entries. An ask rule would force a prompt even in auto mode."""
    perms = _settings()["permissions"]
    assert perms["deny"] == ["Read(./.env)", "Edit(./.env)"]
    assert perms["ask"] == []


def test_settings_register_exactly_one_pretooluse_hook() -> None:
    hooks = _settings()["hooks"]["PreToolUse"]
    assert len(hooks) == 1, "the four guard hooks were replaced by one secrets hook"
    commands = [h["command"] for h in hooks[0]["hooks"]]
    assert len(commands) == 1
    assert "secrets-guard.sh" in commands[0]


# --- the runner's user-level settings ---------------------------------------------------


def test_runner_settings_keep_the_defaults_sentinel() -> None:
    """Dropping ``$defaults`` REPLACES the built-in rule lists rather than extending them.

    That would discard the classifier's own protections — the force-push block among
    them — so the sentinel has to lead both arrays.
    """
    cfg = json.loads(_RUNNER_SETTINGS.read_text(encoding="utf-8"))
    assert cfg["permissions"]["defaultMode"] == "auto"
    assert cfg["autoMode"]["environment"][0] == "$defaults"
    assert cfg["autoMode"]["allow"][0] == "$defaults"


def test_runner_settings_do_not_pre_approve_claude_dir_edits() -> None:
    """``.claude/`` is the one path a lane may not edit without a human (AGENTS.md section 8).

    It is where the agent's own permissions are written, so pre-approving it in the very
    file that grants the lane its permissions is self-modification with no human in the
    loop. #254 wrote that grant; #256 reserved ``.claude/**`` everywhere else and missed
    this file. The grant for ``.github/workflows/`` stays — that one AGENTS.md section 8
    explicitly gives arbi.

    The assertion is on the grant *text*, because the classifier reads these as prose.
    A rule naming ``.claude`` at all is the failure: there is no safe phrasing of it here.
    """
    cfg = json.loads(_RUNNER_SETTINGS.read_text(encoding="utf-8"))
    grants = [g for g in cfg["autoMode"]["allow"] if g != "$defaults"]
    editing = [g for g in grants if "Editing files under" in g]
    assert editing, "the workflow-editing grant vanished; AGENTS.md section 8 gives arbi that one"
    for grant in editing:
        head = grant.split("as part of the requested task.")[0]
        assert ".claude/" not in head, (
            f"a lane grant pre-approves editing .claude/: {grant!r}"
        )


# --- secrets-guard.sh behaviour ---------------------------------------------------------

pytestmark_jq = pytest.mark.skipif(
    shutil.which("jq") is None, reason="secrets-guard.sh needs jq on PATH"
)


def _run_guard(command: str) -> dict:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run(
        ["bash", str(_SECRETS_GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _denied(command: str) -> bool:
    return _run_guard(command).get("permissionDecision") == "deny"


@pytestmark_jq
@pytest.mark.parametrize(
    "command",
    [
        "cat .env",
        "echo $SUPABASE_ACCESS_TOKEN",
        "printenv",
    ],
)
def test_secrets_guard_denies_the_three_leak_shapes(command: str) -> None:
    """Reading .env, expanding a secret-named variable, and dumping the environment."""
    assert _denied(command), f"secrets-guard let this through: {command}"


@pytestmark_jq
@pytest.mark.parametrize("command", ["pytest -q", "git push origin HEAD"])
def test_secrets_guard_allows_the_ordinary_dev_loop(command: str) -> None:
    """Deny-only: a shape it does not recognise runs normally."""
    assert _run_guard(command) == {}, f"secrets-guard blocked ordinary work: {command}"
