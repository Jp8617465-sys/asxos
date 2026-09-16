"""Static guards for migrations 0055/0056/0057 (F-E2E r2 M1) — the file contents.

Import-light (reads the .sql only), like `test_migration_0029_market_cap.py`. The
behavioural contract runs against PostgreSQL 17 in
`tests/test_m1_migrations_integration.py` (the `migration-integration` lane).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
M0055 = MIGRATIONS / "0055_snapshot_cash_nullable.sql"
M0056 = MIGRATIONS / "0056_cash_balance_assertions.sql"
M0057 = MIGRATIONS / "0057_thesis_revisions_source_system_screen.sql"


@pytest.mark.parametrize("path", [M0055, M0056, M0057])
def test_migration_exists_and_is_expand_only(path: Path) -> None:
    assert path.is_file(), f"missing {path}"
    sql = path.read_text()
    assert not re.search(r"\bDROP\s+(TABLE|COLUMN)\b", sql, re.IGNORECASE)
    assert not re.search(r"\bDELETE\s+FROM\b|\bTRUNCATE\b|\bUPDATE\s+\w+\s+SET\b", sql, re.IGNORECASE)


def test_0055_pairs_cash_and_capital_nullability() -> None:
    sql = M0055.read_text()
    assert re.search(r"ALTER\s+COLUMN\s+cash_aud\s+DROP\s+NOT\s+NULL", sql, re.IGNORECASE)
    assert re.search(r"ALTER\s+COLUMN\s+capital_aud\s+DROP\s+NOT\s+NULL", sql, re.IGNORECASE)
    assert re.search(
        r"CHECK\s*\(\s*\(cash_aud IS NULL\)\s*=\s*\(capital_aud IS NULL\)\s*\)", sql, re.IGNORECASE
    )
    # The balance identity stays with the writer, deliberately (see the header).
    assert "holdings_mv_aud + cash_aud)" not in sql.replace("--", "")


def test_0056_is_an_append_only_sourced_ledger() -> None:
    sql = M0056.read_text()
    assert re.search(r"CREATE\s+TABLE\s+cash_balance_assertions", sql, re.IGNORECASE)
    assert "cash_aud      NUMERIC(18,6) NOT NULL CHECK (cash_aud >= 0)" in sql
    assert "'broker_statement', 'bank_statement', 'manual_entry'" in sql
    assert "BEFORE UPDATE OR DELETE ON cash_balance_assertions" in sql
    assert "cash_balance_assertions_statement_names_evidence" in sql
    assert "cash_balance_assertions_agent_is_manual" in sql
    # Staleness is derived at read time, never stored.
    assert not re.search(r"valid_until|expires_at|stale", sql.split("CREATE TABLE")[1].split(";")[0])


def test_0057_widens_the_source_check_and_keeps_the_provenance_constraints() -> None:
    sql = M0057.read_text()
    assert "DROP CONSTRAINT thesis_revisions_source_check" in sql
    assert re.search(
        r"ADD\s+CONSTRAINT\s+thesis_revisions_source_check\s+CHECK\s*\(source IN \('human', 'agent', 'system_screen'\)\)",
        sql,
    )
    # The 0034 provenance constraints are untouched, so they bind the new value too.
    assert "DROP CONSTRAINT thesis_revisions_agent_requires" not in sql
