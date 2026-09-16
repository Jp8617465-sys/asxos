"""Pins the Healthchecks deadman wiring in `.github/workflows/`.

Until 2026-09-17 **no workflow set any `HEALTHCHECK_URL_*`**, so every production
job's deadman was silently skipped — `job_monitor.py:176-179` only pings when the
URL is non-empty, and an unset one is indistinguishable from an unmonitored job.
`.claude/rules/job-conventions.md` recorded the gap; nothing closed it.

The rule pinned here is mechanical rather than a hand-kept list, because a list is
what rotted last time (see `tests/test_workflow_dispatch_scope.py`'s header for the
same lesson on dispatch scope):

    every `run: python jobs/<name>.py` step in a workflow must have
    `HEALTHCHECK_URL_<NAME>` available in that workflow's env

The variable name is derived from the job's own filename, so a new job added to a
workflow without a deadman fails here, by name, on the first run.

Wiring these is safe before the checks exist: a missing repository secret
interpolates to the empty string, and both consumers (`JobMonitor` and
`scripts/backup_irreplaceable.sh:227`) skip the ping when empty.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"

#: Workflows that run `jobs/*.py` on a schedule — the ones a deadman is for.
JOB_WORKFLOWS = ("daily-brief.yml", "weekly-research.yml", "us-positions.yml", "pipeline-health.yml")

_STEP = re.compile(r"^\s*run:\s*python\s+jobs/([a-z0-9_]+)\.py", re.MULTILINE)


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def _job_scripts(name: str) -> list[str]:
    """Every `jobs/<x>.py` a workflow runs, in file order."""
    return _STEP.findall((WORKFLOWS / name).read_text())


def _env_names(name: str) -> set[str]:
    """Every env var visible to the steps of a workflow — job level plus step level."""
    doc = _load(name)
    out: set[str] = set()
    for job in (doc.get("jobs") or {}).values():
        out |= set((job.get("env") or {}).keys())
        for step in job.get("steps") or []:
            out |= set((step.get("env") or {}).keys())
    return out


@pytest.mark.parametrize("workflow", JOB_WORKFLOWS)
def test_every_job_step_has_its_deadman_wired(workflow: str) -> None:
    scripts = _job_scripts(workflow)
    assert scripts, f"{workflow}: no `python jobs/*.py` steps found — has the parser rotted?"
    env = _env_names(workflow)
    missing = [f"HEALTHCHECK_URL_{s.upper()}" for s in scripts if f"HEALTHCHECK_URL_{s.upper()}" not in env]
    assert not missing, (
        f"{workflow} runs a job with no deadman wired: {missing}. Add each to the workflow's "
        f"env: block as ${{{{ secrets.<NAME> }}}} — unset is safe, it skips the ping."
    )


@pytest.mark.parametrize("workflow", JOB_WORKFLOWS)
def test_no_orphan_deadman_variables(workflow: str) -> None:
    """A wired variable whose job no longer runs here is dead config — catch it too."""
    expected = {f"HEALTHCHECK_URL_{s.upper()}" for s in _job_scripts(workflow)}
    wired = {e for e in _env_names(workflow) if e.startswith("HEALTHCHECK_URL_")}
    assert not (wired - expected), f"{workflow}: wired but no longer run: {sorted(wired - expected)}"


def test_backup_wires_the_variable_its_shell_script_pings() -> None:
    """backup.yml runs a shell script, not a job module — A-19."""
    assert "HEALTHCHECK_URL_BACKUP_IRREPLACEABLE" in _env_names("backup.yml")
    script = (ROOT / "scripts/backup_irreplaceable.sh").read_text()
    assert "HEALTHCHECK_URL_BACKUP_IRREPLACEABLE" in script, "the script no longer reads it"


def test_every_wired_variable_reaches_a_reader() -> None:
    """The name in the workflow must be the name some code actually reads."""
    readers = ""
    for path in [
        *(ROOT / "jobs").glob("*.py"),
        ROOT / "asxos/config.py",
        ROOT / "scripts/backup_irreplaceable.sh",
    ]:
        readers += path.read_text()
    for workflow in (*JOB_WORKFLOWS, "backup.yml"):
        for var in sorted(e for e in _env_names(workflow) if e.startswith("HEALTHCHECK_URL_")):
            # settings fields are lower-cased field names; env reads use the upper name
            assert var in readers or var.lower() in readers, (
                f"{workflow} wires {var} but nothing reads it"
            )
