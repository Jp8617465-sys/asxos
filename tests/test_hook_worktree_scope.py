"""Tests that the PreToolUse hooks resolve paths against the *tool call's* checkout.

Three hooks — ``review-gate.sh``, ``push-guard.sh`` and ``unattended-guard.sh`` —
used to anchor every path/branch lookup to ``$CLAUDE_PROJECT_DIR``. A tool call
made inside a **git worktree** has its own index, its own HEAD and its own tree,
so each of those lookups inspected an unrelated checkout and the guarded category
silently failed **open**:

* ``review-gate.sh`` inspected the project root's (empty) index, so Python staged
  in a worktree reached a commit without the review loop ever running;
* ``push-guard.sh`` read the primary checkout's branch, so a worktree sitting on
  ``main`` passed the "are we on main?" check;
* ``unattended-guard.sh``'s ``rel_path()`` strip never matched, so the absolute
  worktree path missed every repo-relative authority/capital pattern — the exact
  inverse of that hook's documented fail-closed contract.

``authority-guard.sh`` was already correct (it resolves the payload's ``.cwd`` via
``git rev-parse --show-toplevel``); these tests pin the other three to that same
behaviour. Each case is driven against a **real** git worktree rather than a mock,
per the "Verification lesson" in ``.claude/rules/portfolio-conventions.md``: mocked
connections don't enforce the semantics the bug actually lived in.

The primary-root cases are deliberately duplicated here as regression anchors — the
fix must not change behaviour for the ordinary, non-worktree path.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("git") is None,
    reason="the hooks need jq + git on PATH",
)


def _git(cwd: Path, *args: str) -> None:
    """Run git with hooks disabled so the harness never self-triggers."""
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def worktree_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repo whose primary checkout is on ``claude/x`` and worktree is on ``main``.

    That split is the point: every hook under test asks a question ("what is
    staged?", "what branch is this?", "is this path in the repo?") whose answer
    differs between the two checkouts, so a project-dir-anchored lookup returns the
    safe answer while the dangerous one goes unexamined. git also refuses two
    worktrees on one branch, so the split is required regardless.
    """
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(primary, "init", "-q", "-b", "main")
    _git(primary, "config", "user.email", "t@t.com")
    _git(primary, "config", "user.name", "t")
    (primary / ".claude").mkdir()
    (primary / "CLAUDE.md").write_text("authority\n")
    (primary / "seed.py").write_text("print(1)\n")
    _git(primary, "add", "-A")
    _git(primary, "commit", "-qm", "seed")
    _git(primary, "branch", "claude/x")
    _git(primary, "checkout", "-q", "claude/x")

    worktree = tmp_path / "wt"
    _git(primary, "worktree", "add", "-q", str(worktree), "main")
    return primary, worktree


def run_hook(
    hook: str,
    *,
    project_dir: Path,
    payload: dict,
    unattended: bool = False,
    path_prefix: Path | None = None,
) -> dict:
    """Feed ``hook`` a PreToolUse payload; return ``{}`` on allow, the decision on deny.

    ``path_prefix`` is prepended to PATH, so a test can shadow a system tool (used
    to stand up a BSD-shaped ``realpath``).
    """
    path = os.environ.get("PATH", "")
    if path_prefix is not None:
        path = f"{path_prefix}:{path}"
    env = {"CLAUDE_PROJECT_DIR": str(project_dir), "PATH": path}
    if unattended:
        env["ARBI_UNATTENDED"] = "1"
    proc = subprocess.run(
        ["bash", str(HOOKS / hook)],
        cwd=project_dir,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"{hook} exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return json.loads(out)["hookSpecificOutput"] if out else {}


def _denied(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


def _bash(cwd: Path, command: str) -> dict:
    return {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}}


def _edit(cwd: Path, file_path: Path) -> dict:
    return {
        "tool_name": "Edit",
        "cwd": str(cwd),
        "tool_input": {"file_path": str(file_path)},
    }


# --------------------------------------------------------------- the worktree gap


def test_review_gate_sees_python_staged_inside_a_worktree(
    worktree_repo: tuple[Path, Path],
) -> None:
    """Staged .py in a worktree must gate, though the project root's index is empty."""
    primary, worktree = worktree_repo
    (worktree / "danger.py").write_text("y = 2\n")
    _git(worktree, "add", "danger.py")

    assert not subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=primary,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip(), "precondition: the primary index must be empty for this to bite"

    decision = run_hook(
        "review-gate.sh", project_dir=primary, payload=_bash(worktree, "git commit -m wip")
    )
    assert _denied(decision), "staged .py in a worktree reached a commit ungated"


def test_push_guard_reads_the_worktrees_own_branch(
    worktree_repo: tuple[Path, Path],
) -> None:
    """A push from a worktree on main must deny, though the primary is on claude/x."""
    primary, worktree = worktree_repo
    decision = run_hook(
        "push-guard.sh", project_dir=primary, payload=_bash(worktree, "git push origin HEAD")
    )
    assert _denied(decision), "push from a worktree checked out on main was allowed"


def test_unattended_guard_matches_authority_paths_inside_a_worktree(
    worktree_repo: tuple[Path, Path],
) -> None:
    """An authority-file edit in a worktree must deny — the fail-closed contract."""
    primary, worktree = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(worktree, worktree / "CLAUDE.md"),
        unattended=True,
    )
    assert _denied(decision), "authority edit inside a worktree failed open"


