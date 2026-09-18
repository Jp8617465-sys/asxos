"""`ASXOS_PORTFOLIO_BRIEF_ENABLED` is read by nothing — A-34.

The dark-launch DELETE verdict #1 (issued 2026-09-14, executed 2026-09-19)
removed `_portfolio_section` and the gate that fronted it. The failure mode this
guards is not the deletion coming back whole — that would be obvious in review.
It is a *fragment* coming back: one `os.environ.get("ASXOS_PORTFOLIO_BRIEF_ENABLED")`
in a new surface, which would read like a live firewall gate to anyone who found
it and would in fact gate nothing, since no workflow sets the variable and no
code consumes it.

Deliberately an **executable-reference** check, not a text search. The string is
supposed to survive in prose — `compose.py`'s section list, `paper_trade.py`'s
docstring and this file all say what was deleted and why, and a doc that records
a removed gate is worth more than a doc that is silent about it. What must not
survive is a read.

Scoped with `ast` rather than `grep` for the same reason
`tests/test_domain_purity.py` is: a comment or a docstring mentioning a name is
not a use of it, and a test that cannot tell the difference gets weakened until
it means nothing.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

GATE = "ASXOS_PORTFOLIO_BRIEF_ENABLED"
REPO = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ("asxos", "jobs", "scripts")


def _env_reads(tree: ast.AST) -> set[str]:
    """Every environment-variable name this module reads, by any of the shapes."""
    names: set[str] = set()

    def literal(node: ast.expr | None) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    for node in ast.walk(tree):
        # os.environ.get("X") / os.getenv("X") / environ.get("X")
        if isinstance(node, ast.Call):
            func = node.func
            is_get = isinstance(func, ast.Attribute) and func.attr in {"get", "getenv"}
            is_getenv = isinstance(func, ast.Name) and func.id == "getenv"
            if (is_get or is_getenv) and node.args:
                got = literal(node.args[0])
                if got is not None:
                    names.add(got)
        # os.environ["X"]
        if isinstance(node, ast.Subscript):
            got = literal(node.slice if isinstance(node.slice, ast.expr) else None)
            if got is not None:
                names.add(got)
    return names


def _python_files() -> list[Path]:
    out: list[Path] = []
    for d in SOURCE_DIRS:
        out.extend(sorted((REPO / d).rglob("*.py")))
    return out


def test_no_module_reads_the_deleted_gate() -> None:
    offenders = [
        str(f.relative_to(REPO))
        for f in _python_files()
        if GATE in _env_reads(ast.parse(f.read_text(encoding="utf-8")))
    ]
    assert not offenders, (
        f"{GATE} was deleted under A-34 and is set by no workflow. "
        f"Reading it gates nothing while looking like a firewall check. "
        f"Offending modules: {offenders}"
    )


def test_no_workflow_sets_the_deleted_gate() -> None:
    """The other half: a variable nobody reads is harmless; one that is *set*
    invites the read back. Both halves have to stay false."""
    setters = [
        str(f.relative_to(REPO))
        for f in sorted((REPO / ".github" / "workflows").glob("*.yml"))
        if GATE in f.read_text(encoding="utf-8")
    ]
    assert not setters, f"{GATE} reappeared in a workflow env block: {setters}"


def test_the_guard_can_actually_fail() -> None:
    """Mutation check (L50) inline, so the two assertions above are not vacuous.

    A guard asserting an absence passes trivially when its detector is broken.
    This feeds `_env_reads` a module that *does* read the gate and requires it
    to be seen — if the ast walk stops matching the shapes real code uses, this
    fails before the absence tests can go quietly green.
    """
    for source in (
        f'import os\nx = os.environ.get("{GATE}")\n',
        f'import os\nx = os.environ["{GATE}"]\n',
        f'import os\nx = os.getenv("{GATE}")\n',
    ):
        assert GATE in _env_reads(ast.parse(source)), f"detector missed: {source!r}"


def test_the_brief_no_longer_exposes_a_portfolio_section() -> None:
    """The deletion's own shape: the section name is gone from the gold order.

    `SECTION_ORDER` is what the materialiser writes and what `load_gold` reads
    back, so a `portfolio` entry here is the one thing that would resurrect the
    surface without anyone touching `compose.py`.
    """
    from asxos.brief.section import SECTION_ORDER

    assert "portfolio" not in SECTION_ORDER


@pytest.mark.parametrize("name", ["PortfolioSection", "PortfolioTradeSummary", "_portfolio_section"])
def test_compose_no_longer_defines_the_portfolio_surface(name: str) -> None:
    import asxos.brief.compose as compose

    assert not hasattr(compose, name), f"{name} came back into asxos/brief/compose.py"
