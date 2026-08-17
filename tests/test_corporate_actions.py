"""Tests for research-store corporate-actions ingestion.

No network, no DB. Heavy on the pure parse/transform helpers (where the real risk
lives — the "<float>%" franking format and "new/old" splits that the 2026-06-24 probe
surfaced), plus a light orchestrator test with faked client/conn.
"""
from __future__ import annotations

import asyncio
import importlib
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from asxos.ingestion import corporate_actions, financial_statements
from asxos.ingestion.corporate_actions import (
    parse_franking,
    parse_split_ratio,
    refresh_corporate_actions,
    to_dividend_rows,
    to_split_rows,
)

# ---------------------------------------------------------------------------
# parse_franking — the format the probe forced us to get right
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("100%", Decimal("100")),
    ("0%", Decimal("0")),
    ("25.03%", Decimal("25.03")),   # decimals are real (QBE)
    ("90.47%", Decimal("90.47")),   # (TLS)
    ("49%", Decimal("49")),
    (None, None),                   # undeclared -> NULL, NOT 0
    ("", None),
    ("   ", None),
    ("150%", None),                 # out of range -> NULL
    ("-5%", None),
    ("abc", None),
    ("100", Decimal("100")),        # tolerate a bare number
])
def test_parse_franking(raw, expected):
    assert parse_franking(raw) == expected


def test_parse_franking_null_is_not_zero():
    """The tax-material distinction: undeclared (None) must not collapse to 0%."""
    assert parse_franking(None) is None
    assert parse_franking("0%") == Decimal("0")


@pytest.mark.parametrize("raw", ["NaN%", "nan", "sNaN", "Infinity", "-Infinity", "inf"])
def test_parse_franking_rejects_decimal_specials(raw):
    """`Decimal("NaN")` parses fine but ANY comparison against it signals
    InvalidOperation — so the range check used to raise straight out of the parser and
    kill the run. The docstring promised NULL; now it delivers NULL."""
    assert parse_franking(raw) is None


@pytest.mark.parametrize("raw", ["NaN/1", "1/NaN", "Infinity", "Infinity/1", "sNaN/1"])
def test_parse_split_ratio_rejects_decimal_specials(raw):
    """Postgres does NOT apply a NUMERIC typmod to the specials, so `Infinity` is
    plausibly persistable into NUMERIC(18,6) and would silently poison every downstream
    split-adjustment multiplication."""
    assert parse_split_ratio(raw) is None


@pytest.mark.parametrize(
    "raw",
    ["1e1000000/1", "1e999999999/1.000000", "-1e1000000/1", "1/1e-1000000"],
)
def test_parse_split_ratio_survives_decimal_overflow(raw):
    """`decimal.Overflow` is an ArithmeticError, NOT an InvalidOperation, and it is
    trapped by default context — so `except (InvalidOperation, ValueError)` did not
    catch it. This is the only parser here that does arithmetic (the n / o division),
    so it is the only one that can raise it.

    It escaped through `to_split_rows`, which runs OUTSIDE the per-symbol executemany
    try/except, so one malformed vendor split string aborted the ENTIRE weekly run —
    the same permanent-wedge mode the write isolation exists to prevent, arriving one
    step earlier on the parse path. Re-runs are not checkpointed, so it would recur
    every week against the same data.
    """
    assert parse_split_ratio(raw) is None


def test_parse_split_ratio_still_accepts_finite_extremes():
    """The Overflow guard must not swallow finite values — those are the DB's job to
    reject (asyncpg raises DataError, which the per-symbol write isolation catches)."""
    assert parse_split_ratio("4.000000/1.000000") == Decimal(4)
    assert parse_split_ratio("1/1e999999999") is not None


@pytest.mark.parametrize("raw", ["Infinity", "-Infinity", "NaN", float("inf"), float("nan")])
def test_dividend_amount_rejects_decimal_specials(raw):
    """Same guard on the money column."""
    rows = to_dividend_rows([{"date": "2026-01-01", "value": raw}], "X.AU")
    assert rows[0][4] is None


