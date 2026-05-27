"""
Tests for the EODHD ingestion layer.
No network calls — httpx client is mocked throughout.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest

from asxos.ingestion.eodhd import EODHDClient, _is_retryable
from asxos.ingestion.prices import to_fx_rows, to_price_rows, to_us_price_rows

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


# ---------------------------------------------------------------------------
# M15-1 — _to_symbol exchange parameter
# ---------------------------------------------------------------------------

def test_to_price_rows_us_exchange_appends_us_suffix():
    """Bare EODHD code 'AAPL' with exchange='US' must map to 'AAPL.US', not 'AAPL.AU'."""
    raw = [{"code": "AAPL", "date": "2026-05-20", "close": 189.5, "open": None, "high": None, "low": None, "volume": None, "adjusted_close": None}]
    rows = to_price_rows(raw, {"AAPL.US"}, exchange="US")
    assert len(rows) == 1
    assert rows[0][0] == "AAPL.US"


def test_to_price_rows_bare_code_default_is_au():
    """Default exchange is 'AU' — existing behaviour must not regress."""
    raw = [{"code": "CBA", "date": "2026-05-20", "close": 120.5, "open": None, "high": None, "low": None, "volume": None, "adjusted_close": None}]
    rows = to_price_rows(raw, {"CBA.AU"})
    assert rows[0][0] == "CBA.AU"


def test_to_price_rows_preserves_code_with_existing_dot():
    """If EODHD returns 'BHP.AU' (already has dot), no extra suffix is appended."""
    raw = [{"code": "BHP.AU", "date": "2026-05-20", "close": 44.5, "open": None, "high": None, "low": None, "volume": None, "adjusted_close": None}]
    rows = to_price_rows(raw, {"BHP.AU"})
    assert rows[0][0] == "BHP.AU"


# ---------------------------------------------------------------------------
# M15-4 — to_fx_rows
# ---------------------------------------------------------------------------

_FX_RAW = [
    {"date": "2026-05-20", "open": 0.6350, "high": 0.6400, "low": 0.6300, "close": 0.6380, "volume": 0},
    {"date": "2026-05-21", "close": 0.6410, "open": 0.6380, "high": 0.6430, "low": 0.6370, "volume": 0},
    {"date": "2026-05-22", "close": None, "open": 0.6400},   # no close — should be skipped
    {"close": 0.6420, "open": 0.6400},                       # no date — should be skipped
]


def test_to_fx_rows_parses_close_and_date():
    rows = to_fx_rows(_FX_RAW, pair="AUDUSD")
    assert len(rows) == 2
    # First row
    assert rows[0][0] == "AUDUSD"
    assert rows[0][1] == date(2026, 5, 20)
    assert rows[0][2] == 0.6380


def test_to_fx_rows_skips_missing_close():
    rows = to_fx_rows(_FX_RAW, pair="AUDUSD")
    dates = {r[1] for r in rows}
    assert date(2026, 5, 22) not in dates


def test_to_fx_rows_skips_missing_date():
    rows = to_fx_rows(_FX_RAW, pair="AUDUSD")
    # Item with no date key — no crash, just skipped
    assert len(rows) == 2


def test_to_fx_rows_empty_input_returns_empty():
    assert to_fx_rows([], pair="AUDUSD") == []


def test_to_fx_rows_pair_label_stored():
    raw = [{"date": "2026-05-20", "close": 0.6380}]
    rows = to_fx_rows(raw, pair="AUDUSD")
    assert rows[0][0] == "AUDUSD"


# ---------------------------------------------------------------------------
# M15-5 — to_us_price_rows
# ---------------------------------------------------------------------------

_US_RAW = [
    {"date": "2026-05-20", "open": 188.5, "high": 190.0, "low": 187.0, "close": 189.5, "volume": 55_000_000, "adjusted_close": 189.5},
    {"date": "2026-05-21", "open": 190.0, "high": 191.5, "low": 189.0, "close": 191.0, "volume": 48_000_000, "adjusted_close": 191.0},
    {"date": "2026-05-22", "open": 192.0, "close": None},   # no close
]


def test_to_us_price_rows_uses_provided_symbol():
    """Symbol comes from the kwarg, not from the item dict (no 'code' key in per-symbol response)."""
    rows = to_us_price_rows(_US_RAW, symbol="AAPL.US")
    assert all(r[0] == "AAPL.US" for r in rows)


def test_to_us_price_rows_skips_missing_close():
    rows = to_us_price_rows(_US_RAW, symbol="AAPL.US")
    assert len(rows) == 2
    dates = {r[1] for r in rows}
    assert date(2026, 5, 22) not in dates


def test_to_us_price_rows_correct_column_order():
    rows = to_us_price_rows(_US_RAW[:1], symbol="AAPL.US")
    r = rows[0]
    assert r[0] == "AAPL.US"       # symbol
    assert r[1] == date(2026, 5, 20)  # dt
    assert r[2] == 188.5           # open
    assert r[3] == 190.0           # high
    assert r[4] == 187.0           # low
    assert r[5] == 189.5           # close
    assert r[6] == 55_000_000      # volume
    assert r[7] == 189.5           # adjusted_close


def test_to_us_price_rows_empty_input_returns_empty():
    assert to_us_price_rows([], symbol="AAPL.US") == []
