"""Screening tests for `scripts/roquery.py` -- the read-only ad-hoc SQL path.

These test the EARLY layer only. The real read-only guarantee is
`conn.set_session(readonly=True)`, enforced by Postgres; nothing here connects to
a database. So a passing suite means "the obvious bypasses are refused with a
clear message", not "writes are impossible" -- that second claim rests on the
server, which is the point of having two independent layers.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "roquery", Path(__file__).resolve().parent.parent / "scripts" / "roquery.py"
)
assert _SPEC and _SPEC.loader
roquery = importlib.util.module_from_spec(_SPEC)
sys.modules["roquery"] = roquery
_SPEC.loader.exec_module(roquery)


# ---------------------------------------------------------------------------
# Accepted: the shapes a real read actually takes.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select count(*) from theses;",
        "  SELECT symbol FROM universe WHERE is_active  ",
        "WITH x AS (SELECT 1 AS n) SELECT n FROM x",
        "SHOW transaction_read_only",
        "EXPLAIN SELECT * FROM prices",
        "TABLE universe",
        "VALUES (1), (2)",
        "SELECT * FROM prices -- trailing comment is fine",
    ],
)
def test_read_only_statements_are_accepted(sql: str) -> None:
    assert roquery.assert_read_only(sql)


def test_column_named_like_a_write_verb_is_not_tripped() -> None:
    """Word-boundary matching, so ordinary schema names still work.

    `updated_at` and `deleted_at` are real column names in this repo; a substring
    scan would refuse every query that touches them.
    """
    assert roquery.assert_read_only("SELECT updated_at, deleted_at FROM thesis_revisions")


# ---------------------------------------------------------------------------
# Refused: writes, in every position they can hide.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM theses",
        "UPDATE holding_lots SET quantity = 0",
        "INSERT INTO decisions (id) VALUES (1)",
        "DROP TABLE prices",
        "TRUNCATE thesis_revisions",
        "ALTER TABLE universe ADD COLUMN x int",
        "GRANT ALL ON theses TO public",
        "COMMENT ON COLUMN prices.close IS 'x'",
        "CREATE TABLE t (id int)",
        "REFRESH MATERIALIZED VIEW mv",
        "VACUUM FULL prices",
        "CALL some_procedure()",
        "DO $$ BEGIN PERFORM 1; END $$",
        "COPY theses FROM '/tmp/x.csv'",
    ],
)
def test_write_statements_are_refused(sql: str) -> None:
    with pytest.raises(roquery.NotReadOnly):
        roquery.assert_read_only(sql)


@pytest.mark.parametrize(
    ("sql", "why"),
    [
        ("SELECT * INTO evil FROM prices", "SELECT..INTO creates a table"),
        ("SELECT * INTO TEMP t FROM prices", "SELECT..INTO TEMP creates a table"),
        ("SELECT nextval('some_seq')", "advances a sequence"),
        ("SELECT setval('some_seq', 1)", "resets a sequence"),
        ("SELECT pg_read_file('/etc/passwd')", "server-side file read"),
        ("SELECT lo_export(1, '/tmp/x')", "server-side file write"),
    ],
)
def test_bypasses_found_by_adversarial_testing_are_refused(sql: str, why: str) -> None:
    """Every case here PASSED the screen when first written, and was found by
    attacking it rather than by reading it.

    ``nextval`` is the one that matters most: a Postgres read-only transaction
    explicitly permits sequence advancement, so unlike the others it is not caught
    by the server-side backstop either. This test is the only thing stopping it.
    """
    with pytest.raises(roquery.NotReadOnly):
        roquery.assert_read_only(sql)


def test_semicolon_inside_a_string_literal_is_refused_not_executed() -> None:
    """A known FALSE REFUSAL, pinned deliberately.

    The single-statement check is naive about string literals, so `SELECT ';'` is
    rejected even though it is harmless. That is the safe direction to be wrong in
    and the cost is retyping a query, so it is recorded rather than "fixed" with a
    real SQL parser this path does not need.
    """
    with pytest.raises(roquery.NotReadOnly, match="multiple statements"):
        roquery.assert_read_only("SELECT ';'")


def test_nested_block_comment_fails_closed() -> None:
    """`/* /* x */ */` leaves a dangling `*/`, which is not an allowed lead verb.

    Postgres nests block comments; the non-greedy regex here does not. It fails
    closed, which is the acceptable outcome for a mismatch.
    """
    with pytest.raises(roquery.NotReadOnly):
        roquery.assert_read_only("/* /* nested */ */ SELECT 1")


def test_writing_cte_is_refused_despite_leading_with() -> None:
    """`WITH ... AS (DELETE ... RETURNING *)` is valid Postgres and it writes.

    This is why the leading verb alone is not sufficient and write keywords are
    matched in any position.
    """
    with pytest.raises(roquery.NotReadOnly, match="delete"):
        roquery.assert_read_only("WITH gone AS (DELETE FROM theses RETURNING *) SELECT * FROM gone")


def test_second_statement_is_refused() -> None:
    with pytest.raises(roquery.NotReadOnly, match="multiple statements"):
        roquery.assert_read_only("SELECT 1; DELETE FROM theses")


def test_write_hidden_behind_a_block_comment_is_refused() -> None:
    """Comments are stripped BEFORE screening, so a comment cannot smuggle a write."""
    with pytest.raises(roquery.NotReadOnly):
        roquery.assert_read_only("SELECT 1; /* harmless */ DELETE FROM theses")


def test_write_hidden_behind_a_line_comment_is_refused() -> None:
    with pytest.raises(roquery.NotReadOnly):
        roquery.assert_read_only("SELECT 1 -- ok\n; DROP TABLE prices")


def test_trailing_semicolon_alone_is_not_a_second_statement() -> None:
    assert roquery.assert_read_only("SELECT 1;") == "SELECT 1"


@pytest.mark.parametrize("sql", ["", "   ", "-- only a comment", "/* only */"])
def test_empty_is_refused(sql: str) -> None:
    with pytest.raises(roquery.NotReadOnly, match="empty"):
        roquery.assert_read_only(sql)


# ---------------------------------------------------------------------------
# CLI: --check screens without connecting, so it is safe to run anywhere.
# ---------------------------------------------------------------------------


def test_check_mode_accepts_a_read(capsys: pytest.CaptureFixture[str]) -> None:
    assert roquery.main(["SELECT 1", "--check"]) == 0
    assert "ok (read-only)" in capsys.readouterr().out


def test_check_mode_rejects_a_write_with_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert roquery.main(["DELETE FROM theses", "--check"]) == 2
    assert "refused" in capsys.readouterr().err
