"""
Tests for the EODHD ingestion layer.
No network calls — httpx client is mocked throughout.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import jobs.sync_prices as sync_prices_job
from asxos.domain.prices.fx import foreign_symbol_sql
from asxos.ingestion.eodhd import EODHDClient, _is_retryable
from asxos.ingestion.prices import (
    fetch_and_upsert_index_symbol,
    to_fx_rows,
    to_price_rows,
    to_us_price_rows,
)
from asxos.ingestion.universe import (
    _CURATED_LIC_SYMBOLS,
    _TYPE_TO_KIND,
    classify_kind,
    refresh_universe,
)

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


# ---------------------------------------------------------------------------
# Index price ingestion — benchmark framing (Phase 1.5)
# ---------------------------------------------------------------------------

_INDEX_RAW = [
    {"date": "2026-06-22", "open": 8500.0, "high": 8550.0, "low": 8480.0,
     "close": 8520.0, "volume": 0, "adjusted_close": 8520.0},
    {"date": "2026-06-23", "open": 8520.0, "high": 8560.0, "low": 8510.0,
     "close": 8540.0, "volume": 0, "adjusted_close": 8540.0},
]


@pytest.mark.asyncio
async def test_fetch_and_upsert_index_symbol_no_remap():
    """The .INDX symbol is the API symbol verbatim — no eodhd_symbol() remap,
    and rows are upserted under that exact symbol (prices→universe FK)."""
    client = MagicMock()
    client.daily_prices = AsyncMock(return_value=_INDEX_RAW)
    conn = AsyncMock()
    conn.executemany = AsyncMock()

    n = await fetch_and_upsert_index_symbol("AXJO.INDX", date(2026, 6, 22), client, conn)

    assert n == 2
    # API symbol passed verbatim (the bug we avoid: remapping AXJO.INDX)
    client.daily_prices.assert_awaited_once_with("AXJO.INDX", from_date="2026-06-22")
    # Rows upserted under the index symbol
    upsert_rows = conn.executemany.await_args.args[1]
    assert all(r[0] == "AXJO.INDX" for r in upsert_rows)
    assert {r[1] for r in upsert_rows} == {date(2026, 6, 22), date(2026, 6, 23)}


@pytest.mark.asyncio
async def test_sync_index_prices_one_failure_does_not_abort(monkeypatch):
    """A single index fetch failure is logged and skipped; others still count."""
    async def _fake_fetch(sym, _from, _client, _conn):
        if sym == "BAD.INDX":
            raise RuntimeError("boom")
        return 5

    monkeypatch.setattr(sync_prices_job, "fetch_and_upsert_index_symbol", _fake_fetch)
    total = await sync_prices_job._sync_index_prices(
        ["AXJO.INDX", "BAD.INDX"], date(2026, 6, 22), MagicMock(), AsyncMock()
    )
    assert total == 5  # AXJO succeeded (5), BAD failed (skipped)


@pytest.mark.asyncio
async def test_get_us_holding_symbols_queries_open_foreign_lots():
    """Held US symbols come from OPEN holding_lots (is_active-independent), via
    the foreign-suffix clause — so an inactive HUBS.NYSE is still fetched."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"symbol": "AAPL.US"}, {"symbol": "HUBS.NYSE"}])
    with patch.object(sync_prices_job, "acquire") as mock_acquire:
        mock_acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        out = await sync_prices_job.get_us_holding_symbols()

    assert out == ["AAPL.US", "HUBS.NYSE"]
    q = conn.fetch.await_args.args[0]
    assert "holding_lots" in q
    assert "disposed_at IS NULL" in q                  # open lots only
    assert foreign_symbol_sql("symbol") in q           # the shared foreign clause
    assert "is_active" not in q                         # independent of is_active (the bug)


@pytest.mark.asyncio
async def test_sync_index_prices_empty_list_returns_zero():
    assert await sync_prices_job._sync_index_prices(
        [], date(2026, 6, 22), MagicMock(), AsyncMock()
    ) == 0


