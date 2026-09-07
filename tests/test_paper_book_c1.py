"""C1 — the paper book (ADR D15): 25,000.000000 AUD at 100% cash.

Two properties are under test:

1.  The paper book is invisible to live-book aggregation. Enforced
    structurally, by putting it in its own table rather than flagging rows in
    `portfolio_daily_snapshots`: an existing live query cannot read it because
    it does not name it.
2.  A 10% position clears the D1 cash floor on it. The live book's cash is
    0.00, so every size the sizer proposes is clamped to zero; the paper book
    exists so the sizing gates can actually be exercised.

The symbol below is a fixture. It names no real position.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asxos.domain.decision_engine.challenge.rules import (
    CASH_FLOOR_PCT,
    ChallengeInput,
    rule_cash_floor,
)
from asxos.domain.decision_engine.paper_book import (
    SQL_PAPER_BOOK,
    load_paper_book_state,
)

FIXTURE_SYMBOL = "TESTCO.AU"
C1_SNAPSHOT_ID = "paper-c1-2026-09-07"
ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "migrations" / "0053_paper_book_snapshots.sql"


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "snapshot_id": C1_SNAPSHOT_ID,
        "book": "paper",
        "as_of": date(2026, 9, 7),
        "label": "C1 paper book",
        "capital_aud": Decimal("25000.000000"),
        "holdings_mv_aud": Decimal("0.000000"),
        "cash_aud": Decimal("25000.000000"),
        "holdings_count": 0,
        "ingested_at": None,
    }
    row.update(overrides)
    return row


def _conn(row: dict[str, Any] | None) -> MagicMock:
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=row)
    conn.fetch = AsyncMock(return_value=[])
    return conn


@pytest.fixture(autouse=True)
def _personal_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASXOS_PERSONAL_USE", "1")


# ---------------------------------------------------------------------------
# The ruled shape
# ---------------------------------------------------------------------------

async def test_c1_paper_book_is_25000_aud_at_100_percent_cash() -> None:
    state = await load_paper_book_state(_conn(_row()), C1_SNAPSHOT_ID)

    assert state.capital_aud == Decimal("25000.000000")
    assert state.cash_pct == Decimal("100.000000")
    assert state.gross_exposure_pct == Decimal("0.000000")
    assert state.borrowing_aud == Decimal("0")
    assert state.sector_weights_pct == {}
    assert state.position_weights_pct == {}
    assert state.evidence_id == f"paper-book-{C1_SNAPSHOT_ID}"


async def test_the_migration_seeds_exactly_the_ruled_numbers() -> None:
    sql = MIGRATION.read_text()
    assert "25000.000000" in sql
    assert "'paper-c1-2026-09-07'" in sql
    # 100% cash means no holdings market value.
    insert = sql.split("INSERT INTO paper_book_snapshots", 1)[1]
    assert re.search(r"25000\.000000,\s*\n?\s*0\.000000,\s*\n?\s*25000\.000000", insert)


# ---------------------------------------------------------------------------
# Invisible to live-book aggregation
# ---------------------------------------------------------------------------

def _sources() -> list[Path]:
    return [
        path
        for directory in ("asxos", "jobs", "scripts")
        for path in (ROOT / directory).rglob("*.py")
    ]


def _queries(text: str, table: str) -> bool:
    """True if the text issues SQL against `table`.

    Deliberately not a bare substring match: naming a table in a docstring to
    explain that this module does NOT read it is exactly the prose we want to
    keep, and it is not a query.
    """
    return re.search(rf"\b(?:FROM|JOIN|INTO|UPDATE)\s+{table}\b", text, re.IGNORECASE) is not None


def test_no_module_issues_sql_against_both_books() -> None:
    """A live aggregation must not be able to pick up paper money."""
    offenders = [
        str(path.relative_to(ROOT))
        for path in _sources()
        if _queries(text := path.read_text(), "portfolio_daily_snapshots")
        and _queries(text, "paper_book_snapshots")
    ]
    assert offenders == [], f"these modules query both books: {offenders}"


def test_exactly_one_module_queries_the_paper_book() -> None:
    readers = sorted(
        str(path.relative_to(ROOT))
        for path in _sources()
        if _queries(path.read_text(), "paper_book_snapshots")
    )
    assert readers == ["asxos/domain/decision_engine/paper_book.py"]


def test_the_paper_loader_reads_no_live_table() -> None:
    assert "paper_book_snapshots" in SQL_PAPER_BOOK
    for live_table in (
        "portfolio_daily_snapshots",
        "current_holdings",
        "holding_lots",
        "prices",
        "fx_rates",
    ):
        assert live_table not in SQL_PAPER_BOOK


async def test_loading_the_paper_book_issues_only_the_paper_query() -> None:
    conn = _conn(_row())
    await load_paper_book_state(conn, C1_SNAPSHOT_ID)

    conn.fetchrow.assert_awaited_once()
    executed = conn.fetchrow.await_args.args[0]
    assert executed == SQL_PAPER_BOOK
    conn.fetch.assert_not_awaited()


def test_paper_table_is_append_only_and_cannot_hold_a_live_book() -> None:
    sql = MIGRATION.read_text()
    assert "BEFORE UPDATE OR DELETE ON paper_book_snapshots" in sql
    assert "CHECK (book = 'paper')" in sql
    assert "CONSTRAINT paper_book_balances" in sql


# ---------------------------------------------------------------------------
# The cash floor can actually be exercised on it
# ---------------------------------------------------------------------------

def _challenge_input(state: Any, weight_pct: str) -> ChallengeInput:
    return ChallengeInput(
        symbol=FIXTURE_SYMBOL,
        as_of=date(2026, 9, 7),
        proposed_weight_pct=Decimal(weight_pct),
        position_cap_pct=Decimal("10.000000"),
        portfolio=state,
        thesis_evidence_id="fixture-thesis-evidence",
    )


async def test_cash_floor_passes_for_a_ten_percent_position_on_the_paper_book() -> None:
    state = await load_paper_book_state(_conn(_row()), C1_SNAPSHOT_ID)
    outcome = rule_cash_floor(_challenge_input(state, "10.000000"))

    assert outcome.finding is None, "a 10% position must clear the D1 floor"
    assert outcome.evaluated is True
    # 100% - 10% = 90% post-trade cash, far above the 7.5% floor.
    assert outcome.detail == "post-trade cash 90.000000%"


async def test_cash_floor_still_blocks_below_d1_on_the_paper_book() -> None:
    """The paper book relaxes the balance, never the register value."""
    state = await load_paper_book_state(_conn(_row()), C1_SNAPSHOT_ID)
    outcome = rule_cash_floor(_challenge_input(state, "95.000000"))

    assert outcome.finding is not None
    assert outcome.finding.severity == "blocking"
    assert str(CASH_FLOOR_PCT) in outcome.finding.finding


async def test_the_d1_boundary_is_exact_on_the_paper_book() -> None:
    state = await load_paper_book_state(_conn(_row()), C1_SNAPSHOT_ID)

    # 92.5% leaves exactly 7.5% — the floor is inclusive, so this passes.
    assert rule_cash_floor(_challenge_input(state, "92.500000")).finding is None
    # One millionth more breaches it.
    assert rule_cash_floor(_challenge_input(state, "92.500001")).finding is not None


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

async def test_missing_snapshot_is_refused() -> None:
    with pytest.raises(RuntimeError, match="no paper_book_snapshots row"):
        await load_paper_book_state(_conn(None), "nope")


async def test_a_row_not_marked_paper_is_refused() -> None:
    with pytest.raises(RuntimeError, match="not 'paper'"):
        await load_paper_book_state(_conn(_row(book="live")), C1_SNAPSHOT_ID)


async def test_an_unbalanced_book_is_refused() -> None:
    with pytest.raises(RuntimeError, match="does not balance"):
        await load_paper_book_state(
            _conn(_row(cash_aud=Decimal("24999.000000"))), C1_SNAPSHOT_ID
        )


async def test_a_paper_book_with_holdings_is_refused() -> None:
    with pytest.raises(RuntimeError, match="only an all-cash paper book"):
        await load_paper_book_state(
            _conn(
                _row(
                    holdings_count=1,
                    holdings_mv_aud=Decimal("1000.000000"),
                    cash_aud=Decimal("24000.000000"),
                )
            ),
            C1_SNAPSHOT_ID,
        )


async def test_paper_book_is_behind_the_personal_use_firewall(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ASXOS_PERSONAL_USE", raising=False)
    with pytest.raises(RuntimeError):
        await load_paper_book_state(_conn(_row()), C1_SNAPSHOT_ID)
