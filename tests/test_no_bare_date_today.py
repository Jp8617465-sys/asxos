"""Guard: no bare ``date.today()`` in shipped code.

Every scheduled job runs on a UTC GitHub Actions runner, so ``date.today()``
resolves to the UTC calendar day — 10 or 11 hours behind Sydney, and the daily
pipeline fires at 20:30 UTC, already the next Sydney day. A bare call there
returns yesterday's date by Sydney reckoning on *every* run, not just at a DST
boundary. ``asxos.clock.today()`` is the fix; this test stops the bug returning.

This is deliberately a CI gate rather than a scheduled sweep: a sweep would only
report the regression after it had already shipped a wrong date, whereas this
fails the build that introduces it.

Detection is AST-based, not textual. A grep would flag the several places that
legitimately *discuss* ``date.today()`` in a comment or docstring — including
this module and ``asxos/clock.py`` — and the resulting allow-list would rot.
The AST only ever sees real calls.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ("asxos", "jobs", "scripts")

# ---------------------------------------------------------------------------
# The only permitted bare calls in the codebase.
#
# asxos/domain/tax/ is excluded by a standing ADR constraint ("nothing under
# asxos/domain/tax/"), so the timezone sweep deliberately stopped at its door.
# All three sites are `today = today or date.today()` — an injectable default
# that every caller in the tax module already overrides, and every test pins
# explicitly, so no test exercises the bare path.
#
# It is NOT therefore harmless: a CGT disposal evaluated one day early can flip
# the 12-month discount (spec 5.1). Converting it needs a tax-spec review, not
# a sweep. Tracked as a finding, not fixed here.
# ---------------------------------------------------------------------------
ALLOWED = {
    "asxos/domain/tax/positions.py",
    "asxos/domain/tax/cgt.py",
}


class _BareTodayVisitor(ast.NodeVisitor):
    """Collect line numbers of ``date.today()`` / ``datetime.date.today()``."""

    def __init__(self) -> None:
        self.hits: list[int] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "today":
            value = func.value
            # `date.today()` — including an aliased `_date.today()`.
            if isinstance(value, ast.Name) and value.id.lstrip("_") == "date":
                self.hits.append(node.lineno)
            # `datetime.date.today()`
            elif (
                isinstance(value, ast.Attribute)
                and value.attr == "date"
                and isinstance(value.value, ast.Name)
                and value.value.id == "datetime"
            ):
                self.hits.append(node.lineno)
        self.generic_visit(node)


def _python_files() -> list[Path]:
    out: list[Path] = []
    for directory in SCANNED:
        out.extend(
            p
            for p in sorted((ROOT / directory).rglob("*.py"))
            if "__pycache__" not in p.parts
        )
    return out


def test_no_bare_date_today() -> None:
    offenders: list[str] = []
    for path in _python_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED:
            continue
        visitor = _BareTodayVisitor()
        visitor.visit(ast.parse(path.read_text()))
        offenders.extend(f"{rel}:{line}" for line in visitor.hits)

    assert not offenders, (
        "bare date.today() resolves to the UTC runner's calendar day, which is "
        "the previous Sydney day for the whole evening pipeline. Use "
        "asxos.clock.today() instead.\n  " + "\n  ".join(offenders)
    )


def test_allowlist_entries_still_exist_and_still_offend() -> None:
    """The allow-list must not outlive what it excuses.

    If a tax site is converted or deleted, this fails and the entry has to go —
    otherwise the allow-list silently widens into a hole that new code can be
    added to.
    """
    for rel in sorted(ALLOWED):
        path = ROOT / rel
        assert path.exists(), f"allow-listed file no longer exists: {rel}"
        visitor = _BareTodayVisitor()
        visitor.visit(ast.parse(path.read_text()))
        assert visitor.hits, (
            f"{rel} no longer contains a bare date.today() — "
            "remove it from ALLOWED in this test."
        )


@pytest.mark.parametrize(
    "source",
    [
        "from datetime import date\nx = date.today()\n",
        "from datetime import date as _date\nx = _date.today()\n",
        "import datetime\nx = datetime.date.today()\n",
    ],
)
def test_visitor_detects_each_spelling(source: str) -> None:
    """Prove the guard actually fires — a green guard that cannot fail is worse
    than no guard, because it reads as coverage."""
    visitor = _BareTodayVisitor()
    visitor.visit(ast.parse(source))
    assert visitor.hits


def test_visitor_ignores_comments_and_docstrings() -> None:
    """Textual detection would flag both of these. AST must not."""
    source = '"""Do not use date.today() here."""\n# date.today() is banned\nx = 1\n'
    visitor = _BareTodayVisitor()
    visitor.visit(ast.parse(source))
    assert not visitor.hits


def test_visitor_ignores_unrelated_today_attributes() -> None:
    """`clock.today()` and `self.today()` are not the banned call."""
    source = "x = clock.today()\ny = self.today()\nz = obj.calendar.today()\n"
    visitor = _BareTodayVisitor()
    visitor.visit(ast.parse(source))
    assert not visitor.hits
