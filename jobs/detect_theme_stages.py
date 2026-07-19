"""
Theme stage detection — M-Theme-Stage-Detection.

Runs at 20:55 UTC (Sun-Thu) — same slot as ingest_regulatory.

For each active theme:
  1. Load holdings (symbols) for the theme
  2. Compute price breadth and momentum from underlying_prices / prices tables
  3. Pull sentiment summary if available (news_sentiment)
  4. Call classify_stage() — returns (label, conditions_fired) or None
  5. If result differs from current stage_suggested: UPDATE themes with new
     stage_suggested + stage_metadata JSON (classifier_version, conditions_fired,
     evaluated_at)

Hard-fail: DB connection failure.
Soft-degrade: single-theme failures logged; job continues.

Non-negotiable: themes.stage is NEVER written. Only stage_suggested and
stage_metadata. The user confirms stage via `asx theme stage`.
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, date, datetime

from asxos.db import acquire, close_pool, init_pool
from asxos.domain.themes.stage_classifier import (
    CLASSIFIER_VERSION,
    THRESHOLDS,
    ClassifierInput,
    classify_stage,
)
from asxos.jobs.utils.job_monitor import JobMonitor

_JOB = "detect_theme_stages"


async def _build_classifier_input(conn, symbols: list[str], as_of: date) -> ClassifierInput:
    """Compute breadth and momentum signals for a theme's holdings."""
    if not symbols:
        return ClassifierInput(price_history_days=0)

    # Price breadth: % holdings above 50d and 200d MA
    # Use prices table since underlying_prices is only for tracked underlyings
    breadth_row = await conn.fetchrow(
        """
        WITH daily_prices AS (
            SELECT
                symbol,
                close,
                AVG(close) OVER (
                    PARTITION BY symbol
                    ORDER BY dt
                    ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                ) AS ma_50d,
                AVG(close) OVER (
                    PARTITION BY symbol
                    ORDER BY dt
                    ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
                ) AS ma_200d,
                dt,
                ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY dt DESC) AS rn
            FROM prices
            WHERE symbol = ANY($1)
              AND dt <= $2
        ),
        latest AS (
            SELECT symbol, close, ma_50d, ma_200d
            FROM daily_prices
            WHERE rn = 1
        )
        SELECT
            COUNT(*)                                                   AS symbol_count,
            MIN(1)::numeric                                            AS min_history,
            SUM(CASE WHEN close > ma_50d THEN 1 ELSE 0 END)::numeric  AS above_50d,
            SUM(CASE WHEN close > ma_200d THEN 1 ELSE 0 END)::numeric AS above_200d
        FROM latest
        """,
        symbols, as_of,
    )

    symbol_count = breadth_row["symbol_count"] or 0
    if symbol_count == 0:
        return ClassifierInput(price_history_days=0)

    above_50d = breadth_row["above_50d"] or 0
    above_200d = breadth_row["above_200d"] or 0
    pct_above_50d = above_50d / symbol_count
    pct_above_200d = above_200d / symbol_count

    # Momentum: average 5-week % move across holdings
    momentum_row = await conn.fetchrow(
        """
        WITH weekly_moves AS (
            SELECT
                symbol,
                (close - LAG(close, 5) OVER (PARTITION BY symbol ORDER BY dt))
                    / NULLIF(LAG(close, 5) OVER (PARTITION BY symbol ORDER BY dt), 0) AS pct_5d
            FROM prices
            WHERE symbol = ANY($1)
              AND dt > $2 - INTERVAL '35 days'
              AND dt <= $2
        )
        SELECT AVG(ABS(pct_5d)) AS avg_weekly_move
        FROM weekly_moves
        WHERE pct_5d IS NOT NULL
        """,
        symbols, as_of,
    )
    avg_weekly = momentum_row["avg_weekly_move"] if momentum_row else None

    # Price history days: how many trading days of data exist for these symbols
    history_row = await conn.fetchrow(
        "SELECT COUNT(DISTINCT dt) AS n FROM prices WHERE symbol = ANY($1) AND dt <= $2",
        symbols, as_of,
    )
    history_days = history_row["n"] or 0

    from decimal import Decimal
    return ClassifierInput(
        price_history_days=history_days,
        pct_above_50d_ma=Decimal(str(pct_above_50d)) if pct_above_50d is not None else None,
        pct_above_200d_ma=Decimal(str(pct_above_200d)) if pct_above_200d is not None else None,
        avg_weekly_move_pct=Decimal(str(avg_weekly)) if avg_weekly is not None else None,
        news_sentiment=None,       # news_sentiment table — populated in M-Ingest-News
        retail_mention_ratio=None, # no retail mention data yet
    )


async def _process_theme(conn, theme_id: int, theme_code: str, current_suggested: str | None, as_of: date) -> bool:
    """Run classifier on one theme. Returns True if stage_suggested was updated."""
    # Get symbols for this theme
    symbol_rows = await conn.fetch(
        "SELECT symbol FROM theme_holdings WHERE theme_id = $1",
        theme_id,
    )
    symbols = [r["symbol"] for r in symbol_rows]

    inputs = await _build_classifier_input(conn, symbols, as_of)
    result = classify_stage(inputs, THRESHOLDS)

    if result is None:
        print(f"  {theme_code}: insufficient data ({inputs.price_history_days}d prices) — skipping")
        return False

    suggested_label, conditions_fired = result

    if suggested_label == current_suggested:
        print(f"  {theme_code}: stage_suggested unchanged ({suggested_label})")
        return False

    stage_metadata = {
        "classifier_version": CLASSIFIER_VERSION,
        "conditions_fired": conditions_fired,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "price_history_days": inputs.price_history_days,
    }

    await conn.execute(
        """
        UPDATE themes
        SET stage_suggested = $1,
            stage_metadata  = $2
        WHERE theme_id = $3
        """,
        suggested_label,
        json.dumps(stage_metadata),
        theme_id,
    )
    print(f"  {theme_code}: stage_suggested {current_suggested!r} → {suggested_label!r}")
    return True


async def main() -> None:
    as_of = date.today()
    updated = 0

    await init_pool()
    try:
        async with JobMonitor(_JOB, as_of) as monitor:
            async with acquire() as conn:
                themes = await conn.fetch(
                    """
                    SELECT theme_id, theme_code, stage_suggested
                    FROM themes
                    WHERE retired_at IS NULL
                    ORDER BY theme_code
                    """
                )

                if not themes:
                    print("No active themes — nothing to classify.", file=sys.stderr)
                    monitor.rows_written = 0
                    return

                print(f"Classifying {len(themes)} active themes as of {as_of}")
                for row in themes:
                    try:
                        changed = await _process_theme(
                            conn,
                            row["theme_id"],
                            row["theme_code"],
                            row["stage_suggested"],
                            as_of,
                        )
                        if changed:
                            updated += 1
                    except Exception as exc:
                        print(f"  {row['theme_code']}: ERROR — {exc}", file=sys.stderr)

            monitor.rows_written = updated
            print(f"detect_theme_stages complete: {updated} theme(s) updated of {len(themes)} classified")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
