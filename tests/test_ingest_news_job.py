"""
Tests for jobs/ingest_news.py — job-level behaviour with AsyncMock.

Coverage:
  _fetch_and_upsert():
    - Returns None (NOT 0) and logs a warning when news_for_symbol raises
    - Returns the upsert count on success

  main():
    - Raises RuntimeError when ASXOS_PERSONAL_USE is not "1"
    - Exits cleanly with no API calls when holdings table is empty
    - Aggregates rows_written correctly across multiple symbols
    - One failing symbol does not abort the rest (gather return_exceptions)
    - Every symbol failing hard-fails (the false-green regression)
    - A genuine 0-article day still passes (the other side of the sentinel)
    - End-to-end against the real worker: a total vendor outage hard-fails
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

# jobs/ is added to sys.path via tests/conftest.py
from jobs.ingest_news import _fetch_and_upsert, main

# ---------------------------------------------------------------------------
# _fetch_and_upsert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_and_upsert_returns_none_on_api_failure() -> None:
    """API exception is swallowed; None returned; job continues.

    The sentinel must be None and NOT 0: main()'s aggregate guard distinguishes
    "this symbol failed" from "this symbol had no news today" purely by type.
    Returning 0 here collapsed that distinction, so the guard could not fail —
    22 consecutive runs recorded status='success' with rows_written=0 against an
    empty holding_news table (docs/market-trends-report-2026-08-05.md §1).
    """
    client = AsyncMock()
    client.news_for_symbol.side_effect = Exception("EODHD 503")
    conn = AsyncMock()

    result = await _fetch_and_upsert(client, "BHP.AU", "2026-05-22", {"BHP.AU"}, conn)
    assert result is None
    # Conn upsert should NOT have been called
    conn.executemany.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_and_upsert_returns_count_on_success() -> None:
    """Successful fetch+upsert returns the upsert count."""
    client = AsyncMock()
    client.news_for_symbol.return_value = [
        {
            "link": "https://example.com/bhp",
            "title": "BHP result",
            "date": "2026-05-22T05:00:00+00:00",
            "symbols": ["BHP.AU"],
            "sentiment": "positive",
        }
    ]

    conn = AsyncMock()
    # upsert_news internally calls conn.executemany; mock the whole function
    with patch("jobs.ingest_news.upsert_news", new=AsyncMock(return_value=1)) as mock_upsert:
        result = await _fetch_and_upsert(
            client, "BHP.AU", "2026-05-22", {"BHP.AU"}, conn
        )
    assert result == 1
    mock_upsert.assert_awaited_once()
    # ASX symbols are already in EODHD's namespace — the remap must be a no-op,
    # not a corruption.
    client.news_for_symbol.assert_awaited_once_with(
        "BHP.AU", limit=10, from_date="2026-05-22"
    )


@pytest.mark.asyncio
async def test_us_holding_is_requested_in_eodhd_namespace_and_stored_as_held() -> None:
    """The round trip for a non-ASX holding: request .US, store the held symbol.

    This is the regression pin for the REQUEST half of the fix, and it was the
    half with no coverage at all — reverting `eodhd_symbol(symbol)` back to a raw
    `symbol` in _fetch_and_upsert left every other news test green, because they
    all use ASX symbols where the remap is a no-op.

    Both directions matter and both were broken:
      - out: EODHD addresses NYSE/NASDAQ listings as `.US`, so asking it for
        `HUBS.NYSE` addresses a namespace it does not serve.
      - back: articles come tagged `HUBS`, and `holding_news.symbols` must carry
        the HELD form, because asxos/brief/compose.py re-intersects it against
        current_holdings and jobs/ingest_sentiment.py unnests it into
        signal_sentiment.symbol (a PK with no FK to catch a wrong format).
    """
    today = date.today().isoformat()
    client = AsyncMock()
    client.news_for_symbol.return_value = [
        {
            "link": "https://example.com/hubs",
            "title": "HubSpot reports Q2",
            "date": f"{today}T05:00:00+00:00",
            "symbols": ["HUBS"],          # vendor tags with the bare ticker
            "sentiment": "positive",
        }
    ]

    conn = AsyncMock()
    with patch("jobs.ingest_news.upsert_news", new=AsyncMock(return_value=1)) as mock_upsert:
        result = await _fetch_and_upsert(
            client, "HUBS.NYSE", today, {"HUBS.NYSE"}, conn
        )

    assert result == 1
    client.news_for_symbol.assert_awaited_once_with(
        "HUBS.US", limit=10, from_date=today
    )
    items = mock_upsert.await_args.args[1]
    assert len(items) == 1, "a bare-ticker tag must resolve against the held symbol"
    assert items[0].symbols == ["HUBS.NYSE"], "must store the HELD form, not HUBS or HUBS.US"


# ---------------------------------------------------------------------------
# main() — ASXOS_PERSONAL_USE gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_raises_when_personal_use_not_set() -> None:
    """main() hard-fails when ASXOS_PERSONAL_USE is absent."""
    env = {k: v for k, v in os.environ.items() if k != "ASXOS_PERSONAL_USE"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE not set"):
            await main()


# ---------------------------------------------------------------------------
# main() — empty holdings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_holdings_exits_cleanly() -> None:
    """When current_holdings is empty, no API calls are made and job exits cleanly."""
    conn = AsyncMock()
    conn.fetch.return_value = []  # no holdings

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client") as mock_get_client,
    ):
        await main()
        mock_get_client.assert_not_called()


# ---------------------------------------------------------------------------
# main() — rows_written aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rows_written_set_correctly() -> None:
    """monitor.rows_written = sum of _fetch_and_upsert return values."""
    conn = AsyncMock()
    # First fetch: current_holdings
    conn.fetch.return_value = [{"symbol": "BHP.AU"}, {"symbol": "CBA.AU"}]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    captured_monitor = {}

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
            captured_monitor["monitor"] = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        # Each symbol upserts 3 rows
        patch("jobs.ingest_news._fetch_and_upsert", new=AsyncMock(return_value=3)),
    ):
        await main()

    assert captured_monitor["monitor"].rows_written == 6  # 2 symbols × 3 rows each


@pytest.mark.asyncio
async def test_symbol_failures_above_threshold_proceed() -> None:
    """Transient single-symbol failure within threshold (3/4 ≥ 0.75) proceeds.

    P0-1 added an aggregate threshold of 0.75 — one bad symbol out of four
    is still acceptable and the run succeeds.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"symbol": "BHP.AU"},
        {"symbol": "CBA.AU"},
        {"symbol": "WBC.AU"},
        {"symbol": "ANZ.AU"},
    ]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    call_count = {"n": 0}
    captured_monitor = {}

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
            captured_monitor["monitor"] = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_fetch_and_upsert(client, symbol, from_date, holdings, conn):
        call_count["n"] += 1
        if symbol == "CBA.AU":
            return None  # real contract: failures return None, never raise
        return 2  # 2 rows for the other symbols

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        await main()  # 3/4 = 75% ≥ threshold; proceeds

    # All 4 symbols attempted
    assert call_count["n"] == 4
    # rows_written = 2 (BHP) + 0 (CBA exception) + 2 (WBC) + 2 (ANZ) = 6
    assert captured_monitor["monitor"].rows_written == 6


