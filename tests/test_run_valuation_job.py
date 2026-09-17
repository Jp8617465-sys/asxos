"""jobs/run_valuation.py — the sweep end to end on a mocked connection, and its workflow step."""
from __future__ import annotations

import ast
import logging
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal as D
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

import jobs.run_valuation as job_mod
from asxos.config import settings
from asxos.domain.valuation import universe

CUTOFF = datetime(2026, 9, 19, 16, 3, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


def _record(symbol: str, **overrides: object) -> dict[str, Any]:
    base: dict[str, Any] = {
        "symbol": symbol,
        "pit_as_of": date(2026, 6, 30),
        "pit_knowledge_date": date(2026, 8, 30),
        "book_value_ps": D("10"),
        "roe": D("0.12"),
        "eps_ttm": D("1"),
        "dividend_ttm": D("0.5"),
        "franking_avg_pct": D("100"),
        "currency": "AUD",
        "roe_average": D("0.11"),
        "roe_periods": 3,
        "last_close_dt": date(2026, 9, 18),
        "last_close": D("8"),
    }
    base.update(overrides)
    return base


class FakeConn:
    def __init__(self, records: list[dict[str, Any]], *, rf: D | None = D("4.831"), fx: D | None = D("0.7134"),
                 insert_status: str = "INSERT 0 1", stored: tuple[int, int] = (0, 0)) -> None:
        self.records = records
        self.rf, self.fx = rf, fx
        self.insert_status = insert_status
        self.stored = stored
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.fetch_calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        return self.insert_status

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        if "valuation_scenario_preregistrations" in query:
            return None
        if "risk_free_rates" in query:
            # The point-in-time series (0058) replaced market_context_current as
            # ke's risk-free source. The row still arrives under the
            # aus_10y_yield key — the query aliases yield_pct to it — so only
            # the routing moved, not the shape load_market_inputs reads.
            return None if self.rf is None else {"as_of": date(2026, 9, 15), "aus_10y_yield": self.rf}
        if "fx_rates" in query:
            return None if self.fx is None else {"dt": date(2026, 9, 18), "rate": self.fx}
        if "count(*)" in query:
            return {"n": self.stored[0], "valued": self.stored[1]}
        return None

    async def fetch(self, query: str, *args: object, **kwargs: object) -> list[dict[str, Any]]:
        self.fetch_calls.append((query, args, kwargs))
        return self.records

    def transaction(self) -> Any:
        @asynccontextmanager
        async def _tx() -> Any:
            yield

        return _tx()


class FakeMonitor:
    def __init__(self) -> None:
        self.rows_written = 0
        self.note: str | None = None


def _patched(conn: FakeConn) -> Any:
    @asynccontextmanager
    async def _acquire() -> Any:
        yield conn

    return patch.object(job_mod, "acquire", side_effect=_acquire)


async def test_run_persists_the_registration_then_every_row() -> None:
    conn = FakeConn([_record("A.AU"), _record("B.AU", roe=D("-0.1")), _record("C.AU", pit_as_of=None, book_value_ps=None, roe=None)])
    monitor = FakeMonitor()
    with _patched(conn):
        counts = await job_mod.run(cutoff=CUTOFF, monitor=monitor, write_batch_size=2)
    assert counts == {"valued": 1, "roe_non_positive": 1, "pit_row_absent": 1}
    assert monitor.rows_written == 3 and monitor.note is None
    kinds = [q.split("INSERT INTO ")[1].split()[0] for q, _ in conn.executed]
    assert kinds == ["valuation_scenario_preregistrations"] + ["valuation_runs"] * 3
    # The universe read is parameterised on the cutoff date, the price window and the
    # registered ROE-average period count, and lifts the pool's 30 s command timeout.
    query, args, kwargs = conn.fetch_calls[0]
    assert "security_kind = 'au_equity'" in query
    assert args == (CUTOFF.date(), CUTOFF.date() - __import__("datetime").timedelta(days=universe.PRICE_WINDOW_DAYS), 3)
    assert kwargs == {"timeout": universe.UNIVERSE_QUERY_TIMEOUT_S}
    # Row shadows: as_of is the UTC cutoff date, value NULL on the blocked rows.
    run_args = [a for q, a in conn.executed if "valuation_runs" in q]
    assert [a[2] for a in run_args] == ["A.AU", "B.AU", "C.AU"]
    assert all(a[3] == CUTOFF.date() for a in run_args)
    assert [a[9] for a in run_args] == ["valued", "blocked", "blocked"]
    assert run_args[1][10] is None and run_args[0][10] is not None


async def test_run_hard_fails_when_nothing_is_valued() -> None:
    conn = FakeConn([_record("A.AU", roe=D("-1")), _record("B.AU", roe=None)])
    with _patched(conn), pytest.raises(RuntimeError, match="valued 0 of 2"):
        await job_mod.run(cutoff=CUTOFF, monitor=FakeMonitor(), write_batch_size=10)
    assert all("valuation_runs" not in q for q, _ in conn.executed)


async def test_run_hard_fails_on_an_empty_universe() -> None:
    with _patched(FakeConn([])), pytest.raises(RuntimeError, match="zero active au_equity rows"):
        await job_mod.run(cutoff=CUTOFF, monitor=FakeMonitor(), write_batch_size=10)


@pytest.mark.parametrize("missing,match", [("rf", "no risk-free rate"), ("fx", "no AUDUSD rate")])
async def test_run_hard_fails_without_a_market_input(missing: str, match: str) -> None:
    conn = FakeConn([_record("A.AU")], rf=None if missing == "rf" else D("4.831"), fx=None if missing == "fx" else D("0.7134"))
    with _patched(conn), pytest.raises(RuntimeError, match=match):
        await job_mod.run(cutoff=CUTOFF, monitor=FakeMonitor(), write_batch_size=10)


async def test_same_day_rerun_writes_nothing_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A benign no-op is logged and left OUT of the degraded channel.

    `monitor.note` is the degraded-partial-success marker
    (`asxos/jobs/utils/job_monitor.py:56-62`), and `check_cron_health` raises on
    every note it finds in a 36-hour window. A same-day re-run is the
    idempotency guard working exactly as designed, so putting it there turned
    the nightly watchdog red for a healthy run — observed 2026-09-17, run
    35165551435. `rows_written == 0` on a 'success' row plus the log line is
    the whole record, and it is enough.
    """
    conn = FakeConn([_record("A.AU")], insert_status="INSERT 0 0", stored=(1880, 572))
    monitor = FakeMonitor()
    with _patched(conn), caplog.at_level(logging.INFO, logger=job_mod.log.name):
        await job_mod.run(cutoff=CUTOFF, monitor=monitor, write_batch_size=10)
    assert monitor.rows_written == 0
    assert monitor.note is None
    assert (
        "same-day re-run: 0 rows written; 1880 rows (572 valued) already stored for 2026-09-19"
        in caplog.text
    )


def test_no_benign_branch_writes_the_degraded_note() -> None:
    """Bind the invariant to the source, not just to the one branch above.

    The only `monitor.note` assignment this job may ever carry is one that
    means "this run degraded". Today it carries none. If a future change adds
    one, this test fails and whoever adds it has to decide deliberately whether
    check_cron_health should page on it.

    Matches an ASSIGNMENT, not a mention — the module's own prose explains why
    the note is not used, and that prose must not trip the guard.
    """
    tree = ast.parse(Path(job_mod.__file__).read_text(encoding="utf-8"))
    assigned = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "note"
        and isinstance(node.ctx, ast.Store)
    ]
    assert assigned == [], (
        f"jobs/run_valuation.py assigns the degraded note at line(s) "
        f"{[n.lineno for n in assigned]} — check_cron_health will page on it"
    )


async def test_zero_written_and_zero_stored_is_a_failure_not_a_green_run() -> None:
    conn = FakeConn([_record("A.AU")], insert_status="INSERT 0 0", stored=(0, 0))
    with _patched(conn), pytest.raises(RuntimeError, match="did not land"):
        await job_mod.run(cutoff=CUTOFF, monitor=FakeMonitor(), write_batch_size=10)


def test_risk_free_is_read_as_a_percent_and_stored_as_a_fraction() -> None:
    """risk_free_rates.yield_pct is 4.831 (percent); Ke needs 0.04831.

    The percent-to-fraction conversion stayed in load_market_inputs when the
    source moved off market_context_current (0058), so it lives in one place
    rather than being re-derived at each reader.
    """

    async def check() -> None:
        conn = FakeConn([_record("A.AU")])
        market = await universe.load_market_inputs(conn, cutoff_date=CUTOFF.date())
        assert market.risk_free == D("0.04831")
        assert market.audusd == D("0.7134")

    import asyncio

    asyncio.run(check())


def test_weekly_research_runs_the_sweep_right_after_the_pit_derivation() -> None:
    wf = yaml.safe_load((ROOT / ".github/workflows/weekly-research.yml").read_text())
    names = [step.get("name") for step in wf["jobs"]["research"]["steps"]]
    assert names.index("Run valuation") == names.index("Derive fundamentals PIT") + 1
    step = next(s for s in wf["jobs"]["research"]["steps"] if s.get("name") == "Run valuation")
    assert step["run"] == "python jobs/run_valuation.py"


def test_healthcheck_slot_exists_for_the_job() -> None:
    assert settings.healthcheck_url_run_valuation == ""
