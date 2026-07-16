"""Tests for ``.claude/hooks/unattended-guard.sh`` — the ARBI_UNATTENDED-gated security/perf
hardening pack (capital-adjacent path-deny, pytest secret-scrub, ad-hoc interpreter deny).

Every check under test lives BELOW the hook's arming gate (the
``[ \"${ARBI_UNATTENDED:-}\" = \"1\" ] || exit 0`` line), so each deny must fire only when
``ARBI_UNATTENDED=1`` is present and be a total no-op otherwise. The GitHub-MCP-write
hardening is settings-level and always-on, so it is asserted statically against
``.claude/settings.json``. This case matrix was verified against the candidate hook before
it shipped (backend-architect design + security-engineer GO-WITH-FIXES review).

Mirrors the subprocess-driven pattern in ``test_authority_guard_hook.py`` /
``test_push_guard_hook.py``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "unattended-guard.sh"
SETTINGS = ROOT / ".claude" / "settings.json"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="unattended-guard.sh needs jq on PATH"
)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    for d in (
        "asxos/domain/portfolio", "asxos/domain/tax", "asxos/domain/models",
        "asxos/domain/theses", "asxos/domain/screening", "asxos/api/routes",
        "jobs", "tests",
    ):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


def run_hook(repo: Path, tool_name: str, tool_input: dict, unattended: bool = True) -> dict:
    env = {"CLAUDE_PROJECT_DIR": str(repo), "PATH": os.environ.get("PATH", "")}
    if unattended:
        env["ARBI_UNATTENDED"] = "1"
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, f"hook exited {proc.returncode}: {proc.stderr}"
    out = proc.stdout.strip()
    return {} if not out else json.loads(out)["hookSpecificOutput"]


def _is_deny(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


CAPITAL_PATHS = [
    "asxos/domain/portfolio/allocator.py",
    "asxos/domain/portfolio/rebalance.py",
    "asxos/domain/portfolio/tax_overlay.py",
    "asxos/domain/portfolio/build.py",
    "asxos/domain/tax/positions.py",
    "asxos/domain/models/model_a.py",
    "asxos/domain/theses/service.py",
]

NON_CAPITAL_PATHS = [
    "asxos/api/routes/foo.py",
    "asxos/domain/screening/foo.py",
    "jobs/ingest_regulatory.py",
    "tests/test_foo.py",
]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
@pytest.mark.parametrize("path", CAPITAL_PATHS)
def test_deny_edit_capital_path_unattended(repo, tool, path):
    assert _is_deny(run_hook(repo, tool, {"file_path": path}))


def test_deny_notebook_edit_capital_path_unattended(repo):
    assert _is_deny(run_hook(repo, "NotebookEdit", {"notebook_path": "asxos/domain/models/x.ipynb"}))


@pytest.mark.parametrize("tool", ["Edit", "Write"])
@pytest.mark.parametrize("path", NON_CAPITAL_PATHS)
def test_allow_edit_non_capital_path_unattended(repo, tool, path):
    assert run_hook(repo, tool, {"file_path": path}) == {}


@pytest.mark.parametrize("command", [
    "sed -i s/a/b/ asxos/domain/tax/positions.py",
    "cp /tmp/x asxos/domain/portfolio/allocator.py",
    "echo x > asxos/domain/models/model_a.py",
])
def test_deny_bash_write_to_capital_path_unattended(repo, command):
    assert _is_deny(run_hook(repo, "Bash", {"command": command}))


@pytest.mark.parametrize("command", [
    "pytest -q",
    "pytest tests/test_foo.py",
    "python -m pytest -q",
    "python3 -m pytest",
    "cd asxos && pytest",
    "FOO=bar pytest",
    "env -i /bin/true; pytest -k planted",
])
def test_deny_unscrubbed_pytest_unattended(repo, command):
    assert _is_deny(run_hook(repo, "Bash", {"command": command}))


@pytest.mark.parametrize("command", [
    'env -i PATH="$PATH" pytest -q',
    'env -i PATH="$PATH" python -m pytest -q',
    'env -i PATH="$PATH" HOME="$HOME" pytest -q',
])
def test_allow_scrubbed_pytest_unattended(repo, command):
    assert run_hook(repo, "Bash", {"command": command}) == {}


@pytest.mark.parametrize("command", [
    'python -c "print(1)"',
    "python3 -c 'import os'",
    'node -e "console.log(1)"',
    "perl -e 'print 1'",
    "ruby -e 'puts 1'",
    "cat x | python -",
    "bash -c 'pytest'",
    "sh -c 'python -c x'",
    "php -r 'x'",
    "awk 'BEGIN{print ENVIRON[\"X\"]}'",
])
def test_deny_adhoc_interpreter_exec_unattended(repo, command):
    assert _is_deny(run_hook(repo, "Bash", {"command": command}))


@pytest.mark.parametrize("command", [
    "ruff check asxos/",
    "mypy asxos/",
    "grep -rn TODO asxos/api/",
    'grep -rn "pytest" tests/',
    'grep -rn "python -c" asxos/api/',
    "python -m py_compile asxos/api/main.py",
    "bash script.sh",
])
def test_allow_read_tooling_unattended(repo, command):
    assert run_hook(repo, "Bash", {"command": command}) == {}


@pytest.mark.parametrize(("tool", "tool_input"), [
    ("Edit", {"file_path": "asxos/domain/portfolio/allocator.py"}),
    ("Write", {"file_path": "asxos/domain/tax/positions.py"}),
    ("NotebookEdit", {"notebook_path": "asxos/domain/models/x.ipynb"}),
    ("Bash", {"command": "pytest -q"}),
    ("Bash", {"command": 'python -c "print(1)"'}),
    ("Bash", {"command": "cp /tmp/x asxos/domain/tax/positions.py"}),
])
def test_new_denies_are_noop_when_attended(repo, tool, tool_input):
    assert run_hook(repo, tool, tool_input, unattended=False) == {}


def test_settings_denies_github_write_mcp():
    deny = json.loads(SETTINGS.read_text())["permissions"]["deny"]
    for tool in (
        "mcp__github__create_or_update_file",
        "mcp__github__push_files",
        "mcp__github__create_branch",
        "mcp__github__delete_file",
    ):
        assert tool in deny, f"{tool} must be denied always-on (security MED-HIGH-4)"
    assert "mcp__github__merge_pull_request" not in deny
