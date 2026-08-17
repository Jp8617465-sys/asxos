"""
Regression coverage for the Phase 2B cron DB-pool initialization bug.

Root cause (Phase 2B): ``asxos.db.acquire()`` calls ``get_pool()``, which
raises ``RuntimeError`` when the pool has not been initialised. ``JobMonitor``
acquires a connection inside ``__aenter__`` to write the ``running`` row to
``job_runs``. Therefore any cron job that enters ``async with JobMonitor(...)``
*before* calling ``await init_pool()`` crashes in ``__aenter__`` — before any
row is written — and silently disappears from ``job_runs``.

The canonical, correct structure (used by the working jobs) is::

    async def _run(as_of):
        await init_pool()
        try:
            async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
                async with acquire() as conn:
                    ...
        finally:
            await close_pool()

These tests are static/source-level (AST) so they run without a database and
catch the bug class without being brittle to comments or formatting.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

JOBS_DIR = pathlib.Path(__file__).resolve().parent.parent / "jobs"

# The jobs fixed in Phase 2B that still exist. These must follow the full
# canonical structure: init_pool() before JobMonitor AND close_pool() in a
# finally block.
#
# check_model_staleness.py (R17) and track_signal_outcomes.py (R18) were dropped
# from this list when the Model A jobs were deleted — see
# docs/product/model-a-reference-manifest.md. The remaining nine keep their guard;
# the universal scan below still covers every surviving JobMonitor + acquire job.
AFFECTED_JOBS = [
    "validate_price_data.py",
    "check_au_positions.py",
    "check_thesis_invalidations.py",
    "check_us_positions.py",
    "check_cron_health.py",
    "compute_opportunity_cost.py",
    "detect_theme_stages.py",
    "ingest_market_context.py",
    "ingest_underlyings.py",
]

# Jobs intentionally excluded from the universal init-before-JobMonitor scan,
# each with a documented reason. Allowlisting is deliberate, not incidental.
ALLOWLIST = {
    # Lazy stub-import pattern: init_pool / JobMonitor are bound to None at
    # module level and resolved at runtime via globals() (mirrors
    # asxos/brief/compose.py). The ordering cannot be checked statically and
    # is covered by each job's own runtime tests
    # (tests/test_ingest_news_job.py, tests/test_ingest_sentiment_job.py).
    "ingest_news.py",
    "ingest_sentiment.py",
}


def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


def _is_jobmonitor_call(node: ast.expr) -> bool:
    """True if ``node`` is a call to ``JobMonitor(...)`` (by name or attribute)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "JobMonitor"
    if isinstance(func, ast.Attribute):
        return func.attr == "JobMonitor"
    return False


def _is_call_named(node: ast.expr, name: str) -> bool:
    """True if ``node`` is ``await? name()`` (a call to the bare function ``name``)."""
    if isinstance(node, ast.Await):
        node = node.value
    if not isinstance(node, ast.Call):
        return False
    return isinstance(node.func, ast.Name) and node.func.id == name


def _enclosing_function(tree: ast.Module, target: ast.AST):
    """Return the innermost function node whose subtree contains ``target``."""
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    node: ast.AST | None = target
    while node is not None:
        node = parents.get(id(node))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            return node
    return None


def _jobmonitor_async_with(tree: ast.Module):
    """Find the ``async with JobMonitor(...)`` node, or None if absent."""
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncWith):
            for item in node.items:
                if _is_jobmonitor_call(item.context_expr):
                    return node
    return None


def _uses_acquire(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "acquire":
            return True
    return False


def _init_pool_linenos(func: ast.AST) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(func)
        if _is_call_named(node, "init_pool")
    ]


def _close_pool_in_finally(func: ast.AST) -> bool:
    """True if ``await close_pool()`` appears inside any ``finally`` block."""
    for node in ast.walk(func):
        if isinstance(node, ast.Try) and node.finalbody:
            for fin in node.finalbody:
                for inner in ast.walk(fin):
                    if _is_call_named(inner, "close_pool"):
                        return True
    return False


def _cron_job_files() -> list[pathlib.Path]:
    """All job modules that use both JobMonitor and acquire()."""
    files = []
    for path in sorted(JOBS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = _parse(path)
        if _jobmonitor_async_with(tree) is not None and _uses_acquire(tree):
            files.append(path)
    return files


# --------------------------------------------------------------------------- #
# Universal invariant: init_pool() before async with JobMonitor(...)          #
# --------------------------------------------------------------------------- #


def test_every_cron_job_initialises_pool_before_job_monitor():
    """
    For every job that uses JobMonitor + acquire (minus the documented
    allowlist), init_pool() must be awaited before entering the JobMonitor
    context. This is the exact Phase 2B bug class: JobMonitor.__aenter__
    acquires a connection, so the pool must already exist.
    """
    offenders: list[str] = []
    scanned: list[str] = []

    for path in _cron_job_files():
        if path.name in ALLOWLIST:
            continue
        scanned.append(path.name)
        tree = _parse(path)
        jm = _jobmonitor_async_with(tree)
        assert jm is not None
        func = _enclosing_function(tree, jm)
        assert func is not None, f"{path.name}: JobMonitor not inside a function"
        init_lines = _init_pool_linenos(func)
        if not init_lines or min(init_lines) >= jm.lineno:
            offenders.append(
                f"{path.name}: init_pool() at {init_lines or 'NONE'} is not "
                f"before JobMonitor at line {jm.lineno}"
            )

    # Sanity: the scan must actually be finding the fixed jobs, otherwise the
    # test is silently passing because it discovered nothing.
    for affected in AFFECTED_JOBS:
        assert affected in scanned, f"{affected} was not discovered by the scan"

    assert not offenders, "init_pool() must precede JobMonitor:\n" + "\n".join(offenders)


# --------------------------------------------------------------------------- #
# Scoped invariant: the fixed jobs close the pool in a finally block           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("job_file", AFFECTED_JOBS)
def test_affected_job_closes_pool_in_finally(job_file):
    path = JOBS_DIR / job_file
    tree = _parse(path)
    jm = _jobmonitor_async_with(tree)
    assert jm is not None, f"{job_file}: expected an async with JobMonitor(...)"
    func = _enclosing_function(tree, jm)
    assert func is not None
    # init_pool before JobMonitor (also asserted universally; kept here so the
    # per-file failure message is precise).
    init_lines = _init_pool_linenos(func)
    assert init_lines and min(init_lines) < jm.lineno, (
        f"{job_file}: init_pool() must be awaited before JobMonitor"
    )
    assert _close_pool_in_finally(func), (
        f"{job_file}: close_pool() must be awaited inside a finally block"
    )


# --------------------------------------------------------------------------- #
# Date-arithmetic regression for validate_price_data.py                        #
# --------------------------------------------------------------------------- #


def test_validate_price_data_uses_date_integer_arithmetic():
    """
    The 7-day lookback must use ``$1::date - 7`` (date - integer -> date), not
    ``$1::date - INTERVAL '7 days'`` (date - interval -> timestamp). Guards
    against reintroducing the interval form.
    """
    source = (JOBS_DIR / "validate_price_data.py").read_text()
    assert "INTERVAL '7 days'" not in source, (
        "validate_price_data.py reintroduced INTERVAL '7 days'; "
        "use $1::date - 7 instead"
    )
    assert "$1::date - 7" in source, (
        "validate_price_data.py should use the $1::date - 7 lookback"
    )
