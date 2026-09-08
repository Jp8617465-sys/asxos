"""Tests for ``.claude/hooks/authority-guard.sh`` — the always-on authority-path guard.

Unlike ``unattended-guard.sh`` (which this hook's authority-path list mirrors), this hook is
NOT gated on ``ARBI_UNATTENDED`` — it must hold in every session, attended or not, because it
exists specifically to close the gap Claude Code's documented ``Edit(...)`` settings-deny
behavior leaves open: interpreter-based writes (a Python/Node script that opens a file
itself) and symlink aliasing. Direct Edit/Write/MultiEdit/NotebookEdit calls on an authority
path are *also* covered by ``.claude/settings.json``'s ``deny`` array at the platform layer —
this hook's Edit/Write/NotebookEdit checks are a second, redundant layer that specifically
canonicalises the path so a symlink alias can't present a non-authority name for an
authority target.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "authority-guard.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="authority-guard.sh needs jq on PATH"
)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / "docs" / "product" / "rubrics").mkdir(parents=True)
    (tmp_path / "docs" / "product" / "memory").mkdir(parents=True)
    (tmp_path / "docs" / "proposals").mkdir(parents=True)
    (tmp_path / "migrations").mkdir()
    (tmp_path / "asxos" / "domain").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{}")
    (tmp_path / ".env").write_text("secret")
    (tmp_path / "AGENTS.md").write_text("x")
    (tmp_path / "CLAUDE.md").write_text("x")
    (tmp_path / "render.yaml").write_text("x")
    (tmp_path / "docs" / "product" / "arbi-constitution.md").write_text("x")
    (tmp_path / "docs" / "product" / "autonomy-policy.md").write_text("x")
    (tmp_path / "docs" / "product" / "rubrics" / "arbi-safety-boundary.md").write_text("x")
    (tmp_path / "docs" / "product" / "memory" / "approved-lessons.md").write_text("x")
    (tmp_path / "docs" / "product" / "roadmap-state.md").write_text("x")
    (tmp_path / "asxos" / "domain" / "foo.py").write_text("x")
    (tmp_path / "tests" / "test_foo.py").write_text("x")
    (tmp_path / "docs" / "proposals" / "pr2.md").write_text("x")
    return tmp_path


def run_raw_hook(
    repo: Path,
    payload: str,
    *,
    project_dir: Path | None = None,
) -> dict:
    project_dir = project_dir or repo
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=payload,
        capture_output=True, text=True,
        env={
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "PATH": os.environ.get("PATH", ""),
        },
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def run_hook(
    repo: Path,
    tool_name: str,
    tool_input: dict,
    *,
    project_dir: Path | None = None,
    payload_cwd: Path | None = None,
) -> dict:
    payload_cwd = payload_cwd or repo
    return run_raw_hook(
        repo,
        json.dumps(
            {
                "cwd": str(payload_cwd),
                "tool_name": tool_name,
                "tool_input": tool_input,
            }
        ),
        project_dir=project_dir,
    )


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


def test_deny_when_jq_is_unavailable(repo: Path) -> None:
    bash = shutil.which("bash")
    assert bash is not None
    proc = subprocess.run(
        [bash, str(HOOK)],
        cwd=repo,
        input=json.dumps(
            {
                "cwd": str(repo),
                "tool_name": "Edit",
                "tool_input": {"file_path": "asxos/domain/foo.py"},
            }
        ),
        capture_output=True,
        text=True,
        env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": "/nonexistent"},
    )
    assert proc.returncode == 0
    decision = json.loads(proc.stdout)["hookSpecificOutput"]
    assert _is_deny(decision)
    assert "jq is unavailable" in decision["permissionDecisionReason"]


@pytest.mark.parametrize("payload", ["{}", "not-json"])
def test_deny_payload_without_valid_tool_name(repo: Path, payload: str) -> None:
    decision = run_raw_hook(repo, payload)
    assert _is_deny(decision)
    assert "valid tool_name" in decision["permissionDecisionReason"]


def test_deny_file_operation_without_cwd_binding(repo: Path) -> None:
    control = repo.parent / f"{repo.name}-control-no-cwd"
    control.mkdir()
    decision = run_raw_hook(
        repo,
        json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "link.md"}}),
        project_dir=control,
    )
    assert _is_deny(decision)
    assert "omitted a valid cwd" in decision["permissionDecisionReason"]


AUTHORITY_PATHS = [
    ".env",
    "AGENTS.md",
    "render.yaml",
    "docs/product/autonomy-policy.md",
    "docs/product/arbi-constitution.md",
    "docs/product/rubrics/arbi-safety-boundary.md",
    "docs/product/memory/approved-lessons.md",
]

NON_AUTHORITY_PATHS = [
    "migrations/0039_x.sql",
    "asxos/domain/foo.py",
    "tests/test_foo.py",
    "docs/proposals/pr2.md",
    "docs/product/roadmap-state.md",
    ".claude/settings.json",
    ".claude/hooks/push-guard.sh",
    "CLAUDE.md",
]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
@pytest.mark.parametrize("path", AUTHORITY_PATHS)
def test_deny_direct_edit_of_authority_path(repo: Path, tool: str, path: str) -> None:
    assert _is_deny(run_hook(repo, tool, {"file_path": path}))


def test_deny_notebook_edit_authority_path(repo: Path) -> None:
    # A notebook under a protected .claude/ subdirectory (agents/) is authority.
    # (A loose root-level .claude/x.ipynb is NOT — see the review-marker tests below.)
    assert _is_deny(run_hook(repo, "NotebookEdit", {"notebook_path": ".claude/agents/x.ipynb"}))


@pytest.mark.parametrize("tool", ["Edit", "Write"])
@pytest.mark.parametrize("path", NON_AUTHORITY_PATHS)
def test_allow_edit_of_non_authority_path(repo: Path, tool: str, path: str) -> None:
    assert run_hook(repo, tool, {"file_path": path}) == {}


def test_deny_symlink_aliasing_an_authority_path(repo: Path) -> None:
    """A non-authority alias must deny after canonical path resolution.

    This is the one gap settings.json's textual path matching may not close on its own.
    """
    (repo / "link.md").symlink_to(repo / "docs" / "product" / "arbi-constitution.md")
    decision = run_hook(repo, "Edit", {"file_path": "link.md"})
    assert _is_deny(decision)
    assert "canonical path resolves" in decision["permissionDecisionReason"]


def test_deny_symlink_aliasing_env(repo: Path) -> None:
    """The hook's authority set must include the .env deny from settings.json."""
    (repo / "secret-link").symlink_to(repo / ".env")
    assert _is_deny(run_hook(repo, "Edit", {"file_path": "secret-link"}))


