"""Point-in-time replay + lineage (Stage 1 exit clauses 1 and 2) — campaign node H2-B.

No DB. A fake conn dispatches on the SQL constants so every branch of the
provenance and as-known-price logic is exercised, and the hash is checked to
be identical across two independent assemblies of the same facts.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from asxos.domain.replay import replay_snapshot, resolve_lineage, snapshot_hash
from asxos.domain.replay.cutoff import (
    SQL_PIT_LATEST,
    SQL_PIT_LATEST_FILED,
    SQL_PRICE_LATEST,
    SQL_PRICE_REVISIONS,
    SQL_SECURITY,
    ReplayError,
    assert_replay_sql_admissible,
    cutoff_instant,
)
from asxos.domain.replay.lineage import SQL_PRICE_KEY, SQL_REVISION_IDS, SQL_STATEMENT_KEYS

D = date.fromisoformat
CUTOFF = D("2025-08-21")


def _pit(*, kd: str, tier: str | None, as_of: str = "2025-06-30") -> dict[str, Any]:
    return {
        "symbol": "TLS.AU", "as_of": D(as_of), "knowledge_date": D(kd),
        "knowledge_tier": tier, "revenue_ttm": Decimal("23140000000"),
        "net_income_ttm": Decimal("2100000000"), "eps_ttm": Decimal("0.181"),
        "book_value_ps": Decimal("1.42"), "roe": Decimal("0.127"),
        "net_debt": Decimal("13400000000"), "currency": "AUD",
    }


class FakeConn:
    """Dispatches on the SQL constant; records every call for assertions."""

    def __init__(
        self,
        *,
        pit_rows: list[dict[str, Any]],
        price: dict[str, Any] | None,
        revisions: list[dict[str, Any]] | None = None,
        statements: list[dict[str, Any]] | None = None,
        known_symbol: bool = True,
    ) -> None:
        self.pit_rows = pit_rows
        self.price = price
        self.revisions = revisions or []
        self.statements = statements if statements is not None else [
            {"symbol": "TLS.AU", "period_end": D("2025-06-30"), "period_type": "yearly",
             "statement_type": "balance_sheet", "filing_date": None, "report_date": D("2025-08-13")},
            {"symbol": "TLS.AU", "period_end": D("2025-06-30"), "period_type": "yearly",
             "statement_type": "income", "filing_date": None, "report_date": D("2025-08-13")},
        ]
        self.known_symbol = known_symbol
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        self.calls.append((sql, args))
        if sql == SQL_SECURITY:
            return {"symbol": args[0]} if self.known_symbol else None
        if sql == SQL_PIT_LATEST:
            visible = [r for r in self.pit_rows if r["knowledge_date"] <= args[1]]
            return max(visible, key=lambda r: r["knowledge_date"]) if visible else None
        if sql == SQL_PIT_LATEST_FILED:
            visible = [
                r for r in self.pit_rows
                if r["knowledge_date"] <= args[1] and r["knowledge_tier"] == "filed"
            ]
            return max(visible, key=lambda r: r["knowledge_date"]) if visible else None
        if sql == SQL_PRICE_LATEST:
            return self.price if self.price and self.price["dt"] <= args[1] else None
        if sql == SQL_PRICE_KEY:
            return {"symbol": args[0], "dt": args[1]} if self.price else None
        raise AssertionError(f"unexpected fetchrow: {sql}")

    async def fetch(self, sql: str, *args: Any) -> list[Any]:
        self.calls.append((sql, args))
        if sql == SQL_PRICE_REVISIONS:
            return sorted(self.revisions, key=lambda r: (r["recorded_at"], r["revision_id"]))
        if sql == SQL_REVISION_IDS:
            return [{"revision_id": r["revision_id"]} for r in self.revisions]
        if sql == SQL_STATEMENT_KEYS:
            return [s for s in self.statements if s["period_end"] == args[1]]
        raise AssertionError(f"unexpected fetch: {sql}")


def _price(dt: str = "2025-08-21", close: str = "5.02") -> dict[str, Any]:
    return {"symbol": "TLS.AU", "dt": D(dt), "close": Decimal(close), "adj_close": Decimal(close)}


# --- provenance ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_filed_row_is_included() -> None:
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    assert snap.fundamentals_status == "included"
    assert snap.payload["fundamentals"]["row"]["knowledge_tier"] == "filed"  # type: ignore[index]
    assert snap.payload["fundamentals"]["latest_by_date_excluded"] is None  # type: ignore[index]


@pytest.mark.asyncio
async def test_untiered_row_is_excluded_and_reported_not_hidden() -> None:
    """NULL is not 'filed' — the live state of every row before the backfill."""
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier=None)], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    assert snap.fundamentals_status == "excluded_untiered"
    assert snap.payload["fundamentals"]["row"] is None  # type: ignore[index]
    excluded = snap.payload["fundamentals"]["latest_by_date_excluded"]  # type: ignore[index]
    assert excluded["knowledge_date"] == "2025-08-13"  # type: ignore[index]


@pytest.mark.asyncio
async def test_estimated_row_is_excluded_but_an_older_filed_row_is_used() -> None:
    """Strict mode wants the best ADMISSIBLE evidence, not 'absent'."""
    conn = FakeConn(
        pit_rows=[
            _pit(kd="2024-08-15", tier="filed", as_of="2024-06-30"),
            _pit(kd="2025-08-20", tier="estimated"),
        ],
        price=_price(),
    )
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    assert snap.fundamentals_status == "included"
    assert snap.payload["fundamentals"]["row"]["knowledge_date"] == "2024-08-15"  # type: ignore[index]
    assert snap.payload["fundamentals"]["latest_by_date_excluded"]["knowledge_tier"] == "estimated"  # type: ignore[index]


@pytest.mark.asyncio
async def test_allow_estimated_admits_the_row_and_changes_the_hash() -> None:
    """Opting in is recorded in the payload, so its hash can never pass as strict."""
    rows = [_pit(kd="2025-08-20", tier="estimated")]
    strict = await replay_snapshot(FakeConn(pit_rows=rows, price=_price()), symbol="TLS.AU", cutoff=CUTOFF)
    loose = await replay_snapshot(
        FakeConn(pit_rows=rows, price=_price()), symbol="TLS.AU", cutoff=CUTOFF, require_filed=False
    )
    assert strict.fundamentals_status == "excluded_estimated"
    assert loose.fundamentals_status == "included"
    assert loose.payload["require_filed"] is False
    assert strict.hash != loose.hash


@pytest.mark.asyncio
async def test_future_knowledge_date_is_invisible_at_the_cutoff() -> None:
    conn = FakeConn(pit_rows=[_pit(kd="2025-09-13", tier="estimated")], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    assert snap.fundamentals_status == "absent"


# --- price as known -----------------------------------------------------------


@pytest.mark.asyncio
async def test_price_with_no_revisions_is_the_current_close() -> None:
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    row = snap.payload["price"]["row"]  # type: ignore[index]
    assert row["close_as_known_at_cutoff"] == "5.02"  # type: ignore[index]
    assert row["revisions_after_cutoff"] == 0  # type: ignore[index]


@pytest.mark.asyncio
async def test_post_cutoff_revision_restores_the_prior_close() -> None:
    """A correction recorded AFTER the cutoff must not rewrite what was known."""
    revisions = [
        {"revision_id": 7, "operation": "update", "prior_close": Decimal("5.02"),
         "replacement_close": Decimal("5.05"), "recorded_at": datetime(2025, 9, 1, 3, 0, tzinfo=UTC)},
    ]
    conn = FakeConn(
        pit_rows=[_pit(kd="2025-08-13", tier="filed")],
        price=_price(close="5.05"),
        revisions=revisions,
    )
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    row = snap.payload["price"]["row"]  # type: ignore[index]
    assert row["close_now"] == "5.05"  # type: ignore[index]
    assert row["close_as_known_at_cutoff"] == "5.02"  # type: ignore[index]
    assert "revision_id=7" in row["as_known_source"]  # type: ignore[index]


@pytest.mark.asyncio
async def test_pre_cutoff_revision_does_not_change_the_as_known_close() -> None:
    revisions = [
        {"revision_id": 3, "operation": "update", "prior_close": Decimal("4.99"),
         "replacement_close": Decimal("5.02"), "recorded_at": datetime(2025, 8, 21, 10, 0, tzinfo=UTC)},
    ]
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price(), revisions=revisions)
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    row = snap.payload["price"]["row"]  # type: ignore[index]
    assert row["close_as_known_at_cutoff"] == "5.02"  # type: ignore[index]
    assert row["revisions_total"] == 1 and row["revisions_after_cutoff"] == 0  # type: ignore[index]


def test_cutoff_instant_is_end_of_day_utc() -> None:
    assert cutoff_instant(CUTOFF) == datetime(2025, 8, 21, 23, 59, 59, tzinfo=UTC)


# --- reproducibility ------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_independent_assemblies_hash_identically() -> None:
    """The Stage 1 gate's operational form: run it twice, get one hash."""
    make = lambda: FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())  # noqa: E731
    a = await replay_snapshot(make(), symbol="TLS.AU", cutoff=CUTOFF)
    b = await replay_snapshot(make(), symbol="TLS.AU", cutoff=CUTOFF)
    assert snapshot_hash(a) == snapshot_hash(b) == a.hash
    assert len(a.hash) == 64