@pytest.mark.asyncio
async def test_resolve_index_start_explicit_from_wins():
    conn = AsyncMock()
    out = await sync_prices_job._resolve_index_start(
        ["AXJO.INDX"], date(2024, 1, 1), date(2026, 6, 22), conn
    )
    assert out == date(2024, 1, 1)
    conn.fetchval.assert_not_called()  # explicit --from short-circuits the query


@pytest.mark.asyncio
async def test_resolve_index_start_no_rows_bootstraps_floor():
    # Freshly-seeded index (no prices yet) → bootstrap from the auto-backfill floor.
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=None)
    today = date(2026, 6, 22)
    out = await sync_prices_job._resolve_index_start(["AXJO.INDX"], None, today, conn)
    assert out == today - timedelta(days=sync_prices_job._MAX_AUTO_BACKFILL_DAYS)


@pytest.mark.asyncio
async def test_resolve_index_start_heals_from_own_latest_not_equity():
    # The index resumes from ITS OWN last date + 1 (the bug being prevented: it
    # must not inherit the equity start, or index-only gaps never self-heal).
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=date(2026, 6, 20))
    out = await sync_prices_job._resolve_index_start(
        ["AXJO.INDX"], None, date(2026, 6, 22), conn
    )
    assert out == date(2026, 6, 21)


@pytest.mark.asyncio
async def test_resolve_index_start_stale_clamps_to_floor():
    # A gap older than the cap heals only the floor window (operator runs --from).
    conn = AsyncMock()
    today = date(2026, 6, 22)
    conn.fetchval = AsyncMock(return_value=date(2026, 1, 1))  # >10 days stale
    out = await sync_prices_job._resolve_index_start(["AXJO.INDX"], None, today, conn)
    assert out == today - timedelta(days=sync_prices_job._MAX_AUTO_BACKFILL_DAYS)


@pytest.mark.asyncio
async def test_daily_prices_coerces_non_list_to_empty():
    # A no-data/error response can come back as {} — daily_prices must return []
    # so the per-symbol parsers never see a non-list (security hardening).
    client = EODHDClient(api_key="x")
    client._get = AsyncMock(return_value={})
    try:
        assert await client.daily_prices("AXJO.INDX") == []
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# sync_prices self-heal helpers — cadence-bug fix
# ---------------------------------------------------------------------------


def test_weekdays_in_range_incident_window_includes_thu_fri():
    """The 06-18→06-22 gap must yield missing Thu 06-18 + Fri 06-19, no weekend.

    This is the exact incident: prices frozen at Wed 06-17; the self-heal must
    fetch the dropped Thursday and Friday ASX sessions and skip Sat/Sun.
    """
    days = sync_prices_job._weekdays_in_range(date(2026, 6, 18), date(2026, 6, 22))
    assert days == [date(2026, 6, 18), date(2026, 6, 19), date(2026, 6, 22)]
    assert date(2026, 6, 20) not in days  # Sat
    assert date(2026, 6, 21) not in days  # Sun


def test_weekdays_in_range_single_weekday():
    assert sync_prices_job._weekdays_in_range(
        date(2026, 6, 18), date(2026, 6, 18)
    ) == [date(2026, 6, 18)]


def test_weekdays_in_range_single_weekend_day_is_empty():
    assert sync_prices_job._weekdays_in_range(date(2026, 6, 20), date(2026, 6, 20)) == []


def test_weekdays_in_range_start_after_end_is_empty():
    # Already current (latest >= today) → nothing to fetch.
    assert sync_prices_job._weekdays_in_range(date(2026, 6, 23), date(2026, 6, 22)) == []


@pytest.mark.asyncio
async def test_resolve_start_explicit_from_passthrough():
    """--from wins verbatim; the DB anchor is never consulted (unbounded backfill)."""
    anchor = AsyncMock(return_value=date(2020, 1, 1))
    with patch.object(sync_prices_job, "latest_observed_price_date", new=anchor):
        start = await sync_prices_job._resolve_start(
            date(2024, 3, 1), date(2026, 6, 22), MagicMock()
        )
    assert start == date(2024, 3, 1)
    anchor.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_start_self_heals_from_day_after_latest():
    """Default mode resumes from MAX(prices.dt)+1 — Wed 06-17 → Thu 06-18."""
    with patch.object(
        sync_prices_job,
        "latest_observed_price_date",
        new=AsyncMock(return_value=date(2026, 6, 17)),
    ):
        start = await sync_prices_job._resolve_start(None, date(2026, 6, 22), MagicMock())
    assert start == date(2026, 6, 18)