@pytest.mark.asyncio
async def test_symbol_failures_below_threshold_hard_fail() -> None:
    """P0-1: when symbol failure ratio breaches 0.75 threshold, hard-fail.

    Previously this case silently swallowed the failures. The new behavior
    raises RuntimeError with the failing identifiers listed so operators
    don't have to grep stdout.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"symbol": "BHP.AU"},
        {"symbol": "CBA.AU"},
        {"symbol": "WBC.AU"},
    ]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_fetch_and_upsert(client, symbol, from_date, holdings, conn):
        if symbol == "CBA.AU":
            return None  # real contract: failures return None, never raise
        return 2

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        # 2/3 = 66.7% < 75% threshold → hard-fail
        with pytest.raises(RuntimeError, match=r"ingest_news.*only 2/3"):
            await main()


# ---------------------------------------------------------------------------
# main() — the false-green regression (docs/market-trends-report-2026-08-05.md §1)
#
# Which test actually pins the bug, verified by running this file against
# pre-fix HEAD: only test_end_to_end_all_symbols_erroring_hard_fails_with_real_
# worker (below) and test_fetch_and_upsert_returns_none_on_api_failure (above)
# FAIL there. The two main()-level tests in this block PASS against the buggy
# code, because they patch _fetch_and_upsert out and so never exercise the
# worker/predicate mismatch that was the defect. They are guards, not the
# regression pin — do not cite them as proof the bug cannot return.
#
# That distinction is the whole lesson: the pre-existing threshold tests passed
# for exactly this reason. Their fake RAISES, while the real _fetch_and_upsert
# catches everything, so they exercised a path production cannot reach. Any test
# that patches the worker out can only ever check main() against a hand-written
# contract — never against the worker's real behaviour.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_symbols_failing_hard_fails() -> None:
    """Every symbol failing must hard-fail, not record a silent success.

    Guard, not regression pin (see block comment above): this passes against the
    buggy code too, because patching _fetch_and_upsert out means the old
    predicate still rejects these None results. It defends the 0/N boundary of
    main()'s aggregate guard, nothing more.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"symbol": "BHP.AU"},
        {"symbol": "CBA.AU"},
        {"symbol": "WBC.AU"},
    ]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_fetch_and_upsert(client, symbol, from_date, holdings, conn):
        return None  # every symbol fails

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        with pytest.raises(RuntimeError, match=r"ingest_news.*only 0/3"):
            await main()