@pytest.mark.asyncio
async def test_a_different_cutoff_hashes_differently() -> None:
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())
    a = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    b = await replay_snapshot(conn, symbol="TLS.AU", cutoff=D("2025-08-22"))
    assert a.hash != b.hash


@pytest.mark.asyncio
async def test_payload_is_json_native_with_decimal_strings() -> None:
    import json

    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    json.dumps(snap.payload)  # must not raise
    assert snap.payload["fundamentals"]["row"]["revenue_ttm"] == "23140000000"  # type: ignore[index]


# --- lineage ------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lineage_resolves_fundamentals_to_statements_and_price_to_itself() -> None:
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    report = await resolve_lineage(conn, snap)
    assert report.complete
    canonicals = [r["canonical"] for r in report.resolved]
    assert "rs_fundamentals_pit(TLS.AU, 2025-08-13)" in canonicals
    assert "prices(TLS.AU, 2025-08-21)" in canonicals
    fund = next(r for r in report.resolved if str(r["canonical"]).startswith("rs_fundamentals"))
    assert "rs_financial_statements(TLS.AU, 2025-06-30, yearly, income)" in fund["source_rows"]  # type: ignore[operator]


@pytest.mark.asyncio
async def test_lineage_reports_a_missing_income_statement_as_unresolved() -> None:
    conn = FakeConn(
        pit_rows=[_pit(kd="2025-08-13", tier="filed")],
        price=_price(),
        statements=[],  # the raw rows the PIT row claims to derive from are gone
    )
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    report = await resolve_lineage(conn, snap)
    assert not report.complete
    assert report.unresolved[0]["reason"] == "no yearly income statement for the row's as_of"
    assert report.as_payload()["complete"] is False


