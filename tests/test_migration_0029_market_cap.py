"""
Static guard for migration 0029 (widen market_cap to NUMERIC(24,6)).

The live-DB schema assertion (information_schema precision=24, scale=6) is a
post-apply check run via Supabase MCP — it needs the real DB and the migration
actually applied, so it cannot run in CI. This test instead pins the migration
FILE's content: that it widens BOTH base market_cap columns (the hidden
`universe.market_cap` is easy to miss), guarding against accidental edits.

Import-light (reads the .sql only) — runs everywhere, no DB, no heavy deps.
"""
from __future__ import annotations

import re
from pathlib import Path

_MIGRATION = (
    Path(__file__).resolve().parent.parent
    / "migrations"
    / "0029_widen_market_cap_columns.sql"
)


def _sql() -> str:
    return _MIGRATION.read_text()


def test_migration_0029_exists() -> None:
    assert _MIGRATION.is_file(), f"missing {_MIGRATION}"


def test_widens_fundamentals_market_cap_to_24_6() -> None:
    assert re.search(
        r"ALTER\s+TABLE\s+fundamentals\s+ALTER\s+COLUMN\s+market_cap\s+TYPE\s+NUMERIC\(24,6\)",
        _sql(), re.IGNORECASE,
    ), "0029 must widen fundamentals.market_cap to NUMERIC(24,6)"


def test_widens_universe_market_cap_to_24_6() -> None:
    # The hidden second column: universe.market_cap is fed from
    # fundamentals.market_cap by propagate_market_cap_to_universe and would
    # overflow on write if left at NUMERIC(18,6).
    assert re.search(
        r"ALTER\s+TABLE\s+universe\s+ALTER\s+COLUMN\s+market_cap\s+TYPE\s+NUMERIC\(24,6\)",
        _sql(), re.IGNORECASE,
    ), "0029 must ALSO widen universe.market_cap to NUMERIC(24,6)"


def test_does_not_narrow_scale() -> None:
    # Scale must stay 6 (precision-only growth is value-preserving). No (24,N!=6).
    assert "NUMERIC(24,6)" in _sql()
    assert not re.search(r"NUMERIC\(24,(?!6\))", _sql())


def test_drops_and_recreates_dependent_view_with_grants() -> None:
    # universe.market_cap is referenced by the view public.stock_universe, so the
    # ALTER must be bracketed by a DROP + CREATE of that view (Postgres refuses the
    # ALTER otherwise) and the view's grants restored. Guard against a future edit
    # that drops the view-restoration and breaks the apply or strips API access.
    sql = _sql()
    assert re.search(r"DROP\s+VIEW\s+IF\s+EXISTS\s+public\.stock_universe", sql, re.IGNORECASE)
    assert re.search(r"CREATE\s+VIEW\s+public\.stock_universe", sql, re.IGNORECASE)
    assert re.search(
        r"GRANT\s+ALL\s+ON\s+public\.stock_universe\s+TO\s+anon,\s*authenticated,\s*service_role",
        sql, re.IGNORECASE,
    )