@pytest.mark.asyncio
async def test_genuine_zero_news_day_succeeds() -> None:
    """A real quiet news day (0 articles, no errors) must NOT hard-fail.

    This is the over-correction guard: a "fix" that tightened the predicate to
    `r > 0` would trade the false green for a false red on every quiet day, and
    this test fails it. Like its sibling above it passes against the original
    bug, so it is a guard rather than the regression pin.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"symbol": "BHP.AU"},
        {"symbol": "CBA.AU"},
        {"symbol": "WBC.AU"},
    ]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    captured_monitor = {}

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
            captured_monitor["monitor"] = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_fetch_and_upsert(client, symbol, from_date, holdings, conn):
        return 0  # genuinely no articles, no failure

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        await main()  # 3/3 healthy — must not raise

    assert captured_monitor["monitor"].rows_written == 0


@pytest.mark.asyncio
async def test_end_to_end_all_symbols_erroring_hard_fails_with_real_worker() -> None:
    """main() + the REAL _fetch_and_upsert: a total vendor outage must hard-fail.

    This is the test that would have caught the original bug on its own, and the
    one whose absence let it ship. Every other threshold test patches
    _fetch_and_upsert out, so they verify main()'s guard against a hand-written
    contract rather than against the worker's actual behaviour — and when the two
    drifted apart (worker returning 0, guard accepting every int), nothing failed.

    Here the only thing faked is the vendor client. The worker, its exception
    handling, its sentinel, the gather, and the aggregate guard all run for real,
    so the halves cannot silently disagree again.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"symbol": "BHP.AU"},
        {"symbol": "CBA.AU"},
        {"symbol": "WBC.AU"},
    ]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    # The only fake: the vendor. Every symbol errors, as in a total outage.
    failing_client = AsyncMock()
    failing_client.news_for_symbol.side_effect = Exception("EODHD 503")

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client", return_value=failing_client),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
    ):
        with pytest.raises(RuntimeError, match=r"ingest_news.*only 0/3"):
            await main()


@pytest.mark.asyncio
async def test_zero_rows_written_sets_degraded_note() -> None:
    """A green run that wrote nothing must leave a marker on the success row.

    This is the guard for the failure mode the sentinel fix does NOT catch. A
    zero-row run needs no exception at all: the vendor can return nothing for the
    symbol requested, or return articles whose tags resolve to no held symbol, so
    every article is dropped and a legitimate 0 is returned. The aggregate predicate passes it (correctly — 0 is a valid
    count), so the only way this becomes visible without inspecting the table is
    monitor.note, which JobMonitor writes to job_runs.error_message on a success
    row and check_cron_health's degraded-run check reads.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [{"symbol": "HUBS.NYSE"}]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    captured_monitor = {}

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
            self.note = None
            captured_monitor["monitor"] = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_fetch_and_upsert(client, symbol, from_date, holdings, conn):
        return 0  # no exception; every article filtered out upstream

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        await main()  # must NOT raise — 0 is a valid count

    note = captured_monitor["monitor"].note
    assert note is not None, "a green run writing 0 rows must set a degraded note"
    assert "0 rows written" in note
    assert "holdings-symbol filter" in note


@pytest.mark.asyncio
async def test_partial_failure_sets_degraded_note() -> None:
    """Failures inside the tolerated 25% band must still leave a marker.

    Mirrors ingest_regulatory._degraded_note: clearing the threshold is not a
    reason for a dead symbol to vanish behind a 'success' row.
    """
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"symbol": "BHP.AU"},
        {"symbol": "CBA.AU"},
        {"symbol": "WBC.AU"},
        {"symbol": "ANZ.AU"},
    ]

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    captured_monitor = {}

    class FakeJobMonitor:
        def __init__(self, *a, **kw):
            self.rows_written = 0
            self.note = None
            captured_monitor["monitor"] = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    async def fake_fetch_and_upsert(client, symbol, from_date, holdings, conn):
        return None if symbol == "CBA.AU" else 2

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.get_client"),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        await main()  # 3/4 clears the threshold

    note = captured_monitor["monitor"].note
    assert note is not None and "1/4 symbols failed" in note
