#!/usr/bin/env python
"""
Weekly signal outcome tracker — Sunday 03:00 UTC.

For signals where as_of is between (today - 90d) and (today - 21d):
  - Finds the actual close N trading days after the signal date using
    ROW_NUMBER() OVER (ORDER BY dt) — no calendar approximations.
  - Computes actual_return_5d, actual_return_21d, was_direction_correct.
  - Inserts into signal_outcomes where (symbol, signal_date, model) does
    not already exist (WHERE NOT EXISTS — table has no unique constraint).

Idempotent: re-running produces the same row count (WHERE NOT EXISTS).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JOB_NAME = "track_signal_outcomes"
_MODEL = "model_a"
_EVAL_MIN_DAYS = 21
_EVAL_MAX_DAYS = 90


async def _fetch_signals_to_evaluate(conn, as_of: date) -> list[dict]:  # type: ignore[type-arg]
    min_date = as_of - timedelta(days=_EVAL_MAX_DAYS)
    max_date = as_of - timedelta(days=_EVAL_MIN_DAYS)
    rows = await conn.fetch(
        """
        SELECT s.symbol,
               s.as_of          AS signal_date,
               s.model,
               s.prob_up,
               s.expected_return,
               s.signal_label
        FROM signals s
        WHERE s.model = $1
          AND s.as_of BETWEEN $2 AND $3
          AND NOT EXISTS (
              SELECT 1
              FROM signal_outcomes so
              WHERE so.symbol      = s.symbol
                AND so.signal_date  = s.as_of
                AND so.model        = s.model
          )
        ORDER BY s.as_of, s.symbol
        """,
        _MODEL,
        min_date,
        max_date,
    )
    return [dict(r) for r in rows]


async def _fetch_nth_trading_close(conn, symbol: str, after_date: date, n: int) -> float | None:  # type: ignore[type-arg]
    """Return the close price N trading days after after_date, or None if unavailable."""
    row = await conn.fetchrow(
        """
        SELECT close
        FROM (
            SELECT close,
                   ROW_NUMBER() OVER (ORDER BY dt) AS rn
            FROM prices
            WHERE symbol = $1
              AND dt > $2
        ) ranked
        WHERE rn = $3
        """,
        symbol,
        after_date,
        n,
    )
    return float(row["close"]) if row is not None else None


async def _insert_outcome(conn, sig: dict, as_of: date) -> bool:  # type: ignore[type-arg]
    """Insert one outcome row. Returns True if inserted, False if skipped."""
    signal_date = sig["signal_date"]

    entry_row = await conn.fetchrow(
        "SELECT close FROM prices WHERE symbol = $1 AND dt = $2",
        sig["symbol"],
        signal_date,
    )
    if entry_row is None:
        log.warning("no close price for signal %s on %s — skipping", sig["symbol"], signal_date)
        return False

    signal_close = float(entry_row["close"])
    close_5d = await _fetch_nth_trading_close(conn, sig["symbol"], signal_date, 5)
    close_21d = await _fetch_nth_trading_close(conn, sig["symbol"], signal_date, 21)

    actual_return_5d = (close_5d / signal_close - 1) if close_5d is not None else None
    actual_return_21d = (close_21d / signal_close - 1) if close_21d is not None else None
    was_correct: bool | None = None
    if close_21d is not None:
        went_up = close_21d > signal_close
        predicted_up = float(sig["prob_up"]) > 0.5
        was_correct = went_up == predicted_up

    result = await conn.execute(
        """
        INSERT INTO signal_outcomes
            (symbol, signal_date, model, ml_prob, ml_expected_return, signal_label,
             actual_return_5d, actual_return_21d, was_direction_correct, evaluation_date)
        -- $1 (symbol) and $3 (model) are cast to varchar explicitly: they flow from
        -- `signals` (text columns) into `signal_outcomes` (varchar columns) AND are
        -- reused in the NOT EXISTS predicate below. Without the cast Postgres deduces
        -- the same parameter as both text (source) and varchar (target/predicate) and
        -- aborts prepare with 42P08 "inconsistent types deduced for parameter $1".
        SELECT $1::varchar, $2, $3::varchar, $4, $5, $6, $7, $8, $9, $10
        WHERE NOT EXISTS (
            SELECT 1 FROM signal_outcomes
            WHERE symbol = $1::varchar AND signal_date = $2 AND model = $3::varchar
        )
        """,
        sig["symbol"],
        sig["signal_date"],
        sig["model"],
        float(sig["prob_up"]),
        float(sig["expected_return"]),
        sig["signal_label"],
        actual_return_5d,
        actual_return_21d,
        was_correct,
        as_of,
    )
    return result.endswith(" 1")


async def _run(as_of: date) -> None:
    healthcheck_url = settings.healthcheck_url_track_signal_outcomes
    # init_pool() BEFORE entering JobMonitor — JobMonitor.__aenter__ acquires a
    # connection to write the 'running' row, so the pool must already exist. The
    # pre-fix ordering (init_pool INSIDE the JobMonitor block) crashed in __aenter__
    # before any row was written, so the job silently vanished from job_runs and
    # signal_outcomes froze from 2026-04-15. This is the Phase 2B init-pool class;
    # the canonical structure is enforced by tests/test_cron_pool_init.py.
    await init_pool()
    try:
        async with JobMonitor(JOB_NAME, as_of, healthcheck_url) as monitor:
            async with acquire() as conn:
                signals = await _fetch_signals_to_evaluate(conn, as_of)

            if not signals:
                log.info("no signals in evaluation window — nothing to track")
                monitor.rows_written = 0
                return

            log.info("evaluating %d signal rows", len(signals))
            inserted = 0
            skipped = 0
            for sig in signals:
                async with acquire() as conn:
                    ok = await _insert_outcome(conn, sig, as_of)
                if ok:
                    inserted += 1
                else:
                    skipped += 1

            log.info(
                "track_signal_outcomes done: %d inserted, %d skipped",
                inserted,
                skipped,
            )
            monitor.rows_written = inserted
    finally:
        await close_pool()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Track model A signal outcomes")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD", help="Evaluation anchor date (default: today)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    asyncio.run(_run(as_of))
