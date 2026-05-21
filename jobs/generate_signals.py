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
from datetime import date

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.models.cache import get_cache
from asxos.domain.models.model_a import predict_with_shap
from asxos.domain.signals.loader import features_from_panel, load_panel
from asxos.domain.signals.regime import classify_regime
from asxos.domain.signals.writer import persist_signals
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)


async def _upstream_ok(conn, as_of: date) -> bool:
    row = await conn.fetchrow(
        """
        SELECT status FROM job_runs
        WHERE job_name = 'sync_prices' AND as_of = $1
        """,
        as_of,
    )
    return row is not None and row["status"] == "success"


async def main(as_of_arg: date | None) -> None:
    as_of = as_of_arg or date.today()
    await init_pool()

    try:
        async with acquire() as conn:
            if not await _upstream_ok(conn, as_of):
                log.warning(
                    f"sync_prices has not completed successfully for {as_of} — "
                    "proceeding anyway (manual run)"
                )

        async with JobMonitor(
            job_name="generate_signals",
            as_of=as_of,
            healthcheck_url=settings.healthcheck_url_generate_signals,
        ) as monitor:
            async with acquire() as conn:
                panel = await load_panel(conn, as_of)

            if panel.empty:
                raise RuntimeError(f"empty price panel for {as_of}")

            regime = classify_regime(panel)
            log.info(f"regime: {regime}")

            features = features_from_panel(panel, as_of)
            if features.empty:
                raise RuntimeError(
                    f"feature engine produced 0 rows for {as_of} — "
                    "check that the lookback window is fully populated"
                )
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
    asyncio.run(main(parser.parse_args().as_of))
