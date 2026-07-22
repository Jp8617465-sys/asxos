"""Tests for research-store security-master ingestion (refresh_security_master).

No network, no DB — the EODHD client and asyncpg connection are faked. These
encode the acceptance criteria in docs/research/sync-security-master-scope.md §5.
"""
from __future__ import annotations

import pytest

from asxos.ingestion.security_master import refresh_security_master


class FakeClient:
    """Stand-in for EODHDClient returning canned symbol lists."""

    def __init__(self, active: list[dict], delisted: list[dict]) -> None:
        self._active = active
        self._delisted = delisted

    async def exchange_symbols(self, exchange: str = "AU") -> list[dict]:
        return self._active

    async def exchange_symbols_delisted(self, exchange: str = "AU") -> list[dict]:
        return self._delisted


class FakeConn:
    """Records every SQL string + args; serves a canned existing-rows snapshot."""

    def __init__(self, existing: list[dict] | None = None) -> None:
        self._existing = existing or []
        self.fetched: list[str] = []
        self.executed: list[tuple[str, tuple]] = []

    async def fetch(self, sql: str, *args):
        self.fetched.append(sql)
        return self._existing

    async def execute(self, sql: str, *args):
        self.executed.append((sql, args))

    async def executemany(self, sql: str, rows):
        # One `executed` entry per row — keeps _executed_map() and every
        # per-row assertion identical after the 2026-07-21 switch from a
        # per-row execute loop to a single executemany (07-18 audit).
        for row in rows:
            self.executed.append((sql, tuple(row)))


def _row(code, name="X", typ="Common Stock", currency="AUD", isin="AU000X"):
    return {"Code": code, "Name": name, "Type": typ, "Currency": currency, "Isin": isin}


# is_active is the 6th positional UPSERT arg (index 5); security_type is index 3.
def _executed_map(conn: FakeConn) -> dict[str, tuple]:
    return {args[0]: args for _sql, args in conn.executed}


@pytest.mark.asyncio
async def test_active_and_delisted_coverage():
    client = FakeClient(active=[_row("CBA"), _row("BHP")], delisted=[_row("OLD1")])
    conn = FakeConn(existing=[])
    counts = await refresh_security_master(client, conn)

    assert counts["active"] == 2
    assert counts["delisted"] == 1
    assert counts["inserted"] == 3
    m = _executed_map(conn)
    assert m["CBA.AU"][5] is True   # is_active
    assert m["BHP.AU"][5] is True
    assert m["OLD1.AU"][5] is False


@pytest.mark.asyncio
async def test_idempotent_rerun_no_inserts():
    """Second run (all symbols already present) inserts nothing, updates all."""
    client = FakeClient(active=[_row("CBA"), _row("BHP")], delisted=[_row("OLD1")])
    conn = FakeConn(existing=[
        {"symbol": "CBA.AU", "is_active": True},
        {"symbol": "BHP.AU", "is_active": True},
        {"symbol": "OLD1.AU", "is_active": False},
    ])
    counts = await refresh_security_master(client, conn)
    assert counts["inserted"] == 0
    assert counts["updated"] == 3


@pytest.mark.asyncio
async def test_upsert_is_on_conflict_symbol():
    client = FakeClient(active=[_row("CBA")], delisted=[])
    conn = FakeConn()
    await refresh_security_master(client, conn)
    assert all("ON CONFLICT (symbol) DO UPDATE" in sql for sql, _ in conn.executed)


@pytest.mark.asyncio
async def test_does_not_touch_universe():
    """No SQL — read or write — may reference the production `universe` table."""
    client = FakeClient(active=[_row("CBA")], delisted=[_row("OLD1")])
    conn = FakeConn()
    await refresh_security_master(client, conn)
    all_sql = conn.fetched + [sql for sql, _ in conn.executed]
    assert all("universe" not in sql.lower() for sql in all_sql)
    assert any("rs_security_master" in sql for sql in all_sql)


@pytest.mark.asyncio
async def test_duplicate_code_active_wins():
    """A code in both lists is written once, as active (currently listed)."""
    client = FakeClient(active=[_row("DUP")], delisted=[_row("DUP")])
    conn = FakeConn()
    counts = await refresh_security_master(client, conn)
    m = _executed_map(conn)
    assert list(m.keys()).count("DUP.AU") == 1
    assert len([s for s, _ in conn.executed if s]) == 1  # only one upsert
    assert m["DUP.AU"][5] is True
    assert counts["active"] == 1 and counts["delisted"] == 0


@pytest.mark.asyncio
async def test_missing_or_blank_code_skipped():
    client = FakeClient(
        active=[_row("CBA"), {"Name": "no code"}, _row("")],
        delisted=[],
    )
    conn = FakeConn()
    counts = await refresh_security_master(client, conn)
    assert counts["skipped_no_code"] == 2
    assert counts["inserted"] == 1
    assert set(_executed_map(conn)) == {"CBA.AU"}


@pytest.mark.asyncio
async def test_relisting_flips_is_active():
    """Previously-delisted symbol now in the active list flips to active."""
    client = FakeClient(active=[_row("BACK")], delisted=[])
    conn = FakeConn(existing=[{"symbol": "BACK.AU", "is_active": False}])
    counts = await refresh_security_master(client, conn)
    assert counts["relisted"] == 1
    assert _executed_map(conn)["BACK.AU"][5] is True


@pytest.mark.asyncio
async def test_stores_all_security_types():
    """ETF/FUND etc. are stored verbatim, not filtered out like `universe`."""
    client = FakeClient(
        active=[_row("ETF1", typ="ETF"), _row("FND1", typ="FUND")],
        delisted=[],
    )
    conn = FakeConn()
    await refresh_security_master(client, conn)
    m = _executed_map(conn)
    assert m["ETF1.AU"][3] == "ETF"     # security_type
    assert m["FND1.AU"][3] == "FUND"


@pytest.mark.asyncio
async def test_to_symbol_suffix_applied():
    client = FakeClient(active=[_row("BHP")], delisted=[])
    conn = FakeConn()
    await refresh_security_master(client, conn)
    assert "BHP.AU" in _executed_map(conn)


@pytest.mark.asyncio
async def test_isin_coalesce_passes_none_when_blank():
    """Blank ISIN is passed as None so the UPSERT COALESCE preserves any prior value."""
    client = FakeClient(active=[_row("CBA", isin="")], delisted=[])
    conn = FakeConn()
    await refresh_security_master(client, conn)
    assert _executed_map(conn)["CBA.AU"][4] is None   # isin arg
