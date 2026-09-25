"""Pins on the agent-lane harness after the 2026-09-10 chief-of-staff rollout.

Four lanes (``claude-execute``, ``nightly-triage``, ``weekly-toolwatch``,
``backlog-roll``) run Claude Code in Actions. This file pins the shape they now share:
``--permission-mode auto`` instead of an ``--allowedTools`` fence, the repo-scoped PAT as
BOTH ``GH_TOKEN`` and the checkout credential, and a step that installs the user-level
auto-mode settings the classifier will actually read.

**What these tests do and do not prove.** Asserting that ``--permission-mode auto`` appears
in ``claude_args`` proves the flag is *passed*. It does NOT prove the session actually got
auto mode — if auto is unavailable the CLI falls back to Manual. Of the two 2026-09-10
first-dispatch unknowns, one is closed: auto mode engaging headlessly, by the 2026-09-14
``weekly-toolwatch`` dispatch, run ``34846052898``. The other — ``CLAUDE_PROJECT_DIR``
resolving so ``secrets-guard.sh`` runs rather than exiting 127 — is **A-22 proof 2** and
is NOT proven by any test here (#353). What this file now pins instead is that the hook
can no longer fail *silently*: a missing guard is exit 2, a missing ``jq`` is exit 2, and
every call leaves a ``GUARD`` line in the proof log that the A-22 canary step reads.

What used to be inferred — that in a headless run an unanswerable prompt is denied rather
than retried against the turn budget — is a named flag as of 2026-09-14:
``--permission-prompts none``. See ``test_lane_denies_what_it_cannot_prompt_for``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_SETTINGS = _ROOT / ".claude" / "settings.json"
_RUNNER_SETTINGS = _ROOT / ".github" / "runner" / "claude-user-settings.json"
_SECRETS_GUARD = _ROOT / ".claude" / "hooks" / "secrets-guard.sh"

# The exact commit all four lanes pin: v1.0.230 peeled (not the tag object).
# Tag v1.0.230 is annotated (3bc13d79…); the pin is the commit it names.
# Bundles Claude Code 2.1.277.
_ACTION_SHA = "4036a180cf690f49529f5d8c79c998855287f590"
_ACTION_RELEASE = "v1.0.230"

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
def test_lane_denies_what_it_cannot_prompt_for(lane: str) -> None:
    """``--permission-prompts none``: an unanswerable prompt is a deny, not a retry.

    Before this flag, whether a would-prompt action was denied, hung, or was retried
    until the turn budget ran out was an inferred property of "headless + auto mode, no
    TTY". The bundled CLI's own ``--help`` states the contract: *"nobody: anything that
    would prompt is denied automatically; the permission mode still decides everything
    else"*.

    It denies strictly more than before, so it is NOT ``--dangerously-skip-permissions``;
    a lane carrying either must fail here.
    """
    text = _lane_text(lane)
    assert "--permission-prompts none" in text, f"{lane} does not deny unanswerable prompts"
    assert "dangerously-skip-permissions" not in text, f"{lane} bypasses permission checks"


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_pins_the_action_to_one_tagged_release(lane: str) -> None:
    """All four lanes share one 40-hex pin, and the comment names the release.

    A floating ``@v1`` would let the bundled CLI change under the lanes with no diff to
    review; four pins drifting apart would make a lane-specific failure unattributable.
    The comment carries the tag because a bare SHA tells a reader nothing.
    """
    text = _lane_text(lane)
    uses = [
        ln.strip()
        for ln in text.splitlines()
        if "claude-code-action@" in ln and not ln.strip().startswith("#")
    ]
    assert len(uses) == 1, f"{lane} has {len(uses)} claude-code-action steps: {uses}"
    assert _ACTION_SHA in uses[0], f"{lane} pin differs: {uses[0]}"
    assert _ACTION_RELEASE in uses[0], f"{lane} pin does not name its release: {uses[0]}"


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_lane_yaml_parses(lane: str) -> None:
    assert yaml.safe_load(_lane_text(lane)) is not None


@pytest.mark.parametrize("lane", AGENT_LANES)
def test_claude_args_comments_are_whole_line_only(lane: str) -> None:
    """Every lane comments inside ``claude_args``; only WHOLE-LINE comments are stripped.

    Verified at the primary source, ``anthropics/claude-code-action`` at the pinned
    commit: ``base-action/src/parse-sdk-options.ts`` filters
    ``!line.trim().startsWith("#")`` before shell-quote sees the string, and its own
    docstring says inline ``#`` "is left untouched". So a comment appended to the END of
    a flag line is passed to the CLI as arguments. This pins the shape the lanes rely on.
    """
    block = _lane_text(lane).split("claude_args: |", 1)[1]
    for raw in block.splitlines():
        line = raw.strip()
        if line and not raw.startswith(" " * 12):
            break  # dedented out of the block scalar
        if line.startswith("#"):
            continue
        assert "#" not in line, f"{lane}: inline comment on a flag line: {line!r}"


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
    assert hooks[0]["matcher"] == "Read|Bash", "shape 4 (secret-shaped files) needs Read too"
    commands = [h["command"] for h in hooks[0]["hooks"]]
    assert len(commands) == 1
    assert "secrets-guard.sh" in commands[0]


def test_pretooluse_hook_fails_closed_when_the_guard_is_missing() -> None:
    """The old command was ``bash $CLAUDE_PROJECT_DIR/.claude/hooks/secrets-guard.sh``:
    with the variable unset that is ``bash /.claude/...``, exit 127, which the harness
    treats as a NON-blocking hook error — the tool call proceeds. A-22's whole question
    was whether that ever happened on the runner. Now the path falls back to the
    workspace and a missing guard is exit 2, a blocking error."""
    (command,) = [h["command"] for h in _settings()["hooks"]["PreToolUse"][0]["hooks"]]
    assert "${CLAUDE_PROJECT_DIR:-${GITHUB_WORKSPACE:-.}}" in command
    assert "exit 2" in command


def test_settings_register_a_sessionstart_marker_hook() -> None:
    """One ``A22-MARKER`` line per session into the proof log; the canary step reads
    ``project_dir=set`` from it. Never tool input — there is none at session start."""
    (entry,) = _settings()["hooks"]["SessionStart"]
    (command,) = [h["command"] for h in entry["hooks"]]
    assert "A22-MARKER" in command
    assert "a22-hook-proof.log" in command
    assert "${CLAUDE_PROJECT_DIR:+set}" in command


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
        assert ".claude/" not in head, f"a lane grant pre-approves editing .claude/: {grant!r}"


# --- secrets-guard.sh behaviour ---------------------------------------------------------

pytestmark_jq = pytest.mark.skipif(
    shutil.which("jq") is None, reason="secrets-guard.sh needs jq on PATH"
)


def _guard(
    *,
    tool_name: str = "Bash",
    command: str | None = None,
    file_path: str | None = None,
    log_dir: Path | None = None,
    path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    tool_input: dict[str, str] = {}
    if command is not None:
        tool_input["command"] = command
    if file_path is not None:
        tool_input["file_path"] = file_path
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    env = {"PATH": os.environ.get("PATH", "") if path is None else path}
    if log_dir is not None:
        env["RUNNER_TEMP"] = str(log_dir)
    return subprocess.run(
        ["bash", str(_SECRETS_GUARD)], input=payload, capture_output=True, text=True, env=env
    )


def _run_guard(command: str, **kw: Any) -> dict:
    proc = _guard(command=command, **kw)
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _denied(command: str, **kw: Any) -> bool:
    return _run_guard(command, **kw).get("permissionDecision") == "deny"


@pytestmark_jq
@pytest.mark.parametrize(
    "command",
    [
        "cat .env",
        "echo $SUPABASE_ACCESS_TOKEN",
        "printenv",
    ],
)
def test_secrets_guard_denies_the_three_leak_shapes(command: str, tmp_path: Path) -> None:
    """Reading .env, expanding a secret-named variable, and dumping the environment."""
    assert _denied(command, log_dir=tmp_path), f"secrets-guard let this through: {command}"


@pytestmark_jq
@pytest.mark.parametrize("command", ["pytest -q", "git push origin HEAD", "ls *.py"])
def test_secrets_guard_allows_the_ordinary_dev_loop(command: str, tmp_path: Path) -> None:
    """Deny-only: a shape it does not recognise runs normally."""
    assert _run_guard(command, log_dir=tmp_path) == {}, (
        f"secrets-guard blocked ordinary work: {command}"
    )


@pytestmark_jq
@pytest.mark.parametrize(
    ("tool_name", "command", "file_path"),
    [
        ("Read", None, "canary.secret"),
        ("Read", None, "/home/runner/work/asxos/asxos/canary.secret"),
        ("Read", None, ".env"),
        ("Read", None, ".env.local"),
        ("Read", None, "keys/deploy.pem"),
        ("Read", None, "signing.key"),
        ("Bash", "cat canary.secret", None),
        ("Bash", "cat .env.local", None),
        ("Bash", "cd /tmp && grep -r x keys/deploy.pem", None),
        ("Bash", "sudo cat /etc/ssl/private/site.key", None),
        ("Bash", "python -c 'print(open(\"keys/deploy.pem\").read())'", None),
    ],
)
def test_secrets_guard_denies_secret_shaped_file_reads(
    tool_name: str, command: str | None, file_path: str | None, tmp_path: Path
) -> None:
    """Shape 4: the A-22 canary is a Read of ``canary.secret``, and a guard that only
    watched Bash would have let the canary through — so the proof needs this rule."""
    proc = _guard(tool_name=tool_name, command=command, file_path=file_path, log_dir=tmp_path)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    assert "secret-shaped file" in out["permissionDecisionReason"]


@pytestmark_jq
@pytest.mark.parametrize(
    ("tool_name", "command", "file_path"),
    [
        ("Read", None, ".env.example"),
        ("Read", None, "asxos/config.py"),
        ("Read", None, "docs/ops/keys.md"),
        ("Bash", "cat .env.example", None),
        ("Bash", "git add .claude/hooks/secrets-guard.sh", None),
        ("Bash", "git add signing.key && git commit -m 'add canary.secret for A-22'", None),
        ("Bash", "ls canary.secret", None),
        (
            "Bash",
            "git commit -q -m \"$(cat <<'EOF'\nfeat: canary.secret is read by the proof\nEOF\n)\"",
            None,
        ),
        ("Edit", None, "canary.secret"),
    ],
)
def test_secrets_guard_allows_env_example_and_ordinary_files(
    tool_name: str, command: str | None, file_path: str | None, tmp_path: Path
) -> None:
    """``.env.example`` is documentation; ``.md``/``.py`` are not secret-shaped; naming a
    secret-shaped file without reading it (``git add``, ``ls``, a commit message, a
    heredoc body) is not a leak; and a tool the matcher does not name (Edit) is allowed
    through untouched."""
    proc = _guard(tool_name=tool_name, command=command, file_path=file_path, log_dir=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_secrets_guard_fails_closed_without_jq(tmp_path: Path) -> None:
    """No jq used to be ``exit 0`` — a guard that silently ran open on a runner without
    it. Exit 2 is the harness's blocking error."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "bash").symlink_to(shutil.which("bash") or "/bin/bash")
    proc = _guard(command="cat .env", log_dir=tmp_path, path=str(bindir))
    assert proc.returncode == 2
    assert "jq is missing" in proc.stderr


