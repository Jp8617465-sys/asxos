"""C1 — the paper book (ADR D15), deliberately kept apart from the live book.

This module is the ONLY place that names `paper_book_snapshots`, and it names
no live table. That separation is the enforcement of James's ruling that the
paper book is invisible to live-book aggregation: a live query cannot read it
by accident because nothing a live query touches mentions it.

`tests/test_paper_book_c1.py::test_no_live_book_reader_names_the_paper_table`
holds the line — it fails if any module ever reads both books.
"""
from __future__ import annotations

import os
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Final, Protocol

from asxos.domain.decision_engine.challenge.rules import PortfolioState
from asxos.domain.decision_engine.portfolio_state import PersonalUseRequired, StateConn


class PaperBookConn(Protocol):
    """The asyncpg surface the S3 writer and the gate reads use (a superset of StateConn)."""

    async def execute(self, query: str, *args: object) -> str: ...
    async def fetchrow(self, query: str, *args: object) -> Any: ...
    async def fetch(self, query: str, *args: object) -> list[Any]: ...
    async def fetchval(self, query: str, *args: object) -> Any: ...

_Q6: Final = Decimal("0.000001")
_HUNDRED: Final = Decimal("100")

SQL_PAPER_BOOK: Final[str] = (
    "SELECT snapshot_id, book, as_of, label, capital_aud, holdings_mv_aud, cash_aud, "
    "holdings_count, ingested_at FROM paper_book_snapshots WHERE snapshot_id = $1"
)


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q6, rounding=ROUND_HALF_EVEN)


def _dec(value: object) -> Decimal:
    if isinstance(value, float):
        raise TypeError("float reached the paper-book loader")
    return Decimal(str(value))


def require_personal_use() -> None:
    if os.environ.get("ASXOS_PERSONAL_USE") != "1":
        raise PersonalUseRequired(
            "the paper-book loader requires ASXOS_PERSONAL_USE=1 (s766B personal-advice firewall)"
        )


async def load_paper_book_state(conn: StateConn, snapshot_id: str) -> PortfolioState:
    """Build a `PortfolioState` from the C1 paper book (ADR D15).

    Reads `paper_book_snapshots` and nothing else. It never touches
    `portfolio_daily_snapshots`, `current_holdings`, `holding_lots` or
    `prices`, so a paper case cannot pick up a live position by accident, and
    equally a live case cannot pick up paper cash — the two books share no
    query.

    The C1 book holds no positions, so gross exposure, sector weights and
    position weights are empty by construction rather than by filtering.
    """
    require_personal_use()
    row = await conn.fetchrow(SQL_PAPER_BOOK, snapshot_id)
    if row is None:
        raise RuntimeError(f"no paper_book_snapshots row for snapshot_id={snapshot_id!r}")
    if row["book"] != "paper":
        raise RuntimeError(
            f"paper_book_snapshots row {snapshot_id!r} is marked {row['book']!r}, not 'paper'"
        )
    capital = _dec(row["capital_aud"])
    if capital <= 0:
        raise RuntimeError(f"paper book {snapshot_id!r} has non-positive capital {capital}")
    cash = _dec(row["cash_aud"])
    holdings_mv = _dec(row["holdings_mv_aud"])
    if cash + holdings_mv != capital:
        raise RuntimeError(
            f"paper book {snapshot_id!r} does not balance: "
            f"cash {cash} + holdings {holdings_mv} != capital {capital}"
        )
    holdings_count = int(row["holdings_count"])
    if holdings_count:
        # A paper book with positions needs a paper holdings ledger to derive
        # per-name and sector weights from. That ledger does not exist, and
        # inventing zero weights for a book that holds something would let a
        # position cap pass on a portfolio the caps were never applied to.
        raise RuntimeError(
            f"paper book {snapshot_id!r} reports {holdings_count} holdings; only an "
            "all-cash paper book is supported (no paper holdings ledger exists)"
        )
    return PortfolioState(
        capital_aud=_q(capital),
        cash_pct=_q(cash / capital * _HUNDRED),
        gross_exposure_pct=_q(holdings_mv / capital * _HUNDRED),
        borrowing_aud=Decimal("0"),  # a paper book cannot borrow; D2 pins LVR at 0
        sector_weights_pct={},
        position_weights_pct={},
        evidence_id=f"paper-book-{snapshot_id}",
    )