@pytest.mark.asyncio
async def test_resolve_start_no_prices_bootstraps_to_floor():
    with patch.object(
        sync_prices_job,
        "latest_observed_price_date",
        new=AsyncMock(return_value=None),
    ):
        start = await sync_prices_job._resolve_start(None, date(2026, 6, 22), MagicMock())
    assert start == date(2026, 6, 22) - timedelta(
        days=sync_prices_job._MAX_AUTO_BACKFILL_DAYS
    )


@pytest.mark.asyncio
async def test_resolve_start_stale_gap_clamps_to_floor_and_warns(caplog):
    today = date(2026, 6, 22)
    with patch.object(
        sync_prices_job,
        "latest_observed_price_date",
        new=AsyncMock(return_value=date(2026, 1, 1)),
    ), caplog.at_level("WARNING"):
        start = await sync_prices_job._resolve_start(None, today, MagicMock())
    assert start == today - timedelta(days=sync_prices_job._MAX_AUTO_BACKFILL_DAYS)
    assert "full backfill" in caplog.text


# ---------------------------------------------------------------------------
# refresh_universe — multi-instrument kind tagging (ETF Phase-2 Slice 2a)
#
# The pollution firewall this branch relies on: funds (ETF/LIC/hybrid) are kept
# OUT of Model A's universe by their security_kind, NOT by is_active. The kind is
# assigned here at ingestion; the 8 ML/screening readers (already on main) filter
# `security_kind = 'au_equity'`. So the writer-level invariant this suite pins is:
# no fund is ever tagged au_equity. See docs/proposals/multi-instrument-
# expansion-2026-07-11.md §7 and asxos/ingestion/universe.py.
# ---------------------------------------------------------------------------


def _mk_universe_conn(existing_rows):
    """AsyncMock conn: .fetch returns the existing-universe rows, .execute records calls."""
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=existing_rows)
    conn.execute = AsyncMock()
    return conn


def _captured_inserts(conn):
    """Return [(sym, name, sector, kind), ...] for every INSERT INTO universe call."""
    out = []
    for call in conn.execute.await_args_list:
        sql = call.args[0]
        if "INSERT INTO universe" in sql:
            out.append(call.args[1:])
    return out


@pytest.mark.asyncio
async def test_refresh_universe_tags_kinds_by_eodhd_type():
    """Each ingested EODHD Type lands with the mapped security_kind."""
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "BHP", "Name": "BHP Group", "Type": "Common Stock", "Sector": "Materials"},
        {"Code": "VAS", "Name": "Vanguard AU Shares", "Type": "ETF", "Sector": ""},
        {"Code": "ARG", "Name": "Argo Investments", "Type": "FUND", "Sector": ""},
        {"Code": "XYZPR", "Name": "Some Pref", "Type": "Preferred Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[])  # empty universe

    counts = await refresh_universe(client, conn)

    kind_by_sym = {ins[0]: ins[3] for ins in _captured_inserts(conn)}
    assert kind_by_sym == {
        "BHP.AU": "au_equity",
        "VAS.AU": "etf",
        "ARG.AU": "lic",
        "XYZPR.AU": "hybrid",
    }
    assert counts["added"] == 4


@pytest.mark.asyncio
async def test_refresh_universe_skips_unmapped_types():
    """Types outside _TYPE_TO_KIND (rights, warrants, unclassified) are never ingested."""
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "BHP", "Name": "BHP", "Type": "Common Stock", "Sector": ""},
        {"Code": "RGHT", "Name": "Some Right", "Type": "Right", "Sector": ""},
        {"Code": "WAR", "Name": "A Warrant", "Type": "Warrant", "Sector": ""},
        {"Code": "MYST", "Name": "Unclassified", "Type": "", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[])

    counts = await refresh_universe(client, conn)

    assert {ins[0] for ins in _captured_inserts(conn)} == {"BHP.AU"}
    assert counts["added"] == 1