# ---------------------------------------------------------------------------
# parse_split_ratio
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("2.000000/1.000000", Decimal("2")),
    ("7.000000/1.000000", Decimal("7")),
    ("0.993600/1.000000", Decimal("0.9936")),   # consolidation (CBA 1996)
    ("4.000000/1.000000", Decimal("4")),
    (None, None),
    ("", None),
    ("x/y", None),
    ("1.0/0.0", None),                           # zero divisor -> NULL
])
def test_parse_split_ratio(raw, expected):
    assert parse_split_ratio(raw) == expected


# ---------------------------------------------------------------------------
# to_dividend_rows / to_split_rows
# ---------------------------------------------------------------------------

_CBA_DIV = [{
    "date": "2026-02-18", "paymentDate": "2026-03-30", "recordDate": None,
    "period": "Final", "franking": "100%", "value": 2.35, "unadjustedValue": 2.35,
    "currency": "AUD",
}]
_AAPL_DIV = [{
    "date": "2026-05-11", "paymentDate": "2026-05-14", "recordDate": "2026-05-11",
    "period": "Quarterly", "value": 0.27, "unadjustedValue": 0.27, "currency": "USD",
}]


def test_to_dividend_rows_au_with_franking():
    (row,) = to_dividend_rows(_CBA_DIV, "CBA.AU")
    assert row[0] == "CBA.AU"
    assert row[1] == date(2026, 2, 18)        # ex_date
    assert row[2] == "dividend"
    assert row[3] is None                      # split_ratio
    assert row[4] == Decimal("2.35")           # dividend_amount (unadjustedValue)
    assert row[5] == Decimal("100")            # franking_pct
    assert row[6] == date(2026, 3, 30)         # pay_date
    assert row[7] is None                      # record_date (null in source)


def test_to_dividend_rows_us_has_no_franking():
    (row,) = to_dividend_rows(_AAPL_DIV, "AAPL.US")
    assert row[5] is None                      # no franking key on US names


def test_to_dividend_rows_prefers_unadjusted_over_value():
    raw = [{"date": "2020-01-01", "value": 1.0, "unadjustedValue": 4.0}]
    assert to_dividend_rows(raw, "X.AU")[0][4] == Decimal("4.0")


def test_to_dividend_rows_falls_back_to_value():
    raw = [{"date": "2020-01-01", "value": 1.5}]   # no unadjustedValue
    assert to_dividend_rows(raw, "X.AU")[0][4] == Decimal("1.5")


def test_to_dividend_rows_skips_missing_ex_date():
    raw = [{"value": 1.0}, {"date": "2026-01-01", "value": 2.0}]
    rows = to_dividend_rows(raw, "X.AU")
    assert len(rows) == 1
    assert rows[0][1] == date(2026, 1, 1)


def test_to_dividend_rows_empty_and_nonlist():
    assert to_dividend_rows([], "X.AU") == []
    assert to_dividend_rows(None, "X.AU") == []
    assert to_dividend_rows({"error": "x"}, "X.AU") == []


def test_to_split_rows():
    raw = [{"date": "2020-08-31", "split": "4.000000/1.000000"}]
    (row,) = to_split_rows(raw, "AAPL.US")
    assert row == ("AAPL.US", date(2020, 8, 31), "split", Decimal("4"), None, None, None, None)


def test_to_split_rows_empty_and_nonlist():
    assert to_split_rows([], "X.AU") == []
    assert to_split_rows(None, "X.AU") == []


# ---------------------------------------------------------------------------
# refresh_corporate_actions — orchestrator
# ---------------------------------------------------------------------------


class FakeClient:
    def __init__(self, divs: dict, splits: dict, errors: set | None = None) -> None:
        self._divs = divs
        self._splits = splits
        self._errors = errors or set()

    async def dividends(self, symbol: str):
        if symbol in self._errors:
            raise RuntimeError("boom")
        return self._divs.get(symbol, [])

    async def splits(self, symbol: str):
        if symbol in self._errors:
            raise RuntimeError("boom")
        return self._splits.get(symbol, [])


