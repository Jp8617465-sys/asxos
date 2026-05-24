"""
ingest_sentiment.py job-level tests — M14b.

Patches the module-level stubs at jobs.ingest_sentiment namespace.
Pattern mirrors tests/test_ingest_news_job.py exactly.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import jobs.ingest_sentiment as job_mod


def _make_stubs(symbols: list[str], sentiments_return: list[dict] | None = None):
    """Build the standard set of test stubs for ingest_sentiment."""
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

    client = MagicMock()
    # sentiments_for_symbol returns empty list by default
    client.sentiments_for_symbol = AsyncMock(return_value=sentiments_return or [])

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
        "get_client": lambda: client,
        "JobMonitor": FakeMonitor,
        "client": client,
    }


def _run(symbols: list[str], **stub_overrides):
    stubs = _make_stubs(symbols)
    stubs.update(stub_overrides)

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "get_client", stubs["get_client"]),
        patch.object(job_mod, "JobMonitor", stubs["JobMonitor"]),
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
    """Empty current_holdings → skips ingest, no API calls."""
    stubs = _make_stubs([])
    client = MagicMock()
    client.sentiments_for_symbol = AsyncMock()

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "get_client", lambda: client),
        # JobMonitor should NOT be called — don't patch it so it would crash if called
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())

    client.sentiments_for_symbol.assert_not_called()


def test_symbol_failure_does_not_abort() -> None:
    """One symbol raising an exception doesn't prevent others from completing."""
    call_count = 0

    async def sentiments_for_symbol(symbol, *, from_date, to_date):
        nonlocal call_count
        call_count += 1
        if symbol == "FAIL.AU":
            raise RuntimeError("EODHD 503")
        return [{"date": "2026-05-23", "count": 5, "normalized": 0.2}]

    stubs = _make_stubs(["BHP.AU", "FAIL.AU", "CBA.AU"])
    stubs["client"] = MagicMock()
    stubs["client"].sentiments_for_symbol = sentiments_for_symbol

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "get_client", lambda: stubs["client"]),
        patch.object(job_mod, "JobMonitor", stubs["JobMonitor"]),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())  # must not raise

    assert call_count == 3  # all three symbols were attempted


def test_rows_written_set_correctly() -> None:
    """monitor.rows_written equals sum of upsert returns across symbols."""
    from asxos.ingestion.sentiment import SentimentEntry

    async def sentiments_for_symbol(symbol, *, from_date, to_date):
        return [{"date": "2026-05-23", "count": 5, "normalized": 0.1}]

    rows_written_captured = []

    class CapturingMonitor:
        def __init__(self, *, job_name, as_of, healthcheck_url):
            self.rows_written = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            rows_written_captured.append(self.rows_written)

    # upsert_sentiment returns len(entries) which is 1 per symbol × 2 symbols
    stubs = _make_stubs(["BHP.AU", "CBA.AU"])
    stubs["client"] = MagicMock()
    stubs["client"].sentiments_for_symbol = sentiments_for_symbol

    with (
        patch.object(job_mod, "acquire", stubs["acquire"]),
        patch.object(job_mod, "init_pool", stubs["init_pool"]),
        patch.object(job_mod, "close_pool", stubs["close_pool"]),
        patch.object(job_mod, "get_client", lambda: stubs["client"]),
        patch.object(job_mod, "JobMonitor", CapturingMonitor),
        patch("jobs.ingest_sentiment.upsert_sentiment", new=AsyncMock(return_value=1)),
        patch.dict(os.environ, {"ASXOS_PERSONAL_USE": "1"}),
    ):
        asyncio.run(job_mod.main())

    assert rows_written_captured == [2]  # 1 per symbol × 2 symbols