@pytest.mark.asyncio
async def test_refresh_universe_funds_never_land_as_au_equity():
    """The pollution firewall at the writer: no ETF/LIC/hybrid row is tagged
    au_equity, so the kind-scoped ML readers can never pull a fund into Model A."""
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "VAS", "Name": "ETF", "Type": "ETF", "Sector": ""},
        {"Code": "ARG", "Name": "LIC", "Type": "FUND", "Sector": ""},
        {"Code": "NOTE", "Name": "Note", "Type": "Notes", "Sector": ""},
        {"Code": "BND", "Name": "Bond", "Type": "BOND", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[])

    await refresh_universe(client, conn)

    inserts = _captured_inserts(conn)
    assert inserts, "expected fund rows to be inserted"
    for sym, _name, _sector, kind in inserts:
        assert kind != "au_equity", f"{sym} tagged au_equity — would pollute Model A"
        assert kind in set(_TYPE_TO_KIND.values())


@pytest.mark.asyncio
async def test_refresh_universe_delists_absent_active_skips_inactive_out_of_band():
    """An active, now-absent symbol is delisted; an already-inactive out-of-band
    row (e.g. a held US equity) is left untouched by the `and is_active` guard."""
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "BHP", "Name": "BHP", "Type": "Common Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[
        {"symbol": "BHP.AU", "is_active": True, "security_kind": "au_equity"},   # still listed → unchanged
        {"symbol": "CBA.AU", "is_active": True, "security_kind": "au_equity"},   # active, now absent → delist
        {"symbol": "HUBS.NYSE", "is_active": False, "security_kind": "us_equity"},  # inactive out-of-band → skip
    ])

    counts = await refresh_universe(client, conn)

    delisted = [
        call.args[1]
        for call in conn.execute.await_args_list
        if "is_active = FALSE" in call.args[0]
    ]
    assert delisted == ["CBA.AU"]
    assert "HUBS.NYSE" not in delisted
    assert counts["delisted"] == 1
    assert counts["unchanged"] == 1


@pytest.mark.asyncio
async def test_refresh_universe_reactivates_relisted_symbol():
    """A previously-delisted (is_active=FALSE) symbol that reappears is reactivated,
    not re-inserted (no duplicate row)."""
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "TLS", "Name": "Telstra", "Type": "Common Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[{"symbol": "TLS.AU", "is_active": False, "security_kind": "au_equity"}])

    counts = await refresh_universe(client, conn)

    assert _captured_inserts(conn) == []  # no INSERT — the row already exists
    reactivated = [
        call.args[1]
        for call in conn.execute.await_args_list
        if "is_active = TRUE" in call.args[0]
    ]
    assert reactivated == ["TLS.AU"]
    assert counts["reactivated"] == 1


# ---------------------------------------------------------------------------
# refresh_universe — curated LIC reclassification (2026-09-18)
#
# EODHD types every ASX listed investment company as "Common Stock", so LICs landed as
# au_equity and entered the residual-income sweep, whose valuation of a LIC is circular
# (its book value IS a marked securities portfolio). Six of the sixteen names the weekly
# scan surfaced on 2026-09-16 were LICs. These pin both halves of the fix: new rows
# classify correctly, and — because security_kind was otherwise written ONLY on INSERT —
# already-wrong rows are reconciled.
# ---------------------------------------------------------------------------


def _captured_updates(conn, needle):
    return [c.args for c in conn.execute.await_args_list if needle in c.args[0]]


