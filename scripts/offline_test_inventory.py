"""Derive the test suite's external-integration surface from checked-in source.

This is a report-only Phase-1 control-plane probe, the sibling of
``scripts/workflow_effects.py``. It parses test modules with ``ast``, never
imports or executes them, never opens a socket, and never reads a credential.

Why it exists
-------------
The ACP plan (``docs/proposals/arbi-chief-of-staff-and-feature-control-plane-plan-2026-09-03.md``
§5.4) requires that "the Phase-1 inventory must identify tests that currently
call live endpoints", and makes fixture conversion part of the verifier exit
gate. ``tests/_netguard.py`` enforces the offline property at runtime; this
script is the standing, machine-readable statement of what remains
*deliberately* external and how each case is opted into.

Only flagged modules are reported. A suite where every module appeared would be
noise, and the committed artifact
(``docs/ops/offline-test-inventory.json``) would churn on every unrelated test
added. As scoped, it changes only when the external surface changes — which is
exactly when a reviewer should look.

Findings vocabulary
-------------------
``network-marked``
    Carries ``@pytest.mark.network`` — the guard is lifted for it.
``env-gated-integration``
    Reads an environment variable at module level *and* has a module-level
    ``pytest.skip(..., allow_module_level=True)``: the opt-in shape.
``network-client-import``
    Imports a client capable of egress (httpx, requests, urllib, socket,
    psycopg2, asyncpg, resend). Import alone is not a call — most of these
    modules build in-memory objects or patch the client — so this is a review
    pointer, not a defect.
``subprocess-spawns-process``
    Spawns a child process. The in-process guard does not extend across that
    boundary; closing it is the verifier's ``--network none``, not this script's
    job. Recorded so the residual surface is enumerated rather than assumed.
``network-marked-without-env-gate``
    Marked as permitted egress with no environment variable gating it, so the
    lift applies on an ordinary run. That is not automatically wrong — the
    guard's own regression module carries the marker to assert the guard is
    *disarmed*, and performs no egress — but it is the shape that would let a
    genuinely external test run unconditionally, so every instance needs a
    reason. ``tests/test_offline_test_inventory.py`` pins the current set.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

_EGRESS_MODULES = frozenset(
    {"httpx", "requests", "urllib", "socket", "psycopg2", "asyncpg", "resend"}
)


def _root_module(name: str) -> str:
    return name.split(".", 1)[0]


class _ModuleVisitor(ast.NodeVisitor):
    """Collect the egress-relevant facts about one test module."""

    def __init__(self) -> None:
        self.egress_imports: set[str] = set()
        self.env_vars: set[str] = set()
        self.uses_subprocess = False
        self.spawned_commands: set[str] = set()
        self.has_network_marker = False
        self.network_marked_tests: set[str] = set()
        self.module_level_skip = False

    # -- imports ----------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = _root_module(alias.name)
            if root in _EGRESS_MODULES:
                self.egress_imports.add(root)
            if root == "subprocess":
                self.uses_subprocess = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.level == 0:
            root = _root_module(node.module)
            if root in _EGRESS_MODULES:
                self.egress_imports.add(root)
            if root == "subprocess":
                self.uses_subprocess = True
        self.generic_visit(node)

    # -- pytest.mark.network ---------------------------------------------
    def visit_Attribute(self, node: ast.Attribute) -> None:
        if _is_network_marker(node):
            self.has_network_marker = True
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_decorators(node)
        self.generic_visit(node)

    def _record_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(target, ast.Attribute) and _is_network_marker(target):
                self.network_marked_tests.add(node.name)

    # -- calls -------------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        # os.environ.get("X") / os.getenv("X")
        if isinstance(func, ast.Attribute) and func.attr in {"get", "getenv"}:
            if _reads_environ(func) and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    self.env_vars.add(first.value)

        # pytest.skip(..., allow_module_level=True)
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "skip"
            and isinstance(func.value, ast.Name)
            and func.value.id == "pytest"
        ):
            for keyword in node.keywords:
                if (
                    keyword.arg == "allow_module_level"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    self.module_level_skip = True

        # subprocess.run / .check_output / .Popen / .call
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "subprocess":
                self.uses_subprocess = True
                if node.args:
                    command = _first_command(node.args[0])
                    if command:
                        self.spawned_commands.add(command)

        self.generic_visit(node)

    # -- os.environ["X"] ---------------------------------------------------
    def visit_Subscript(self, node: ast.Subscript) -> None:
        if (
            isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            self.env_vars.add(node.slice.value)
        self.generic_visit(node)


def _is_network_marker(node: ast.Attribute) -> bool:
    """Match ``pytest.mark.network`` exactly."""
    return (
        node.attr == "network"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    )


def _reads_environ(func: ast.Attribute) -> bool:
    """Match ``os.environ.get`` and ``os.getenv``."""
    if func.attr == "getenv":
        return isinstance(func.value, ast.Name) and func.value.id == "os"
    return isinstance(func.value, ast.Attribute) and func.value.attr == "environ"


def _first_command(node: ast.expr) -> str | None:
    """Best-effort static read of the executable a subprocess call spawns.

    Only literal argv is resolved. A command assembled at runtime or routed
    through a local helper is deliberately reported as nothing rather than
    guessed at — an inventory that invents entries is worse than one that
    under-reports a name it cannot see, because the module is flagged either way.
    """
    if isinstance(node, ast.List) and node.elts:
        first = node.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
        if isinstance(first, ast.Attribute) and first.attr == "executable":
            return "sys.executable"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.split()[0] if node.value.split() else None
    return None


def _analyse(path: Path, root: Path) -> dict[str, Any] | None:
    """Return the inventory entry for one test module, or None if unremarkable."""
    visitor = _ModuleVisitor()
    visitor.visit(ast.parse(path.read_text(encoding="utf-8")))

    findings: list[str] = []
    if visitor.has_network_marker:
        findings.append("network-marked")
    if visitor.env_vars and visitor.module_level_skip:
        findings.append("env-gated-integration")
    if visitor.egress_imports:
        findings.append("network-client-import")
    if visitor.uses_subprocess:
        findings.append("subprocess-spawns-process")
    if visitor.has_network_marker and not (visitor.env_vars and visitor.module_level_skip):
        findings.append("network-marked-without-env-gate")

    if not findings:
        return None

    return {
        "path": path.relative_to(root).as_posix(),
        "findings": sorted(findings),
        "network_marked": visitor.has_network_marker,
        "network_marked_tests": sorted(visitor.network_marked_tests),
        "opt_in_env_vars": sorted(visitor.env_vars) if visitor.module_level_skip else [],
        "egress_client_imports": sorted(visitor.egress_imports),
        "spawns_subprocess": visitor.uses_subprocess,
        "spawned_commands": sorted(visitor.spawned_commands),
    }


def build_inventory(tests_dir: Path, *, root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(tests_dir.rglob("test_*.py")):
        if "__pycache__" in path.parts:
            continue
        entry = _analyse(path, root)
        if entry is not None:
            entries.append(entry)

    finding_counts: dict[str, int] = {}
    for entry in entries:
        for finding in entry["findings"]:
            finding_counts[finding] = finding_counts.get(finding, 0) + 1

    return {
        "schema_version": 1,
        "tests_dir": tests_dir.relative_to(root).as_posix(),
        "summary": {
            "flagged_module_count": len(entries),
            "network_marked_modules": sorted(
                entry["path"] for entry in entries if entry["network_marked"]
            ),
            "subprocess_modules": sorted(
                entry["path"] for entry in entries if entry["spawns_subprocess"]
            ),
            "opt_in_env_vars": sorted(
                {var for entry in entries for var in entry["opt_in_env_vars"]}
            ),
            "finding_counts": dict(sorted(finding_counts.items())),
        },
        "tests": entries,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=Path("tests"),
        help="test directory relative to --root",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON instead of indented JSON",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    root = args.root.resolve()
    tests_dir = args.tests_dir
    if not tests_dir.is_absolute():
        tests_dir = root / tests_dir
    tests_dir = tests_dir.resolve()
    try:
        tests_dir.relative_to(root)
    except ValueError as exc:
        raise SystemExit("--tests-dir must be inside --root") from exc
    if not tests_dir.is_dir():
        raise SystemExit(f"test directory does not exist: {tests_dir}")

    inventory = build_inventory(tests_dir, root=root)
    print(
        json.dumps(
            inventory,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
