"""
Price coverage and latest-complete-trading-day helper — Batch 1 (additive).

Pure, read-only helpers that distinguish a *complete* ASX trading day from
partial / residue / non-trading days. The goal is to give downstream jobs a
trustworthy data-date anchor instead of raw ``MAX(prices.dt)`` — which can be
a tiny non-trading-day residue (e.g. the 12/14-row weekend ``sync_prices``
results observed 2026-06-14 / 2026-06-15, where the rows were FX/US residue,
not an ASX equity session).

Wiring status. The date-anchor readers (``latest_complete_trading_day``,
``assess_completeness`` and the other DB helpers) remain advisory and unwired.
The only consumer is ``classify_sync_completeness`` at the foot of this module,
which ``sync_prices`` uses for NON-gating completeness logging (Batch 1 Step 2):
it changes no job status, no ``rows_written`` semantics and no downstream gate.
``snapshot_portfolio``, ``generate_signals`` and ``compose_brief`` are unchanged.
Status-gating wiring is a deliberate later batch.

Design
------
- **Data-driven completeness.** A date is ``complete`` when its active-universe
  equity row count meets a threshold derived from the *trailing median* of
  recent real trading days, with an absolute floor (``MIN_COMPLETE_ROWS``) as a
  safety net. This auto-scales as the universe grows (ASX now, US later) without
  a hardcoded per-day expectation.
- **No holiday calendar (v1, intentional).** Non-trading days fall out naturally
  as zero/residue row counts and classify as ``NO_EQUITY_DATA``. Avoiding a
  hardcoded ASX holiday calendar keeps this helper simple and self-correcting.
- **Conservative bands.** Tiny residue (≤ ``NON_TRADING_MAX_ROWS``) is treated as
  "no equity data", not "partial", so a 12/14-row weekend sync never looks like a
  half-populated trading day.

Limitations (documented for the wiring batch)
---------------------------------------------
- ``is_stale`` uses *calendar* days, not trading days. Trading-day staleness is
  deferred until a calendar source exists.
- ``MIN_COMPLETE_ROWS`` assumes an ASX-scale universe (~1850 active symbols).
  Revisit the floor when a materially smaller universe (or US-only) is added.
- The trailing median is computed over a single recent window and applied to
  every date in that window — adequate for a weekly-cadence single-user system.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from statistics import median
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    import asyncpg

# --- Tunable policy constants -------------------------------------------------

# Absolute minimum active-universe equity rows for a date to count as complete.
# Floor only — the effective threshold scales up with the trailing median.
MIN_COMPLETE_ROWS = 1500

# A date is complete when its row count reaches this fraction of the trailing
# median of recent trading days (subject to the floor above).
COMPLETE_FRACTION = Decimal("0.80")

# Row counts at or below this are residue / non-trading (weekend, holiday, or
# provider FX/US residue) — classified NO_EQUITY_DATA, never PARTIAL.
NON_TRADING_MAX_ROWS = 100

# How far back to look when assessing recent coverage.
DEFAULT_LOOKBACK_DAYS = 30

# Calendar-day staleness ceiling used by is_stale (v1 — calendar, not trading).
DEFAULT_MAX_STALE_DAYS = 5


class PriceDateStatus(StrEnum):
    """Completeness classification for a single price date."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    NO_EQUITY_DATA = "no_equity_data"  # zero rows or tiny residue (non-trading)


@dataclass(frozen=True)
class DateCoverage:
    """A price date with its active-universe row count and classification."""

    dt: date
    row_count: int
    status: PriceDateStatus


# --- Pure classification core (no DB) -----------------------------------------


def complete_threshold(
    trailing_median: int,
    *,
    floor: int = MIN_COMPLETE_ROWS,
    fraction: Decimal = COMPLETE_FRACTION,
) -> int:
    """Minimum row count for a date to be COMPLETE.

    ``max(floor, round(fraction * trailing_median))`` — data-driven with an
    absolute safety floor. A non-positive median falls back to the floor.
    """
    if trailing_median <= 0:
        return floor
    scaled = int((Decimal(trailing_median) * fraction).to_integral_value(rounding=ROUND_HALF_UP))
    return max(floor, scaled)