class FakeConn:
    """Records both write shapes so tests can assert the per-row path is GONE.

    `executed` (per-row `execute`) must stay empty on the write path — the per-row
    loop was the 175.5 ms/row defect that ate the weekly workflow budget on
    2026-08-15. `executemany_calls` is the batched path that replaced it.
    """

    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple]] = []
        self.executemany_calls: list[tuple[str, list[tuple]]] = []

    async def execute(self, sql: str, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql: str, rows):
        self.executemany_calls.append((sql, list(rows)))

    # Every write the module makes, flattened to (sql, row) pairs — lets the
    # invariant tests below stay agnostic about which API carried the row.
    @property
    def written(self) -> list[tuple[str, tuple]]:
        out = list(self.executed)
        for sql, rows in self.executemany_calls:
            out.extend((sql, tuple(r)) for r in rows)
        return out


@pytest.mark.asyncio
async def test_refresh_counts_and_upsert_shape():
    client = FakeClient(
        divs={"CBA.AU": _CBA_DIV, "BHP.AU": []},
        splits={"AAPL.US": [{"date": "2020-08-31", "split": "4.000000/1.000000"}]},
    )
    conn = FakeConn()
    counts = await refresh_corporate_actions(
        client, conn, ["CBA.AU", "BHP.AU", "AAPL.US"], concurrency=2
    )
    assert counts["dividends"] == 1
    assert counts["splits"] == 1
    assert counts["symbols_with_actions"] == 2     # CBA (div) + AAPL (split)
    assert counts["failed"] == 0
    # every write is an idempotent UPSERT on the composite PK
    assert all("ON CONFLICT (symbol, ex_date, action_type) DO UPDATE" in s for s, _ in conn.written)


@pytest.mark.asyncio
async def test_counts_dict_shape_is_stable():
    """The returned `counts` keys are the job's logging + JobMonitor contract
    (jobs/sync_corporate_actions.py reads all five). Batching must not change them."""
    client = FakeClient(divs={"CBA.AU": _CBA_DIV}, splits={})
    conn = FakeConn()
    counts = await refresh_corporate_actions(client, conn, ["CBA.AU"], concurrency=1)
    assert set(counts) == {"symbols", "dividends", "splits", "symbols_with_actions", "failed"}
    assert all(isinstance(v, int) for v in counts.values())


@pytest.mark.asyncio
async def test_writes_are_batched_once_per_symbol():
    """THE regression pin: one executemany per symbol-with-actions, and NO per-row
    execute anywhere on the write path.

    The per-row loop measured 175.5 ms/row on run 31895667938 (30,099 rows / 5,281s),
    consuming 88.1 min of the 90-minute weekly-research budget.
    """
    client = FakeClient(
        divs={"CBA.AU": _CBA_DIV, "BHP.AU": _CBA_DIV},
        splits={"CBA.AU": [{"date": "1996-05-27", "split": "0.993600/1.000000"}]},
    )
    conn = FakeConn()
    await refresh_corporate_actions(client, conn, ["CBA.AU", "BHP.AU"], concurrency=2)

    # No per-row round-trips survive.
    assert conn.executed == []
    # Exactly one batch per symbol that had actions — never one accumulated batch.
    assert len(conn.executemany_calls) == 2
    by_symbol = {rows[0][0]: rows for _sql, rows in conn.executemany_calls}
    assert set(by_symbol) == {"CBA.AU", "BHP.AU"}
    assert len(by_symbol["CBA.AU"]) == 2      # 1 dividend + 1 split
    assert len(by_symbol["BHP.AU"]) == 1      # 1 dividend
    # Each batch is single-symbol: that is what bounds rollback blast radius to one
    # symbol and keeps the run resumable after a partial failure.
    for _sql, rows in conn.executemany_calls:
        assert len({r[0] for r in rows}) == 1