@pytest.mark.asyncio
async def test_curated_lic_overrides_common_stock_on_insert():
    """A curated LIC typed "Common Stock" by EODHD is inserted as lic, not au_equity."""
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "WQG", "Name": "WCM Global Growth Ltd", "Type": "Common Stock", "Sector": ""},
        {"Code": "LSF", "Name": "L1 Long Short Fund Ltd", "Type": "Common Stock", "Sector": ""},
        {"Code": "BHP", "Name": "BHP Group Ltd", "Type": "Common Stock", "Sector": "Materials"},
    ])
    conn = _mk_universe_conn(existing_rows=[])

    await refresh_universe(client, conn)

    kind_by_sym = {ins[0]: ins[3] for ins in _captured_inserts(conn)}
    assert kind_by_sym == {"WQG.AU": "lic", "LSF.AU": "lic", "BHP.AU": "au_equity"}


@pytest.mark.asyncio
async def test_curated_lic_reconciles_an_already_misclassified_row():
    """The live defect: a curated LIC already stored as au_equity is corrected in place.

    security_kind is written only on INSERT, so without the reconcile branch this row stays
    au_equity forever and keeps re-entering the valuation sweep every week.
    """
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "FGX", "Name": "Future Generation Australia Ltd", "Type": "Common Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(
        existing_rows=[{"symbol": "FGX.AU", "is_active": True, "security_kind": "au_equity"}]
    )

    counts = await refresh_universe(client, conn)

    updates = _captured_updates(conn, "security_kind = $2")
    assert [(u[1], u[2]) for u in updates] == [("FGX.AU", "lic")]
    assert counts["reclassified"] == 1
    assert counts["unchanged"] == 1


@pytest.mark.asyncio
async def test_reclassification_is_idempotent():
    """Re-running over rows that already match writes nothing.

    Was ``..._and_narrow`` until A-51: the branch no longer corrects only TO 'lic', so the
    narrowness this used to assert is gone and the guard that replaced it is
    ``_VENDOR_OWNED_KINDS`` — see the hand-set-row tests below. What survives unchanged is
    the idempotence: a row whose stored kind already equals its classified kind is not
    rewritten, so a correct universe produces zero writes every week.
    """
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "FGX", "Name": "Future Generation Australia Ltd", "Type": "Common Stock", "Sector": ""},
        {"Code": "BHP", "Name": "BHP Group Ltd", "Type": "Common Stock", "Sector": "Materials"},
    ])
    conn = _mk_universe_conn(existing_rows=[
        {"symbol": "FGX.AU", "is_active": True, "security_kind": "lic"},        # already correct
        {"symbol": "BHP.AU", "is_active": True, "security_kind": "au_equity"},  # not curated
    ])

    counts = await refresh_universe(client, conn)

    assert _captured_updates(conn, "security_kind") == []
    assert counts["reclassified"] == 0


# refresh_universe — generalised kind reconcile (A-51, 2026-09-24)
#
# A-49 fixed the reconcile narrowly on purpose: only TO 'lic', only for a curated symbol.
# That left the general case open — `security_kind` is written only on INSERT, so a symbol
# EODHD retypes keeps its original kind forever, exactly the permanent silent wrongness the
# six LICs demonstrated. The generalisation needs a rule for what a vendor feed is allowed
# to overwrite, and `_VENDOR_OWNED_KINDS` is that rule.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_vendor_retype_is_applied():
    """The case A-51 exists for: EODHD retypes a stored au_equity as an ETF.

    Before this, the row kept `au_equity` forever — no code path rewrites `security_kind`
    after INSERT.
    """
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "VAS", "Name": "Vanguard Australian Shares Index ETF", "Type": "ETF", "Sector": ""},
    ])
    conn = _mk_universe_conn(
        existing_rows=[{"symbol": "VAS.AU", "is_active": True, "security_kind": "au_equity"}]
    )

    counts = await refresh_universe(client, conn)

    updates = _captured_updates(conn, "security_kind = $2")
    assert [(u[1], u[2]) for u in updates] == [("VAS.AU", "etf")]
    assert counts["reclassified"] == 1


