"""Valuation persistence: statement shape, idempotency, registration drift, the SQL screen."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal as D
from typing import Any

import pytest

from asxos.domain.valuation import repository, sweep
from asxos.domain.valuation.contracts import ValuationRun
from asxos.domain.valuation.inputs import assert_valuation_sql_admissible
from asxos.domain.valuation.preregistration import load_bundled_preregistration
from asxos.domain.valuation.universe import MarketInputs, UniverseRow

PREREG = load_bundled_preregistration()
MARKET = MarketInputs(D("0.04831"), date(2026, 9, 15), D("0.7134"), date(2026, 9, 14))
KE = sweep.ke_band_for(MARKET, PREREG)
CUTOFF = datetime(2026, 9, 16, 1, 0, tzinfo=UTC)


def _run(symbol: str, roe: D = D("0.12")) -> ValuationRun:
    row = UniverseRow(
        symbol=symbol, pit_as_of=date(2026, 6, 30), pit_knowledge_date=date(2026, 8, 30),
        book_value_ps=D("10"), roe=roe, eps_ttm=D("1"), dividend_ttm=D("0.5"),
        franking_avg_pct=D("100"), currency="AUD", roe_average=roe, roe_periods=3,
        last_close_dt=date(2026, 9, 14), last_close=D("8"),
    )
    return sweep.value_row(row, market=MARKET, ke=KE, prereg=PREREG, cutoff=CUTOFF, created_at=CUTOFF)


class FakeConn:
    """Records every statement; `conflicts` names run_ids the store already holds."""

    def __init__(self, *, prereg_hash: str | None = None, conflicts: set[str] | None = None) -> None:
        self.prereg_hash = prereg_hash
        self.conflicts = conflicts or set()
        self.executed: list[tuple[str, tuple[object, ...]]] = []
        self.transactions = 0
        self.fetch_rows: list[dict[str, Any]] = []
        self.count_row: dict[str, Any] | None = None
        self.symbol_row: dict[str, Any] | None = None

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((query, args))
        if "INSERT INTO valuation_runs" in query and args[0] in self.conflicts:
            return "INSERT 0 0"
        return "INSERT 0 1"

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        if "valuation_scenario_preregistrations" in query:
            return None if self.prereg_hash is None else {"content_hash": self.prereg_hash}
        if "count(*)" in query:
            return self.count_row
        if "symbol = $1" in query:
            return self.symbol_row
        return None

    async def fetch(self, query: str, *args: object) -> list[dict[str, Any]]:
        return self.fetch_rows

    def transaction(self) -> Any:
        self.transactions += 1

        @asynccontextmanager
        async def _tx() -> Any:
            yield

        return _tx()


# --- registration -------------------------------------------------------------


async def test_ensure_preregistered_inserts_when_absent() -> None:
    conn = FakeConn()
    assert await repository.ensure_preregistered(conn, PREREG) is True
    (query, args), = conn.executed
    assert "INSERT INTO valuation_scenario_preregistrations" in query
    assert args[0] == PREREG.preregistration_id and args[1] == PREREG.content_hash
    payload = json.loads(str(args[5]))
    assert payload["content_hash"] == PREREG.content_hash
    assert payload["preregistration_id"] == PREREG.preregistration_id


async def test_ensure_preregistered_is_a_no_op_on_the_same_hash() -> None:
    conn = FakeConn(prereg_hash=PREREG.content_hash)
    assert await repository.ensure_preregistered(conn, PREREG) is False
    assert conn.executed == []


async def test_ensure_preregistered_refuses_drift() -> None:
    conn = FakeConn(prereg_hash="0" * 64)
    with pytest.raises(repository.PreregistrationDriftError, match="NEW id"):
        await repository.ensure_preregistered(conn, PREREG)
    assert conn.executed == []


# --- runs ---------------------------------------------------------------------


async def test_save_runs_writes_every_row_in_bounded_transactions() -> None:
    conn = FakeConn()
    runs = [_run(f"S{i}.AU") for i in range(5)]
    progress: list[int] = []
    written = await repository.save_runs(conn, runs, batch_size=2, on_rows_committed=progress.append)
    assert written == 5
    assert conn.transactions == 3
    assert progress == [2, 4, 5]
    query, args = conn.executed[0]
    assert "ON CONFLICT (run_id) DO NOTHING" in query
    run = runs[0]
    assert args[:4] == (run.run_id, run.content_hash, run.symbol, run.as_of)
    assert args[9] == "valued" and args[10] == run.value_per_share
    assert args[12] == PREREG.preregistration_id
    payload = json.loads(str(args[13]))
    assert payload["run_id"] == run.run_id and payload["terminal_convention"] == "zero_excess"


async def test_save_runs_counts_only_rows_actually_inserted() -> None:
    runs = [_run("A.AU"), _run("B.AU"), _run("C.AU")]
    conn = FakeConn(conflicts={runs[1].run_id})
    assert await repository.save_runs(conn, runs) == 2


async def test_save_runs_rejects_a_zero_batch() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        await repository.save_runs(FakeConn(), [], batch_size=0)


def test_inserted_parses_the_status_tag_and_refuses_garbage() -> None:
    assert repository._inserted("INSERT 0 1") == 1
    assert repository._inserted("INSERT 0 0") == 0
    with pytest.raises(RuntimeError, match="status tag"):
        repository._inserted("nonsense")


async def test_blocked_rows_persist_with_a_null_value() -> None:
    conn = FakeConn()
    blocked = _run("L.AU", roe=D("-0.2"))
    assert blocked.outcome == "blocked"
    await repository.save_runs(conn, [blocked])
    _, args = conn.executed[0]
    assert args[9] == "blocked" and args[10] is None


async def test_count_runs_for_reads_the_pair() -> None:
    conn = FakeConn()
    conn.count_row = {"n": 1880, "valued": 572}
    assert await repository.count_runs_for(conn, date(2026, 9, 16)) == (1880, 572)
    conn.count_row = None
    assert await repository.count_runs_for(conn, date(2026, 9, 16)) == (0, 0)


async def test_latest_runs_reconstructs_from_payload_only() -> None:
    run = _run("CBA.AU")
    conn = FakeConn()
    conn.fetch_rows = [{"payload": json.dumps(run.model_dump(mode="json"))}, {"payload": run.model_dump(mode="json")}]
    loaded = await repository.latest_runs(conn, as_of=date(2026, 9, 20))
    assert loaded == [run, run]


# --- the SQL screen -------------------------------------------------------------


def test_screen_admits_a_statement_local_cte_but_not_a_foreign_table() -> None:
    assert_valuation_sql_admissible("WITH pit AS (SELECT 1 FROM prices) SELECT * FROM pit")
    with pytest.raises(AssertionError, match="inadmissible table: pit"):
        assert_valuation_sql_admissible("SELECT * FROM pit")
    with pytest.raises(AssertionError, match="forbidden token"):
        assert_valuation_sql_admissible("WITH s AS (SELECT 1 FROM signals) SELECT * FROM s")
    with pytest.raises(AssertionError, match="inadmissible table: model_versions"):
        assert_valuation_sql_admissible("SELECT 1 FROM model_versions")


def test_every_repository_statement_passes_the_screen() -> None:
    for sql in (
        repository.SQL_PREREG_BY_ID,
        repository.SQL_INSERT_PREREG,
        repository.SQL_INSERT_RUN,
        repository.SQL_COUNT_RUNS_FOR_AS_OF,
        repository.SQL_LATEST_RUNS,
        repository.SQL_LATEST_RUN_FOR_SYMBOL,
    ):
        assert_valuation_sql_admissible(sql)


async def test_latest_run_for_symbol_reads_one_payload_or_none() -> None:
    run = _run("CBA.AU")
    conn = FakeConn()
    conn.symbol_row = {"payload": json.dumps(run.model_dump(mode="json"))}
    assert await repository.latest_run_for_symbol(conn, symbol="CBA.AU", as_of=date(2026, 9, 20)) == run
    conn.symbol_row = None
    assert await repository.latest_run_for_symbol(conn, symbol="CBA.AU", as_of=date(2026, 9, 20)) is None
    assert_valuation_sql_admissible(repository.SQL_LATEST_RUN_FOR_SYMBOL)


def test_latest_run_sql_shares_sweep_eligibility_and_cannot_resurface_an_excluded_kind() -> None:
    """#359 §3: a LIC valued on 2026-09-16 stays in the store after A-49, but
    must not be the current residual-income value. The reader joins `universe`
    on the same predicate the sweep uses; dropping either the join or the
    kind filter re-opens the hole. Sentinel blocked rows were the other
    option — they would still be a run the builder cites as evidence.
    """
    from asxos.domain.valuation.universe import SQL_RESIDUAL_INCOME_ELIGIBLE, SQL_UNIVERSE_INPUTS

    assert SQL_RESIDUAL_INCOME_ELIGIBLE in SQL_UNIVERSE_INPUTS
    for sql in (repository.SQL_LATEST_RUNS, repository.SQL_LATEST_RUN_FOR_SYMBOL):
        assert "JOIN universe u ON u.symbol = v.symbol" in sql
        assert SQL_RESIDUAL_INCOME_ELIGIBLE in sql
        assert "v.method = 'residual_income'" in sql
        assert_valuation_sql_admissible(sql)
    # Mutation: a reader that only DISTINCT ON symbol (the pre-fix shape)
    # would still return AUI.AU's 19.74. The join is the gate.
    assert "FROM valuation_runs\nWHERE as_of" not in repository.SQL_LATEST_RUNS
    assert "WHERE symbol = $1 AND as_of" not in repository.SQL_LATEST_RUN_FOR_SYMBOL