@pytest.mark.asyncio
async def test_batched_upsert_preserves_franking_never_wipe():
    """A later run returning NULL franking must never wipe a known value (§tax-material).

    The COALESCE lives in the SQL, so the pin is that batching still sends exactly that
    statement — and that a NULL-franking row is passed through as NULL, not coerced to 0.
    """
    client = FakeClient(divs={"AAPL.US": _AAPL_DIV}, splits={})
    conn = FakeConn()
    await refresh_corporate_actions(client, conn, ["AAPL.US"], concurrency=1)

    (sql, rows) = conn.executemany_calls[0]
    # Whitespace-insensitive on purpose: _UPSERT's column alignment is cosmetic, and
    # an exact-spacing assertion would break on a pure realignment.
    assert "COALESCE(EXCLUDED.franking_pct, rs_corporate_actions.franking_pct)" in sql
    assert rows[0][5] is None          # undeclared franking stays NULL, never 0


@pytest.mark.asyncio
async def test_refresh_does_not_touch_universe_or_prices():
    client = FakeClient(divs={"CBA.AU": _CBA_DIV}, splits={})
    conn = FakeConn()
    await refresh_corporate_actions(client, conn, ["CBA.AU"], concurrency=1)
    assert conn.written
    for sql, _ in conn.written:
        low = sql.lower()
        assert "universe" not in low
        assert " prices" not in low
        assert "rs_corporate_actions" in low


@pytest.mark.asyncio
async def test_refresh_tolerates_per_symbol_errors():
    client = FakeClient(divs={"OK.AU": _CBA_DIV}, splits={}, errors={"BAD.AU"})
    conn = FakeConn()
    counts = await refresh_corporate_actions(client, conn, ["OK.AU", "BAD.AU"], concurrency=2)
    assert counts["failed"] == 1
    assert counts["dividends"] == 1   # the good symbol still processed
    # Isolation survives batching: the failed symbol contributes no batch, and the run
    # completes normally rather than aborting.
    assert len(conn.executemany_calls) == 1
    assert {r[0] for _sql, rows in conn.executemany_calls for r in rows} == {"OK.AU"}


class ExplodingConn(FakeConn):
    """Fails the write for `poison` symbols only."""

    def __init__(self, poison: set[str]) -> None:
        super().__init__()
        self.poison = poison

    async def execute(self, sql: str, *args):
        raise AssertionError("no per-row execute may remain on the write path")

    async def executemany(self, sql: str, rows):
        rows = list(rows)
        if rows and rows[0][0] in self.poison:
            raise RuntimeError("numeric field overflow")
        await super().executemany(sql, rows)


@pytest.mark.asyncio
async def test_one_poison_symbol_does_not_wedge_the_whole_run():
    """A write failure is isolated to its symbol — it must NOT abort the run.

    Regression guard for the failure mode batching introduces: before batching,
    per-row autocommit made rows 1..k-1 of a bad symbol durable. Batched, the symbol
    rolls back — and if that also aborted the run, the weekly re-run would re-fetch
    identical data, hit the identical poison row, and roll back again forever, while
    skipping every symbol not yet drained. Real trigger: EODHD returning `1e40`,
    which overflows NUMERIC(18,6).
    """
    client = FakeClient(divs={"BAD.AU": _CBA_DIV, "OK.AU": _CBA_DIV}, splits={})
    conn = ExplodingConn(poison={"BAD.AU"})
    counts = await refresh_corporate_actions(
        client, conn, ["BAD.AU", "OK.AU"], concurrency=1
    )
    assert counts["failed"] == 1
    assert counts["dividends"] == 1            # the good symbol still landed
    # The failing symbol must not be counted as having contributed actions — the
    # tally happens AFTER the write, not before.
    assert counts["symbols_with_actions"] == 1
    assert {r[0] for _sql, rows in conn.executemany_calls for r in rows} == {"OK.AU"}


@pytest.mark.asyncio
async def test_overflowing_amount_is_the_realistic_poison_row():
    """`_dec` must not hand NUMERIC(18,6) a value that can only ever be rejected."""
    rows = to_dividend_rows([{"date": "2026-01-01", "value": "1e40"}], "X.AU")
    # It is still passed through (the overflow is the DB's call, not the parser's) —
    # this pins that the poison-row path above is reachable from real payload shapes.
    assert rows[0][4] == Decimal("1E+40")