def test_deny_symlinked_authority_directory_for_new_file(repo: Path) -> None:
    """Canonicalisation must resolve a linked parent even when the leaf is new."""
    (repo / "control").symlink_to(repo / ".claude", target_is_directory=True)
    assert _is_deny(
        run_hook(repo, "Write", {"file_path": "control/agents/new.md"})
    )


def test_deny_alias_to_loaded_control_authority_file(repo: Path) -> None:
    """A target checkout cannot mutate authority bytes in the loaded-control checkout."""
    control = repo.parent / f"{repo.name}-control"
    (control / "docs" / "product").mkdir(parents=True)
    (control / "docs" / "product" / "arbi-constitution.md").write_text("x")
    (repo / "control-settings.json").symlink_to(control / "docs" / "product" / "arbi-constitution.md")
    assert _is_deny(
        run_hook(
            repo,
            "Write",
            {"file_path": "control-settings.json"},
            project_dir=control,
            payload_cwd=repo,
        )
    )


def test_allow_alias_to_authority_named_file_outside_configured_roots(repo: Path) -> None:
    """The authority list is scoped to target and loaded-control checkouts."""
    unrelated = repo.parent / f"{repo.name}-unrelated"
    unrelated.mkdir()
    (unrelated / "CLAUDE.md").write_text("not this project's authority")
    (repo / "external-doc").symlink_to(unrelated / "CLAUDE.md")
    assert run_hook(repo, "Edit", {"file_path": "external-doc"}) == {}


