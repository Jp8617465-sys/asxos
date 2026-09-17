"""Static guard for migration 0059 — the closed `theses.governance_status` default.

Import-light (reads the .sql only), matching `test_m1_migrations.py`. The
behavioural proof for this one is the live apply: `information_schema.columns`
must show `column_default IS NULL` afterwards, and that is recorded in the PR body
with the applied version, per `AGENTS.md` §8.

Why a test at all for a one-line ALTER: the default it removes is the mechanism
that put eleven unreviewed rows into `approved` with zero `governance_events` to
show for it. If a later migration re-adds a default here, that is a decision
someone should have to make deliberately, against a failing test — not something
that slips back in as a convenience.
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
M0059 = MIGRATIONS / "0059_theses_governance_status_no_default.sql"


def test_0059_exists_and_touches_no_data() -> None:
    assert M0059.is_file(), f"missing {M0059}"
    sql = M0059.read_text()
    assert not re.search(r"\bDROP\s+(TABLE|COLUMN)\b", sql, re.IGNORECASE)
    assert not re.search(r"\bDELETE\s+FROM\b|\bTRUNCATE\b|\bUPDATE\s+\w+\s+SET\b", sql, re.IGNORECASE)


def test_0059_drops_the_default_and_nothing_else() -> None:
    sql = M0059.read_text()
    assert re.search(
        r"ALTER\s+TABLE\s+theses\s+ALTER\s+COLUMN\s+governance_status\s+DROP\s+DEFAULT",
        sql,
        re.IGNORECASE,
    )
    # The NOT NULL and the CHECK must survive — losing either would be a widening,
    # and the NOT NULL is what makes an omitting INSERT fail loudly.
    assert not re.search(r"DROP\s+NOT\s+NULL", sql, re.IGNORECASE)
    assert not re.search(r"DROP\s+CONSTRAINT", sql, re.IGNORECASE)


def test_0059_records_why_the_default_and_not_the_approval_path() -> None:
    """The register review's first draft blamed approve_object and its own red team
    found that wrong: the eleven never went through it. The header must keep that
    correction, because it is the reason this migration exists in this form."""
    sql = M0059.read_text().lower()
    assert "approve_object" in sql
    assert "governance_events" in sql


def test_no_migration_reintroduces_a_default_on_this_column() -> None:
    """Scans every migration after 0059. Fails if one sets a default here again."""
    offenders = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name <= M0059.name:
            continue
        body = "\n".join(
            line for line in path.read_text().splitlines() if not line.strip().startswith("--")
        )
        if re.search(
            r"theses[\s\S]{0,400}?governance_status[^;]{0,200}?(SET\s+DEFAULT|DEFAULT\s+')",
            body,
            re.IGNORECASE,
        ):
            offenders.append(path.name)
    assert not offenders, (
        f"{offenders} appear to set a default on theses.governance_status again — 0059 removed it "
        f"on purpose; re-adding it needs a deliberate decision and this test updated with the reason"
    )