@pytest.mark.asyncio
async def test_refresh_action_type_recorded_in_args():
    client = FakeClient(divs={"CBA.AU": _CBA_DIV}, splits={"CBA.AU": [{"date": "1996-05-27", "split": "0.993600/1.000000"}]})
    conn = FakeConn()
    await refresh_corporate_actions(client, conn, ["CBA.AU"], concurrency=1)
    action_types = {args[2] for _s, args in conn.written}
    assert action_types == {"dividend", "split"}


# ---------------------------------------------------------------------------
# _RUN_DEADLINE_S — the wall-clock hang guard
# ---------------------------------------------------------------------------


def _workflow_job_timeout_s() -> int:
    """The REAL `timeout-minutes` from weekly-research.yml, not a copy of it.

    Reading the yml is the whole point: hardcoding `90 * 60` would let someone drop
    the workflow budget to 45 minutes and leave this test passing while the guard went
    dead — which is precisely the defect the test exists to prevent.
    """
    wf = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".github/workflows/weekly-research.yml").read_text()
    )
    return int(wf["jobs"]["research"]["timeout-minutes"]) * 60


def test_run_deadline_fits_inside_the_workflow_job_budget():
    """The guard must be a SHARE of weekly-research.yml's whole-job timeout.

    financial_statements.py's 5400s guard is dead on the scheduled path for exactly
    this reason: 5400s == the 90-minute budget for all six steps, so GitHub's timeout
    always fires first (observed, run 31895667938). A per-step guard sized at or above
    the job budget can never fire.
    """
    budget = _workflow_job_timeout_s()
    assert corporate_actions._RUN_DEADLINE_S < budget
    # and it must still leave real room for the three downstream steps (financial
    # statements alone was 11.4 min on run 31267448443).
    assert budget - corporate_actions._RUN_DEADLINE_S > 30 * 60


def test_financial_statements_deadline_is_dead_as_sized():
    """Pins the KNOWN-BAD sibling constant so nobody "fixes" the docs and forgets it.

    financial_statements._RUN_DEADLINE_S == the entire job budget, so it can never
    fire — it is step 4 of 6. Annotated in that module; not re-tuned here (out of
    scope). If someone re-sizes it properly, this test flips and should be updated
    to the same `< budget` assertion the corporate-actions guard gets above.
    """
    assert financial_statements._RUN_DEADLINE_S >= _workflow_job_timeout_s()


class HangingClient(FakeClient):
    """Both endpoints never return — the systemic-upstream-stall shape."""

    def __init__(self) -> None:
        super().__init__(divs={}, splits={})

    async def dividends(self, symbol: str):
        await asyncio.sleep(3600)

    async def splits(self, symbol: str):
        await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_deadline_guard_fires_on_a_hung_fetch(monkeypatch):
    """A systemic upstream stall must fail loud in-window, not hang the workflow."""
    monkeypatch.setattr(corporate_actions, "_RUN_DEADLINE_S", 0.05)
    conn = FakeConn()
    with pytest.raises(TimeoutError):
        await refresh_corporate_actions(
            HangingClient(), conn, ["A.AU", "B.AU"], concurrency=2
        )
    assert conn.executemany_calls == []


@pytest.mark.asyncio
async def test_deadline_timeout_is_distinguishable_from_a_statement_timeout(monkeypatch):
    """`asxos/db.py` sets command_timeout=30 and asyncpg raises asyncio.TimeoutError,
    which IS builtin TimeoutError on 3.11+ — so `job_runs.error_message` could not tell
    "the run deadline fired" from "one statement took >30s". The deadline must say so
    explicitly, and carry ints only (no vendor payload, no symbols, no API token).
    """
    monkeypatch.setattr(corporate_actions, "_RUN_DEADLINE_S", 0.05)
    with pytest.raises(TimeoutError, match=r"run deadline 0\.05s exceeded; counts=") as ei:
        await refresh_corporate_actions(
            HangingClient(), FakeConn(), ["A.AU"], concurrency=1
        )
    assert "A.AU" not in str(ei.value)
    assert isinstance(ei.value.__cause__, TimeoutError)