@pytest.mark.asyncio
async def test_lineage_notes_a_missing_balance_sheet_without_failing() -> None:
    conn = FakeConn(
        pit_rows=[_pit(kd="2025-08-13", tier="filed")],
        price=_price(),
        statements=[{"symbol": "TLS.AU", "period_end": D("2025-06-30"), "period_type": "yearly",
                     "statement_type": "income", "filing_date": None, "report_date": D("2025-08-13")}],
    )
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    report = await resolve_lineage(conn, snap)
    assert report.complete
    assert "balance_sheet absent" in str(report.resolved[0].get("note"))


@pytest.mark.asyncio
async def test_lineage_includes_revision_ids_for_the_price_row() -> None:
    revisions = [{"revision_id": 7, "operation": "update", "prior_close": Decimal("5.02"),
                  "replacement_close": Decimal("5.05"), "recorded_at": datetime(2025, 9, 1, tzinfo=UTC)}]
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price(), revisions=revisions)
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    report = await resolve_lineage(conn, snap)
    price_entry = next(r for r in report.resolved if str(r["canonical"]).startswith("prices"))
    assert "price_revisions.revision_id=7" in price_entry["source_rows"]  # type: ignore[operator]


# --- boundaries -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_symbol_raises() -> None:
    conn = FakeConn(pit_rows=[], price=None, known_symbol=False)
    with pytest.raises(ReplayError, match="absent from rs_security_master"):
        await replay_snapshot(conn, symbol="ZZZ.AU", cutoff=CUTOFF)


def test_replay_sql_refuses_forbidden_tables_and_tokens() -> None:
    with pytest.raises(ReplayError):
        assert_replay_sql_admissible("SELECT prob_up FROM signals WHERE symbol = $1")
    with pytest.raises(ReplayError):
        assert_replay_sql_admissible("SELECT * FROM holding_lots")
    with pytest.raises(ReplayError):
        assert_replay_sql_admissible("SELECT stop_price FROM theses")


@pytest.mark.asyncio
async def test_snapshot_declares_what_it_excludes_by_policy() -> None:
    conn = FakeConn(pit_rows=[_pit(kd="2025-08-13", tier="filed")], price=_price())
    snap = await replay_snapshot(conn, symbol="TLS.AU", cutoff=CUTOFF)
    joined = " ".join(snap.payload["not_included"])  # type: ignore[arg-type]
    assert "rule #11" in joined and "signals" in joined
