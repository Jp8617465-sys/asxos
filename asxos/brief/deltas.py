"""Book-level snapshot delta for the live daily brief (Stage 1).

Four sequential SELECTs on the caller's connection, then in-memory
:class:`BookDelta`. This is a change in *levels*, never a return:
``capital_delta`` is ``current.capital_aud - prior.capital_aud``. Do not
divide by prior capital. Do not ``asyncio.gather`` — asyncpg forbids
concurrent operations on one connection.

``brief_runs.snapshot_json`` is not read. No ``signals`` query.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg


def _dec(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, order=True)
class SnapshotLevels:
    """One day's book levels. Ordered by ``as_of``, then the numeric fields."""

    as_of: date
    capital_aud: Decimal
    holdings_mv_aud: Decimal
    cash_aud: Decimal
    holdings_count: int


def _levels(row: Any) -> SnapshotLevels:
    as_of = row["as_of"]
    if isinstance(as_of, datetime):
        as_of = as_of.date()
    return SnapshotLevels(
        as_of=as_of,
        capital_aud=_dec(row["capital_aud"]),
        holdings_mv_aud=_dec(row["holdings_mv_aud"]),
        cash_aud=_dec(row["cash_aud"]),
        holdings_count=int(row["holdings_count"]),
    )


@dataclass(frozen=True)
class BookDelta:
    """Paired snapshot levels plus provenance timestamps from prior jobs.

    ``*_delta`` properties are current minus prior (a level change). They are
    ``None`` when either side of the pair is missing. They are never a return.
    """

    current: SnapshotLevels | None = None
    prior: SnapshotLevels | None = None
    prior_job_finished_at: datetime | None = None
    prior_brief_composed_at: datetime | None = None

    @property
    def capital_delta(self) -> Decimal | None:
        if self.current is None or self.prior is None:
            return None
        return self.current.capital_aud - self.prior.capital_aud

    @property
    def holdings_mv_delta(self) -> Decimal | None:
        if self.current is None or self.prior is None:
            return None
        return self.current.holdings_mv_aud - self.prior.holdings_mv_aud

    @property
    def cash_delta(self) -> Decimal | None:
        if self.current is None or self.prior is None:
            return None
        return self.current.cash_aud - self.prior.cash_aud

    @property
    def holdings_count_delta(self) -> int | None:
        if self.current is None or self.prior is None:
            return None
        return self.current.holdings_count - self.prior.holdings_count


_PRIOR_JOB_SQL = """
SELECT as_of, finished_at
FROM job_runs
WHERE job_name = 'compose_brief'
  AND status = 'success'
  AND as_of < $1
ORDER BY finished_at DESC NULLS LAST, as_of DESC
LIMIT 1
"""

_PRIOR_BRIEF_SQL = """
SELECT as_of, composed_at
FROM brief_runs
WHERE as_of < $1
ORDER BY composed_at DESC, as_of DESC
LIMIT 1
"""

_SNAPSHOT_SQL = """
SELECT as_of, capital_aud, holdings_mv_aud, cash_aud, holdings_count
FROM portfolio_daily_snapshots
WHERE as_of <= $1
ORDER BY as_of DESC
LIMIT 1
"""

_PRIOR_SNAPSHOT_SQL = """
SELECT as_of, capital_aud, holdings_mv_aud, cash_aud, holdings_count
FROM portfolio_daily_snapshots
WHERE as_of < $1
ORDER BY as_of DESC
LIMIT 1
"""


async def load_book_delta(conn: asyncpg.Connection, as_of: date) -> BookDelta:
    """Four sequential fetches on ``conn``; never gather; never INSERT.

    1. Prior successful ``compose_brief`` job (``finished_at``, ``as_of``).
    2. Prior ``brief_runs`` row (``as_of``, ``composed_at`` only).
    3. Current snapshot with ``as_of <=`` the brief date.
    4. Prior snapshot with ``as_of <`` the current snapshot's ``as_of``
       (or the brief date when no current row exists).
    """
    prior_job = await conn.fetchrow(_PRIOR_JOB_SQL, as_of)
    prior_brief = await conn.fetchrow(_PRIOR_BRIEF_SQL, as_of)
    current_row = await conn.fetchrow(_SNAPSHOT_SQL, as_of)
    prior_bound = current_row["as_of"] if current_row is not None else as_of
    if isinstance(prior_bound, datetime):
        prior_bound = prior_bound.date()
    prior_row = await conn.fetchrow(_PRIOR_SNAPSHOT_SQL, prior_bound)

    return BookDelta(
        current=_levels(current_row) if current_row is not None else None,
        prior=_levels(prior_row) if prior_row is not None else None,
        prior_job_finished_at=(prior_job["finished_at"] if prior_job is not None else None),
        prior_brief_composed_at=(prior_brief["composed_at"] if prior_brief is not None else None),
    )
