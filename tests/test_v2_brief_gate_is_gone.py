"""`ASXOS_V2_BRIEF_ENABLED` is read by nothing, and the V2 renderer is gone — A-35.

Dark-launch DELETE verdict #3 (issued 2026-09-14, executed 2026-09-20) removed the
V2 rendering branch in `asxos/domain/brief/composer.py`, `render_v2_html()`, and the
frozen `_archive/brief_v2.html.j2` template it loaded.

Same guard shape as `tests/test_portfolio_brief_gate_is_gone.py`, and the same
reasoning for it: the failure mode worth catching is not the whole branch returning —
that is visible in review — but a *fragment*, one
`os.environ.get("ASXOS_V2_BRIEF_ENABLED")` in a new surface, which would read like a
live gate and in fact gate nothing, since no workflow sets the variable.

Deliberately an executable-reference check over `ast`, not a text search: the string
is supposed to survive in the prose that records what was removed (`composer.py` and
`renderer.py` both say so). Only a *read* must not survive.
"""

from __future__ import annotations

import ast
from pathlib import Path

GATE = "ASXOS_V2_BRIEF_ENABLED"
REPO = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ("asxos", "jobs", "scripts")


def _env_reads(tree: ast.AST) -> set[str]:
    """Every environment-variable name this module reads, by any of the shapes."""
    names: set[str] = set()

    def literal(node: ast.expr | None) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_get = isinstance(func, ast.Attribute) and func.attr in {"get", "getenv"}
            is_getenv = isinstance(func, ast.Name) and func.id == "getenv"
            if (is_get or is_getenv) and node.args:
                got = literal(node.args[0])
                if got is not None:
                    names.add(got)
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
        f"{GATE} was deleted under A-35 and is set by no workflow. "
        f"Reading it gates nothing while looking like a live dark-launch gate. "
        f"Offending modules: {offenders}"
    )


def test_no_workflow_sets_the_deleted_gate() -> None:
    setters = [
        str(f.relative_to(REPO))
        for f in sorted((REPO / ".github" / "workflows").glob("*.yml"))
        if GATE in f.read_text(encoding="utf-8")
    ]
    assert not setters, f"{GATE} reappeared in a workflow env block: {setters}"


def test_the_guard_can_actually_fail() -> None:
    """Mutation check (L50) inline, so the absence assertions are not vacuous."""
    for source in (
        f'import os\nx = os.environ.get("{GATE}")\n',
        f'import os\nx = os.environ["{GATE}"]\n',
        f'import os\nx = os.getenv("{GATE}")\n',
    ):
        assert GATE in _env_reads(ast.parse(source)), f"detector missed: {source!r}"


def test_the_v2_renderer_is_gone() -> None:
    """`render_v2_html` was the only consumer of the frozen V2 template."""
    import asxos.domain.brief.renderer as renderer

    assert not hasattr(renderer, "render_v2_html")
    assert hasattr(renderer, "render_html"), "the surviving alias must stay"


def test_the_frozen_v2_template_is_gone() -> None:
    """Its own `_archive/README.md` said the copy existed only for that renderer,
    so leaving an unrenderable template behind would be dead weight that reads
    like a deliberate archive."""
    assert not (REPO / "asxos/brief/templates/_archive/brief_v2.html.j2").exists()


def test_composer_renders_v1_unconditionally() -> None:
    """The branch is gone, not merely defaulted off.

    An `if` that always takes the same arm is still a gate someone can flip; the
    point of the verdict was to remove the choice.
    """
    src = (REPO / "asxos/domain/brief/composer.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert GATE not in _env_reads(tree)
    assert "render_v2_html" not in src
