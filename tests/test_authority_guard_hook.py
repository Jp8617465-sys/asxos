"""Tests for ``.claude/hooks/authority-guard.sh`` — the always-on authority-path guard.

Unlike ``unattended-guard.sh`` (which this hook's authority-path list mirrors), this hook is
NOT gated on ``ARBI_UNATTENDED`` — it must hold in every session, attended or not, because it
exists specifically to close the gap Claude Code's documented ``Edit(...)`` settings-deny
behavior leaves open: interpreter-based writes (a Python/Node script that opens a file
itself) and symlink aliasing. Direct Edit/Write/MultiEdit/NotebookEdit calls on an authority
path are *also* covered by ``.claude/settings.json``'s ``deny`` array at the platform layer —
this hook's Edit/Write/NotebookEdit checks are a second, redundant layer that specifically
re-resolves the path via ``realpath`` so a symlink alias can't present a non-authority name
for an authority target.
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
    (tmp_path / "CLAUDE.md").write_text("x")
    (tmp_path / "render.yaml").write_text("x")
    (tmp_path / "docs" / "product" / "arbi-constitution.md").write_text("x")
    (tmp_path / "docs" / "product" / "rubrics" / "arbi-safety-boundary.md").write_text("x")
    (tmp_path / "docs" / "product" / "memory" / "approved-lessons.md").write_text("x")
    (tmp_path / "docs" / "product" / "roadmap-state.md").write_text("x")
    (tmp_path / "asxos" / "domain" / "foo.py").write_text("x")
    (tmp_path / "tests" / "test_foo.py").write_text("x")
    (tmp_path / "docs" / "proposals" / "pr2.md").write_text("x")
    return tmp_path


def run_hook(repo: Path, tool_name: str, tool_input: dict) -> dict:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(repo), "PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


AUTHORITY_PATHS = [
    ".claude/settings.json",
    ".claude/hooks/push-guard.sh",
    "CLAUDE.md",
    "render.yaml",
    "migrations/0039_x.sql",
    "docs/product/arbi-constitution.md",
    "docs/product/rubrics/arbi-safety-boundary.md",
    "docs/product/memory/approved-lessons.md",
]

NON_AUTHORITY_PATHS = [
    "asxos/domain/foo.py",
    "tests/test_foo.py",
    "docs/proposals/pr2.md",
    "docs/product/roadmap-state.md",
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
    """A symlink presenting a non-authority name must still deny via realpath resolution —
    this is the one gap settings.json's textual path-matching may not close on its own."""
    (repo / "link.md").symlink_to(repo / ".claude" / "settings.json")
    assert _is_deny(run_hook(repo, "Edit", {"file_path": "link.md"}))


# --- Bash: interpreter-based writes (the documented Edit-deny gap) --------------------


@pytest.mark.parametrize(
    "command",
    [
        "python3 -c \"open('.claude/settings.json','w').write('x')\"",
        "node -e \"require('fs').writeFileSync('CLAUDE.md','x')\"",
        "cp /tmp/evil .claude/settings.json",
        "cat /tmp/x | tee render.yaml",
        "cp evil.sql migrations/0039_x.sql",
        'echo "malicious" > CLAUDE.md',  # bare redirect: no "recognized" file command at all
        'printf "x" >> CLAUDE.md',
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
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/agents/x.md",
        ".claude/commands/x.md",
        ".claude/hooks/review-gate.sh",
        ".claude/rules/x.md",
        ".claude/skills/x.md",
    ],
)
def test_deny_edit_of_protected_claude_surface(repo: Path, tool: str, path: str) -> None:
    assert _is_deny(run_hook(repo, tool, {"file_path": path}))


@pytest.mark.parametrize(
    "command",
    [
        "echo x > .claude/settings.json",  # redirect write to a protected file
        "python3 -c \"open('.claude/hooks/review-gate.sh','w').write('x')\"",  # interpreter write to hooks/
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
