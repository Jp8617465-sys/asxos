"""Tests for segment_map resolution (D3/S3, segment-valuation architecture doc).

normalize_segment_name/resolve_segment_key are pure functions checked on the
exact variant strings observed live 2026-08-19. The orchestrator is driven
with a fake conn. No network, no DB.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from asxos.domain.research.segment_map import (
    normalize_segment_name,
    refresh_segment_map,
    resolve_segment_key,
)

D = date.fromisoformat


# ---------------------------------------------------------------------------
# normalize_segment_name — pure alias mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Already canonical GICS — passes through unchanged.
        ("Materials", "Materials"),
        ("Financials", "Financials"),
        ("Health Care", "Health Care"),
        ("Information Technology", "Information Technology"),
        ("Consumer Discretionary", "Consumer Discretionary"),
        ("Consumer Staples", "Consumer Staples"),
        # Morningstar variants observed live in BOTH universe.sector and the
        # supposedly-GICS rs_security_master.gics_sector column.
        ("Basic Materials", "Materials"),
        ("Consumer Cyclical", "Consumer Discretionary"),
        ("Consumer Defensive", "Consumer Staples"),
        ("Financial", "Financials"),
        ("Financial Services", "Financials"),
        ("Healthcare", "Health Care"),
        ("Industrial Goods", "Industrials"),
        ("Technology", "Information Technology"),
    ],
)
def test_normalize_maps_known_variants(raw: str, expected: str) -> None:
    assert normalize_segment_name(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "  ", "Other", "Unclassified Nonsense"])
def test_normalize_returns_none_for_unresolvable(raw: str | None) -> None:
    assert normalize_segment_name(raw) is None


def test_normalize_strips_whitespace_before_matching() -> None:
    assert normalize_segment_name("  Basic Materials  ") == "Materials"


# ---------------------------------------------------------------------------
# resolve_segment_key — the two-source priority + unresolved fallback
# ---------------------------------------------------------------------------


def test_prefers_gics_when_both_present_and_resolvable() -> None:
    key, source = resolve_segment_key("Materials", "Basic Materials")
    assert key == "Materials"
    assert source == "gics"


def test_falls_back_to_universe_sector_when_gics_unresolvable() -> None:
    """The dirty-gics_sector case: 'Other' or NULL in the gics column must not stop
    the resolver from trying universe.sector."""
    key, source = resolve_segment_key(None, "Basic Materials")
    assert key == "Materials"
    assert source == "morningstar_alias"

    key2, source2 = resolve_segment_key("Other", "Financial Services")
    assert key2 == "Financials"
    assert source2 == "morningstar_alias"


def test_unresolved_when_neither_source_maps() -> None:
    key, source = resolve_segment_key(None, None)
    assert key is None
    assert source == "unresolved"

    key2, source2 = resolve_segment_key("Other", "")
    assert key2 is None
    assert source2 == "unresolved"


def test_gics_leaked_morningstar_value_still_normalizes_via_gics_source() -> None:
    """D3's sharpest finding: gics_sector itself carries Morningstar leakage (e.g.
    'Healthcare' instead of 'Health Care').

    It must still normalize and still count as source='gics', not silently fall
    through."""
    key, source = resolve_segment_key("Healthcare", None)
    assert key == "Health Care"
    assert source == "gics"


# ---------------------------------------------------------------------------
# refresh_segment_map — orchestrator (FakeConn)
# ---------------------------------------------------------------------------


class FakeConn:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows
        self.fetched: list[str] = []
        self.executed_many: list[tuple[str, list[tuple[Any, ...]]]] = []

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        self.fetched.append(sql)
        return self._rows

    async def executemany(self, sql: str, args: list[tuple[Any, ...]]) -> None:
        self.executed_many.append((sql, list(args)))


@pytest.mark.asyncio
async def test_orchestrator_reads_security_master_joined_to_universe() -> None:
    conn = FakeConn(
        [
            {"symbol": "BHP.AU", "gics_sector": None, "universe_sector": "Basic Materials"},
            {"symbol": "CBA.AU", "gics_sector": "Financials", "universe_sector": "Financial Services"},
            {"symbol": "XYZ.AU", "gics_sector": "Other", "universe_sector": None},
        ]
    )
    counts = await refresh_segment_map(conn, as_of=D("2026-08-19"))
    assert counts == {
        "symbols": 3,
        "resolved_gics": 1,
        "resolved_alias": 1,
        "unresolved": 1,
    }
    assert any("rs_security_master" in s and "universe" in s for s in conn.fetched)


@pytest.mark.asyncio
async def test_orchestrator_upserts_segment_map_with_taxonomy_version() -> None:
    conn = FakeConn([{"symbol": "BHP.AU", "gics_sector": "Materials", "universe_sector": "Basic Materials"}])
    await refresh_segment_map(conn, as_of=D("2026-08-19"), taxonomy_version="gics_alias_v1")
    sql, rows = conn.executed_many[0]
    assert "segment_map" in sql
    assert "ON CONFLICT (symbol, taxonomy_version) DO UPDATE" in sql
    symbol, taxonomy_version, segment_key, source, effective_from = rows[0]
    assert symbol == "BHP.AU"
    assert taxonomy_version == "gics_alias_v1"
    assert segment_key == "Materials"
    assert source == "gics"
    assert effective_from == D("2026-08-19")


@pytest.mark.asyncio
async def test_orchestrator_handles_empty_source() -> None:
    conn = FakeConn([])
    counts = await refresh_segment_map(conn, as_of=D("2026-08-19"))
    assert counts == {"symbols": 0, "resolved_gics": 0, "resolved_alias": 0, "unresolved": 0}
    assert conn.executed_many == []