def test_unattended_guard_matches_capital_paths_inside_a_worktree(
    worktree_repo: tuple[Path, Path],
) -> None:
    """The capital carve-out is anchored the same way, so it regressed the same way."""
    primary, worktree = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(worktree, worktree / "asxos/domain/tax/positions.py"),
        unattended=True,
    )
    assert _denied(decision), "capital-path edit inside a worktree failed open"


def test_review_gate_prints_an_absolute_marker_path(
    worktree_repo: tuple[Path, Path],
) -> None:
    """The marker instruction must name the checkout it belongs to.

    ``marker`` is resolved under the commit's own checkout, which is not
    necessarily where the user is standing. Printed relative, a worktree commit
    produced a silent deny loop: touching ``.claude/.review-passed-*`` at the
    project root does not satisfy it, and nothing in the message says so. The
    path is therefore emitted absolute.
    """
    primary, worktree = worktree_repo
    (worktree / "danger.py").write_text("y = 2\n")
    _git(worktree, "add", "danger.py")

    decision = run_hook(
        "review-gate.sh", project_dir=primary, payload=_bash(worktree, "git commit -m wip")
    )
    reason = decision.get("permissionDecisionReason", "")
    marker = next(
        (tok for tok in reason.split() if ".review-passed-" in tok),
        "",
    )
    assert marker.startswith("/"), f"marker path is not absolute: {marker!r}"
    assert marker.startswith(str(worktree.resolve())), (
        f"marker names the wrong checkout: {marker!r} should live under {worktree}"
    )


# ------------------------------------------------------- fail-closed / fail-open


def test_unattended_guard_still_denies_when_payload_omits_cwd(
    worktree_repo: tuple[Path, Path],
) -> None:
    """No ``.cwd`` falls back to the project dir rather than skipping the check."""
    primary, _ = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload={"tool_name": "Edit", "tool_input": {"file_path": str(primary / "CLAUDE.md")}},
        unattended=True,
    )
    assert _denied(decision), "a cwd-less payload skipped the authority check"


def test_unattended_guard_ignores_an_authority_name_outside_every_guarded_root(
    worktree_repo: tuple[Path, Path], tmp_path: Path
) -> None:
    """Only paths *under* a guarded checkout are authority surfaces.

    This is authority-guard.sh's rule ("an identically named file in an unrelated
    repository is not an Arbi authority surface") and it turns on the **target
    path**, not the cwd: the call is made from inside our repo, but the file it
    names lives somewhere else entirely, so it strips under neither root.
    """
    primary, _ = worktree_repo
    outsider = tmp_path / "elsewhere"
    outsider.mkdir()
    (outsider / "CLAUDE.md").write_text("not ours\n")
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(primary, outsider / "CLAUDE.md"),
        unattended=True,
    )
    assert not _denied(decision), "a CLAUDE.md outside every guarded root was gated"


def test_unattended_guard_treats_a_non_repo_cwd_as_its_own_guarded_root(
    worktree_repo: tuple[Path, Path], tmp_path: Path
) -> None:
    """When ``git rev-parse`` can't name a checkout, the cwd itself becomes the root.

    That fallback is deliberate and fail-closed — mirroring authority-guard.sh's
    ``|| printf '%s' "$payload_cwd"``. If the hook cannot establish which repo a
    call belongs to, an authority-shaped path beneath it is denied rather than
    waved through. Pinned because it is the safe direction, and a future
    refactor that "fixed" this into an allow would be a regression.
    """
    primary, _ = worktree_repo
    outsider = tmp_path / "loose"
    outsider.mkdir()
    (outsider / "CLAUDE.md").write_text("not a repo\n")
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(outsider, outsider / "CLAUDE.md"),
        unattended=True,
    )
    assert _denied(decision), "an unresolvable cwd should fail closed, not open"


# ---------------------------------------- portable canonicalisation & relative paths


