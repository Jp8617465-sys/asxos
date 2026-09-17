"""Migrations 0055/0056/0057/0060 executed on PostgreSQL 17 (the `migration-integration` lane).

Runs only when `MIGRATION_TEST_DATABASE_URL` points at the disposable database the
lane provisions; skipped everywhere else, like
`test_price_revision_migration_integration.py`, whose harness this mirrors. The
prerequisite tables are created here in their production shape for the columns
the migrations touch (0011 for `portfolio_daily_snapshots`, 0034 for
`thesis_revisions.source`, 0021 for `thesis_revisions.revision_type`), then the
four files are applied verbatim and the behaviour they promise is exercised —
not just that they parse.
"""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
import pytest
from psycopg2.extensions import connection as PgConnection

_DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
_EXPECTED_DATABASE = "asxos_migration_test"
MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

pytestmark = [
    pytest.mark.network,  # lifts tests/_netguard.py for the disposable local database
    pytest.mark.skipif(
        not _DATABASE_URL, reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL integration tests"
    ),
]


def _connect() -> PgConnection:
    conn = psycopg2.connect(_DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        observed = cur.fetchone()[0]
    assert observed == _EXPECTED_DATABASE, f"refusing outside the disposable database: {observed!r}"
    return conn


@pytest.fixture(scope="module")
def migrated() -> PgConnection:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            DROP TABLE IF EXISTS cash_balance_assertions;
            DROP TABLE IF EXISTS portfolio_daily_snapshots;
            DROP TABLE IF EXISTS thesis_revisions;
            CREATE TABLE portfolio_daily_snapshots (
                as_of            DATE          PRIMARY KEY,
                capital_aud      NUMERIC(18,6) NOT NULL,
                holdings_mv_aud  NUMERIC(18,6) NOT NULL,
                cash_aud         NUMERIC(18,6) NOT NULL,
                holdings_count   INTEGER       NOT NULL,
                ingested_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
            );
            INSERT INTO portfolio_daily_snapshots (as_of, capital_aud, holdings_mv_aud, cash_aud, holdings_count)
            VALUES ('2026-09-15', 8431.000000, 8431.000000, 0.000000, 1);
            CREATE TABLE thesis_revisions (
                revision_id         BIGSERIAL PRIMARY KEY,
                reasoning           TEXT NOT NULL,
                -- 0021's shape and constraint NAME, so 0060's DROP CONSTRAINT IF EXISTS
                -- actually drops it and the widened ADD does not collide.
                revision_type       TEXT NOT NULL DEFAULT 'opened'
                    CONSTRAINT thesis_revisions_revision_type_check CHECK (revision_type IN (
                        'opened', 'assumption_change', 'target_adjusted', 'stop_adjusted',
                        'timeline_extended', 'reviewed_no_change', 'status_change',
                        'entered', 'exited', 'exited_by_stop', 'exited_by_target',
                        'expired', 'analyst_action')),
                source              TEXT NOT NULL DEFAULT 'human' CHECK (source IN ('human','agent')),
                agent_name          TEXT,
                evidence_confidence TEXT CHECK (evidence_confidence IN ('verified','inferred','speculative')),
                evidence_citations  JSONB NOT NULL DEFAULT '[]'::jsonb,
                CONSTRAINT thesis_revisions_agent_requires_confidence
                    CHECK (source = 'human' OR evidence_confidence IS NOT NULL),
                CONSTRAINT thesis_revisions_agent_requires_citation
                    CHECK (source = 'human' OR jsonb_array_length(evidence_citations) > 0)
            );
            INSERT INTO thesis_revisions (reasoning) VALUES ('opened');
            """
        )
        for name in (
            "0055_snapshot_cash_nullable.sql",
            "0056_cash_balance_assertions.sql",
            "0057_thesis_revisions_source_system_screen.sql",
            "0060_thesis_revisions_packet_examined.sql",
        ):
            cur.execute((MIGRATIONS / name).read_text(encoding="utf-8"))
    yield conn
    conn.close()


def _fails(conn: PgConnection, sql: str, params: tuple[Any, ...] = ()) -> str:
    with conn.cursor() as cur:
        try:
            cur.execute(sql, params)
        except psycopg2.Error as exc:
            return str(exc)
    return ""


# --- 0055 -----------------------------------------------------------------------


def test_0055_existing_row_is_untouched(migrated: PgConnection) -> None:
    with migrated.cursor() as cur:
        cur.execute("SELECT capital_aud, cash_aud FROM portfolio_daily_snapshots WHERE as_of = '2026-09-15'")
        assert cur.fetchone() == (Decimal("8431.000000"), Decimal("0.000000"))


def test_0055_both_null_is_the_honest_unmeasured_row(migrated: PgConnection) -> None:
    assert _fails(
        migrated,
        "INSERT INTO portfolio_daily_snapshots (as_of, capital_aud, holdings_mv_aud, cash_aud, holdings_count) "
        "VALUES ('2026-09-16', NULL, 8431, NULL, 1)",
    ) == ""


@pytest.mark.parametrize(("capital", "cash"), [("8431", None), (None, "0")])
def test_0055_one_sided_null_is_refused(migrated: PgConnection, capital: str | None, cash: str | None) -> None:
    err = _fails(
        migrated,
        "INSERT INTO portfolio_daily_snapshots (as_of, capital_aud, holdings_mv_aud, cash_aud, holdings_count) "
        "VALUES ('2026-09-17', %s, 8431, %s, 1)",
        (capital, cash),
    )
    assert "portfolio_daily_snapshots_cash_capital_paired" in err


# --- 0056 -----------------------------------------------------------------------


def test_0056_assertion_round_trip_and_read_order(migrated: PgConnection) -> None:
    with migrated.cursor() as cur:
        cur.execute(
            "INSERT INTO cash_balance_assertions (as_of, cash_aud, source, asserted_by, evidence_uri) "
            "VALUES ('2026-09-10', 100.5, 'broker_statement', 'human', 'file://statement-2026-09.pdf')"
        )
        cur.execute(
            "INSERT INTO cash_balance_assertions (as_of, cash_aud, source, asserted_by, note) "
            "VALUES ('2026-09-10', 120.0, 'manual_entry', 'human', 'corrected after the fee posted')"
        )
        cur.execute(
            "SELECT cash_aud FROM cash_balance_assertions WHERE as_of <= %s "
            "ORDER BY as_of DESC, recorded_at DESC LIMIT 1",
            (date(2026, 9, 16),),
        )
        assert cur.fetchone()[0] == Decimal("120.000000")  # the later correction wins


def test_0056_is_append_only(migrated: PgConnection) -> None:
    assert "append-only" in _fails(migrated, "UPDATE cash_balance_assertions SET cash_aud = 0")
    assert "append-only" in _fails(migrated, "DELETE FROM cash_balance_assertions")


@pytest.mark.parametrize(
    ("values", "constraint"),
    [
        ("('2026-09-10', -1, 'manual_entry', 'human', NULL)", "cash_balance_assertions_cash_aud_check"),
        ("('2026-09-10', 1, 'broker_statement', 'human', NULL)", "cash_balance_assertions_statement_names_evidence"),
        ("('2026-09-10', 1, 'bank_statement', 'agent', 'file://x')", "cash_balance_assertions_agent_is_manual"),
        ("('2026-09-10', 1, 'policy_floor', 'human', NULL)", "cash_balance_assertions_source_check"),
    ],
)
def test_0056_refuses_the_shapes_it_names(migrated: PgConnection, values: str, constraint: str) -> None:
    err = _fails(
        migrated,
        "INSERT INTO cash_balance_assertions (as_of, cash_aud, source, asserted_by, evidence_uri) VALUES " + values,
    )
    assert constraint in err


# --- 0057 -----------------------------------------------------------------------


def test_0057_system_screen_is_admitted_only_with_evidence(migrated: PgConnection) -> None:
    ok = _fails(
        migrated,
        "INSERT INTO thesis_revisions (reasoning, source, evidence_confidence, evidence_citations) "
        "VALUES ('screen', 'system_screen', 'verified', '[\"asxos://valuation_runs/vr-X.AU-2026-09-16-zero_excess\"]')",
    )
    assert ok == ""
    bare = _fails(migrated, "INSERT INTO thesis_revisions (reasoning, source) VALUES ('screen', 'system_screen')")
    assert "thesis_revisions_agent_requires" in bare
    # Evidence supplied so the only constraint left to fail is the widened source CHECK
    # (Postgres reports the first violated constraint, and the provenance pair sorts earlier).
    unknown = _fails(
        migrated,
        "INSERT INTO thesis_revisions (reasoning, source, evidence_confidence, evidence_citations) "
        "VALUES ('x', 'oracle', 'verified', '[\"asxos://x\"]')",
    )
    assert "thesis_revisions_source_check" in unknown
    with migrated.cursor() as cur:
        cur.execute("SELECT source FROM thesis_revisions ORDER BY revision_id")
        assert [r[0] for r in cur.fetchall()] == ["human", "system_screen"]


# --- 0060 -----------------------------------------------------------------------


def test_0060_packet_examined_is_admitted_with_evidence_and_nothing_else_widens(migrated: PgConnection) -> None:
    """The A-47 writeback's row shape, against the real widened CHECK on Postgres 17.

    Three things, in the order Postgres reports them: the exact row the writeback
    emits is admitted; the same row without evidence is refused by the 0034
    provenance pair (0057's header says those bind system_screen, and 0060 leaves
    them untouched); and an unknown type is refused by the widened CHECK by NAME,
    proving 0060 widened the list by exactly one value rather than dropping it.
    """
    ok = _fails(
        migrated,
        "INSERT INTO thesis_revisions (reasoning, revision_type, source, evidence_confidence, evidence_citations) "
        "VALUES ('packet dpk-cba-1-2026-09-16 examined', 'packet_examined', 'system_screen', 'inferred', "
        "'[\"decision_packet:dpk-cba-1-2026-09-16\", \"content_hash:abc\"]')",
    )
    assert ok == ""
    bare = _fails(
        migrated,
        "INSERT INTO thesis_revisions (reasoning, revision_type, source) "
        "VALUES ('x', 'packet_examined', 'system_screen')",
    )
    assert "thesis_revisions_agent_requires" in bare
    unknown = _fails(
        migrated,
        "INSERT INTO thesis_revisions (reasoning, revision_type, source, evidence_confidence, evidence_citations) "
        "VALUES ('x', 'oracle_examined', 'system_screen', 'verified', '[\"asxos://x\"]')",
    )
    assert "thesis_revisions_revision_type_check" in unknown
    # Expand-only: a pre-0060 answering type is still admitted after the widening.
    assert _fails(migrated, "INSERT INTO thesis_revisions (reasoning, revision_type) VALUES ('hold', 'reviewed_no_change')") == ""
