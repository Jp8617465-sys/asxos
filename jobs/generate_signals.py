#!/usr/bin/env python
"""
Daily Model A signal generation.

Reads prices + fundamentals for a 450-day lookback window, runs the
FeatureEngine, predicts with Model A v1_5, classifies labels under the
detected regime, and upserts rows into the signals table.

GATE: refuses to run if sync_prices has no success row for `as_of`
(ml-conventions / job-conventions: never write signals on stale prices).

Usage:
    python jobs/generate_signals.py                # today
    python jobs/generate_signals.py --as-of 2026-05-20
"""
import argparse
import asyncio
import logging
from datetime import date, timedelta

import asyncpg
import pandas as pd

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.models.cache import get_cache
from asxos.domain.models.model_a import predict_with_shap
from asxos.domain.signals.loader import features_from_panel, load_panel
from asxos.domain.signals.regime import classify_regime
from asxos.domain.signals.writer import persist_signals
from asxos.jobs._helpers import UpstreamBlocked
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# Batch 300 symbols at a time so peak memory stays ~100MB per batch
# (300 symbols × 450 days × 33 cols × 8B ≈ 36MB base; 3× with intermediates).
# Render free tier: 512MB. Full 1872-symbol panel in one shot: ~450MB → OOM.
_FEATURE_BATCH_SIZE = 300
_REGIME_TOP_N = 20  # top-N liquid symbols used to build the market-regime proxy


async def _upstream_ok(conn: "asyncpg.Connection", as_of: date) -> bool:
    # Allow up to 5 calendar days lag — covers weekends + public holidays.
    # sync_prices records as_of = the run date (not the target data date), so
    # we can't do an exact match against the price date.
    row = await conn.fetchrow(
        """
        SELECT 1 FROM job_runs
        WHERE job_name = 'sync_prices'
          AND status    = 'success'
          AND as_of    >= $1::date - 5
        """,
        as_of,
    )
    return row is not None


async def _last_price_date(conn: "asyncpg.Connection") -> date | None:
    """Return the most recent dt in the prices table across active symbols."""
    return await conn.fetchval(
        """
        SELECT MAX(p.dt)
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        WHERE u.is_active = TRUE
        """
    )


async def _top_liquid_symbols(conn: "asyncpg.Connection", as_of: date, n: int = _REGIME_TOP_N) -> list[str]:
    """Top-N symbols by recent average dollar volume — used for regime proxy panel."""
    rows = await conn.fetch(
        """
        SELECT p.symbol
        FROM prices p
        JOIN universe u ON u.symbol = p.symbol
        WHERE p.dt BETWEEN $1 AND $2
          AND u.is_active = TRUE
        GROUP BY p.symbol
        ORDER BY AVG(p.close * p.volume) DESC
        LIMIT $3
        """,
        as_of - timedelta(days=30),
        as_of,
        n,
    )
    return [r["symbol"] for r in rows]


async def main(as_of_arg: date | None, allow_stale_upstream: bool = False) -> None:
    await init_pool()

    try:
        # Determine as_of from the last available price date in the DB.
        # Using date.today() would filter panel["dt"] == today, but sync_prices
        # only writes target = yesterday, so today's rows never exist → 0 features.
        # Using the actual last price date makes the job robust to holidays and
        # weekend gaps where sync_prices writes 0 AU rows.
        async with acquire() as conn:
            last_dt = await _last_price_date(conn)
        if last_dt is None:
            raise RuntimeError("no prices in DB — run sync_prices first")
        as_of = as_of_arg or last_dt

        # Upstream check is INSIDE the JobMonitor block so a UpstreamBlocked
        # raise gets recorded to job_runs as status='blocked'. The previous
        # placement (outside JobMonitor) silently emitted a warning and
        # generated stale signals — see P0-2 in docs/maintenance/guards-backlog.md.
        async with JobMonitor(
            job_name="generate_signals",
            as_of=as_of,
            healthcheck_url=settings.healthcheck_url_generate_signals,
            override_reason=(
                "operator: --allow-stale-upstream" if allow_stale_upstream else None
            ),
        ) as monitor:
            async with acquire() as conn:
                upstream_ok = await _upstream_ok(conn, as_of)

            if not upstream_ok:
                if not allow_stale_upstream:
                    raise UpstreamBlocked(
                        f"sync_prices has no success row for {as_of}; refusing "
                        "to generate signals on stale prices. Use "
                        "--allow-stale-upstream for a one-off manual override."
                    )
                log.warning(
                    "Proceeding on stale upstream by explicit --allow-stale-upstream "
                    "(recorded in job_runs.override_reason)."
                )

            # Step 1: regime from a tiny proxy panel (top-20 most liquid symbols).
            # Avoids loading the full 1872-symbol panel just for regime detection.
            async with acquire() as conn:
                regime_syms = await _top_liquid_symbols(conn, as_of)
                regime_panel = await load_panel(conn, as_of, symbols=regime_syms)
            if regime_panel.empty:
                raise RuntimeError(f"empty price panel for regime detection on {as_of}")
            regime = classify_regime(regime_panel)
            del regime_panel
            log.info(f"regime: {regime}")

            # Step 2: load all active symbols in batches, compute features per batch,
            # then concatenate. Keeps peak memory ~100MB vs ~450MB for a single pass.
            async with acquire() as conn:
                sym_rows = await conn.fetch(
                    "SELECT symbol FROM universe WHERE is_active = TRUE ORDER BY symbol"
                )
            all_symbols = [r["symbol"] for r in sym_rows]

            feature_batches: list[pd.DataFrame] = []
            for batch_start in range(0, len(all_symbols), _FEATURE_BATCH_SIZE):
                batch = all_symbols[batch_start : batch_start + _FEATURE_BATCH_SIZE]
                async with acquire() as conn:
                    batch_panel = await load_panel(conn, as_of, symbols=batch)
                batch_features = features_from_panel(batch_panel, as_of)
                del batch_panel
                if not batch_features.empty:
                    feature_batches.append(batch_features)
                log.info(
                    f"batch {batch_start // _FEATURE_BATCH_SIZE + 1}/"
                    f"{(len(all_symbols) - 1) // _FEATURE_BATCH_SIZE + 1}: "
                    f"{len(batch_features)} symbols"
                )

            if not feature_batches:
                raise RuntimeError(
                    f"feature engine produced 0 rows for {as_of} — "
                    "check that the lookback window is fully populated"
                )
            features = pd.concat(feature_batches)
            log.info(f"features: {len(features)} symbols ready for predict")

            model = await get_cache().get("model_a")
            preds, shap_df = await predict_with_shap(features)

            async with acquire() as conn:
                n = await persist_signals(
                    conn,
                    model="model_a",
                    model_version=model.version,
                    as_of=as_of,
                    preds=preds,
                    shap_df=shap_df,
                    regime=regime,
                )
            monitor.rows_written = n
            log.info(f"generate_signals done: {n} rows written for {as_of}")
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--as-of",
        dest="as_of",
        type=date.fromisoformat,
        default=None,
        help="Prediction date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--allow-stale-upstream",
        action="store_true",
        help=(
            "Proceed even if sync_prices has no success row for as_of. "
            "Manual operator override only — recorded in job_runs.override_reason. "
            "Cron services must NEVER pass this flag."
        ),
    )
    args = parser.parse_args()
    asyncio.run(main(args.as_of, allow_stale_upstream=args.allow_stale_upstream))
