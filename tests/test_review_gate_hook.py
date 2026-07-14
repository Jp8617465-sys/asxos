"""Tests for ``.claude/hooks/review-gate.sh`` — the PreToolUse(Bash) review gate.

The hook is a shell script, so these tests drive the *real* script via
``subprocess`` against a throwaway git repo, feeding it the same JSON payload
shape Claude Code's PreToolUse hook delivers on stdin
(``{"tool_input": {"command": "..."}}``) and asserting on its emitted
permission decision.

R13 (2026-07-13) is the reason this file exists: the gate inspects the *staged*
diff, so a command that stages Python in the same breath as the commit — a
compound ``git add X.py && git commit`` or an auto-staging ``git commit -a`` —
used to race past it. The DENY-compound / DENY-autostage cases below pin that
hole shut; the ALLOW cases pin the contract that the hook stays out of the way
for plain commits, docs-only work, ``--amend``, and reviewed (marker-present)
diffs.

The hook is advisory + fail-open by contract (see its header): jq missing or a
bad project dir means it exits without denying. These tests assume ``jq`` and
``git`` are on PATH (they are in CI); if ``jq`` is absent the suite skips rather
than asserting fail-open behaviour it can't distinguish from a real allow.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "review-gate.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("git") is None,
    reason="review-gate.sh needs jq + git on PATH",
)


def _git(repo: Path, *args: str) -> None:
    """Run git in ``repo`` with hooks disabled so the harness never self-triggers."""
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A tmp git repo with one committed .py file, ready for gate scenarios."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / ".claude").mkdir()
    (tmp_path / "seed.py").write_text("print(1)\n")
    _git(tmp_path, "add", "seed.py")
    _git(tmp_path, "commit", "-qm", "seed")
    return tmp_path


def run_hook(repo: Path, command: str) -> dict:
    """Feed the hook the PreToolUse payload for ``command``; return its decision.

    Returns ``{}`` when the hook allows (exits 0 with no JSON), or the parsed
    ``hookSpecificOutput`` dict when it denies. The hook always exits 0 (deny is
    expressed in the JSON, not the exit code), so a non-zero exit is a bug.
    """
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    if not out:
        return {}
    return json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


def _stage_and_mark(repo: Path) -> None:
    """Stage seed.py and write the diff-keyed marker the plain-commit path wants."""
    _git(repo, "add", "seed.py")
    staged = subprocess.run(
        ["git", "diff", "--cached"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout
    sha = subprocess.run(
        ["git", "hash-object", "--stdin"],
        cwd=repo,
        input=staged,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()[:12]
    (repo / ".claude" / f".review-passed-{sha}").touch()


# --- R13: commands that stage Python in the same step must be denied ----------


@pytest.mark.parametrize(
    "command",
    [
        "git add seed.py && git commit -m x",  # compound
        "git stage seed.py && git commit -m x",  # `git stage` == `git add` synonym
        "git commit -a -m x",  # auto-stage short
        "git commit -am x",  # auto-stage + message cluster
        'git commit -am"WIP"',  # message glued to the flag, no space (anchor drop)
        "git commit --all -m x",  # auto-stage long
        "git commit -a --amend",  # -a still caught alongside --amend
    ],
)
def test_deny_inline_stage(repo: Path, command: str) -> None:
    """Every shape that stages tracked .py in the same step is denied up front,
    and all cite the 'same step' guidance (same branch)."""
    (repo / "seed.py").write_text("print(2)\n")  # unstaged tracked change
    decision = run_hook(repo, command)
    assert _is_deny(decision)
    assert "same step" in decision["permissionDecisionReason"]


def test_deny_compound_add_untracked_py(repo: Path) -> None:
    (repo / "new_mod.py").write_text("print('new')\n")  # untracked .py
    assert _is_deny(run_hook(repo, "git add . && git commit -m x"))


# --- ALLOW: the gate must stay out of the way for these ------------------------


def test_allow_plain_commit_nothing_staged(repo: Path) -> None:
    (repo / "seed.py").write_text("print(2)\n")  # unstaged only — nothing to gate
    assert run_hook(repo, "git commit -m x") == {}


def test_allow_amend_does_not_autostage(repo: Path) -> None:
    # --amend alone does not auto-stage, so it must fall through to the normal
    # path (nothing staged -> allow), NOT be caught by the -a heuristic.
    (repo / "seed.py").write_text("print(3)\n")
    assert run_hook(repo, "git commit --amend --no-edit") == {}


def test_allow_docs_only_compound(repo: Path) -> None:
    (repo / "README.md").write_text("hello\n")  # no .py pending
    assert run_hook(repo, "git add README.md && git commit -m docs") == {}


def test_allow_autostage_when_no_py_pending(repo: Path) -> None:
    # The -a/-am branch must still respect the .py filter: an auto-stage commit
    # with only non-.py changes pending is allowed, not blanket-denied.
    (repo / "README.md").write_text("hello\n")  # tracked... make it tracked first
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "add readme")
    (repo / "README.md").write_text("hello world\n")  # unstaged non-.py change
    assert run_hook(repo, "git commit -am docs") == {}


def test_allow_non_commit_command(repo: Path) -> None:
    assert run_hook(repo, "git status") == {}


# --- the pre-existing plain-commit path still holds ---------------------------


def test_deny_staged_py_without_marker(repo: Path) -> None:
    (repo / "seed.py").write_text("print(2)\n")
    _git(repo, "add", "seed.py")
    decision = run_hook(repo, "git commit -m x")
    assert _is_deny(decision)
    assert "review loop" in decision["permissionDecisionReason"]


def test_allow_staged_py_with_marker(repo: Path) -> None:
    (repo / "seed.py").write_text("print(2)\n")
    _stage_and_mark(repo)
    assert run_hook(repo, "git commit -m x") == {}