@pytest.fixture()
def bsd_realpath(tmp_path: Path) -> Path:
    """A ``realpath`` that behaves like BSD/macOS: no flags, no missing leaves.

    `realpath -m` is GNU-only. When it is unavailable the hook's canonicalisation
    fails and both sides of the comparison fall back to unresolved literals — a
    plain textual prefix match that `..` segments walk straight through. This is
    the same defect that made ``authority-guard.sh`` fail open before PR #77 (see
    its ``canonical_path()`` header), so it is pinned here rather than trusted.
    """
    bindir = tmp_path / "bsdbin"
    bindir.mkdir()
    shim = bindir / "realpath"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "args = sys.argv[1:]\n"
        "for a in args:\n"
        "    if a.startswith('-') and a != '--':\n"
        "        sys.exit(1)\n"
        "args = [a for a in args if a != '--']\n"
        "if not args:\n"
        "    sys.exit(1)\n"
        "p = args[0]\n"
        "if not os.path.exists(p):\n"
        "    sys.exit(1)\n"
        "print(os.path.realpath(p))\n"
    )
    shim.chmod(0o755)
    return bindir


def test_capital_path_via_dotdot_is_denied_without_gnu_realpath(
    worktree_repo: tuple[Path, Path], bsd_realpath: Path
) -> None:
    """`..` segments must not walk out of the guarded comparison on a BSD realpath."""
    primary, _ = worktree_repo
    (primary / "asxos/domain/tax").mkdir(parents=True, exist_ok=True)
    (primary / "asxos/domain/tax/positions.py").write_text("x = 1\n")
    sneaky = primary / "asxos/../asxos/domain/tax/positions.py"
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(primary, sneaky),
        unattended=True,
        path_prefix=bsd_realpath,
    )
    assert _denied(decision), "a capital path reached via .. escaped the guard"


def test_relative_file_path_resolves_against_the_tool_calls_cwd(
    worktree_repo: tuple[Path, Path],
) -> None:
    """A relative path is relative to the CALL's cwd, not to the repo root.

    Resolving against the root instead would mis-locate every call made from a
    subdirectory — ``cwd=<root>/asxos`` with ``domain/tax/positions.py`` would
    become ``<root>/domain/...`` and match nothing.
    """
    primary, _ = worktree_repo
    (primary / "asxos/domain/tax").mkdir(parents=True, exist_ok=True)
    (primary / "asxos/domain/tax/positions.py").write_text("x = 1\n")
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload={
            "tool_name": "Edit",
            "cwd": str(primary / "asxos"),
            "tool_input": {"file_path": "domain/tax/positions.py"},
        },
        unattended=True,
    )
    assert _denied(decision), "a subdirectory-relative capital path was not resolved"


def test_relative_file_path_without_a_usable_cwd_fails_closed(
    worktree_repo: tuple[Path, Path],
) -> None:
    """With no base to resolve against, over-deny rather than under-deny."""
    primary, _ = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload={
            "tool_name": "Edit",
            "cwd": str(primary / "does-not-exist"),
            "tool_input": {"file_path": "asxos/domain/tax/positions.py"},
        },
        unattended=True,
    )
    assert _denied(decision), "an unresolvable relative path failed open"


def test_unattended_guard_bare_push_reads_the_worktrees_own_branch(
    worktree_repo: tuple[Path, Path],
) -> None:
    """unattended-guard's A1 branch read is anchored the same way push-guard's is.

    Sibling of ``test_push_guard_reads_the_worktrees_own_branch`` — the fix touched
    both, so both are pinned.
    """
    primary, worktree = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_bash(worktree, "git push origin HEAD"),
        unattended=True,
    )
    assert _denied(decision), "a bare push from a worktree on main was allowed"


# -------------------------------------- dual-root: the guarded set must only grow


@pytest.fixture()
def primary_on_main(tmp_path: Path) -> tuple[Path, Path]:
    """The inverse split: primary checkout on ``main``, worktree on ``claude/x``.

    Needed because repointing a check at the payload's cwd alone does not just add
    coverage — it *removes* the control checkout from view. These fixtures together
    cover both directions.
    """
    primary = tmp_path / "p2"
    primary.mkdir()
    _git(primary, "init", "-q", "-b", "main")
    _git(primary, "config", "user.email", "t@t.com")
    _git(primary, "config", "user.name", "t")
    (primary / ".claude").mkdir()
    (primary / "seed.py").write_text("print(1)\n")
    _git(primary, "add", "-A")
    _git(primary, "commit", "-qm", "seed")
    _git(primary, "branch", "claude/x")
    worktree = tmp_path / "p2-wt"
    _git(primary, "worktree", "add", "-q", str(worktree), "claude/x")
    return primary, worktree


