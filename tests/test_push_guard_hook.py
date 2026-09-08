"""Tests for ``.claude/hooks/push-guard.sh`` — the always-on PreToolUse(Bash) push/gh guard.

DENY-only by design (see the hook's header): the hook only emits ``deny`` or stays silent.
For project-allowlisted PR lifecycle commands, silence can execute without a prompt, so those
paths first require remote repository variable ``AUTONOMY=STANDING`` for the exact ASXOS
origin. Direct/force pushes to ``main`` and merge-bypass modes remain denied in every state.
These tests assert the attended/standing split as well as reversible branch pushes.

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
    _git(tmp_path, "remote", "add", "origin", "https://github.com/Jp8617465-sys/asxos.git")
    return tmp_path


def run_hook(
    repo: Path,
    command: str,
    *,
    autonomy: str = "ATTENDED",
    gh_repo: str | None = None,
    payload_cwd: str | None = None,
) -> dict:
    gh_bin = repo.parent / f"{repo.name}-fake-gh"
    gh_bin.mkdir(exist_ok=True)
    gh = gh_bin / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        "if [ \"$1 $2 $3\" = \"variable get AUTONOMY\" ]; then\n"
        f"  printf '%s\\n' {autonomy!r}\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n"
    )
    gh.chmod(0o755)
    env = {
        "CLAUDE_PROJECT_DIR": str(repo),
        "PATH": f"{gh_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    if gh_repo is not None:
        env["GH_REPO"] = gh_repo
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": command},
                **({"cwd": payload_cwd} if payload_cwd is not None else {}),
            }
        ),
        capture_output=True, text=True,
        env=env,
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


def test_missing_jq_fails_closed() -> None:
    proc = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}}),
        capture_output=True,
        text=True,
        env={"PATH": ""},
    )
    assert proc.returncode == 0
    assert _is_deny(json.loads(proc.stdout)["hookSpecificOutput"])


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
        "gh pr merge 5 --rebase",
        "gh pr merge --auto",
        "gh pr merge 5 --admin",
        "gh pr merge 5",
        "gh pr ready 5",
        "gh pr create --title x",  # no --draft
        "gh api -X PUT /repos/o/r/pulls/5/merge",
        "gh variable set AUTONOMY --body STANDING",
        "gh variable delete AUTONOMY",
        "gh api -X PATCH /repos/Jp8617465-sys/asxos/actions/variables/AUTONOMY -f value=STANDING",
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


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --base main --head claude/x --title x",
        "gh pr ready 5",
        "gh pr merge 5 --squash",
    ],
)
def test_allow_server_gated_pr_lifecycle_only_when_remote_standing(
    repo: Path, command: str
) -> None:
    assert run_hook(repo, command, autonomy="STANDING") == {}


@pytest.mark.parametrize("state", ["", "ATTENDED", "standing", "BROKEN"])
def test_deny_merge_without_exact_remote_standing(repo: Path, state: str) -> None:
    assert _is_deny(run_hook(repo, "gh pr merge 5 --squash", autonomy=state))


@pytest.mark.parametrize("flag", ["--merge", "--rebase", "--auto", "--admin"])
def test_deny_non_squash_or_bypass_merge_even_when_standing(
    repo: Path, flag: str
) -> None:
    assert _is_deny(run_hook(repo, f"gh pr merge 5 {flag}", autonomy="STANDING"))


def test_deny_bare_merge_even_when_standing(repo: Path) -> None:
    assert _is_deny(run_hook(repo, "gh pr merge 5", autonomy="STANDING"))


def test_deny_standing_claim_for_wrong_origin(repo: Path) -> None:
    _git(repo, "remote", "set-url", "origin", "https://github.com/example/other.git")
    assert _is_deny(run_hook(repo, "gh pr merge 5 --squash", autonomy="STANDING"))


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 5 --squash --repo example/other",
        "gh pr merge https://github.com/example/other/pull/5 --squash",
        "gh pr merge $(printf 5) --squash",
    ],
)
def test_deny_standing_pr_lifecycle_repo_redirection(repo: Path, command: str) -> None:
    assert _is_deny(run_hook(repo, command, autonomy="STANDING"))


def test_deny_standing_pr_lifecycle_gh_repo_override(repo: Path) -> None:
    assert _is_deny(
        run_hook(
            repo,
            "gh pr merge 5 --squash",
            autonomy="STANDING",
            gh_repo="example/other",
        )
    )


def test_deny_standing_pr_lifecycle_outside_project_cwd(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside-pr-context")
    assert _is_deny(
        run_hook(
            repo,
            "gh pr merge 5 --squash",
            autonomy="STANDING",
            payload_cwd=str(outside),
        )
    )


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
