"""PostgreSQL 17 behavioural proof for migration 0043.

The dedicated CI workflow supplies a disposable database named
``asxos_migration_test``. The exact-name guard makes this suite refuse any other
database, because the schema setup and malformed-schema probe are intentionally
destructive to their ephemeral targets.
"""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg2
import pytest
from psycopg2 import errors
from psycopg2.extensions import connection as PgConnection
from psycopg2.extensions import make_dsn

_DATABASE_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
if _DATABASE_URL is None:
    pytest.skip(
        "MIGRATION_TEST_DATABASE_URL is required for PostgreSQL integration tests",
        allow_module_level=True,
    )

_MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "migrations"
    / "0043_price_revisions.sql"
)
_EXPECTED_DATABASE = "asxos_migration_test"


def _connect(dsn: str = _DATABASE_URL) -> PgConnection:
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    return conn


def _assert_disposable_database(conn: PgConnection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        observed = cur.fetchone()[0]
    assert observed == _EXPECTED_DATABASE, (
        "refusing migration integration test outside the disposable database: "
        f"expected {_EXPECTED_DATABASE!r}, observed {observed!r}"
    )


@pytest.fixture(scope="module")
def migrated_dsn() -> str:
    conn = _connect()
    _assert_disposable_database(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE public.universe (
                symbol TEXT PRIMARY KEY
            );
            CREATE TABLE public.prices (
                symbol TEXT NOT NULL REFERENCES public.universe(symbol),
                dt DATE NOT NULL,
                open NUMERIC(18,6),
                high NUMERIC(18,6),
                low NUMERIC(18,6),
                close NUMERIC(18,6) NOT NULL,
                volume BIGINT,
                adj_close NUMERIC(18,6),
                PRIMARY KEY (symbol, dt)
            );
            """
        )
        cur.execute(_MIGRATION.read_text(encoding="utf-8"))
    conn.close()
    return _DATABASE_URL


def _insert_price(conn: PgConnection, symbol: str, *, close: str = "10.000000") -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.universe(symbol) VALUES (%s) ON CONFLICT DO NOTHING",
            (symbol,),
        )
        cur.execute(
            """
            INSERT INTO public.prices(
                symbol, dt, open, high, low, close, volume, adj_close
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                symbol,
                date(2026, 8, 11),
                Decimal("9.500000"),
                Decimal("10.500000"),
                Decimal("9.250000"),
                Decimal(close),
                1_000,
                Decimal(close),
            ),
        )


def test_migration_rejects_drifted_prices_shape_before_creating_ledger() -> None:
    admin = _connect()
    _assert_disposable_database(admin)
    bad_database = "asxos_migration_bad_shape"
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (bad_database,))
        assert cur.fetchone() is None, f"disposable database already exists: {bad_database}"
        cur.execute(f'CREATE DATABASE "{bad_database}"')
    admin.close()

    bad_dsn = make_dsn(_DATABASE_URL, dbname=bad_database)
    conn = _connect(bad_dsn)
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE public.prices (
                symbol TEXT NOT NULL,
                dt DATE NOT NULL,
                open NUMERIC(18,6),
                high NUMERIC(18,6),
                low NUMERIC(18,6),
                close NUMERIC(18,6) NOT NULL,
                volume BIGINT,
                adj_close NUMERIC(18,6),
                unexpected_column TEXT,
                PRIMARY KEY (symbol, dt)
            )
            """
        )
        with pytest.raises(errors.RaiseException, match="prices shape mismatch"):
            cur.execute(_MIGRATION.read_text(encoding="utf-8"))
        # The migration file opens its own explicit transaction. This connection
        # otherwise runs in autocommit mode, so clear the failed SQL transaction
        # explicitly before inspecting whether any objects escaped the rollback.
        cur.execute("ROLLBACK")
        cur.execute("SELECT to_regclass('public.price_revisions')")
        assert cur.fetchone()[0] is None
    conn.close()


def test_material_update_captures_complete_old_and_new_rows(
    migrated_dsn: str,
) -> None:
    conn = _connect(migrated_dsn)
    _insert_price(conn, "UPDATE.AU")
    with conn.cursor() as cur:
        cur.execute("SET application_name = 'migration-0043-integration'")
        cur.execute(
            "UPDATE public.prices SET close = 11, adj_close = 11 WHERE symbol = 'UPDATE.AU'"
        )
        cur.execute(
            """
            SELECT operation, prior_close, replacement_close, recorded_by,
                   recorded_application, transaction_id IS NOT NULL
            FROM public.price_revisions
            WHERE prior_symbol = 'UPDATE.AU'
            """
        )
        row = cur.fetchone()
    conn.close()

    assert row == (
        "update",
        Decimal("10.000000"),
        Decimal("11.000000"),
        "postgres",
        "migration-0043-integration",
        True,
    )


def test_no_op_update_creates_no_revision(migrated_dsn: str) -> None:
    conn = _connect(migrated_dsn)
    _insert_price(conn, "NOOP.AU")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.price_revisions")
        before = cur.fetchone()[0]
        cur.execute(
            "UPDATE public.prices SET adj_close = adj_close WHERE symbol = 'NOOP.AU'"
        )
        cur.execute("SELECT count(*) FROM public.price_revisions")
        after = cur.fetchone()[0]
    conn.close()
    assert after == before


def test_delete_creates_a_tombstone(migrated_dsn: str) -> None:
    conn = _connect(migrated_dsn)
    _insert_price(conn, "DELETE.AU")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.prices WHERE symbol = 'DELETE.AU'")
        cur.execute(
            """
            SELECT operation, prior_close, replacement_symbol, replacement_dt,
                   replacement_close
            FROM public.price_revisions
            WHERE prior_symbol = 'DELETE.AU'
            """
        )
        row = cur.fetchone()
    conn.close()
    assert row == ("delete", Decimal("10.000000"), None, None, None)


def test_revision_capture_rolls_back_with_the_price_update(migrated_dsn: str) -> None:
    setup = _connect(migrated_dsn)
    _insert_price(setup, "ROLLBACK.AU")
    setup.close()

    conn = psycopg2.connect(migrated_dsn)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET LOCAL application_name = 'migration-0043-rollback'")
        cur.execute(
            "UPDATE public.prices SET close = 12 WHERE symbol = 'ROLLBACK.AU'"
        )
        cur.execute(
            """
            SELECT transaction_id = pg_current_xact_id()::text::bigint
            FROM public.price_revisions
            WHERE prior_symbol = 'ROLLBACK.AU'
            """
        )
        assert cur.fetchone()[0] is True
    conn.rollback()
    conn.close()

    verify = _connect(migrated_dsn)
    with verify.cursor() as cur:
        cur.execute("SELECT close FROM public.prices WHERE symbol = 'ROLLBACK.AU'")
        assert cur.fetchone()[0] == Decimal("10.000000")
        cur.execute(
            "SELECT count(*) FROM public.price_revisions WHERE prior_symbol = 'ROLLBACK.AU'"
        )
        assert cur.fetchone()[0] == 0
    verify.close()


def test_revision_ledger_is_append_only_and_prices_cannot_truncate(
    migrated_dsn: str,
) -> None:
    conn = _connect(migrated_dsn)
    _insert_price(conn, "IMMUTABLE.AU")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.prices SET close = 13 WHERE symbol = 'IMMUTABLE.AU'"
        )
        with pytest.raises(errors.ObjectNotInPrerequisiteState):
            cur.execute(
                """
                UPDATE public.price_revisions
                SET recorded_application = 'tampered'
                WHERE prior_symbol = 'IMMUTABLE.AU'
                """
            )
        with pytest.raises(errors.ObjectNotInPrerequisiteState):
            cur.execute("TRUNCATE public.prices")
    conn.close()
