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
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from asxos.domain.decision_engine.challenge.rules import PortfolioState
from asxos.domain.decision_engine.portfolio_state import PersonalUseRequired, StateConn

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