def test_allow_symlink_aliasing_a_non_authority_path(repo: Path) -> None:
    """Canonicalisation must not turn into a blanket ban on symlinks."""
    (repo / "module-link.py").symlink_to(repo / "asxos" / "domain" / "foo.py")
    assert run_hook(repo, "Edit", {"file_path": "module-link.py"}) == {}


def test_case_variant_matches_filesystem_semantics(
    repo: Path,
) -> None:
    alias = repo / ".ENV"
    try:
        same_file = alias.samefile(repo / ".env")
    except FileNotFoundError:
        same_file = False
    decision = run_hook(repo, "Write", {"file_path": ".ENV"})
    if same_file:
        assert _is_deny(decision)
    else:
        assert decision == {}


def test_new_file_below_case_variant_directory_matches_filesystem_semantics(
    repo: Path,
) -> None:
    alias = repo / ".CLAUDE"
    try:
        same_directory = alias.samefile(repo / ".claude")
    except FileNotFoundError:
        same_directory = False
    decision = run_hook(repo, "Write", {"file_path": ".CLAUDE/agents/new-guard.sh"})
    if same_directory:
        assert _is_deny(decision)
    else:
        assert decision == {}


def test_guard_does_not_use_gnu_only_realpath_flags() -> None:
    """Keep the macOS portability defect reproducible in Linux CI."""
    assert re.search(r"\brealpath\s+-m\b", HOOK.read_text()) is None


# --- Bash: interpreter-based writes (the documented Edit-deny gap) --------------------


@pytest.mark.parametrize(
    "command",
    [
        "python3 -c \"open('docs/product/arbi-constitution.md','w').write('x')\"",
        "node -e \"require('fs').writeFileSync('.env','x')\"",
        "cp /tmp/evil .claude/agents/arbi.md",
        "cat /tmp/x | tee render.yaml",
        'echo "malicious" > docs/README.md',  # bare redirect: no "recognized" file command at all
        'printf "x" >> .env',
    ],
)
def test_deny_bash_write_to_authority_path(repo: Path, command: str) -> None:
    assert _is_deny(run_hook(repo, "Bash", {"command": command}))


def test_deny_direct_edit_of_docs_readme(repo: Path) -> None:
    """docs/README.md sits at the same source-of-truth ladder level as CLAUDE.md
    (arbi-authority.md) but was missing from the original authority list — pins the fix."""
    (repo / "docs" / "README.md").write_text("x")
    assert _is_deny(run_hook(repo, "Edit", {"file_path": "docs/README.md"}))


@pytest.mark.parametrize(
    "command",
    [
        "python3 -c \"open('asxos/domain/foo.py','w').write('x')\"",  # write, non-authority
        "cp /tmp/x asxos/domain/foo.py",  # write, non-authority
        "grep -n rule CLAUDE.md",  # authority-path reference, but no write verb
        "cat CLAUDE.md",  # ditto
        "echo x > /tmp/notauth.txt",  # redirect, non-authority path
        "echo x > .env.example",  # exact .env boundary must not match a prefix
        "echo x > CLAUDE.md.bak",  # exact-file authority names are not prefixes
        "echo x > docs/CLAUDE.md",  # same basename below a non-authority directory
        "echo x > CLAUDE.md/child",  # exact files are not directory prefixes
        "echo x > .env/child",  # same rule for a dotfile authority name
        "cp evil.sql migrations/0039_x.sql",
        "echo x > migrations/0039_x.sql",
        "echo x > migrations/0039_x.sql 2>/dev/null",
        "git status",
    ],
)
def test_allow_bash_without_authority_write(repo: Path, command: str) -> None:
    assert run_hook(repo, "Bash", {"command": command}) == {}


