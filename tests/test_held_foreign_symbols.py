"""`held_foreign_symbols` and the statements job's union — incident #327.

The incident: `HUBS.NYSE`, an approved and actively held thesis, had **zero**
`rs_financial_statements` rows, so `build_decision_case` raised "no admissible yearly
income row" for it every night and held `pipeline-health` red.

The incident's own write-up blamed `_load_symbols` appending `AND is_active`. That is
not the cause, and a fix aimed at it would not have worked: `_load_symbols` selects
`FROM rs_security_master`, which `asxos/ingestion/security_master.py` fills from
`exchange_symbols("AU")` — 4,439 rows on 2026-09-18, **every one `.AU`**. The row was
never there to be filtered out. `test_dropping_active_only_is_not_the_fix` pins that,
so nobody re-derives the wrong remedy from the issue text.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import jobs.sync_financial_statements as stmts
from asxos.domain.portfolio.holdings import held_foreign_symbols

pytestmark = pytest.mark.asyncio


class FakeConn:
    """Records every query so the test can assert which table was asked."""

    def __init__(self, master: list[str], held: list[str]) -> None:
        self.master = master
        self.held = held
        self.queries: list[str] = []

    async def fetch(self, query: str, *args: object) -> list[dict[str, str]]:
        self.queries.append(query)
        if "holding_lots" in query:
            return [{"symbol": s} for s in self.held]
        return [{"symbol": s} for s in self.master]


async def test_held_foreign_symbols_reads_open_lots_not_the_universe() -> None:
    conn = FakeConn(master=[], held=["HUBS.NYSE"])
    assert await held_foreign_symbols(conn) == ["HUBS.NYSE"]  # type: ignore[arg-type]
    (q,) = conn.queries
    assert "holding_lots" in q and "disposed_at IS NULL" in q
    # The whole point: it must not consult universe.is_active, which is FALSE for a
    # held US name by convention and would return nothing.
    assert "is_active" not in q and "universe" not in q


async def test_held_foreign_symbols_matches_every_us_suffix_not_just_dot_us() -> None:
    """fx.py's header names this exact stale-copy bug; the SQL is built from
    FOREIGN_SUFFIXES so a new suffix cannot be missed here."""
    conn = FakeConn(master=[], held=[])
    await held_foreign_symbols(conn)  # type: ignore[arg-type]
    (q,) = conn.queries
    for suffix in (".US", ".NYSE", ".NASDAQ", ".AMEX"):
        assert suffix in q


async def test_held_foreign_symbols_empty_is_a_valid_answer() -> None:
    conn = FakeConn(master=[], held=[])
    assert await held_foreign_symbols(conn) == []  # type: ignore[arg-type]


async def test_statements_job_includes_a_held_us_name_even_under_active_only() -> None:
    """The regression that was #327: --active-only is how weekly-research invokes it."""
    conn = FakeConn(master=["BHP.AU", "CBA.AU"], held=["HUBS.NYSE"])
    out = await stmts._load_symbols(conn, active_only=True, limit=None)
    assert "HUBS.NYSE" in out
    assert out[:2] == ["BHP.AU", "CBA.AU"], "the master selection keeps its order"


async def test_statements_job_does_not_duplicate_a_name_in_both_sets() -> None:
    conn = FakeConn(master=["CBA.AU", "HUBS.NYSE"], held=["HUBS.NYSE"])
    out = await stmts._load_symbols(conn, active_only=False, limit=None)
    assert out.count("HUBS.NYSE") == 1


async def test_limit_caps_the_master_but_never_drops_a_held_name() -> None:
    """A limited run must not silently reintroduce the incident."""
    conn = FakeConn(master=["AAA.AU"], held=["HUBS.NYSE"])
    out = await stmts._load_symbols(conn, active_only=True, limit=1)
    assert out == ["AAA.AU", "HUBS.NYSE"]


async def test_dropping_active_only_is_not_the_fix() -> None:
    """#327 proposed widening the is_active filter. Pinned as insufficient.

    With a master that contains no US row — which is the live shape, since the master
    is built from the AU exchange — `active_only=False` still yields nothing for
    HUBS unless the held set is unioned in. If a future change reverts to selecting
    from the master alone, this fails.
    """
    conn = FakeConn(master=["CBA.AU", "BHP.AU"], held=[])
    assert "HUBS.NYSE" not in await stmts._load_symbols(conn, active_only=False, limit=None)

    conn_with_lot = FakeConn(master=["CBA.AU", "BHP.AU"], held=["HUBS.NYSE"])
    assert "HUBS.NYSE" in await stmts._load_symbols(conn_with_lot, active_only=False, limit=None)


async def test_sync_prices_still_answers_through_the_shared_helper() -> None:
    """The extraction must not change sync_prices' behaviour."""
    import jobs.sync_prices as prices

    with patch.object(
        prices, "held_foreign_symbols", AsyncMock(return_value=["HUBS.NYSE"])
    ) as shared:
        class _Ctx:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *a: object) -> bool:
                return False

        with patch.object(prices, "acquire", lambda: _Ctx()):
            assert await prices.get_us_holding_symbols() == ["HUBS.NYSE"]
    shared.assert_awaited_once()
