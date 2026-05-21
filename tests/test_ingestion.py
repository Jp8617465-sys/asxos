"""
Tests for the EODHD ingestion layer.
No network calls — httpx client is mocked throughout.
"""
from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from asxos.ingestion.eodhd import EODHDClient, _is_retryable
from asxos.ingestion.prices import to_price_rows


# ---------------------------------------------------------------------------
# _is_retryable
# ---------------------------------------------------------------------------

def _status_error(status: int) -> httpx.HTTPStatusError:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    return httpx.HTTPStatusError("err", request=MagicMock(), response=resp)


def test_retryable_on_429():
    assert _is_retryable(_status_error(429))


def test_retryable_on_503():
    assert _is_retryable(_status_error(503))


def test_not_retryable_on_404():
    assert not _is_retryable(_status_error(404))


def test_retryable_on_request_error():
    assert _is_retryable(httpx.ConnectError("timeout"))


# ---------------------------------------------------------------------------
# EODHDClient._get — URL construction and auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_adds_api_token():
    captured = {}

    async def fake_get(url: str, *, params: dict, **kw):
        captured["params"] = params
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json = lambda: []
        return resp

    client = EODHDClient(api_key="testkey123")
    client._client.get = fake_get  # type: ignore[method-assign]

    await client.exchange_symbols("AU")

    assert captured["params"]["api_token"] == "testkey123"
    assert captured["params"]["fmt"] == "json"


@pytest.mark.asyncio
async def test_client_retries_on_429():
    call_count = 0

    async def flaky_get(url: str, *, params: dict, **kw):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 429
            raise httpx.HTTPStatusError("rate limited", request=MagicMock(), response=resp)
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = lambda: None
        resp.json = lambda: [{"Code": "BHP", "Type": "Common Stock"}]
        return resp

    client = EODHDClient(api_key="testkey")
    client._client.get = flaky_get  # type: ignore[method-assign]

    # Patch wait to avoid sleeping in tests
    with patch("asxos.ingestion.eodhd.wait_exponential", return_value=lambda _: 0):
        result = await client.exchange_symbols("AU")

    assert call_count == 2
    assert result[0]["Code"] == "BHP"


# ---------------------------------------------------------------------------
# to_price_rows — filtering logic
# ---------------------------------------------------------------------------

_UNIVERSE = {"BHP.AU", "CBA.AU", "ANZ.AU"}

_BULK_RAW = [
    {"code": "BHP.AU", "date": "2026-05-20", "open": 44.0, "high": 45.0, "low": 43.5, "close": 44.5, "volume": 1_000_000, "adjusted_close": 44.5},
    {"code": "CBA.AU", "date": "2026-05-20", "open": 120.0, "high": 121.0, "low": 119.0, "close": 120.5, "volume": 500_000, "adjusted_close": 120.5},
    {"code": "XYZ.AU", "date": "2026-05-20", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100, "adjusted_close": 1.0},  # not in universe
    {"code": "ANZ.AU", "date": "2026-05-20", "open": None, "high": None, "low": None, "close": None, "volume": None, "adjusted_close": None},  # no close
]


def test_to_price_rows_filters_non_universe():
    rows = to_price_rows(_BULK_RAW, _UNIVERSE)
    symbols = {r[0] for r in rows}
    assert "XYZ.AU" not in symbols


def test_to_price_rows_filters_missing_close():
    rows = to_price_rows(_BULK_RAW, _UNIVERSE)
    symbols = {r[0] for r in rows}
    assert "ANZ.AU" not in symbols


def test_to_price_rows_correct_columns():
    rows = to_price_rows(_BULK_RAW, _UNIVERSE)
    bhp = next(r for r in rows if r[0] == "BHP.AU")
    assert bhp[0] == "BHP.AU"
    assert bhp[1] == date(2026, 5, 20)
    assert float(bhp[5]) == 44.5   # close


def test_to_price_rows_normalises_symbol_without_suffix():
    raw = [{"code": "BHP", "date": "2026-05-20", "close": 44.5, "open": None, "high": None, "low": None, "volume": None, "adjusted_close": None}]
    rows = to_price_rows(raw, {"BHP.AU"})
    assert len(rows) == 1
    assert rows[0][0] == "BHP.AU"
