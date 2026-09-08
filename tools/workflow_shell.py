#!/usr/bin/env python3
"""Execute the *real* ``run:`` blocks from a checked-in workflow, in a sandbox.

Why this exists
---------------
``tests/test_standing_lane_workflows.py`` asserted the safety of
``nightly-triage.yml`` with substring matches against the YAML *as text*::

    assert "^claude/triage-[0-9]{8}-[a-z0-9-]+$" in NIGHTLY
    assert ".triage-diagnosis.md must be a regular, non-symlink file" in NIGHTLY

Those assert that the regex and the guard's *error message* appear in the file.
Neither is ever executed. Measured 2026-09-08: all ten substring assertions
across that module's five tests are satisfied by text whose live check is
``[[ ! "$name" =~ .* ]]`` — a validator that accepts every branch name,
``claude/triage-20260908-x; rm -rf /`` included. The tests could not tell a
working guard from a destroyed one.

That is the failure this repository already named in writing:
``docs/session-handoff-2026-09-07.md`` Lesson 1, *"A grep hit proves a string
exists, never what it does"*, and Lesson 3, *"probe the guard; do not read it
and believe it"*. The fence work in #211 found three ordinary bypasses that way,
in a guard whose own header called its residual risk exotic.

Why extraction was rejected
---------------------------
The obvious fix — move the shell into a script and unit-test the script —
requires editing the workflow to *call* that script. ``.github/**`` is fenced,
and James declined to lift that fence on 2026-09-07, so the change would ship as
a staged patch. Until he applied it the workflow would keep running its inline
copy while the tests exercised a second, divergent implementation: a new false
assurance of exactly the class being removed.

So this module does the opposite. It reads the byte-exact ``run:`` body out of
the workflow that actually ships, substitutes the ``${{ }}`` expressions GitHub
would substitute, and runs *that* under ``bash``. There is no second copy to
drift, and no step for James.

Honest limits, stated rather than discovered later
--------------------------------------------------
This covers the **shell surface**, which is where the untested logic lives. It
is not an end-to-end rehearsal and must never be described as one:

* the ``anthropics/claude-code-action`` step is not executed;
* job-level ``if:``, ``needs:`` and ``outputs:`` are GitHub-evaluated
  expressions, not shell, and are out of reach here;
* ``${{ }}`` substitution below is a *test fixture* standing in for GitHub's
  expression evaluator, not a reimplementation of it.

A green run of this harness means the shell does what it claims. It does not
mean the lane works.

Report-only: contacts GitHub never, resolves no secret value.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path
from typing import Any

_EXPRESSION = re.compile(r"\$\{\{(.+?)\}\}", re.DOTALL)


def _load_effects_module(root: Path) -> Any:
    """Import ``scripts/workflow_effects.py`` by path.

    ``scripts/`` carries no ``__init__.py``, so a path import is the honest way
    in — the same idiom ``tools/workflow_inventory.py`` uses, and for the same
    reason. The hardened loader is worth reusing rather than re-deriving: it is
    ``yaml.BaseLoader`` (no arbitrary tag construction) plus duplicate-key
    rejection, so a workflow that defines the same key twice fails loudly here
    instead of silently taking the last one.
    """
    path = root / "scripts" / "workflow_effects.py"
    spec = importlib.util.spec_from_file_location("workflow_effects", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_workflow(path: Path, *, root: Path) -> dict[str, Any]:
    """Parse a workflow with the hardened loader.

    Every scalar comes back as ``str`` because the loader is ``BaseLoader``.
    That is deliberate: a ``run:`` body must not be reinterpreted as anything
    but the text bash will receive.
    """
    import yaml

    effects = _load_effects_module(root)
    loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=effects._UniqueBaseLoader)
    if not isinstance(loaded, dict):
        raise RuntimeError(f"{path} did not parse to a mapping")
    return loaded


def step_run_block(workflow: dict[str, Any], job: str, step_name: str) -> str:
    """Return the exact ``run:`` body of one named step.

    Raises rather than returning a default. A test that silently exercised an
    empty string because a step was renamed would be the same class of false
    assurance this module exists to remove.
    """
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or job not in jobs:
        raise KeyError(f"no job {job!r}; have {sorted(jobs) if isinstance(jobs, dict) else '<none>'}")
    steps = jobs[job].get("steps")
    if not isinstance(steps, list):
        raise KeyError(f"job {job!r} has no steps list")
    for step in steps:
        if isinstance(step, dict) and step.get("name") == step_name:
            run = step.get("run")
            if not isinstance(run, str):
                raise KeyError(f"step {step_name!r} in job {job!r} has no run: block")
            return run
    names = [s.get("name") for s in steps if isinstance(s, dict)]
    raise KeyError(f"no step {step_name!r} in job {job!r}; have {names}")


def render(run_block: str, substitutions: dict[str, str]) -> str:
    """Substitute ``${{ expr }}`` occurrences, failing closed on any leftover.

    The fail-closed part is the point. Bash would happily accept a literal
    ``${{ inputs.run_id }}`` and expand it to something surprising rather than
    erroring, so an un-substituted expression would let a test pass while
    exercising something other than the shipped logic. Keys are matched on the
    expression with surrounding whitespace stripped, e.g. ``inputs.run_id``.
    """
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key not in substitutions:
            missing.append(key)
            return match.group(0)
        return substitutions[key]

    rendered = _EXPRESSION.sub(_replace, run_block)
    if missing:
        raise KeyError(f"unsubstituted workflow expressions: {sorted(set(missing))}")
    return rendered


def run_shell(
    script: str,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    path_prepend: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a rendered block under ``bash -euo pipefail`` in ``cwd``.

    ``env`` is the complete environment — the ambient one is NOT inherited, so a
    credential or ``GITHUB_*`` variable present in the caller's shell cannot
    reach the block under test and quietly change its behaviour. ``PATH`` is set
    explicitly, with ``path_prepend`` first so a test can shadow ``git``/``gh``
    with a recording stub.
    """
    full_env = {"PATH": "/usr/bin:/bin", "HOME": str(cwd)}
    if path_prepend is not None:
        full_env["PATH"] = f"{path_prepend}:{full_env['PATH']}"
    full_env.update(env or {})
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        cwd=cwd,
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