@pytestmark_jq
def test_secrets_guard_writes_one_proof_line_per_call_without_tool_input(tmp_path: Path) -> None:
    """The A-22 canary step greps this log. It must say what was decided and whether
    CLAUDE_PROJECT_DIR was set — and must never carry the command or the path."""
    _guard(tool_name="Read", file_path="canary.secret", log_dir=tmp_path)
    _guard(command="pytest -q", log_dir=tmp_path)
    lines = (tmp_path / "a22-hook-proof.log").read_text(encoding="utf-8").splitlines()
    assert lines == [
        "GUARD tool=Read decision=BLOCK rule=secret-file project_dir=unset",
        "GUARD tool=Bash decision=allow rule=- project_dir=unset",
    ]
    assert "canary" not in "".join(lines) and "pytest" not in "".join(lines)


@pytestmark_jq
def test_secrets_guard_reports_project_dir_when_set(tmp_path: Path) -> None:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    subprocess.run(
        ["bash", str(_SECRETS_GUARD)],
        input=payload,
        capture_output=True,
        text=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "RUNNER_TEMP": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(_ROOT),
        },
        check=True,
    )
    assert (
        (tmp_path / "a22-hook-proof.log")
        .read_text(encoding="utf-8")
        .strip()
        .endswith("project_dir=set")
    )
