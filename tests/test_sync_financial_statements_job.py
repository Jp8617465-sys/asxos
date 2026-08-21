"""Tests for jobs/sync_financial_statements.py's symbol-loading query.

Covers D2 (segment-valuation architecture doc): hybrid/capital-note
security_type values must be excluded from the population that gets
statements ingested. No network, no DB — a fake connection records the SQL
and params it was called with.
"""
from __future__ import annotations

from typing import Any

import pytest

from jobs.sync_financial_statements import _HYBRID_SECURITY_TYPES, _load_symbols


class FakeConn:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.calls.append((sql, args))
        return [{"symbol": "BHP.AU"}, {"symbol": "CBA.AU"}]


@pytest.mark.asyncio
async def test_load_symbols_excludes_hybrid_types() -> None:
    conn = FakeConn()
    await _load_symbols(conn, active_only=False, limit=None)
    sql, args = conn.calls[0]
    assert "security_type" in sql
    assert args[0] == list(_HYBRID_SECURITY_TYPES)


@pytest.mark.asyncio
async def test_load_symbols_hybrid_filter_is_null_safe() -> None:
    """A NULL security_type must not be excluded -- we don't know it's a hybrid, so
    the safe default is to keep it (matches universe.py's own 'Common Stock is the
    safe default' convention)."""
    conn = FakeConn()
    await _load_symbols(conn, active_only=False, limit=None)
    sql, _args = conn.calls[0]
    assert "security_type IS NULL OR" in sql


@pytest.mark.asyncio
async def test_load_symbols_combines_active_only_and_limit() -> None:
    conn = FakeConn()
    result = await _load_symbols(conn, active_only=True, limit=10)
    sql, _args = conn.calls[0]
    assert "AND is_active" in sql
    assert "LIMIT 10" in sql
    assert result == ["BHP.AU", "CBA.AU"]
