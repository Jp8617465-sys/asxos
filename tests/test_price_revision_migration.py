"""Static safety contract for migration 0043 price-revision containment.

The migration is intentionally not applied in CI, so these tests pin the
load-bearing PostgreSQL design: same-transaction trigger capture, complete
OLD/NEW price values, delete tombstones, no-op idempotency, append-only history,
and an explicit block on unobservable TRUNCATE operations.
"""
from __future__ import annotations

import re
from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "migrations"
    / "0043_price_revisions.sql"
)
_PRICE_FIELDS = ("symbol", "dt", "open", "high", "low", "close", "volume", "adj_close")


def _sql() -> str:
    return _MIGRATION.read_text()


def _normalised_sql() -> str:
    without_comments = re.sub(r"--.*$", "", _sql(), flags=re.MULTILINE)
    return re.sub(r"\s+", " ", without_comments).strip()


def _function_body(name: str) -> str:
    match = re.search(
        rf"CREATE\s+OR\s+REPLACE\s+FUNCTION\s+(?:public\.)?{name}\(\).*?\$\$(.*?)\$\$",
        _sql(),
        flags=re.IGNORECASE | re.DOTALL,
    )
    assert match is not None, f"missing function {name}"
    return match.group(1)


def test_migration_0043_exists_and_is_transactional() -> None:
    assert _MIGRATION.is_file()
    sql = _normalised_sql()
    assert sql.startswith("BEGIN;")
    assert sql.endswith("COMMIT;")
    assert "0042" in _sql() and "reserved" in _sql()


def test_revision_ledger_preserves_typed_prior_and_replacement_rows() -> None:
    sql = _normalised_sql()
    assert "CREATE TABLE public.price_revisions" in sql

    for prefix in ("prior", "replacement"):
        assert re.search(rf"{prefix}_symbol\s+TEXT", sql, re.IGNORECASE)
        assert re.search(rf"{prefix}_dt\s+DATE", sql, re.IGNORECASE)
        for field in ("open", "high", "low", "close", "adj_close"):
            assert re.search(
                rf"{prefix}_{field}\s+NUMERIC\(18,6\)",
                sql,
                re.IGNORECASE,
            )
        assert re.search(rf"{prefix}_volume\s+BIGINT", sql, re.IGNORECASE)

    for identity_column in (
        "revision_id",
        "recorded_at",
        "transaction_id",
        "recorded_by",
        "recorded_application",
    ):
        assert identity_column in sql


def test_price_trigger_captures_old_and_new_values_after_mutation() -> None:
    sql = _normalised_sql()
    assert re.search(
        r"CREATE TRIGGER prices_revision_capture "
        r"AFTER UPDATE OR DELETE ON public\.prices "
        r"FOR EACH ROW EXECUTE FUNCTION public\._capture_price_revision\(\)",
        sql,
        re.IGNORECASE,
    )

    body = _function_body("_capture_price_revision")
    for field in _PRICE_FIELDS:
        assert f"OLD.{field}" in body
        assert f"NEW.{field}" in body
    assert "pg_current_xact_id()" in body
    assert "clock_timestamp()" in body


def test_no_op_updates_are_idempotent_and_deletes_are_tombstoned() -> None:
    body = re.sub(r"\s+", " ", _function_body("_capture_price_revision"))
    assert re.search(
        r"IF to_jsonb\(OLD\) IS NOT DISTINCT FROM to_jsonb\(NEW\) "
        r"THEN RETURN NEW;",
        body,
        re.IGNORECASE,
    )
    assert "IF TG_OP = 'DELETE'" in body
    assert re.search(
        r"VALUES \( 'delete', .*? NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,",
        body,
        re.IGNORECASE,
    )


def test_revision_history_is_append_only_and_prices_cannot_be_truncated() -> None:
    sql = _normalised_sql()
    assert re.search(
        r"CREATE TRIGGER price_revisions_append_only "
        r"BEFORE UPDATE OR DELETE OR TRUNCATE ON public\.price_revisions "
        r"FOR EACH STATEMENT EXECUTE FUNCTION public\._reject_price_history_loss\(\)",
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        r"CREATE TRIGGER prices_reject_untracked_truncate "
        r"BEFORE TRUNCATE ON public\.prices "
        r"FOR EACH STATEMENT EXECUTE FUNCTION public\._reject_price_history_loss\(\)",
        sql,
        re.IGNORECASE,
    )
    assert "RAISE EXCEPTION" in _function_body("_reject_price_history_loss")


def test_capture_function_is_hardened_and_migration_has_no_backfill() -> None:
    sql = _normalised_sql()
    assert re.search(
        r"_capture_price_revision\(\).*?LANGUAGE plpgsql "
        r"SECURITY DEFINER SET search_path = pg_catalog, public",
        sql,
        re.IGNORECASE,
    )

    # This containment begins prospectively. It must not rewrite existing price
    # data or pretend to recover revisions already lost before migration 0043.
    assert not re.search(
        r"\b(?:UPDATE|DELETE FROM|TRUNCATE|ALTER TABLE)\s+(?:public\.)?prices\b",
        sql,
        re.IGNORECASE,
    )
    assert not re.search(r"\bFROM\s+(?:public\.)?prices\b", sql, re.IGNORECASE)
