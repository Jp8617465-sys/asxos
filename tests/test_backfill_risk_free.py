"""Pins on the risk-free point-in-time backfill (issue #301).

The gap this closes was not a slow backtest, it was no backtest: with no
risk-free history the valuation model could not be replayed at any historical
cutoff, so it could not be validated against a realised return at all. These
tests pin the properties that keep the replacement honest — that a backfill
writing nothing is never reported as success, that a truncated series is
detected rather than passed off as "the publisher had no data", and that the
series id is derived from `capm.RISK_FREE_SERIES` rather than copied.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jobs"))

import backfill_risk_free as job  # noqa: E402

from asxos.domain.valuation import capm  # noqa: E402

WORKFLOW = (ROOT / ".github/workflows/risk-free-backfill.yml").read_text()
MIGRATION = (ROOT / "migrations/0058_risk_free_pit.sql").read_text()


def _obs(d: str, value: str | None) -> SimpleNamespace:
    return SimpleNamespace(date=date.fromisoformat(d), value=None if value is None else Decimal(value))


class _FakeClient:
    def __init__(self, observations: list[SimpleNamespace]) -> None:
        self._observations = observations
        self.closed = False
        self.call: dict[str, object] = {}

    async def get_series(self, series_id: str, **kwargs: object) -> list[SimpleNamespace]:
        self.call = {"series_id": series_id, **kwargs}
        return self._observations

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def run_job(monkeypatch):
    """Run the job's main() with a fake FRED client and argv."""

    def _run(observations: list[SimpleNamespace], argv: list[str]) -> _FakeClient:
        client = _FakeClient(observations)
        monkeypatch.setattr(job, "get_fred_client", lambda: client)
        monkeypatch.setattr(sys, "argv", ["backfill_risk_free.py", *argv])
        import asyncio

        asyncio.run(job.main())
        return client

    return _run


def test_series_id_is_derived_from_capm_not_copied() -> None:
    """Two hardcoded copies of a series id is how the two drift apart."""
    assert capm.RISK_FREE_SERIES == f"FRED {job.FRED_SERIES_ID}"
    assert job.FRED_SERIES_ID == "IRLTLT01AUM156N"


def test_dry_run_fetches_but_opens_no_database_connection(run_job, monkeypatch) -> None:
    def _explode() -> None:
        raise AssertionError("dry run must not open a pool")

    monkeypatch.setattr(job, "init_pool", _explode)
    client = run_job([_obs("2025-01-01", "4.31"), _obs("2025-02-01", "4.42")], ["--dry-run"])

    assert client.call["series_id"] == "IRLTLT01AUM156N"
    assert client.call["sort_order"] == "asc"
    assert client.closed


def test_all_missing_observations_is_a_failure_not_a_quiet_success(run_job) -> None:
    """FRED returns '.' for missing. A backfill that wrote nothing is not a backfill."""
    with pytest.raises(RuntimeError, match="no usable observations"):
        run_job([_obs("2025-01-01", None), _obs("2025-02-01", None)], ["--dry-run"])


def test_no_observations_at_all_is_a_failure(run_job) -> None:
    with pytest.raises(RuntimeError, match="no usable observations"):
        run_job([], ["--dry-run"])


def test_a_truncated_series_is_detected_rather_than_silently_short(run_job) -> None:
    """Exactly the limit means the tail is missing, which looks like absent data."""
    full = [_obs("2025-01-01", "4.31")] * job.OBSERVATION_LIMIT
    with pytest.raises(RuntimeError, match="truncated"):
        run_job(full, ["--dry-run"])


def test_observation_start_is_passed_through(run_job) -> None:
    client = run_job([_obs("2024-06-01", "4.10")], ["--start", "2024-06-01", "--dry-run"])
    assert client.call["observation_start"] == "2024-06-01"


def test_upsert_overwrites_a_revision_and_no_ops_an_unchanged_print() -> None:
    """FRED revises. A series that cannot take a revision keeps a stale print."""
    assert "ON CONFLICT (series, as_of) DO UPDATE" in job.SQL_UPSERT
    assert "ingested_at = NOW()" in job.SQL_UPSERT
    # The guard that makes a re-run of unchanged data a no-op rather than
    # churning ingested_at on every row.
    assert "IS DISTINCT FROM EXCLUDED.yield_pct" in job.SQL_UPSERT


def test_the_job_writes_only_the_risk_free_table() -> None:
    """It must not touch market_context, valuation output, or the research store.

    This inspects the SQL the job actually executes, not the file text: the
    module docstring names those tables precisely to say it leaves them alone,
    and a grep over prose would fail on its own explanation.
    """
    executed_sql = " ".join(
        value for name, value in vars(job).items()
        if name.startswith("SQL_") and isinstance(value, str)
    ).lower()

    assert "risk_free_rates" in executed_sql
    for forbidden in (
        "market_context",
        "valuation_runs",
        "research_runs",
        "holding_lots",
        "theses",
        "signals",
    ):
        assert forbidden not in executed_sql, forbidden


def test_migration_stores_percent_and_keeps_the_series_per_row() -> None:
    assert "PRIMARY KEY (series, as_of)" in MIGRATION
    assert "yield_pct" in MIGRATION
    assert "NUMERIC(18,6)" in MIGRATION
    # Overwritable by design — the opposite of the append-only trigger tables.
    assert "CREATE TRIGGER" not in MIGRATION


def test_lane_is_dispatch_only_defaults_to_dry_run_and_runs_from_main() -> None:
    assert "workflow_dispatch:" in WORKFLOW
    trigger = WORKFLOW.split("concurrency:", 1)[0]
    assert "\n  schedule:" not in trigger
    assert "\n  push:" not in trigger
    assert "\n  pull_request:" not in trigger

    dry_run = WORKFLOW.split("dry_run:", 1)[1].split("type: boolean", 1)[0]
    assert "default: true" in dry_run

    assert "ref: refs/heads/main" in WORKFLOW
    assert "permissions:\n  contents: read" in WORKFLOW

    secrets_used = {
        fragment.split("}}", 1)[0].strip() for fragment in WORKFLOW.split("${{ secrets.")[1:]
    }
    assert secrets_used == {"DATABASE_URL", "FRED_API_KEY"}, secrets_used
