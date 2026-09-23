"""The coverage predicate is shared, and stays shared — E-30 / #327.

`jobs/build_decision_packets.py` partitions an approved thesis out of the
builder when the data layer has never held a statement for its symbol, and
`asxos/brief/compose.py` reports that same set as a discipline finding so the
thesis does not become invisible the moment it stops paging.

If those two ever disagreed about what "covered" means, the brief would either
hide a thesis the job is still failing on, or announce one the job is quietly
handling. The guard below is therefore about *drift*, not about SQL: it fails
if either consumer grows its own copy of the query.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from asxos.domain.theses.coverage import (
    SQL_SYMBOL_HAS_STATEMENTS,
    SQL_SYMBOLS_WITH_STATEMENTS,
    covered_symbols,
)

REPO = Path(__file__).resolve().parent.parent
TABLE = "rs_financial_statements"
#: The two consumers of the COVERAGE question — "has this symbol ever been
#: served at all?" — which must partition the identical set.
#:
#: Scoped to exactly these two on purpose. Ten other modules query this table
#: (valuation inputs, PIT derivation, replay lineage, results review) and are
#: none of this test's business: they ask what the statements SAY, not whether
#: any exist. A first draft of this guard banned the table name repo-wide and
#: failed on all ten — a test asserting an invariant the codebase does not have
#: and should not have.
_COVERAGE_CONSUMERS = ("jobs/build_decision_packets.py", "asxos/brief/compose.py")


def _string_literals(tree: ast.AST) -> list[str]:
    return [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def test_neither_consumer_restates_the_coverage_query() -> None:
    """A second copy of this query is the whole failure mode, so it is banned
    in the two places that would cause it.

    Deliberately an `ast` string-literal check rather than a text search: the
    table name is *supposed* to survive in the prose that explains the
    invariant — `coverage.py`'s docstring says it, and so do the comments in
    both consumers. Only an executable restatement must not survive.
    """
    offenders = sorted(
        path
        for path in _COVERAGE_CONSUMERS
        if any(
            TABLE in lit
            for lit in _string_literals(ast.parse((REPO / path).read_text(encoding="utf-8")))
        )
    )
    assert not offenders, (
        f"{TABLE} is queried through asxos.domain.theses.coverage so the packet "
        f"builder and the brief cannot drift apart. These restated it: {offenders}"
    )


def test_the_guard_can_actually_fail() -> None:
    """Mutation check (L50) inline, so the assertion above is not vacuous."""
    src = f'q = "SELECT 1 FROM {TABLE} WHERE symbol = $1"\n'
    assert any(TABLE in lit for lit in _string_literals(ast.parse(src)))


def test_the_packet_builder_imports_the_shared_predicate() -> None:
    """The other half of the guard: banning a copy is only useful if the job
    still asks the question at all."""
    src = (REPO / "jobs/build_decision_packets.py").read_text(encoding="utf-8")
    assert "from asxos.domain.theses.coverage import SQL_SYMBOL_HAS_STATEMENTS" in src
    assert "SQL_SYMBOL_HAS_STATEMENTS" in src


def test_both_statements_ask_ever_not_at_a_cutoff() -> None:
    """The safety property, pinned. A date/cutoff predicate in either query
    would turn a partition that can only quiet a never-covered name into one
    that quiets a real regression — the mute button `coverage.py` warns about.
    """
    for sql in (SQL_SYMBOL_HAS_STATEMENTS, SQL_SYMBOLS_WITH_STATEMENTS):
        lowered = sql.lower()
        assert TABLE in lowered
        for cutoff_token in ("as_of", "period_end", "fiscal", "<=", ">=", "date"):
            assert cutoff_token not in lowered, f"{cutoff_token!r} narrows {sql!r} to a cutoff"


@pytest.mark.asyncio
async def test_empty_input_does_not_hit_the_database() -> None:
    """The brief runs this on every compose; an empty thesis set is the common case."""

    class _Boom:
        async def fetch(self, *a: object, **k: object) -> list[dict[str, str]]:
            raise AssertionError("queried the DB for an empty symbol list")

    assert await covered_symbols(_Boom(), []) == set()


@pytest.mark.asyncio
async def test_returns_the_covered_subset() -> None:
    class _Conn:
        def __init__(self) -> None:
            self.seen: list[object] = []

        async def fetch(self, sql: str, *args: object) -> list[dict[str, str]]:
            self.seen.append(args[0])
            return [{"symbol": "CBA.AU"}]

    conn = _Conn()
    got = await covered_symbols(conn, ["CBA.AU", "HUBS.NYSE"])
    assert got == {"CBA.AU"}
    assert conn.seen == [["CBA.AU", "HUBS.NYSE"]]
