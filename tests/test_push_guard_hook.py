"""Tests for ``.claude/hooks/push-guard.sh`` — the always-on PreToolUse(Bash) push/gh guard.

DENY-only by design (see the hook's header): whether a PreToolUse hook's
``permissionDecision:"allow"`` reliably suppresses Claude Code's interactive prompt is not
confirmed in the platform's documented behavior, so this hook never attempts to pre-approve
anything — it only ever emits ``deny`` or stays silent (silence falls through to the normal
permission flow). These tests therefore only assert two outcomes: an explicit deny for
dangerous shapes, and ``{}`` (no-op) for everything else — including the reversible cases a
naive glob would wrongly treat as dangerous (a `claude/**`-to-`claude/**` push, a force-push
to one's own `claude/**` branch).

The deny set is driven by real bugs this hook exists to catch: a `claude/x:main` refspec
defeats a source-prefix glob (the R13-class false-boundary the autonomy-unlock-pack's
red-team found in PR #38's first draft) while still landing on remote `main`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "push-guard.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("git") is None,
    reason="push-guard.sh needs jq + git on PATH",
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=repo, check=True, capture_output=True, text=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A tmp git repo, default branch 'main', checked out onto claude/work."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "seed.py").write_text("print(1)\n")
    _git(tmp_path, "add", "seed.py")
    _git(tmp_path, "commit", "-qm", "seed")
    _git(tmp_path, "checkout", "-b", "claude/work")
    return tmp_path


def run_hook(repo: Path, command: str) -> dict:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


# --- DENY: dangerous git-push shapes -------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push origin master",
        "git push origin HEAD:main",
        "git push origin HEAD:refs/heads/main",
        "git push origin claude/x:main",  # the glob-defeating refspec (PR #38 red-team)
        "git push origin +claude/x:main",
        "git push -f origin main",
        "git push --force-with-lease origin main",
        "git push --mirror origin",
        "git push --all origin",
        "git push --tags origin",
        "git push --follow-tags origin",
        "git push origin :main",
        "git push origin --delete main",
        "git push origin -d main",
        "git push origin '+refs/heads/*:refs/heads/*'",  # wildcard refspec = --all/--mirror
        "git push origin 'refs/heads/*:refs/heads/*'",
        "git -c remote.origin.push=HEAD:main push origin",  # config-injected retarget
        "git config remote.origin.push '+refs/heads/*:refs/heads/*'",
        "git -C /tmp/other push origin claude/x",  # repo-redirect this hook can't verify
        "git --git-dir=/tmp/other/.git push origin claude/x",
    ],
)
def test_deny_dangerous_push_shape(repo: Path, command: str) -> None:
    assert _is_deny(run_hook(repo, command))


# --- DENY: gh CLI shapes that bypass the MCP-level PR/merge denies --------------------


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 5 --merge",
        "gh pr merge --auto",
        "gh pr ready 5",
        "gh pr create --title x",  # no --draft
        "gh api -X PUT /repos/o/r/pulls/5/merge",
        "gh workflow run deploy.yml",
        "gh workflow run daily-brief.yml",
        "gh workflow run us-positions.yml",
        # A compound smuggling a non-allowlisted dispatch alongside an
        # allowlisted one is denied on the offending segment.
        "gh workflow run backup.yml && gh workflow run daily-brief.yml",
        # Command substitution is not a segment separator, so the inner (denied)
        # dispatch would ride inside an allowlisted outer segment AND prefix-match
        # the settings allow-rule, executing with no prompt at all. The guard
        # refuses the combination rather than parsing it.
        "gh workflow run backup.yml $(gh workflow run daily-brief.yml)",
        "gh workflow run backup.yml -f x=$(gh workflow run us-positions.yml)",
        "gh workflow run backup.yml `gh workflow run daily-brief.yml`",
        # rerun re-executes a prior run with its secrets re-injected — any
        # workflow, up to 30 days back.
        "gh run rerun 12345678",
        "gh run rerun 12345678 --failed",
        "gh run rerun --job 99887766",
        "gh workflow run",
        "gh workflow disable full-check.yml",
        "gh release create v1",
    ],
)
def test_deny_dangerous_gh_shape(repo: Path, command: str) -> None:
    assert _is_deny(run_hook(repo, command))


# --- ALLOW (no-op): reversible claude/** work must not be denied ----------------------


@pytest.mark.parametrize(
    "command",
    [
        "git push origin claude/feature-x",
        "git push origin claude/x:claude/x",
        "git push origin HEAD:claude/x",
        "git push origin refs/heads/claude/x:refs/heads/claude/x",
        "git add . && git commit -m x && git push origin claude/x",
        "gh pr create --draft --base main --head claude/x --title x",
        "gh workflow run full-check.yml --ref claude/x",
        "gh workflow run targeted-ml-tests.yml --ref claude/x",
        "gh workflow run migration-integration.yml --ref claude/x",
        # Carve-outs (James, 2026-08-12): backup.yml restores into a disposable
        # CI container; claude-execute.yml is the governed harness, whose own
        # workflow file carries its tool ceiling. Both fall through to the
        # normal permission prompt rather than a hard deny.
        "gh workflow run backup.yml -f restore_drill=true --ref main",
        "gh workflow run claude-execute.yml -f prompt=x",
        "gh workflow run full-check.yml && gh workflow run backup.yml",
        "git push origin claude/x && gh workflow run full-check.yml --ref claude/x",
        "git push -f origin claude/x",  # force to own branch: reversible, not denied
        "git push --force-with-lease origin claude/x",
        "git status",
        "pytest -q",
        "git fetch origin",
    ],
)
def test_allow_reversible_shape(repo: Path, command: str) -> None:
    assert run_hook(repo, command) == {}


# --- current-branch-is-main: any push denied regardless of explicit destination -------


def test_deny_bare_push_on_main(repo: Path) -> None:
    _git(repo, "checkout", "main")
    assert _is_deny(run_hook(repo, "git push"))


def test_deny_push_while_checked_out_on_main(repo: Path) -> None:
    _git(repo, "checkout", "main")
    assert _is_deny(run_hook(repo, "git push origin claude/x"))


def test_allow_detached_head_bare_push_falls_through(repo: Path) -> None:
    """An unresolvable branch (detached HEAD) is not explicitly denied — the hook only
    knows how to deny confirmed-dangerous shapes; the unmatched case falls through to the
    normal prompt rather than being silently allowed."""
    _git(repo, "checkout", "--detach")
    assert run_hook(repo, "git push") == {}
