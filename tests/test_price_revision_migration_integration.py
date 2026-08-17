"""PostgreSQL 17 behavioural proof for migration 0043.

The dedicated CI workflow supplies a disposable database named
``asxos_migration_test``. The exact-name guard makes this suite refuse any other
database, because the schema setup and malformed-schema probe are intentionally
destructive to their ephemeral targets.

That guard checks the DATABASE, but this module needs a disposable **cluster**:
it creates a second database, and it creates and drops a ROLE, both of which are
cluster-scoped and escape the exact-name check entirely. CI gives it a throwaway
``postgres:17`` service container, which satisfies that. Do not point
``MIGRATION_TEST_DATABASE_URL`` at a shared cluster.

Everything here needs a real server: grants, SECURITY DEFINER, trigger firing
order and the payload-shape CHECK are runtime behaviour, so a text-level
assertion on the migration file cannot reach them. That is the whole reason
this lane exists alongside ``test_price_revision_migration.py``.
"""
from __future__ import annotations

import os
import re
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


# One source of truth for the row identity. The upsert cases below re-send this
# exact primary key to hit the ON CONFLICT arm; if the date drifted between the
# insert and the upsert, the upsert would quietly become a plain INSERT, the
# AFTER UPDATE trigger would never fire, and "no revision was written" would
# pass while proving nothing. Drift in the non-key columns fails loudly instead
# (it becomes a real change and writes a revision), so only this one matters.
_DT = date(2026, 8, 11)


def _price_row(symbol: str, *, close: str, adj_close: str) -> tuple[object, ...]:
    """The canonical `prices` row every case in this module writes."""
    return (
        symbol,
        _DT,
        Decimal("9.500000"),
        Decimal("10.500000"),
        Decimal("9.250000"),
        Decimal(close),
        1_000,
        Decimal(adj_close),
    )


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
            _price_row(symbol, close=close, adj_close=close),
        )


# A copy of ``asxos/ingestion/prices.py::upsert_prices``, differing only in
# placeholder style (psycopg2 ``%s`` vs asyncpg ``$N``) and schema qualification.
# The two upsert cases below exercise the PRODUCTION write shape against the
# trigger rather than a hand-written UPDATE, so the copy has to stay honest —
# ``test_production_upsert_constant_has_not_drifted`` is what keeps it that way.
_PRODUCTION_UPSERT = """
    INSERT INTO public.prices (symbol, dt, open, high, low, close, volume, adj_close)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (symbol, dt) DO UPDATE SET
        open      = EXCLUDED.open,
        high      = EXCLUDED.high,
        low       = EXCLUDED.low,
        close     = EXCLUDED.close,
        volume    = EXCLUDED.volume,
        adj_close = EXCLUDED.adj_close
"""


def _drop_role_if_exists(cur: object, role: str) -> None:
    """Remove ``role`` and every privilege granted to it, if it is present.

    Roles are CLUSTER-wide, not per-database, so a role leaked by a failed run
    outlives the disposable database and breaks the next run's CREATE. This is
    called both before creating the role and in cleanup, so neither a leftover
    from last time nor a failure midway through this test can strand one.

    ``DROP OWNED BY`` is the documented way to clear a role's grants in the
    current database; enumerating REVOKEs instead would need updating every
    time the test grants something new.
    """
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
    if cur.fetchone() is None:
        return
    # Identifiers cannot be bound as parameters; `role` is a module-local
    # literal, never caller-supplied.
    cur.execute(f"DROP OWNED BY {role}")
    cur.execute(f"DROP ROLE {role}")


def _normalise_sql(sql: str) -> str:
    """Collapse the differences the two copies are allowed to have."""
    sql = re.sub(r"\$\d+", "%s", sql)             # asyncpg -> psycopg2 placeholders
    sql = sql.replace("public.prices", "prices")  # schema qualification
    return " ".join(sql.split())                  # indentation and line breaks


