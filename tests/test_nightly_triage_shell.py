"""Behavioural tests for the shell that actually ships in ``nightly-triage.yml``.

These replace assurance-by-substring. Every test below pulls the byte-exact
``run:`` body out of the workflow and executes it; none asserts that a string is
present in the file.

The lane has never fired — 0 runs, and ``claude/secperf-ledger`` does not exist
(both measured 2026-09-08) — so this is the first evidence of any kind that its
input validation does what its header claims. That is the red-team evidence
backlog item A-22 asks for before the lane is armed.

Scope limit, repeated from ``tools/workflow_shell.py``: this exercises the shell
surface only. The ``claude-code-action`` step and the job-level ``if:`` /
``needs:`` plumbing are GitHub-evaluated and untested here. A green run of this
module does not mean the lane works.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "nightly-triage.yml"


def _load_tool() -> Any:
    """Path-import ``tools/workflow_shell.py`` — ``tools/`` has no package init."""
    path = ROOT / "tools" / "workflow_shell.py"
    spec = importlib.util.spec_from_file_location("workflow_shell", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shell = _load_tool()


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    return shell.load_workflow(WORKFLOW, root=ROOT)


@pytest.fixture(scope="module")
def branch_step(workflow: dict[str, Any]) -> str:
    return shell.step_run_block(workflow, "triage", "Read branch name")


@pytest.fixture(scope="module")
def validate_step(workflow: dict[str, Any]) -> str:
    return shell.step_run_block(workflow, "triage", "Validate dispatch input")


def _fake_git(tmp_path: Path, *, sha: str) -> Path:
    """A ``git`` stub that answers ``ls-remote`` with one line, like the real one.

    Only ``ls-remote`` is emulated because that is the sole git call in the step
    under test; anything else exits non-zero so an unnoticed new git call fails
    loudly rather than silently succeeding.
    """
    bindir = tmp_path / "fakebin"
    bindir.mkdir(exist_ok=True)
    git = bindir / "git"
    git.write_text(
        "#!/bin/bash\n"
        'if [ "$1" = "ls-remote" ]; then\n'
        f'  printf "%s\\trefs/heads/x\\n" "{sha}"\n'
        "  exit 0\n"
        "fi\n"
        'echo "unexpected git call: $*" >&2\n'
        "exit 3\n"
    )
    git.chmod(git.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return bindir


def _run_branch_step(
    script: str, tmp_path: Path, *, branch: str | None, sha: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    work = tmp_path / "work"
    work.mkdir(parents=True, exist_ok=True)
    if branch is not None:
        (work / ".triage-branch").write_text(branch)
    out = work / "gh_output"
    out.write_text("")
    proc = shell.run_shell(
        script,
        cwd=work,
        env={"GITHUB_OUTPUT": str(out)},
        path_prepend=_fake_git(tmp_path, sha=sha),
    )
    parsed = dict(
        line.split("=", 1) for line in out.read_text().splitlines() if "=" in line
    )
    return proc, parsed


VALID_SHA = "a" * 40


# --------------------------------------------------------------------------
# The branch-name guard — the check the old substring test could not exercise.
# --------------------------------------------------------------------------


def test_valid_branch_name_is_accepted(branch_step: str, tmp_path: Path) -> None:
    proc, out = _run_branch_step(
        branch_step, tmp_path, branch="claude/triage-20260908-fix-thing", sha=VALID_SHA
    )
    assert proc.returncode == 0, proc.stderr
    assert out["found"] == "true"
    assert out["name"] == "claude/triage-20260908-fix-thing"
    assert out["sha"] == VALID_SHA


@pytest.mark.parametrize(
    "hostile",
    [
        "claude/triage-20260908-x; rm -rf /",  # command injection
        "claude/triage-20260908-x$(id)",  # command substitution
        "claude/triage-20260908-x`id`",  # backtick substitution
        "claude/triage-20260908-x&&id",  # operator chaining
        "../../etc/passwd",  # path traversal
        "claude/triage-20260908-x/../../main",  # traversal past the prefix
        "claude/triage-2026-09-08-x",  # dashes in the date: 8 digits required
        "claude/triage-2026098-x",  # 7 digits
        "claude/triage-202609081-x",  # 9 digits
        "claude/triage-20260908-",  # empty slug
        "claude/triage-20260908-UPPER",  # uppercase outside [a-z0-9-]
        "main",  # an entirely different branch
        "refs/heads/claude/triage-20260908-x",  # fully-qualified ref
        " claude/triage-20260908-x",  # leading space
    ],
)
def test_hostile_branch_names_are_rejected(
    branch_step: str, tmp_path: Path, hostile: str
) -> None:
    proc, out = _run_branch_step(branch_step, tmp_path, branch=hostile, sha=VALID_SHA)
    assert proc.returncode == 1, f"accepted hostile branch name {hostile!r}"
    assert "invalid triage branch name" in proc.stdout + proc.stderr
    assert "found" not in out, "a rejected branch must not report found"


def test_injection_in_branch_name_does_not_execute(
    branch_step: str, tmp_path: Path
) -> None:
    """The guard must reject, and nothing in the name may run as a command.

    Asserted by side effect, not by reading the script: the payload would create
    a marker file if it were ever evaluated by the shell.
    """
    work = tmp_path / "work"
    work.mkdir()
    marker = tmp_path / "PWNED"
    proc, _ = _run_branch_step(
        branch_step,
        tmp_path,
        branch=f"claude/triage-20260908-x$(touch {marker})",
        sha=VALID_SHA,
    )
    assert proc.returncode == 1
    assert not marker.exists(), "branch name was evaluated as a command"


# --------------------------------------------------------------------------
# The SHA guard.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_sha",
    [
        "a" * 39,  # too short
        "a" * 41,  # too long
        "A" * 40,  # uppercase hex is not matched by [0-9a-f]
        "g" * 40,  # non-hex
        "",  # empty
    ],
)
def test_non_canonical_sha_is_rejected(
    branch_step: str, tmp_path: Path, bad_sha: str
) -> None:
    proc, out = _run_branch_step(
        branch_step, tmp_path, branch="claude/triage-20260908-x", sha=bad_sha
    )
    assert proc.returncode == 1, f"accepted malformed sha {bad_sha!r}"
    assert "did not resolve to one commit SHA" in proc.stdout + proc.stderr
    assert out.get("found") != "true"


# --------------------------------------------------------------------------
# The diagnosis-only path — the branch the lane takes when no fix was produced.
# This is the only end-to-end path reachable without a red nightly-check.
# --------------------------------------------------------------------------


def test_absent_triage_branch_file_is_diagnosis_only(
    branch_step: str, tmp_path: Path
) -> None:
    proc, out = _run_branch_step(branch_step, tmp_path, branch=None, sha=VALID_SHA)
    assert proc.returncode == 0, proc.stderr
    assert out["found"] == "false"
    assert "name" not in out and "sha" not in out


def test_empty_triage_branch_file_is_rejected_not_treated_as_absent(
    branch_step: str, tmp_path: Path
) -> None:
    """An empty file is present, so it takes the validating path and must fail.

    Worth pinning: ``[ -f ]`` is true for an empty file, so this is the boundary
    where "no branch produced" and "a broken branch name" are told apart.
    """
    proc, out = _run_branch_step(branch_step, tmp_path, branch="", sha=VALID_SHA)
    assert proc.returncode == 1
    assert out.get("found") != "true"


def test_trailing_newline_is_stripped(branch_step: str, tmp_path: Path) -> None:
    """``tr -d '\\r\\n'`` exists so a normal ``echo >`` from the agent works."""
    proc, out = _run_branch_step(
        branch_step, tmp_path, branch="claude/triage-20260908-x\r\n", sha=VALID_SHA
    )
    assert proc.returncode == 0, proc.stderr
    assert out["name"] == "claude/triage-20260908-x"


# --------------------------------------------------------------------------
# The dispatch-input guard.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("good", ["", "123", "34264977559"])
def test_valid_run_ids_accepted(validate_step: str, tmp_path: Path, good: str) -> None:
    proc = shell.run_shell(
        shell.render(validate_step, {}), cwd=tmp_path, env={"REQUESTED_RUN_ID": good}
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize(
    "bad", ["12a", "-1", "1 2", "1;id", "$(id)", "1\n2", "0x10", " 1"]
)
def test_hostile_run_ids_rejected(validate_step: str, tmp_path: Path, bad: str) -> None:
    proc = shell.run_shell(
        shell.render(validate_step, {}), cwd=tmp_path, env={"REQUESTED_RUN_ID": bad}
    )
    assert proc.returncode == 1, f"accepted hostile run_id {bad!r}"
    assert "decimal digits only" in proc.stdout + proc.stderr


# --------------------------------------------------------------------------
# Meta: prove this module is not itself vacuous.
# --------------------------------------------------------------------------


def test_harness_detects_a_neutered_guard(branch_step: str, tmp_path: Path) -> None:
    """Mutation check. Neuter the regex in an in-memory COPY; tests must fail.

    Without this, the module above could be as hollow as the substring tests it
    replaces. The mutation is applied to a string in memory — the workflow file
    is never written to, and ``.github/**`` stays fenced.
    """
    neutered = branch_step.replace(
        "^claude/triage-[0-9]{8}-[a-z0-9-]+$", "^.*$"
    )
    assert neutered != branch_step, "mutation anchor not found — test is stale"

    proc, out = _run_branch_step(neutered, tmp_path, branch="main", sha=VALID_SHA)
    assert proc.returncode == 0 and out.get("found") == "true", (
        "the neutered guard should accept 'main' — if it does not, this "
        "mutation check is not exercising the real validation path"
    )

    proc, _ = _run_branch_step(
        branch_step, tmp_path / "real", branch="main", sha=VALID_SHA
    )
    assert proc.returncode == 1, "the shipped guard must reject 'main'"


def test_render_fails_closed_on_unsubstituted_expression() -> None:
    """A leftover ``${{ }}`` must raise, never reach bash."""
    with pytest.raises(KeyError, match="unsubstituted"):
        shell.render('echo "${{ inputs.run_id }}"', {})


def test_step_lookup_raises_when_a_step_is_renamed(workflow: dict[str, Any]) -> None:
    """Guards against this module silently testing nothing after a rename."""
    with pytest.raises(KeyError):
        shell.step_run_block(workflow, "triage", "No Such Step")


def test_run_shell_does_not_inherit_ambient_environment(tmp_path: Path) -> None:
    """A credential in the caller's env must not reach the block under test."""
    os.environ["ASXOS_TEST_LEAK_CANARY"] = "leaked"
    try:
        proc = shell.run_shell(
            'echo "${ASXOS_TEST_LEAK_CANARY:-absent}"', cwd=tmp_path
        )
        assert proc.stdout.strip() == "absent"
    finally:
        del os.environ["ASXOS_TEST_LEAK_CANARY"]


# --------------------------------------------------------------------------
# The findings-log heartbeat — `if: always()`, so it runs on EVERY fire,
# including the failed and diagnosis-only ones. Its guards had no execution
# coverage at all; the old test matched their error-message strings.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def heartbeat_step(workflow: dict[str, Any]) -> str:
    return shell.step_run_block(workflow, "triage", "Findings-log heartbeat")


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0"},
    )


def _repo_with_local_origin(tmp_path: Path) -> tuple[Path, Path]:
    """A real repo whose ``origin`` is a real local bare repo.

    Deliberately not a stub. The heartbeat's create-vs-update logic is driven by
    ``git ls-remote --exit-code --heads``, and the whole point of covering it is
    that ``claude/secperf-ledger`` does not exist yet (measured 2026-09-08), so
    the *create* path is what fires first. A stubbed git would let that path pass
    without ever proving it works.
    """
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git("init", "--bare", "--initial-branch=main", ".", cwd=origin)

    work = tmp_path / "repo"
    work.mkdir()
    _git("init", "--initial-branch=main", ".", cwd=work)
    _git("config", "user.email", "t@example.invalid", cwd=work)
    _git("config", "user.name", "t", cwd=work)
    (work / "docs" / "product").mkdir(parents=True)
    (work / "docs" / "product" / "security-perf-findings-log.md").write_text("| log |\n")
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "seed", cwd=work)
    _git("remote", "add", "origin", str(origin), cwd=work)
    _git("push", "-u", "origin", "main", cwd=work)
    return work, origin


def _run_heartbeat(
    script: str, work: Path, tmp_path: Path, *, status: str = "success"
) -> subprocess.CompletedProcess[str]:
    runner_temp = tmp_path / "runner_temp"
    runner_temp.mkdir(exist_ok=True)
    return shell.run_shell(
        script,
        cwd=work,
        env={
            "TRIAGE_STATUS": status,
            "GITHUB_RUN_NUMBER": "1",
            "GITHUB_RUN_ID": "34264977559",
            "RUNNER_TEMP": str(runner_temp),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def test_heartbeat_creates_the_ledger_branch_when_absent(
    heartbeat_step: str, tmp_path: Path
) -> None:
    """The first-ever fire must create ``claude/secperf-ledger`` from main."""
    work, origin = _repo_with_local_origin(tmp_path)
    proc = _run_heartbeat(heartbeat_step, work, tmp_path)
    assert proc.returncode == 0, proc.stderr

    listing = subprocess.run(
        ["git", "ls-remote", "--heads", str(origin), "refs/heads/claude/secperf-ledger"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "claude/secperf-ledger" in listing.stdout, "ledger branch was not created"
    assert "main" not in proc.stdout.split("\n")[-1:], "must never push to main"


def test_heartbeat_appends_on_a_second_fire(
    heartbeat_step: str, tmp_path: Path
) -> None:
    """The update path: a second fire adds a row rather than replacing the file."""
    work, origin = _repo_with_local_origin(tmp_path)
    assert _run_heartbeat(heartbeat_step, work, tmp_path).returncode == 0
    second = _run_heartbeat(heartbeat_step, work, tmp_path, status="failure")
    assert second.returncode == 0, second.stderr

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-b", "claude/secperf-ledger", str(origin), str(clone)],
        check=True,
        capture_output=True,
    )
    body = (clone / "docs" / "product" / "security-perf-findings-log.md").read_text()
    assert body.count("34264977559") == 2, "second fire did not append a row"
    assert "success" in body and "failure" in body


def test_heartbeat_rejects_a_symlinked_diagnosis(
    heartbeat_step: str, tmp_path: Path
) -> None:
    """The guard exists so a symlink cannot exfiltrate a file into the ledger."""
    work, _ = _repo_with_local_origin(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("SENSITIVE")
    (work / ".triage-diagnosis.md").symlink_to(secret)

    proc = _run_heartbeat(heartbeat_step, work, tmp_path)
    assert proc.returncode == 1, "a symlinked diagnosis was accepted"
    assert "must be a regular, non-symlink file" in proc.stdout + proc.stderr


def test_heartbeat_rejects_an_oversize_diagnosis(
    heartbeat_step: str, tmp_path: Path
) -> None:
    work, _ = _repo_with_local_origin(tmp_path)
    (work / ".triage-diagnosis.md").write_text("x" * 65537)
    proc = _run_heartbeat(heartbeat_step, work, tmp_path)
    assert proc.returncode == 1, "a 64 KiB + 1 diagnosis was accepted"
    assert "exceeds 64 KiB" in proc.stdout + proc.stderr


def test_heartbeat_accepts_a_diagnosis_at_the_size_boundary(
    heartbeat_step: str, tmp_path: Path
) -> None:
    """Exactly 65536 bytes is allowed — the guard is ``-gt``, not ``-ge``.

    Pinned so a later 'tightening' to ``-ge`` is a visible decision rather than
    an accident.
    """
    work, origin = _repo_with_local_origin(tmp_path)
    (work / ".triage-diagnosis.md").write_text("x" * 65536)
    proc = _run_heartbeat(heartbeat_step, work, tmp_path)
    assert proc.returncode == 0, proc.stderr

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-b", "claude/secperf-ledger", str(origin), str(clone)],
        check=True,
        capture_output=True,
    )
    assert (clone / "docs" / "ops" / "triage-diagnoses" / "34264977559.md").exists()