@pytest.mark.parametrize("hook", ["push-guard.sh", "unattended-guard.sh"])
def test_push_denied_when_the_control_checkout_is_on_main(
    primary_on_main: tuple[Path, Path], hook: str
) -> None:
    """A relocating command (``cd <primary> && git push``) must still be caught.

    The payload's cwd says ``claude/x``, but the command explicitly moves into the
    primary checkout — which is on ``main`` — and pushes from there. Reading only
    the payload cwd waved this through.
    """
    primary, worktree = primary_on_main
    decision = run_hook(
        hook,
        project_dir=primary,
        payload=_bash(worktree, f"cd {primary} && git push"),
        unattended=True,
    )
    assert _denied(decision), "a push relocating into a main checkout was allowed"


def test_push_denied_when_cwd_is_an_unrelated_repo(
    primary_on_main: tuple[Path, Path], tmp_path: Path
) -> None:
    """An unrecognised cwd must not disable the control checkout's branch check."""
    primary, _ = primary_on_main
    stranger = tmp_path / "stranger"
    stranger.mkdir()
    _git(stranger, "init", "-q", "-b", "claude/z")
    decision = run_hook(
        "push-guard.sh", project_dir=primary, payload=_bash(stranger, "git push")
    )
    assert _denied(decision), "an unrelated cwd suppressed the control-root check"


def test_push_still_allowed_when_no_checkout_is_on_main(
    worktree_repo: tuple[Path, Path],
) -> None:
    """Dual-root must not over-deny when every relevant checkout is safe."""
    primary, _ = worktree_repo
    decision = run_hook(
        "push-guard.sh", project_dir=primary, payload=_bash(primary, "git push origin claude/x")
    )
    assert not _denied(decision), "a safe claude/** push was blocked"


def test_review_gate_sees_python_staged_in_the_control_checkout(
    worktree_repo: tuple[Path, Path],
) -> None:
    """Staged Python in the *other* checkout must still gate the commit.

    Repointing the gate at the payload's cwd fixed worktree-staged Python but blinded
    it to Python staged in the control checkout — trading one fail-open for another.
    """
    primary, worktree = worktree_repo
    (primary / "only_in_primary.py").write_text("p = 1\n")
    _git(primary, "add", "only_in_primary.py")
    decision = run_hook(
        "review-gate.sh", project_dir=primary, payload=_bash(worktree, "git commit -m wip")
    )
    assert _denied(decision), "Python staged in the control checkout went ungated"


def test_unknown_path_predicate_fails_closed(
    worktree_repo: tuple[Path, Path],
) -> None:
    """``path_matches`` resolves its predicate through PATH if it is not a function.

    Every call site passes a literal today; the allowlist is what stops a future one
    passing a variable from turning this into a command-execution sink.
    """
    primary, _ = worktree_repo
    hook = HOOKS / "unattended-guard.sh"
    probe = (
        f'source "{hook}" 2>/dev/null; '
        'path_matches /tmp/x /bin/echo && echo REACHED || echo BLOCKED'
    )
    proc = subprocess.run(
        ["bash", "-c", probe],
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(primary), "PATH": os.environ.get("PATH", "")},
    )
    assert "REACHED" not in proc.stdout, "an arbitrary predicate was invoked"


# ------------------------------------------------------------ regression anchors


def test_review_gate_unchanged_at_the_primary_root(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, _ = worktree_repo
    (primary / "more.py").write_text("z = 3\n")
    _git(primary, "add", "more.py")
    decision = run_hook(
        "review-gate.sh", project_dir=primary, payload=_bash(primary, "git commit -m wip")
    )
    assert _denied(decision)


def test_review_gate_still_ignores_docs_only_commits(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, _ = worktree_repo
    decision = run_hook(
        "review-gate.sh", project_dir=primary, payload=_bash(primary, "git commit -m docs")
    )
    assert not _denied(decision)


def test_unattended_guard_unchanged_at_the_primary_root(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, _ = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(primary, primary / "CLAUDE.md"),
        unattended=True,
    )
    assert _denied(decision)


def test_unattended_guard_does_not_over_deny_ordinary_files(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, _ = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(primary, primary / "docs/notes.md"),
        unattended=True,
    )
    assert not _denied(decision)


def test_unattended_guard_is_a_no_op_when_attended(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, worktree = worktree_repo
    decision = run_hook(
        "unattended-guard.sh",
        project_dir=primary,
        payload=_edit(worktree, worktree / "CLAUDE.md"),
    )
    assert not _denied(decision), "the guard must stay disarmed for attended sessions"


def test_push_guard_unchanged_for_a_safe_branch_push(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, _ = worktree_repo
    decision = run_hook(
        "push-guard.sh", project_dir=primary, payload=_bash(primary, "git push origin claude/x")
    )
    assert not _denied(decision)


def test_push_guard_still_denies_an_explicit_main_push(
    worktree_repo: tuple[Path, Path],
) -> None:
    primary, _ = worktree_repo
    decision = run_hook(
        "push-guard.sh", project_dir=primary, payload=_bash(primary, "git push origin main")
    )
    assert _denied(decision)
