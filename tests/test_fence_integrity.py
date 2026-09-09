"""Fence-integrity regressions for the always-on authority guard.

Each case here was found by *probing the hook*, not by reading it. That
distinction is the point: the guard's own header (`:22-27`) frames its residual
risk as exotic — "a base64-decoded path, `os.rename`, indirect string
construction" — and measurement showed the two most ordinary spellings walked
straight through:

  * `rm <fenced path>` — deletion appeared in neither the write-verb list nor the
    redirect check, so removing a fenced file needed no bypass at all.
  * `echo x > ./<fenced path>` — `$authority_ref`'s left-boundary class excludes
    `/`, so a leading `./` un-matched the path.

Both change what runs as surely as an edit does. A third case, `jq` being absent,
made the always-on fence silently vanish: it failed OPEN where its sibling
`unattended-guard.sh:49` fails closed.

The probes invoke the guard and read its decision. None of them performs the
destructive act to see whether it is caught — a probe that turns destructive when
the guard is missing is not a test, it is the incident.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_HOOK = ROOT / ".claude" / "hooks" / "authority-guard.sh"
UNATTENDED_HOOK = ROOT / ".claude" / "hooks" / "unattended-guard.sh"
SETTINGS = ROOT / ".claude" / "settings.json"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="hook guards require jq"
)


def _run(hook: Path, payload: dict, *, env_extra: dict | None = None) -> dict:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "CLAUDE_PROJECT_DIR": str(ROOT),
        **(env_extra or {}),
    }
    proc = subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "cwd": str(ROOT), "tool_input": {"command": command}}


def _decision(result: dict) -> str:
    return result.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


# ---------------------------------------------------------------------------
# W1c — deletion of a fenced path
# ---------------------------------------------------------------------------

DELETION_COMMANDS = [
    "rm .github/workflows/full-check.yml",
    "rm -f .github/workflows/full-check.yml",
    "git rm .github/workflows/full-check.yml",
    "rm docs/product/arbi-constitution.md",
    "rm .env",
    "rm render.yaml",
    "unlink .env",
]


@pytest.mark.parametrize("command", DELETION_COMMANDS)
def test_deleting_an_authority_path_is_denied(command: str) -> None:
    """Deleting a fenced file changes what runs as surely as editing it."""
    assert _decision(_run(AUTHORITY_HOOK, _bash(command))) == "deny"


# ---------------------------------------------------------------------------
# W1b — `./` path spellings
# ---------------------------------------------------------------------------

DOT_SLASH_COMMANDS = [
    "echo x > ./.github/workflows/foo.yml",
    "echo x > ./docs/product/arbi-constitution.md",
    "echo x > ./.env",
    "python -c \"open('./.github/workflows/x.yml','w')\"",
    "cp evil.yml ./.github/workflows/x.yml",
]


@pytest.mark.parametrize("command", DOT_SLASH_COMMANDS)
def test_dot_slash_prefix_does_not_evade_the_fence(command: str) -> None:
    """`./x` and `x` name the same file; the guard must not distinguish them."""
    assert _decision(_run(AUTHORITY_HOOK, _bash(command))) == "deny"


def test_parent_directory_spelling_is_left_alone() -> None:
    """The `./` collapse must not eat `../`, which names a different path.

    A write outside the repo is not this guard's business, and rewriting `../`
    would make it one.
    """
    assert _decision(_run(AUTHORITY_HOOK, _bash("echo x > ../outside.txt"))) == "allow"


# ---------------------------------------------------------------------------
# Regressions: the guard must stay quiet on ordinary work
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS = [
    "pytest -q",
    "rm -rf .pytest_cache",
    "rm /tmp/scratch.txt",
    "rm build/artifact.tar.gz",
    "git checkout -- tests/test_foo.py",
    "cat .github/workflows/full-check.yml",
    "grep -n secrets .github/workflows/full-check.yml",
    "mv build/a.txt build/b.txt",
    "echo x > docs/proposals/note.md",
]


@pytest.mark.parametrize("command", ALLOWED_COMMANDS)
def test_ordinary_commands_are_not_denied(command: str) -> None:
    """A fence that blocks routine work gets routed around, so this half of the
    contract matters as much as the deny half. Reading a fenced file is allowed;
    only writes and deletions are fenced."""
    assert _decision(_run(AUTHORITY_HOOK, _bash(command))) == "allow"


# ---------------------------------------------------------------------------
# W1 — fail closed without jq
# ---------------------------------------------------------------------------


def test_guard_fails_closed_when_jq_is_absent(tmp_path: Path) -> None:
    """Without jq the guard cannot read the payload at all.

    It previously `exit 0`-ed, so the always-on fence silently disappeared on any
    machine lacking jq. `unattended-guard.sh:49` already failed closed here; this
    is the missing half of that pair. The probe builds a PATH holding every
    binary the script needs EXCEPT jq — an empty PATH would fail for the
    uninteresting reason that `bash` itself is missing.
    """
    binfmt = tmp_path / "bin"
    binfmt.mkdir()
    for tool in ("bash", "sh", "cat", "sed", "grep", "realpath", "python3"):
        found = shutil.which(tool)
        if found:
            (binfmt / tool).symlink_to(found)
    assert shutil.which("jq", path=str(binfmt)) is None

    payload = {
        "tool_name": "Write",
        "cwd": str(ROOT),
        # Deliberately a NON-authority path: the only thing under test is the
        # missing-jq branch, so the path must not be a second reason to deny.
        "tool_input": {"file_path": "tests/test_foo.py", "content": "x"},
    }
    proc = subprocess.run(
        ["bash", str(AUTHORITY_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": str(binfmt), "CLAUDE_PROJECT_DIR": str(ROOT)},
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip(), "guard produced no decision without jq (failed open)"
    assert _decision(json.loads(proc.stdout)) == "deny"


# ---------------------------------------------------------------------------
# W2 — unattended-guard parity on .github/
# ---------------------------------------------------------------------------


def test_unattended_guard_denies_github_when_armed() -> None:
    """`.github/` was absent from unattended-guard's authority case, so the whole
    fence rested on authority-guard.sh alone with no second layer behind it."""
    payload = {
        "tool_name": "Write",
        "cwd": str(ROOT),
        "tool_input": {"file_path": ".github/workflows/x.yml", "content": "x"},
    }
    armed = _run(UNATTENDED_HOOK, payload, env_extra={"ARBI_UNATTENDED": "1"})
    assert _decision(armed) == "deny"


def test_unattended_guard_is_a_noop_when_not_armed() -> None:
    """It is ARBI_UNATTENDED-gated by design; authority-guard.sh covers attended."""
    payload = {
        "tool_name": "Write",
        "cwd": str(ROOT),
        "tool_input": {"file_path": ".github/workflows/x.yml", "content": "x"},
    }
    assert _run(UNATTENDED_HOOK, payload) == {}