# --- Review-gate markers: loose .claude/ root files are NOT authority (writable) -------
# The fragment list was narrowed from a broad ".claude/" prefix to explicit subpaths so it
# mirrors the settings.json deny array; a broad ".claude/" fragment would deadlock the
# review-gate commit flow by treating its own ".claude/.review-passed-*" markers as
# authority. These pins keep that lockout from silently returning.

_MARKER = ".claude/.review-passed-abc123"


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_allow_edit_of_review_marker(repo: Path, tool: str) -> None:
    assert run_hook(repo, tool, {"file_path": _MARKER}) == {}


@pytest.mark.parametrize(
    "command",
    [
        f"touch {_MARKER}",  # how the review gate actually creates the marker
        f"echo x > {_MARKER}",  # redirect write
        f"python3 -c \"open('{_MARKER}','w').write('x')\"",  # interpreter write
    ],
)
def test_allow_bash_write_to_review_marker(repo: Path, command: str) -> None:
    assert run_hook(repo, "Bash", {"command": command}) == {}


# --- Protected .claude/ surfaces still denied (regression: narrowing didn't over-open) --


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
@pytest.mark.parametrize(
    "path",
    [
        # One per enumerated .claude/ surface, so dropping ANY single subpath from the
        # narrowed AUTHORITY_FRAGMENTS array is caught (the no-broad-prefix regex only
        # guards against RE-broadening, not against over-narrowing an individual entry).
            ".claude/settings.local.json",
        ".claude/agents/x.md",
        ".claude/commands/x.md",
        ".claude/rules/x.md",
        ".claude/skills/x.md",
    ],
)
def test_deny_edit_of_protected_claude_surface(repo: Path, tool: str, path: str) -> None:
    assert _is_deny(run_hook(repo, tool, {"file_path": path}))


@pytest.mark.parametrize(
    "command",
    [
        "echo x > .claude/settings.local.json",
        "python3 -c \"open('.claude/agents/x.md','w').write('x')\"",
    ],
)
def test_deny_bash_write_to_protected_claude_surface(repo: Path, command: str) -> None:
    assert _is_deny(run_hook(repo, "Bash", {"command": command}))


def test_authority_fragments_has_no_broad_claude_prefix() -> None:
    """Regression: the bare broad ``".claude/"`` fragment (which over-blocked the
    review-gate markers and self-locked the config edits) must never return — only the
    enumerated subpaths. Matches the literal quoted array element, so ``.claude/agents/``
    etc. (whose closing quote follows a subpath, not the ``/``) do not trip it."""
    src = HOOK.read_text()
    assert re.search(r'"\.claude/"', src) is None

@pytest.mark.parametrize(
    "command",
    [
        'grep -rn "fx_rates|FROM fx" --include=*.py --include=*.sql -i asxos/ migrations/ jobs/ 2>/dev/null | head -20',
        "ls -la .claude/ | head -20; cat .claude/settings.json; cat .claude/settings.local.json 2>/dev/null",
        "cat > docs/reviews/hubs-position-review-2026-08-21.md <<'EOF'\nSee CLAUDE.md and hooks plus migrations/.\nEOF",
    ],
)
def test_allow_bash_authority_false_positives(repo, command):
    assert run_hook(repo, "Bash", {"command": command}) == {}


@pytest.mark.parametrize(
    "command",
    [
        "echo x > docs/product/arbi-constitution.md",
        "echo x > docs/product/arbi-constitution.md 2>/dev/null",
    ],
)
def test_deny_bash_redirect_to_authority_after_scrub(repo, command):
    assert _is_deny(run_hook(repo, "Bash", {"command": command}))