def test_production_upsert_constant_has_not_drifted() -> None:
    """The copied upsert must still be the statement production issues.

    Without this the copy rots silently and the two upsert cases below decay
    into testing a statement nobody runs. The concrete regression it catches:
    if ingestion gains a column in its SET list (an ``updated_at = now()``,
    say), every run would start manufacturing one ledger row per symbol — the
    exact noise ``test_production_upsert_with_unchanged_values_writes_no_revision``
    claims to rule out, and which that test could no longer detect once its
    copy had gone stale.

    Read as text rather than imported: ``asxos.ingestion.prices`` pulls in
    ``asxos.config``, which builds settings requiring ``database_url`` at import
    time, and this lane sets only ``MIGRATION_TEST_DATABASE_URL`` — an import
    would fail at collection and take the whole lane down.

    Known gap: the workflow is path-filtered on ``migrations/**`` and
    ``tests/test_price_revision_migration*.py``, so a change to
    ``asxos/ingestion/prices.py`` alone does not trigger this lane. Adding that
    path to ``.github/workflows/migration-integration.yml`` would close it.
    """
    production = (
        Path(__file__).resolve().parent.parent / "asxos" / "ingestion" / "prices.py"
    ).read_text(encoding="utf-8")
    assert _normalise_sql(_PRODUCTION_UPSERT) in _normalise_sql(production), (
        "the upsert copied into this module no longer matches "
        "asxos/ingestion/prices.py::upsert_prices"
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


def test_production_upsert_with_unchanged_values_writes_no_revision(
    migrated_dsn: str,
) -> None:
    """The ingestion job re-upserts every row on every run.

    Without the trigger's ``to_jsonb(OLD) IS NOT DISTINCT FROM to_jsonb(NEW)``
    guard this would manufacture one revision per symbol per run, and the ledger
    would be noise rather than evidence. ``test_no_op_update_creates_no_revision``
    proves the guard with a hand-written self-assignment; this proves it against
    the statement production actually issues, including its ON CONFLICT arm.
    """
    conn = _connect(migrated_dsn)
    _insert_price(conn, "REUPSERT.AU", close="5.100000")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.price_revisions")
        before = cur.fetchone()[0]
        cur.execute(
            _PRODUCTION_UPSERT,
            # RETURNING is appended here rather than baked into the constant so
            # the constant stays byte-comparable with production above.
            _PRODUCTION_UPSERT + " RETURNING (xmax <> 0)",
            _price_row("REUPSERT.AU", close="5.100000", adj_close="5.100000"),
        )
        # Prove the ON CONFLICT arm was taken: a non-zero xmax means this row was
        # UPDATEd, not inserted. Without it the assertion below is a pure
        # negative that also passes if the statement quietly took the INSERT
        # path (a drifted key), or if the trigger were dropped outright.
        assert cur.fetchone()[0] is True, "upsert did not take the ON CONFLICT arm"

        cur.execute("SELECT count(*) FROM public.price_revisions")
        after = cur.fetchone()[0]
    conn.close()
    assert after == before


def test_production_upsert_rewriting_adj_close_is_recoverable(
    migrated_dsn: str,
) -> None:
    """The exact defect 0043 exists to contain.

    Every dividend or split makes the provider restate ``adj_close`` for prior
    dates, and the ingestion upsert overwrites it in place. Before 0043 the old
    value was simply gone, so the system could not reconstruct what it served on
    any past date. Here both sides must survive in the ledger.
    """
    conn = _connect(migrated_dsn)
    _insert_price(conn, "ADJUSTED.AU", close="5.100000")
    with conn.cursor() as cur:
        cur.execute(
            _PRODUCTION_UPSERT,
            # A dividend restatement: close is untouched, adj_close is rewritten.
            _price_row("ADJUSTED.AU", close="5.100000", adj_close="4.870000"),
        )
        cur.execute(
            """
            SELECT operation, prior_close, prior_adj_close,
                   replacement_close, replacement_adj_close
            FROM public.price_revisions
            WHERE prior_symbol = 'ADJUSTED.AU'
            """
        )
        row = cur.fetchone()
    conn.close()
    assert row == (
        "update",
        Decimal("5.100000"),
        Decimal("5.100000"),
        Decimal("5.100000"),
        Decimal("4.870000"),
    )


def test_writer_without_ledger_rights_still_captures(migrated_dsn: str) -> None:
    """SECURITY DEFINER does what the function's COMMENT claims.

    The production ingestion role is granted DML on ``prices`` and nothing on
    ``price_revisions``. If the trigger function ever loses SECURITY DEFINER,
    that role's writes start failing outright — this pins the property so the
    regression surfaces in CI rather than in the ingestion job.

    On attribution, the assertion below is deliberately weak: it pins that
    ``recorded_by`` is NOT the assumed role. It cannot distinguish
    ``session_user`` from ``current_user``, because the connection's session
    user and the SECURITY DEFINER owner are both ``postgres`` here — swapping
    the migration to ``current_user`` would keep this green. Telling them apart
    would need a second LOGIN role connecting on its own DSN, which is more
    fixture than the property is worth today.
    """
    # A module-local literal, never caller-supplied, so there is no injection
    # path. Identifiers cannot be BOUND as parameters; psycopg2.sql.Identifier
    # would also work, and f-strings under a hardcoded-literal guard are the
    # documented house convention (.claude/rules/portfolio-conventions.md).
    # Keep it lowercase: Postgres case-folds unquoted identifiers, so a name
    # with capitals would stop matching the string compared against below.
    role = "drill_writer_no_ledger_rights"
    conn = _connect(migrated_dsn)
    _insert_price(conn, "DEFINER.AU")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT session_user")
            session_user = cur.fetchone()[0]

            _drop_role_if_exists(cur, role)
            cur.execute(f"CREATE ROLE {role} NOLOGIN")
            cur.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
            cur.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.prices TO {role}"
            )
            # Deliberately no grant on price_revisions and none on its sequence.
            # Pin that premise rather than assuming it: if a future edit granted
            # the role INSERT here, the capture below would succeed for an
            # ordinary reason and the SECURITY DEFINER conclusion would be
            # unsupported while the test stayed green.
            cur.execute(
                "SELECT has_table_privilege(%s, 'public.price_revisions', 'INSERT')",
                (role,),
            )
            assert cur.fetchone()[0] is False, "the drill role can write the ledger"

            cur.execute("SELECT count(*) FROM public.price_revisions")
            before = cur.fetchone()[0]

            cur.execute(f"SET ROLE {role}")
            cur.execute(
                "UPDATE public.prices SET close = 6.25 WHERE symbol = 'DEFINER.AU'"
            )
            cur.execute("RESET ROLE")

            cur.execute("SELECT count(*) FROM public.price_revisions")
            assert cur.fetchone()[0] == before + 1

            cur.execute(
                """
                SELECT recorded_by, prior_close, replacement_close
                FROM public.price_revisions
                WHERE prior_symbol = 'DEFINER.AU'
                """
            )
            recorded_by, prior_close, replacement_close = cur.fetchone()
            assert (prior_close, replacement_close) == (
                Decimal("10.000000"),
                Decimal("6.250000"),
            )
            # The load-bearing half: the ledger does not name the assumed role.
            assert recorded_by != role
            assert recorded_by == session_user
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute("RESET ROLE")
                _drop_role_if_exists(cur, role)
        finally:
            # Inside its own finally: a cleanup failure must not also leak the
            # connection on top of masking the original error.
            conn.close()