# ---------------------------------------------------------------------------
# F-E2E r2 S3 — the daily writer and the reads the sign-off gate needs.
#
# Still the only module that names `paper_book_snapshots`
# (`tests/test_paper_book_c1.py::test_exactly_one_module_queries_the_paper_book`):
# the job, the gate and the packet builder all come through here.
# ---------------------------------------------------------------------------

#: The arbi-declared paper capital (sprint §4 decision, 2026-09-16), read from
#: the workflow `env:` block — never inferred from a profile or a policy figure.
PAPER_CAPITAL_ENV: Final[str] = "ASXOS_PAPER_CAPITAL_AUD"
PAPER_DAILY_LABEL: Final[str] = "paper, arbi-declared — daily snapshot (ASXOS_PAPER_CAPITAL_AUD)"

SQL_INSERT_PAPER_SNAPSHOT: Final[str] = (
    "INSERT INTO paper_book_snapshots "
    "(snapshot_id, as_of, label, capital_aud, holdings_mv_aud, cash_aud, holdings_count) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (snapshot_id) DO NOTHING"
)
SQL_LATEST_PAPER_SNAPSHOT_ID: Final[str] = (
    "SELECT snapshot_id FROM paper_book_snapshots WHERE as_of <= $1 "
    "ORDER BY as_of DESC, ingested_at DESC LIMIT 1"
)
SQL_COUNT_PAPER_SNAPSHOTS_MATURED: Final[str] = (
    "SELECT COUNT(*) FROM paper_book_snapshots WHERE as_of <= $1"
)
SQL_PAPER_SNAPSHOT_DATES: Final[str] = (
    "SELECT DISTINCT as_of FROM paper_book_snapshots WHERE as_of >= $1 ORDER BY as_of"
)


def declared_paper_capital() -> Decimal:
    """The paper capital the workflow declares. Absent or non-positive hard-fails."""
    raw = os.environ.get(PAPER_CAPITAL_ENV, "").strip()
    if not raw:
        raise RuntimeError(
            f"{PAPER_CAPITAL_ENV} is not set: the paper book is arbi-declared in the "
            "workflow env block and is never inferred from a profile or a policy figure"
        )
    capital = _q(Decimal(raw))
    if capital <= 0:
        raise RuntimeError(f"{PAPER_CAPITAL_ENV}={raw!r} must be a positive AUD amount")
    return capital


def paper_snapshot_id(as_of: date) -> str:
    return f"paper-daily-{as_of.isoformat()}"


async def write_daily_paper_snapshot(conn: PaperBookConn, *, as_of: date, capital_aud: Decimal) -> bool:
    """Append today's all-cash paper book. False when the day's row already exists.

    No paper holdings ledger exists, so the book is 100% cash by construction
    (`load_paper_book_state` refuses any other shape). The table is append-only;
    a same-day re-run keeps the first row.
    """
    require_personal_use()
    if capital_aud <= 0:
        raise RuntimeError(f"paper capital must be positive, got {capital_aud}")
    status = await conn.execute(
        SQL_INSERT_PAPER_SNAPSHOT,
        paper_snapshot_id(as_of),
        as_of,
        PAPER_DAILY_LABEL,
        _q(capital_aud),
        Decimal("0"),
        _q(capital_aud),
        0,
    )
    return str(status).endswith(" 1")


async def latest_paper_snapshot_id(conn: StateConn, *, as_of: date) -> str | None:
    """The most recent paper book at or before `as_of` — the packet builder's read (S5)."""
    row = await conn.fetchrow(SQL_LATEST_PAPER_SNAPSHOT_ID, as_of)
    return None if row is None else str(row["snapshot_id"])


async def count_paper_snapshots_matured(conn: PaperBookConn, *, window_open: date) -> int:
    """Paper snapshots old enough to have `window` of subsequent history."""
    value = await conn.fetchval(SQL_COUNT_PAPER_SNAPSHOTS_MATURED, window_open)
    return int(value or 0)


async def paper_snapshot_dates(conn: PaperBookConn, *, since: date) -> list[date]:
    """Every distinct paper-book as_of from `since` — the gate's continuity input."""
    rows = await conn.fetch(SQL_PAPER_SNAPSHOT_DATES, since)
    return [r["as_of"] for r in rows]
