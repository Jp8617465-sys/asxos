"""F-E2E fixture rows: marked by id prefix, listable, inert, never removed.

James's ruling of 2026-09-07: theme/candidate rows written for the first
positive control are marked `f-e2e-`, stay `data_mode='real'` (the data is
live, only the purpose is fixture), and are **retained** — `theme_versions`
and `candidate_snapshots` are append-only (`migrations/0051` lines 61-62 and
93-94) and that guarantee is not weakened for them.

What must hold is therefore not removability but inertness: no live-book
aggregation may read them.
"""
from __future__ import annotations

import re
from pathlib import Path

from asxos.cli.candidates import FIXTURE_ID_PREFIX
from asxos.domain.decision_engine.portfolio_state import (
    SQL_CANDIDATES,
    SQL_CLOSE,
    SQL_FX,
    SQL_HOLDINGS,
    SQL_PROFILE,
    SQL_SNAPSHOT,
)

ROOT = Path(__file__).resolve().parent.parent

# The queries that compute the live book: capital, cash, exposure, weights.
# These are what a size is derived from, so these are what must never see a
# fixture row.
LIVE_BOOK_AGGREGATION_SQL = {
    "SQL_SNAPSHOT": SQL_SNAPSHOT,
    "SQL_HOLDINGS": SQL_HOLDINGS,
    "SQL_CLOSE": SQL_CLOSE,
    "SQL_FX": SQL_FX,
    "SQL_PROFILE": SQL_PROFILE,
}

FIXTURE_TABLES = ("theme_versions", "candidate_snapshots", "paper_book_snapshots")

# The listing query of record — quoted in the PR and the ADR so the rows can be
# found by anyone later without reading this file.
FIXTURE_LISTING_SQL = """
SELECT 'theme_versions' AS table_name, theme_version_id AS id, theme_code AS subject,
       as_of, data_mode, created_at
FROM theme_versions WHERE theme_version_id LIKE 'f-e2e-%'
UNION ALL
SELECT 'candidate_snapshots', candidate_id, symbol, as_of, data_mode, created_at
FROM candidate_snapshots WHERE candidate_id LIKE 'f-e2e-%'
ORDER BY table_name, id;
"""


def test_no_live_book_aggregation_reads_fixture_rows() -> None:
    """The live book is computed from tables that hold no fixture rows."""
    offenders = []
    for name, sql in LIVE_BOOK_AGGREGATION_SQL.items():
        for table in FIXTURE_TABLES:
            if re.search(rf"\b(?:FROM|JOIN)\s+{table}\b", sql, re.IGNORECASE):
                offenders.append(f"{name} reads {table}")
    assert offenders == [], offenders


def test_positive_control_selection_is_the_only_reader_of_candidate_snapshots() -> None:
    """Candidate rows feed control SELECTION, never the book they are sized against.

    `SQL_CANDIDATES` is deliberately excluded from the aggregation set above:
    reading candidates to pick a positive control is not computing a portfolio.
    This pins that separation so a future edit cannot quietly join the two.
    """
    assert "candidate_snapshots" in SQL_CANDIDATES
    for live_table in ("portfolio_daily_snapshots", "current_holdings", "holding_lots"):
        assert live_table not in SQL_CANDIDATES


def test_fixture_rows_are_listable_by_id_prefix() -> None:
    assert FIXTURE_ID_PREFIX == "f-e2e-"
    assert "theme_version_id LIKE 'f-e2e-%'" in FIXTURE_LISTING_SQL
    assert "candidate_id LIKE 'f-e2e-%'" in FIXTURE_LISTING_SQL


def test_the_fixture_tables_remain_append_only() -> None:
    """The ruling retains fixture rows; the guarantee that keeps them must stand."""
    sql = (ROOT / "migrations" / "0051_theme_candidates.sql").read_text()
    assert "BEFORE UPDATE OR DELETE ON theme_versions" in sql
    assert "BEFORE UPDATE OR DELETE ON candidate_snapshots" in sql

    # And no later migration may add a delete path for them.
    for path in sorted((ROOT / "migrations").glob("*.sql")):
        text = path.read_text()
        for table in ("theme_versions", "candidate_snapshots"):
            assert not re.search(rf"\bDELETE\s+FROM\s+{table}\b", text, re.IGNORECASE), (
                f"{path.name} adds a delete path for {table}"
            )
            assert not re.search(
                rf"\bDROP\s+TRIGGER\b.*{table}", text, re.IGNORECASE
            ), f"{path.name} drops the append-only trigger on {table}"


def test_fixture_prefix_changes_identity_not_data_mode() -> None:
    """A fixture row is a different identity, not a production row wearing a label.

    The prefix is inside the id, and the id is inside the content hash, so a
    fixture build and a production build of the same day are two distinct
    content-addressed artifacts. `data_mode` stays 'real' because the inputs
    are live.
    """
    from asxos.cli import candidates as candidates_mod

    source = Path(candidates_mod.__file__).read_text()
    assert 'prefix = FIXTURE_ID_PREFIX if fixture else ""' in source
    # Mentioning data_mode in help text is fine; assigning it is not.
    assert re.search(r"data_mode\s*=", source) is None, (
        "the fixture flag must not set data_mode — the inputs are live"
    )