# Keep this last: it mutates the shared `prices` shape that every other case in
# this module depends on. It restores the shape in `finally`, but ordering it
# last means a failure mid-test cannot cascade into unrelated assertions.
def test_change_to_an_unledgered_column_fails_closed(migrated_dsn: str) -> None:
    """A column the ledger does not carry must break the write, not vanish.

    The trigger compares whole rows with ``to_jsonb`` but copies only the
    columns 0043 knows about. So a future column changing on its own is "not a
    no-op" (a revision is attempted) while producing prior and replacement
    payloads that are identical — which the payload-shape CHECK rejects.

    The alternative would be a revision row claiming nothing changed while the
    real change was silently lost. This is the subtlest claim in the migration
    and the one most likely to rot as `prices` grows columns.
    """
    conn = _connect(migrated_dsn)
    _insert_price(conn, "UNLEDGERED.AU")
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE public.prices ADD COLUMN drill_future_col TEXT")
            cur.execute("SELECT count(*) FROM public.price_revisions")
            before = cur.fetchone()[0]

            with pytest.raises(errors.CheckViolation, match="price_revisions_payload_shape"):
                cur.execute(
                    "UPDATE public.prices SET drill_future_col = 'changed' "
                    "WHERE symbol = 'UNLEDGERED.AU'"
                )

            cur.execute("SELECT count(*) FROM public.price_revisions")
            assert cur.fetchone()[0] == before, "fail-closed path still wrote a row"

            cur.execute(
                "SELECT drill_future_col FROM public.prices "
                "WHERE symbol = 'UNLEDGERED.AU'"
            )
            assert cur.fetchone()[0] is None, "the rejected UPDATE still mutated prices"
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE public.prices DROP COLUMN IF EXISTS drill_future_col"
                )
        finally:
            conn.close()
