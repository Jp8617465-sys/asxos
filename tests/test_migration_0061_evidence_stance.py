"""Static guard for migration 0061 — the `stance` column on both evidence tables.

Import-light (reads the `.sql` only), matching `test_m1_migrations.py` and
`test_migration_0059_governance_default.py`. The behavioural proof runs on
PostgreSQL 17 in `test_migration_0061_evidence_stance_integration.py`.

What these guards hold is not "the SQL parses" — it is the two properties that
make the column mean anything.

**Expand-only.** Nothing dropped, no row rewritten.

**No DEFAULT, no backfill.** This is the load-bearing one. NULL means *nobody
judged*; `neutral` means *someone judged and found the citation
non-diagnostic*. A DEFAULT would assert the second about rows that are the
first — precisely what `theses.governance_status` did to eleven rows before
`0059` closed it. That is also why this file scans every later migration for a
re-introduction: the convenience is easy to add and the meaning is silent when
it goes.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
M0061 = MIGRATIONS / "0061_evidence_stance.sql"

STANCES = ("supports", "contradicts", "neutral")


def test_0061_exists_and_touches_no_data() -> None:
    assert M0061.is_file(), f"missing {M0061}"
    sql = M0061.read_text()
    assert not re.search(r"\bDROP\s+(TABLE|COLUMN|CONSTRAINT)\b", sql, re.IGNORECASE)
    assert not re.search(r"\bDELETE\s+FROM\b|\bTRUNCATE\b|\bUPDATE\s+\w+\s+SET\b", sql, re.IGNORECASE)


def test_0061_adds_the_column_to_both_evidence_tables() -> None:
    sql = M0061.read_text()
    for table in ("thesis_evidence", "agent_evidence"):
        assert re.search(
            rf"ALTER\s+TABLE\s+{table}\s+ADD\s+COLUMN\s+stance\s+TEXT",
            sql,
            re.IGNORECASE,
        ), f"0061 must add stance to {table}"


def test_0061_check_admits_exactly_the_three_values_and_null() -> None:
    sql = M0061.read_text()
    checks = re.findall(r"CHECK\s*\((stance[^;]*?)\)\s*;", sql, re.IGNORECASE | re.DOTALL)
    assert len(checks) == 2, f"expected one stance CHECK per table, found {len(checks)}"
    for body in checks:
        assert re.search(r"stance\s+IS\s+NULL", body, re.IGNORECASE), (
            "the CHECK must permit NULL — an unmarked citation is the corpus's "
            "honest state, not a violation"
        )
        for value in STANCES:
            assert f"'{value}'" in body, f"the CHECK dropped {value!r}"


def test_0061_sets_no_default_on_either_column() -> None:
    """The NULL-vs-neutral distinction is the column's entire purpose.

    A DEFAULT of 'neutral' would record "someone weighed this" about 26 rows of
    deterministic screen output that nobody weighed.
    """
    body = "\n".join(
        line for line in M0061.read_text().splitlines() if not line.strip().startswith("--")
    )
    assert not re.search(r"stance[^;]{0,120}?DEFAULT", body, re.IGNORECASE)


def test_0061_backfills_nothing() -> None:
    body = "\n".join(
        line for line in M0061.read_text().splitlines() if not line.strip().startswith("--")
    )
    assert "stance" in body
    assert not re.search(r"\bSET\s+stance\b|\bINSERT\s+INTO\b", body, re.IGNORECASE), (
        "the 26 existing rows are system_screen output and hold no stance; "
        "backfilling them to 'neutral' would invent a judgement nobody made"
    )


def test_no_later_migration_defaults_or_backfills_stance() -> None:
    """Scans every migration after 0061.

    A later convenience DEFAULT would silently undo this column's meaning, so it
    has to be a deliberate choice made against a failing test.
    """
    offenders = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name <= M0061.name:
            continue
        body = "\n".join(
            line for line in path.read_text().splitlines() if not line.strip().startswith("--")
        )
        if re.search(
            r"stance[^;]{0,200}?(SET\s+DEFAULT|DEFAULT\s+')|UPDATE[\s\S]{0,200}?SET\s+stance",
            body,
            re.IGNORECASE,
        ):
            offenders.append(path.name)
    assert not offenders, (
        f"{offenders} appear to default or backfill stance — 0061 left it NULL on purpose "
        f"(NULL = nobody judged); changing that needs a decision and this test updated with the reason"
    )
