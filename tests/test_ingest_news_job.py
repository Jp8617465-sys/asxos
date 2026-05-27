"""
Tests for jobs/ingest_news.py — job-level behaviour with AsyncMock.

Coverage:
  _fetch_and_upsert():
    - Returns 0 and logs a warning when news_for_symbol raises
    - Returns the upsert count on success

  main():
    - Raises RuntimeError when ASXOS_PERSONAL_USE is not "1"
    - Exits cleanly with no API calls when holdings table is empty
    - Aggregates rows_written correctly across multiple symbols
    - One failing symbol does not abort the rest (gather return_exceptions)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

# jobs/ is added to sys.path via tests/conftest.py
from jobs.ingest_news import _fetch_and_upsert, main

# ---------------------------------------------------------------------------
# _fetch_and_upsert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_and_upsert_returns_zero_on_api_failure() -> None:
    """API exception is swallowed; 0 returned; job continues."""
    client = AsyncMock()
    client.news_for_symbol.side_effect = Exception("EODHD 503")
    conn = AsyncMock()

    result = await _fetch_and_upsert(client, "BHP.AU", "2026-05-22", {"BHP.AU"}, conn)
    assert result == 0
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
            raise RuntimeError("API error for CBA")
        return 2  # 2 rows for the other symbols

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
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
            raise RuntimeError("API error for CBA")
        return 2

    with (
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
        patch("jobs.ingest_news.init_pool", new=AsyncMock()),
        patch("jobs.ingest_news.close_pool", new=AsyncMock()),
        patch("jobs.ingest_news.acquire", new=fake_acquire),
        patch("jobs.ingest_news.JobMonitor", new=FakeJobMonitor),
        patch("jobs.ingest_news._fetch_and_upsert", new=fake_fetch_and_upsert),
    ):
        # 2/3 = 66.7% < 75% threshold → hard-fail
        with pytest.raises(RuntimeError, match=r"ingest_news.*only 2/3"):
            await main()
