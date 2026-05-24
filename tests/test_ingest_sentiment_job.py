"""
ingest_sentiment.py job-level tests — M14b REV-K.

REV-K (2026-05-24): job repurposed from EODHD /sentiments API caller to SQL
aggregation from holding_news.sentiment_polarity.  No client/sentiments stubs.

Pattern mirrors tests/test_ingest_news_job.py; patches at jobs.ingest_sentiment namespace.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.ingest_sentiment as job_mod


def _make_stubs(symbols: list[str]):
    """Build standard test stubs for ingest_sentiment (REV-K: SQL aggregation, no EODHD API)."""
    rows = [{"symbol": s} for s in symbols]

    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    async def fake_init():
        pass

    async def fake_close():
        pass

    class FakeMonitor:
        def __init__(self, *, job_name, as_of, healthcheck_url):
            self.rows_written = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    return {
        "acquire": fake_acquire,
        "init_pool": fake_init,
        "close_pool": fake_close,
        "JobMonitor": FakeMonitor,
        "conn": conn,
    }


def _run(symbols: list[str], *, aggregate_return: int = 0, upstream_ok: bool = True, **stub_overrides):
    """Run main() with stubs injected.

    Patches _aggregate_from_news and _upstream_ok at module level so the
    actual SQL does not run during unit tests.
    """
    stubs = _make_stubs(symbols)
    stubs.update(stub_overrides)

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "JobMonitor", stubs["JobMonitor"]),
        patch("jobs.ingest_sentiment._aggregate_from_news", new=AsyncMock(return_value=aggregate_return)),
        patch("jobs.ingest_sentiment._upstream_ok", new=AsyncMock(return_value=upstream_ok)),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())

    return stubs


def test_regulatory_firewall_raises_when_flag_missing() -> None:
    """main() raises immediately if ASXOS_PERSONAL_USE != '1'."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("ASXOS_PERSONAL_USE", None)
        with pytest.raises(RuntimeError, match="ASXOS_PERSONAL_USE not set"):
            asyncio.run(job_mod.main())


def test_no_holdings_exits_cleanly() -> None:
    """Empty current_holdings → skips aggregation, no DB calls beyond holdings fetch."""
    mock_aggregate = AsyncMock()
    stubs = _make_stubs([])

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        # JobMonitor should NOT be called — don't patch it so it would crash if called
        patch("jobs.ingest_sentiment._aggregate_from_news", mock_aggregate),
        patch("jobs.ingest_sentiment._upstream_ok", AsyncMock(return_value=True)),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())

    mock_aggregate.assert_not_called()


def test_rows_written_set_correctly() -> None:
    """monitor.rows_written equals the return value of _aggregate_from_news."""
    rows_written_captured = []

    class CapturingMonitor:
        def __init__(self, *, job_name, as_of, healthcheck_url):
            self.rows_written = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            rows_written_captured.append(self.rows_written)

    stubs = _make_stubs(["BHP.AU", "CBA.AU"])

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "JobMonitor", CapturingMonitor),
        patch("jobs.ingest_sentiment._aggregate_from_news", new=AsyncMock(return_value=14)),
        patch("jobs.ingest_sentiment._upstream_ok", new=AsyncMock(return_value=True)),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())

    assert rows_written_captured == [14]


def test_upstream_gate_logs_warning_not_raises() -> None:
    """_upstream_ok=False → logs WARNING but aggregation still runs (7-day window degrades gracefully)."""
    mock_aggregate = AsyncMock(return_value=5)
    stubs = _make_stubs(["BHP.AU"])

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "JobMonitor", stubs["JobMonitor"]),
        patch("jobs.ingest_sentiment._aggregate_from_news", mock_aggregate),
        patch("jobs.ingest_sentiment._upstream_ok", new=AsyncMock(return_value=False)),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())  # must not raise

    # Aggregation ran despite upstream gate miss
    mock_aggregate.assert_called_once()