def trailing_median_row_count(
    row_counts: Iterable[int],
    *,
    non_trading_max: int = NON_TRADING_MAX_ROWS,
) -> int:
    """Median row count over *real* trading days (counts above the residue band).

    Residue/non-trading days (≤ ``non_trading_max``) are excluded so weekends and
    provider residue do not drag the median down. Returns 0 when no trading-ish
    days are present.
    """
    trading = [c for c in row_counts if c > non_trading_max]
    if not trading:
        return 0
    return int(median(trading))


def classify_row_count(
    row_count: int,
    trailing_median: int,
    *,
    floor: int = MIN_COMPLETE_ROWS,
    fraction: Decimal = COMPLETE_FRACTION,
    non_trading_max: int = NON_TRADING_MAX_ROWS,
) -> PriceDateStatus:
    """Classify a single date's row count against the trailing median."""
    if row_count <= non_trading_max:
        return PriceDateStatus.NO_EQUITY_DATA
    if row_count >= complete_threshold(trailing_median, floor=floor, fraction=fraction):
        return PriceDateStatus.COMPLETE
    return PriceDateStatus.PARTIAL


def classify_coverage(
    rows: Sequence[tuple[date, int]],
    *,
    floor: int = MIN_COMPLETE_ROWS,
    fraction: Decimal = COMPLETE_FRACTION,
    non_trading_max: int = NON_TRADING_MAX_ROWS,
) -> list[DateCoverage]:
    """Classify a window of ``(dt, row_count)`` pairs, newest first.

    The trailing median is computed once over the whole window (trading days
    only) and applied to every date — adequate for a recent (~30-day) window.
    """
    counts = [c for _, c in rows]
    tmed = trailing_median_row_count(counts, non_trading_max=non_trading_max)
    coverage = [
        DateCoverage(
            dt=dt,
            row_count=count,
            status=classify_row_count(
                count, tmed, floor=floor, fraction=fraction, non_trading_max=non_trading_max
            ),
        )
        for dt, count in rows
    ]
    return sorted(coverage, key=lambda c: c.dt, reverse=True)


def select_latest_complete(coverage: Sequence[DateCoverage]) -> date | None:
    """Most recent date classified COMPLETE, or None if none qualify."""
    complete = [c.dt for c in coverage if c.status is PriceDateStatus.COMPLETE]
    return max(complete) if complete else None


def is_stale(
    latest_complete: date | None,
    reference: date,
    *,
    max_calendar_days: int = DEFAULT_MAX_STALE_DAYS,
) -> bool:
    """True when there is no complete day, or the latest one is too old.

    v1 uses calendar days (not trading days) — see module Limitations.
    """
    if latest_complete is None:
        return True
    return (reference - latest_complete).days > max_calendar_days


# --- Async DB readers (thin; orchestrate the pure core) -----------------------


async def latest_observed_price_date(conn: asyncpg.Connection) -> date | None:
    """``MAX(prices.dt)`` over the active universe, regardless of completeness."""
    return cast(
        "date | None",
        await conn.fetchval(
            """
            SELECT MAX(p.dt)
            FROM prices p
            JOIN universe u ON u.symbol = p.symbol
            WHERE u.is_active = TRUE AND u.security_kind = 'au_equity'
            """
        ),
    )