@pytest.mark.asyncio
async def test_statement_timeout_is_isolated_not_relabelled():
    """A per-statement TimeoutError is a write failure for ONE symbol; it must not be
    relabelled as the run deadline (which has not expired)."""

    class SlowConn(FakeConn):
        async def executemany(self, sql: str, rows):
            raise TimeoutError            # what asyncpg command_timeout surfaces as

    counts = await refresh_corporate_actions(
        FakeClient(divs={"CBA.AU": _CBA_DIV}, splits={}), SlowConn(), ["CBA.AU"],
        concurrency=1,
    )
    assert counts["failed"] == 1
    assert counts["dividends"] == 0


@pytest.mark.asyncio
async def test_deadline_cancels_outstanding_fetches_before_returning(monkeypatch):
    """On abort, no orphaned HTTP fetch may outlive the call.

    Scoped claim on purpose: connection safety here is STRUCTURAL, not something the
    abort handler provides — `fetch()` closes over the client/semaphore only and never
    touches `conn`, and the drain loop runs inline in the caller's own task. (In
    financial_statements.py the equivalent handler IS load-bearing for the connection,
    because there the workers call `conn.executemany` directly.)
    """
    before = asyncio.all_tasks()
    monkeypatch.setattr(corporate_actions, "_RUN_DEADLINE_S", 0.05)
    with pytest.raises(TimeoutError):
        await refresh_corporate_actions(
            HangingClient(), FakeConn(), ["A.AU", "B.AU"], concurrency=2
        )
    # Nothing the call created may still be pending once it has raised.
    leaked = [t for t in asyncio.all_tasks() - before if not t.done()]
    assert leaked == []


@pytest.mark.asyncio
async def test_partial_progress_is_reported_before_an_abort():
    """`on_rows_written` must fire per landed symbol, so a deadline-aborted run still
    reports the rows it really wrote (JobMonitor persists rows_written on failure)."""
    seen: list[int] = []
    client = FakeClient(divs={"A.AU": _CBA_DIV, "B.AU": _CBA_DIV}, splits={})
    await refresh_corporate_actions(
        client, FakeConn(), ["A.AU", "B.AU"], concurrency=1, on_rows_written=seen.append
    )
    assert seen == [1, 2]


# ---------------------------------------------------------------------------
# Systemic-failure gate (jobs/sync_corporate_actions.py)
#
# Per-symbol write isolation is right for ONE poison row and wrong for a dead
# connection. Without a ratio gate the job returns normally when every symbol
# fails, so JobMonitor writes status='success' and the Healthchecks deadman is
# pinged GREEN — the deadman cannot catch a failure that keeps feeding it.
# ---------------------------------------------------------------------------

sync_corporate_actions = importlib.import_module("jobs.sync_corporate_actions")


def _counts(symbols: int, failed: int) -> dict[str, int]:
    return {
        "symbols": symbols,
        "failed": failed,
        "dividends": 0,
        "splits": 0,
        "symbols_with_actions": 0,
    }


def test_systemic_failure_raises_instead_of_reporting_green():
    """The regression that matters: connection dies, every symbol fails, and the run
    would otherwise complete 'successfully' with rows_written near zero."""
    with pytest.raises(RuntimeError, match="systemic"):
        sync_corporate_actions.assert_symbol_success_ratio(_counts(2392, 2382))


def test_isolated_failures_do_not_fail_the_run():
    """The observed 2026-08-15 run had failed=14 of 2392 (0.6%) — that must stay green,
    otherwise the per-symbol isolation this gate sits on top of is pointless."""
    assert sync_corporate_actions.assert_symbol_success_ratio(_counts(2392, 14)) == 2378


def test_threshold_boundary_is_inclusive():
    """Exactly at the threshold passes; one below it fails."""
    assert sync_corporate_actions.assert_symbol_success_ratio(_counts(100, 25)) == 75
    with pytest.raises(RuntimeError):
        sync_corporate_actions.assert_symbol_success_ratio(_counts(100, 26))


def test_zero_symbols_does_not_divide_by_zero():
    """`refresh_corporate_actions` is never called with an empty list (the job hard-fails
    earlier), but the gate must not be the thing that raises ZeroDivisionError."""
    assert sync_corporate_actions.assert_symbol_success_ratio(_counts(0, 0)) == 0