@pytest.mark.asyncio
async def test_a_hand_set_kind_is_never_rewritten_by_the_feed():
    """The safety rule, tested directly rather than via the suffix argument.

    `us_equity` and `index` are hand-set out of band and are not values EODHD's Type field
    can produce, so the feed has no opinion about them. Today such a row is ALSO unreachable
    because `incoming` only ever holds `.AU` symbols — this test deliberately puts one in
    `incoming` anyway, so the guard is what is being tested and not the loop's domain.
    """
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "HUBS.NYSE", "Name": "HubSpot Inc", "Type": "Common Stock", "Sector": "Technology"},
        {"Code": "AXJO.INDX", "Name": "S&P/ASX 200", "Type": "Common Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[
        {"symbol": "HUBS.NYSE", "is_active": False, "security_kind": "us_equity"},
        {"symbol": "AXJO.INDX", "is_active": False, "security_kind": "index"},
    ])

    counts = await refresh_universe(client, conn)

    assert _captured_updates(conn, "security_kind = $2") == []
    assert counts["reclassified"] == 0


@pytest.mark.asyncio
async def test_a_curated_lic_cannot_be_retyped_back_to_au_equity():
    """Ordering that matters now that the branch is general.

    `classify_kind` applies the curated override AFTER the type map, so EODHD typing a
    curated LIC as "Common Stock" — which is exactly what it does for every ASX LIC — still
    classifies as `lic`. Without that ordering the generalisation would undo A-49 weekly.
    """
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "FGX", "Name": "Future Generation Australia Ltd", "Type": "Common Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(
        existing_rows=[{"symbol": "FGX.AU", "is_active": True, "security_kind": "lic"}]
    )

    counts = await refresh_universe(client, conn)

    assert _captured_updates(conn, "security_kind = $2") == []
    assert counts["reclassified"] == 0


@pytest.mark.asyncio
async def test_a_retype_that_is_not_a_lic_correction_is_logged(caplog):
    """No vendor retype has ever been observed, so the first one should be visible.

    A silent weekly rewrite is how a flapping vendor type would go unnoticed; the LIC
    correction is the expected, already-understood case and stays quiet.
    """
    client = MagicMock()
    client.exchange_symbols = AsyncMock(return_value=[
        {"Code": "VAS", "Name": "Vanguard Australian Shares Index ETF", "Type": "ETF", "Sector": ""},
        {"Code": "FGX", "Name": "Future Generation Australia Ltd", "Type": "Common Stock", "Sector": ""},
    ])
    conn = _mk_universe_conn(existing_rows=[
        {"symbol": "VAS.AU", "is_active": True, "security_kind": "au_equity"},
        {"symbol": "FGX.AU", "is_active": True, "security_kind": "au_equity"},
    ])

    with caplog.at_level(logging.WARNING, logger="asxos.ingestion.universe"):
        counts = await refresh_universe(client, conn)

    assert counts["reclassified"] == 2
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1, warnings
    assert "VAS.AU" in warnings[0] and "au_equity -> etf" in warnings[0]


@pytest.mark.asyncio
async def test_areits_and_property_operators_stay_au_equity():
    """A-REITs and property operators are deliberately NOT reclassified.

    portfolio/build.py::forced_sell_inactive_symbols relies on A-REITs staying au_equity so a
    genuine delisting is still force-sold, and a REIT's book is marked property rather than
    marked securities, so the circularity argument does not carry. CWP is an operating
    homebuilder that a name-based matcher would have wrongly caught.
    """
    for sym in ("BWP.AU", "ARF.AU", "CQR.AU", "GOZ.AU", "WPR.AU", "CWP.AU", "AXI.AU"):
        assert sym not in _CURATED_LIC_SYMBOLS
        assert classify_kind(sym, "Common Stock") == "au_equity"


def test_curated_set_contains_the_six_that_reached_the_candidate_scan():
    """The measured defect, pinned: the six LICs in the 2026-09-16 passing set of sixteen."""
    assert {"FGG.AU", "FGX.AU", "HM1.AU", "LSF.AU", "PGF.AU", "WQG.AU"} <= _CURATED_LIC_SYMBOLS


def test_curated_symbols_are_exchange_qualified():
    """Every entry must carry the .AU suffix _to_symbol produces, or the override never fires."""
    assert all(s.endswith(".AU") for s in _CURATED_LIC_SYMBOLS)
