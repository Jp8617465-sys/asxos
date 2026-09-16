"""S3 — the daily arbi-declared paper book: writer, gate reads, job and workflow step.

The paper table is still named by exactly one module (`decision_engine/paper_book.py`,
pinned by `tests/test_paper_book_c1.py`); the job and the sign-off gate come through it.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml

import jobs.snapshot_paper_book as job_mod
from asxos.config import settings
from asxos.domain.decision_engine import paper_book
from asxos.domain.portfolio.paper_trade import has_enough_paper_weeks

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 17)


class FakeConn:
    def __init__(self, *, insert_status: str = "INSERT 0 1") -> None:
        self.insert_status = insert_status
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.latest: dict[str, Any] | None = None

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return self.insert_status

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        return self.latest

    async def fetch(self, query: str, *args: object) -> list[Any]:
        return []

    async def fetchval(self, query: str, *args: object) -> Any:
        return 0


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")
    monkeypatch.setenv(paper_book.PAPER_CAPITAL_ENV, "25000")


# --- declared capital ----------------------------------------------------------


def test_declared_capital_is_read_from_the_env_and_quantised() -> None:
    assert paper_book.declared_paper_capital() == D("25000.000000")


@pytest.mark.parametrize("raw", ["", "   ", "0", "-5"])
def test_declared_capital_refuses_absent_or_non_positive(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv(paper_book.PAPER_CAPITAL_ENV, raw)
    with pytest.raises(RuntimeError, match=paper_book.PAPER_CAPITAL_ENV):
        paper_book.declared_paper_capital()


# --- writer --------------------------------------------------------------------


async def test_writer_appends_an_all_cash_labelled_paper_row() -> None:
    conn = FakeConn()
    assert await paper_book.write_daily_paper_snapshot(conn, as_of=AS_OF, capital_aud=D("25000")) is True
    (query, args), = conn.executed
    assert "INSERT INTO paper_book_snapshots" in query and "ON CONFLICT (snapshot_id) DO NOTHING" in query
    assert args == (
        "paper-daily-2026-09-17", AS_OF, paper_book.PAPER_DAILY_LABEL,
        D("25000.000000"), D("0"), D("25000.000000"), 0,
    )
    assert "paper" in paper_book.PAPER_DAILY_LABEL and "arbi-declared" in paper_book.PAPER_DAILY_LABEL


async def test_writer_reports_a_same_day_re_run_as_not_written() -> None:
    conn = FakeConn(insert_status="INSERT 0 0")
    assert await paper_book.write_daily_paper_snapshot(conn, as_of=AS_OF, capital_aud=D("25000")) is False


async def test_writer_is_behind_the_personal_use_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE")
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        await paper_book.write_daily_paper_snapshot(FakeConn(), as_of=AS_OF, capital_aud=D("25000"))


async def test_writer_refuses_non_positive_capital() -> None:
    with pytest.raises(RuntimeError, match="positive"):
        await paper_book.write_daily_paper_snapshot(FakeConn(), as_of=AS_OF, capital_aud=D("0"))


async def test_latest_snapshot_id_reads_the_newest_at_or_before() -> None:
    conn = FakeConn()
    conn.latest = {"snapshot_id": "paper-daily-2026-09-16"}
    assert await paper_book.latest_paper_snapshot_id(conn, as_of=AS_OF) == "paper-daily-2026-09-16"
    conn.latest = None
    assert await paper_book.latest_paper_snapshot_id(conn, as_of=AS_OF) is None
    assert "ORDER BY as_of DESC, ingested_at DESC LIMIT 1" in paper_book.SQL_LATEST_PAPER_SNAPSHOT_ID


# --- the sign-off gate is reachable ----------------------------------------------


def _gate_conn(*, matured: int, dates: list[date]) -> AsyncMock:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=matured)
    conn.fetch = AsyncMock(return_value=[{"as_of": d} for d in dates])
    return conn


async def test_gate_passes_on_four_weeks_of_daily_paper_snapshots() -> None:
    """Item 9 (session-handoff-2026-09-14-3): the gate counted a deleted cron and could never be True."""
    today = date(2026, 10, 15)
    daily = [today - timedelta(days=i) for i in range(0, 29)]
    conn = _gate_conn(matured=1, dates=sorted(daily))
    assert await has_enough_paper_weeks(conn, today=today) is True
    assert "paper_book_snapshots" in conn.fetchval.await_args.args[0]
    assert "paper_book_snapshots" in conn.fetch.await_args.args[0]
    assert "job_runs" not in conn.fetch.await_args.args[0]


async def test_gate_fails_on_a_three_week_blackout_of_paper_snapshots() -> None:
    today = date(2026, 10, 15)
    conn = _gate_conn(matured=1, dates=[today - timedelta(days=28), today])
    assert await has_enough_paper_weeks(conn, today=today) is False


# --- job -------------------------------------------------------------------------


class FakeMonitor:
    def __init__(self, **kwargs: object) -> None:
        self.rows_written = 0
        self.note: str | None = None

    async def __aenter__(self) -> FakeMonitor:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


def _patched(conn: FakeConn) -> Any:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    class _Clock:
        @staticmethod
        def today() -> date:
            return AS_OF

    return (
        patch.object(job_mod, "acquire", side_effect=_acquire),
        patch.object(job_mod, "init_pool", AsyncMock()),
        patch.object(job_mod, "close_pool", AsyncMock()),
        patch.object(job_mod, "JobMonitor", FakeMonitor),
        patch.object(job_mod, "clock", _Clock),
    )


async def test_job_writes_one_row_for_today() -> None:
    conn = FakeConn()
    patches = _patched(conn)
    for p in patches:
        p.start()
    try:
        await job_mod.main()
    finally:
        for p in patches:
            p.stop()
    assert len(conn.executed) == 1 and conn.executed[0][1][0] == "paper-daily-2026-09-17"


async def test_job_refuses_without_the_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE")
    with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE"):
        await job_mod.main()


async def test_job_refuses_without_a_declared_capital(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(paper_book.PAPER_CAPITAL_ENV)
    with pytest.raises(RuntimeError, match=paper_book.PAPER_CAPITAL_ENV):
        await job_mod.main()


# --- workflow ----------------------------------------------------------------------


def test_daily_brief_runs_the_paper_snapshot_after_the_live_one_with_a_declared_capital() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/daily-brief.yml").read_text())
    job = next(iter(wf["jobs"].values()))
    names = [s.get("name") for s in job["steps"]]
    assert names.index("Snapshot paper book") == names.index("Snapshot portfolio") + 1
    assert job["env"]["ASXOS_PAPER_CAPITAL_AUD"] == "25000"
    assert job["env"]["ASXOS_PERSONAL_USE"] == "1"
    assert settings.healthcheck_url_snapshot_paper_book == ""
