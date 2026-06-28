"""Tests for PortfolioService.persist() — asxos/domain/portfolio/build.py.

Covers the M13.6 DB write path (plan H.2 QUICK-WIN-5/-7):
  - idempotent DELETE-then-reinsert keyed on (profile_id, as_of)
  - RETURNING run_id (not currval())
  - both executemany batch inserts (target_allocations, proposed_trades)
  - the whole thing wrapped in a single conn.transaction() CM

Mocks asyncpg connections; no real DB. asyncio_mode = "auto" in
pyproject.toml — no @pytest.mark.asyncio marker needed.

NOTE: build.py imports domain modules (allocator/constraints/rebalance/
tax_overlay) that are Decimal-only and dependency-light, so this file
import-collects cleanly even in the bare sandbox.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from asxos.domain.portfolio.build import PortfolioService
from asxos.domain.portfolio.types import (
    AllocationTarget,
    ProposedTrade,
    RebalanceResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AS_OF = date(2026, 6, 28)
_SIGNALS_AS_OF = date(2026, 6, 27)


def _make_profile(profile_id: int = 7) -> MagicMock:
    """A duck-typed Profile — persist() only reads profile_id + capital_aud."""
    profile = MagicMock()
    profile.profile_id = profile_id
    profile.capital_aud = Decimal("100000.000000")
    return profile


def _make_target(symbol: str = "CBA.AU") -> AllocationTarget:
    return AllocationTarget(
        symbol=symbol,
        sector="Financials",
        target_weight=Decimal("0.050000"),
        inv_vol_score=Decimal("12.500000"),
        signal_label="buy",
        prob_up=Decimal("0.610000"),
        expected_return=Decimal("0.034000"),
        constraint_log={"sector_cap": "applied"},
    )


def _make_trade(symbol: str = "CBA.AU", side: str = "buy") -> ProposedTrade:
    return ProposedTrade(
        symbol=symbol,
        side=side,  # type: ignore[arg-type]
        delta_qty=Decimal("50.000000"),
        delta_aud=Decimal("5000.000000"),
        target_qty=Decimal("50.000000"),
        current_qty=Decimal("0.000000"),
        reference_price=Decimal("100.000000"),
        rationale_tags={"reason": "rebalance"},
        lot_hints={},
    )


def _make_result(
    *,
    profile_id: int = 7,
    targets: list[AllocationTarget] | None = None,
    trades: list[ProposedTrade] | None = None,
    model_version: str = "v1_5",
) -> RebalanceResult:
    return RebalanceResult(
        run_id=None,
        as_of=_AS_OF,
        signals_as_of=_SIGNALS_AS_OF,
        profile=_make_profile(profile_id),
        targets=targets if targets is not None else [_make_target()],
        trades=trades if trades is not None else [_make_trade()],
        summary={"model_version": model_version},
    )


def _make_conn(run_id: int = 42) -> MagicMock:
    """Mock asyncpg conn. transaction() is an async CM; the write methods
    are AsyncMocks so we can assert await args.
    """
    tx_entered = {"count": 0}

    @asynccontextmanager
    async def _tx():
        tx_entered["count"] += 1
        yield

    conn = MagicMock()
    conn.transaction = _tx
    conn._tx_entered = tx_entered
    conn.execute = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(return_value={"run_id": run_id})
    conn.executemany = AsyncMock(return_value=None)
    return conn


# ---------------------------------------------------------------------------
# 1. Returns the run_id from RETURNING (not currval)
# ---------------------------------------------------------------------------

async def test_persist_returns_run_id_from_returning() -> None:
    conn = _make_conn(run_id=99)
    result = _make_result()

    run_id = await PortfolioService().persist(conn, result)

    assert run_id == 99
    # The header INSERT must use RETURNING run_id, fetched via fetchrow.
    insert_sql = conn.fetchrow.await_args.args[0]
    assert "INSERT INTO rebalance_runs" in insert_sql
    assert "RETURNING run_id" in insert_sql


# ---------------------------------------------------------------------------
# 2. Idempotent DELETE keyed on (profile_id, as_of) runs before insert
# ---------------------------------------------------------------------------

async def test_persist_deletes_existing_run_first() -> None:
    conn = _make_conn()
    result = _make_result(profile_id=7)

    await PortfolioService().persist(conn, result)

    conn.execute.assert_awaited_once()
    delete_sql, profile_id, as_of = conn.execute.await_args.args
    assert "DELETE FROM rebalance_runs" in delete_sql
    assert "profile_id = $1 AND as_of = $2" in delete_sql
    assert profile_id == 7
    assert as_of == _AS_OF


# ---------------------------------------------------------------------------
# 3. The whole write happens inside a single transaction CM
# ---------------------------------------------------------------------------

async def test_persist_wraps_writes_in_transaction() -> None:
    conn = _make_conn()
    await PortfolioService().persist(conn, _make_result())

    assert conn._tx_entered["count"] == 1


# ---------------------------------------------------------------------------
# 4. target_allocations executemany — one row per target, correct shape
# ---------------------------------------------------------------------------

async def test_persist_batch_inserts_target_allocations() -> None:
    conn = _make_conn(run_id=42)
    targets = [_make_target("CBA.AU"), _make_target("BHP.AU")]
    result = _make_result(targets=targets, trades=[])

    await PortfolioService().persist(conn, result)

    # Two executemany calls: targets first, trades second.
    target_call = conn.executemany.await_args_list[0]
    sql = target_call.args[0]
    rows = target_call.args[1]
    assert "INSERT INTO target_allocations" in sql
    assert len(rows) == 2

    # Each row tuple: (run_id, symbol, target_weight, target_aud, sector, ...).
    first = rows[0]
    assert first[0] == 42  # run_id wired through from RETURNING
    assert first[1] == "CBA.AU"
    assert first[2] == Decimal("0.050000")  # target_weight
    # target_aud = target_weight * capital_aud.
    assert first[3] == Decimal("0.050000") * Decimal("100000.000000")
    assert first[4] == "Financials"  # sector
    # constraint_log is JSON-serialised (last element).
    assert first[-1] == json.dumps({"sector_cap": "applied"})


# ---------------------------------------------------------------------------
# 5. proposed_trades executemany — one row per trade, JSON-encoded tags/hints
# ---------------------------------------------------------------------------

async def test_persist_batch_inserts_proposed_trades() -> None:
    conn = _make_conn(run_id=42)
    trades = [_make_trade("CBA.AU", "buy"), _make_trade("BHP.AU", "sell")]
    result = _make_result(targets=[], trades=trades)

    await PortfolioService().persist(conn, result)

    trade_call = conn.executemany.await_args_list[1]
    sql = trade_call.args[0]
    rows = trade_call.args[1]
    assert "INSERT INTO proposed_trades" in sql
    assert len(rows) == 2

    first = rows[0]
    assert first[0] == 42  # run_id
    assert first[1] == "CBA.AU"
    assert first[2] == "buy"  # side
    assert first[3] == Decimal("50.000000")  # delta_qty
    # rationale_tags and lot_hints are JSON-encoded (last two elements).
    assert first[-2] == json.dumps({"reason": "rebalance"})
    assert first[-1] == json.dumps({})


# ---------------------------------------------------------------------------
# 6. Empty targets/trades still issue executemany with empty row lists
# ---------------------------------------------------------------------------

async def test_persist_empty_collections_pass_empty_batches() -> None:
    conn = _make_conn()
    result = _make_result(targets=[], trades=[])

    run_id = await PortfolioService().persist(conn, result)

    assert run_id == 42
    assert conn.executemany.await_count == 2
    assert conn.executemany.await_args_list[0].args[1] == []
    assert conn.executemany.await_args_list[1].args[1] == []


# ---------------------------------------------------------------------------
# 7. Missing model_version in summary falls back to "unknown"
# ---------------------------------------------------------------------------

async def test_persist_model_version_defaults_to_unknown() -> None:
    conn = _make_conn()
    result = _make_result()
    result.summary.pop("model_version")

    await PortfolioService().persist(conn, result)

    # Header INSERT args: (profile_id, as_of, signals_as_of, model_version, capital_aud).
    header_args = conn.fetchrow.await_args.args[1:]
    assert header_args[3] == "unknown"
    assert header_args[0] == 7  # profile_id
    assert header_args[2] == _SIGNALS_AS_OF
