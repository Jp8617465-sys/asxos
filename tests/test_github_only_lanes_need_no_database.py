"""The GitHub-only lanes hold a PAT and nothing else — so their imports must not need a DB.

``daily-digest.yml`` and the four script steps of ``backlog-roll.yml`` run
``scripts/*.py`` with ``ARBI_GITHUB_TOKEN`` as their only secret: no ``DATABASE_URL``, by
design (AGENTS.md §12; the lanes' headers). Incident #389: the first production run of
``daily-digest`` died at import — ``asxos.clock`` pulled in ``asxos.config``, whose
``CoreSettings()`` raises without ``DATABASE_URL`` — and nothing in this suite could have
caught it, because CI, the sandbox and every developer shell carry the variable.

So this file spawns a fresh interpreter with ``DATABASE_URL`` removed and imports exactly
what those lanes import. A module that grows a path back to ``CoreSettings`` fails here,
not on the runner at 07:00 Brisbane.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: The import surface of the GitHub-only lanes, leaf to root.
MODULES = (
    "asxos.clock",
    "asxos.github_api",
    "asxos.backlog",
    "asxos.domain.governance.issue_eligibility",
    "asxos.domain.governance.provenance",
    "asxos.autoready",
    "asxos.backlog_issues",
    "asxos.digest",
)

#: Every script a lane without DATABASE_URL runs (daily-digest; backlog-roll's Layers 1/3/4
#: and its label bootstrap), plus the attended issue-filer that shares the chain.
SCRIPTS = (
    "scripts/post_daily_digest.py",
    "scripts/ensure_labels.py",
    "scripts/issue_eligibility.py",
    "scripts/issue_ready_apply.py",
    "scripts/issue_next.py",
    "scripts/backlog_to_issues.py",
)

_LOAD_SCRIPT = (
    "import importlib.util, sys\n"
    "spec = importlib.util.spec_from_file_location('lane_script', sys.argv[1])\n"
    "mod = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(mod)\n"  # module-level imports run; the __main__ guard does not
)


def _env_without_database() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    assert "DATABASE_URL" not in env
    return env


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *argv],
        cwd=ROOT,
        env=_env_without_database(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_the_lane_import_surface_needs_no_database_url() -> None:
    code = "import importlib, sys\nfor m in sys.argv[1:]:\n    importlib.import_module(m)\n"
    result = _run("-c", code, *MODULES)
    assert result.returncode == 0, result.stderr[-3000:]


@pytest.mark.parametrize("script", SCRIPTS)
def test_each_github_only_script_loads_without_a_database_url(script: str) -> None:
    result = _run("-c", _LOAD_SCRIPT, script)
    assert result.returncode == 0, result.stderr[-3000:]
    assert "DATABASE_URL" not in result.stderr, result.stderr[-3000:]
