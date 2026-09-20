"""Migration 0061 executed on PostgreSQL 17 (the `migration-integration` lane).

Runs only when `MIGRATION_TEST_DATABASE_URL` points at the disposable database the
lane provisions; skipped everywhere else. Harness mirrors
`test_m1_migrations_integration.py`: the two tables are created in their
production shape for the columns 0061 touches, one pre-existing row is seeded into
each, then the file is applied verbatim and the behaviour it promises is exercised
— not just that it parses.

The seeded rows stand in for the 26 `system_screen` citations in production. That
they come out the other side of the ALTER still unmarked is the property worth
testing: an expand-only column that quietly marked its own backfill would defeat
the distinction the column exists to record.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2
import pytest
from psycopg2.extensions import connection as PgConnection

_DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
_EXPECTED_DATABASE = "asxos_migration_test"
MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
M0061 = MIGRATIONS / "0061_evidence_stance.sql"

STANCES = ("supports", "contradicts", "neutral")

pytestmark = [
    pytest.mark.network,  # lifts tests/_netguard.py for the disposable local database
    pytest.mark.skipif(
        not _DATABASE_URL,
        reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL integration tests",
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
        # 0033's thesis_evidence and the governance trail's agent_evidence, reduced
        # to the columns 0061 touches plus the tier CHECK both carry in production.
        cur.execute(
            """
            DROP TABLE IF EXISTS thesis_evidence;
            DROP TABLE IF EXISTS agent_evidence;
            CREATE TABLE thesis_evidence (
                evidence_id  BIGSERIAL PRIMARY KEY,
                thesis_id    BIGINT NOT NULL,
                source_agent TEXT   NOT NULL,
                tier         TEXT   NOT NULL CHECK (tier IN ('verified','inferred','speculative')),
                claim_text   TEXT   NOT NULL CHECK (claim_text <> ''),
                retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE agent_evidence (
                evidence_id  BIGSERIAL PRIMARY KEY,
                agent_name   TEXT NOT NULL,
                claim        TEXT NOT NULL CHECK (claim <> ''),
                tier         TEXT NOT NULL CHECK (tier IN ('verified','inferred','speculative')),
                retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            INSERT INTO thesis_evidence (thesis_id, source_agent, tier, claim_text)
            VALUES (14, 'system_screen', 'verified', 'residual income > 0');
            INSERT INTO agent_evidence (agent_name, claim, tier)
            VALUES ('macro-economist', 'terms of trade rolling over', 'inferred');
            """
        )
        cur.execute(M0061.read_text(encoding="utf-8"))
    yield conn
    conn.close()


def _fails(conn: PgConnection, sql: str, params: tuple[Any, ...] = ()) -> str:
    with conn.cursor() as cur:
        try:
            cur.execute(sql, params)
        except psycopg2.Error as exc:
            return str(exc)
    return ""


def test_0061_leaves_existing_rows_unmarked(migrated: PgConnection) -> None:
    """The ALTER must not invent a stance for rows that predate the column."""
    with migrated.cursor() as cur:
        cur.execute("SELECT count(*) FROM thesis_evidence WHERE stance IS NOT NULL")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM agent_evidence WHERE stance IS NOT NULL")
        assert cur.fetchone()[0] == 0


@pytest.mark.parametrize("stance", STANCES)
def test_0061_admits_each_stance(migrated: PgConnection, stance: str) -> None:
    with migrated.cursor() as cur:
        cur.execute(
            "INSERT INTO thesis_evidence (thesis_id, source_agent, tier, claim_text, stance) "
            "VALUES (14, 'james', 'verified', %s, %s) RETURNING stance",
            (f"claim {stance}", stance),
        )
        assert cur.fetchone()[0] == stance
        cur.execute(
            "INSERT INTO agent_evidence (agent_name, claim, tier, stance) "
            "VALUES ('macro-economist', %s, 'inferred', %s) RETURNING stance",
            (f"claim {stance}", stance),
        )
        assert cur.fetchone()[0] == stance


def test_0061_admits_an_unmarked_insert(migrated: PgConnection) -> None:
    """Omitting stance stays legal — a citation nobody has judged is a real state,
    and the deterministic screen that wrote 26 of them holds no opinion."""
    with migrated.cursor() as cur:
        cur.execute(
            "INSERT INTO thesis_evidence (thesis_id, source_agent, tier, claim_text) "
            "VALUES (14, 'system_screen', 'verified', 'no stance') RETURNING stance"
        )
        assert cur.fetchone()[0] is None


def test_0061_rejects_a_value_outside_the_vocabulary(migrated: PgConnection) -> None:
    err = _fails(
        migrated,
        "INSERT INTO thesis_evidence (thesis_id, source_agent, tier, claim_text, stance) "
        "VALUES (14, 'james', 'verified', 'bad stance', 'refutes')",
    )
    assert "thesis_evidence_stance_check" in err, err
    err = _fails(
        migrated,
        "INSERT INTO agent_evidence (agent_name, claim, tier, stance) "
        "VALUES ('macro-economist', 'bad stance', 'inferred', 'maybe')",
    )
    assert "agent_evidence_stance_check" in err, err
