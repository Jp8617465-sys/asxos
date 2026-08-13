"""
Structural guard: the `asx` CLI entrypoint must never reach the ML import chain.

WHY THIS EXISTS (manifest Finding 4). `asxos/cli/main.py` builds the Typer app by
importing every command module at load time. Before the Model A retirement it
carried `from asxos.cli.predict import predict`, which reached
`domain/models/model_a.py` -> `domain/models/cache.py` -> `import joblib` at module
level. That single line meant **every** `asx` command — `tax-view`, `tax-action`,
`thesis`, `portfolio`, `import-holdings`, `brief`: precisely the model-independent
commands the shelf strategy is built on — died with `ModuleNotFoundError: joblib`
if the optional `[ml]` extra was absent. The line carried zero Model A tokens, so
no grep for `model_a` would ever have found it.

Removal order alone is not a control: it is a fact about one past commit, not a
property anything re-checks. This test makes the property mechanical, so the
hazard cannot be reintroduced by a later import added in good faith three modules
deep.

RUNS ANYWHERE: pure `ast` + `pathlib`, no imports of the modules under test, so it
executes in the bare sandbox lane as well as CI.

Pattern follows tests/test_thesis_discipline.py::test_module_imports_are_model_independent,
extended from a single-file scan to the full transitive first-party closure.
"""
from __future__ import annotations

import ast
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ENTRYPOINT = "asxos.cli.main"

# Third-party packages that only exist under the optional `[ml]` extra. Any of
# these anywhere in the CLI's import closure re-arms the total-CLI-failure mode.
_ML_PACKAGES = frozenset({"joblib", "lightgbm", "sklearn", "scikit_learn", "xgboost", "shap"})

# First-party modules deleted by the Model A runtime retirement. Named explicitly
# so a reintroduction fails with a message that says *why*, not just "missing file".
# NB: `asxos.cli.model` (R14) is deliberately NOT listed — it is still present and
# still registered on the CLI, because its deletion is blocked on a test named in
# .github/workflows/targeted-ml-tests.yml. Add it here when R14 lands.
_RETIRED_MODULES = frozenset(
    {
        "asxos.cli.predict",
        "asxos.domain.models.cache",
        "asxos.domain.models.model_a",
        "asxos.domain.signals.writer",
    }
)

# The quarantine gate (manifest E2/E3). This is the asymmetry the retirement turns
# on: the artefact *loader* is removed, the approval *gate* is kept. Asserted
# present so a future "delete the Model A plumbing" pass that takes the gate with
# it fails here instead of silently disarming rule #11.
_QUARANTINE_GATE = "asxos.domain.models.production_gate"


def _module_files(module: str) -> list[pathlib.Path]:
    """Candidate on-disk files for a dotted first-party module name."""
    rel = module.replace(".", "/")
    return [p for p in (_ROOT / f"{rel}.py", _ROOT / rel / "__init__.py") if p.is_file()]


def _imported_names(path: pathlib.Path) -> list[tuple[str, int]]:
    """Every dotted name imported by `path`, at any nesting depth.

    Deliberately walks the whole tree rather than just module level: a lazy
    `import joblib` inside a function body would not break `asx --help`, but it
    would still put an ML dependency on a model-independent code path, which is
    the thing rule #11 forbids.
    """
    tree = ast.parse(path.read_text(), filename=str(path))
    names: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module is None:
                # Relative import — resolvable, but the codebase uses none. If one
                # appears, fail loudly rather than skipping it silently.
                raise AssertionError(
                    f"{path.relative_to(_ROOT)}:{node.lineno}: relative import found; "
                    "this scan assumes absolute imports and would otherwise skip it"
                )
            names.append((node.module, node.lineno))
            names.extend((f"{node.module}.{alias.name}", node.lineno) for alias in node.names)
    return names


def _closure() -> tuple[set[str], list[str]]:
    """(first-party modules reachable from the entrypoint, third-party violations)."""
    visited: set[str] = set()
    violations: list[str] = []

    def visit(module: str) -> None:
        if module in visited:
            return
        files = _module_files(module)
        if not files:
            return  # a `from pkg.mod import symbol` name, not a module
        visited.add(module)
        for path in files:
            for name, lineno in _imported_names(path):
                root = name.split(".")[0]
                if root == "asxos":
                    if name in _RETIRED_MODULES:
                        violations.append(
                            f"{path.relative_to(_ROOT)}:{lineno} imports {name} — "
                            "a retired Model A module (rule #11)"
                        )
                    visit(name)
                elif root in _ML_PACKAGES:
                    violations.append(
                        f"{path.relative_to(_ROOT)}:{lineno} imports {name} — "
                        f"'{root}' is an optional [ml] dependency and must not be "
                        "reachable from the CLI entrypoint"
                    )

    visit(_ENTRYPOINT)
    return visited, violations


def test_cli_entrypoint_does_not_import_retired_model_a_modules() -> None:
    """Direct scan of asxos/cli/main.py — the exact line Finding 4 identified."""
    src = (_ROOT / "asxos" / "cli" / "main.py").read_text()
    import_lines = [
        ln for ln in src.splitlines() if ln.strip().startswith(("import ", "from "))
    ]
    joined = "\n".join(import_lines)
    for retired in _RETIRED_MODULES:
        assert retired not in joined, f"cli/main.py re-imports retired module: {retired}"
    for tok in ("joblib", "lightgbm", "sklearn", "shap"):
        assert tok not in joined, f"cli/main.py imports ML dependency: {tok}"


def test_cli_import_closure_is_free_of_the_ml_chain() -> None:
    """No module transitively reachable from `asx` may touch the [ml] extra.

    This is the assertion that actually closes the hazard: `cli/main.py` was clean
    of Model A tokens *and still* pulled joblib, three imports down.
    """
    modules, violations = _closure()

    # Sanity: the walk must really be traversing the CLI, otherwise this test
    # passes by discovering nothing (cf. the `scanned` guard in
    # tests/test_cron_pool_init.py).
    assert len(modules) > 40, (
        f"import closure collapsed to {len(modules)} modules — the scan is not "
        "reaching the CLI command tree, so it is not proving anything"
    )
    assert _ENTRYPOINT in modules

    assert not violations, (
        "the `asx` CLI must not reach the optional [ml] dependency chain "
        "(every command breaks without it — manifest Finding 4):\n  "
        + "\n  ".join(violations)
    )


def test_cli_closure_still_reaches_the_quarantine_gate() -> None:
    """The loader is gone; the approval gate must not have gone with it.

    `resolve_production_model()` + `ModelGateDormant` are rule #11's mechanical
    enforcement point (manifest E2/E3). They live under `asxos/domain/models/`,
    the same package as the deleted artefact loader, which makes them the most
    likely collateral of a future "remove the Model A plumbing" pass.
    """
    modules, _ = _closure()
    assert _QUARANTINE_GATE in modules, (
        f"{_QUARANTINE_GATE} is no longer reachable from the CLI — rule #11's "
        "allocator gate may have been deleted alongside the Model A loader"
    )
    gate_src = (_ROOT / "asxos" / "domain" / "models" / "production_gate.py").read_text()
    assert "def resolve_production_model" in gate_src
    assert "class ModelGateDormant" in gate_src
    assert "approved_for_allocation" in gate_src