async def fetch_recent_coverage(
    conn: asyncpg.Connection,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[tuple[date, int]]:
    """Active-universe equity row counts per date for the recent window.

    Anchored on the latest observed price date (not wall-clock today) so it is
    robust to timezone and weekend gaps. Returns ``(dt, row_count)`` newest first.
    """
    rows = await conn.fetch(
        """
        WITH latest AS (
            SELECT MAX(p.dt) AS mx
            FROM prices p
            JOIN universe u ON u.symbol = p.symbol
            WHERE u.is_active = TRUE AND u.security_kind = 'au_equity'
        )
        SELECT p.dt AS dt, COUNT(*) AS row_count
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        CROSS JOIN latest
        WHERE u.is_active = TRUE AND u.security_kind = 'au_equity'
          AND latest.mx IS NOT NULL
          AND p.dt >= latest.mx - $1::int
        GROUP BY p.dt
        ORDER BY p.dt DESC
        """,
        lookback_days,
    )
    return [(r["dt"], int(r["row_count"])) for r in rows]


async def latest_complete_trading_day(
    conn: asyncpg.Connection,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    floor: int = MIN_COMPLETE_ROWS,
    fraction: Decimal = COMPLETE_FRACTION,
    non_trading_max: int = NON_TRADING_MAX_ROWS,
) -> date | None:
    """Most recent COMPLETE trading day in the recent window, or None.

    This is the trustworthy data-date anchor downstream jobs should adopt
    (later batch) in place of raw ``MAX(prices.dt)``.
    """
    raw = await fetch_recent_coverage(conn, lookback_days=lookback_days)
    coverage = classify_coverage(
        raw, floor=floor, fraction=fraction, non_trading_max=non_trading_max
    )
    return select_latest_complete(coverage)


@dataclass(frozen=True)
class CompletenessReport:
    """Full coverage picture for the recent window."""

    latest_observed: date | None
    latest_complete: date | None
    coverage: tuple[DateCoverage, ...]


async def assess_completeness(
    conn: asyncpg.Connection,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    floor: int = MIN_COMPLETE_ROWS,
    fraction: Decimal = COMPLETE_FRACTION,
    non_trading_max: int = NON_TRADING_MAX_ROWS,
) -> CompletenessReport:
    """Latest observed date, latest complete date, and the classified window."""
    raw = await fetch_recent_coverage(conn, lookback_days=lookback_days)
    coverage = classify_coverage(
        raw, floor=floor, fraction=fraction, non_trading_max=non_trading_max
    )
    return CompletenessReport(
        latest_observed=coverage[0].dt if coverage else None,
        latest_complete=select_latest_complete(coverage),
        coverage=tuple(coverage),
    )


# --- sync_prices completeness adapter (Batch 1 Step 2) ------------------------


@dataclass(frozen=True)
class SyncCompleteness:
    """ASX-equity completeness verdict for a single sync_prices run.

    The verdict is derived ONLY from Phase-1 AU bulk equity rows (``au_rows``).
    Phase-2 US (``us_rows``) and Phase-3 FX (``fx_rows``) writes are carried for
    context but DELIBERATELY excluded from the classification: a non-trading ASX
    day can still produce US/FX residue — the 2026-06-14 incident wrote 12/14
    residue rows on a day with no ASX session — and that residue must never read
    as ASX equity coverage.

    v1 limitation: the verdict counts the AU bulk rows returned for the run; it
    does not yet assert those rows carry ``dt == target`` (an EODHD holiday
    response can echo the prior trading day's closes). Target-date assertion via
    the DB coverage readers above is a deliberate later step.
    """

    target: date
    status: PriceDateStatus
    au_rows: int
    us_rows: int
    fx_rows: int

    @property
    def is_complete(self) -> bool:
        return self.status is PriceDateStatus.COMPLETE


def classify_sync_completeness(
    target: date, *, au_rows: int, us_rows: int, fx_rows: int
) -> SyncCompleteness:
    """Classify a sync_prices run's ASX-equity completeness from phase counts.

    Reuses the canonical floor-only threshold: ``classify_row_count(au_rows, 0)``
    falls back to ``MIN_COMPLETE_ROWS`` (no trailing median needed, so no DB
    round-trip). The active ASX universe is ~1,800 symbols, so the 1,500-row
    floor cleanly separates a full session from residue. US and FX counts never
    enter the classification, so FX-only or US-only runs can never look
    ASX-complete.
    """
    return SyncCompleteness(
        target=target,
        status=classify_row_count(au_rows, 0),
        au_rows=au_rows,
        us_rows=us_rows,
        fx_rows=fx_rows,
    )
