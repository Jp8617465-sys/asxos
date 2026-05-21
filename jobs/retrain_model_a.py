#!/usr/bin/env python
"""
Weekly Model A retraining.

Loads the full price + fundamentals panel for the configured training
window, runs the FeatureEngine, trains a candidate model via walk-forward
TimeSeriesSplit, checks the three gates (AUC, samples, degradation vs
the active baseline), and — on pass — writes:
  - models/model_a_{version}_classifier.pkl
  - models/model_a_{version}_regressor.pkl
  - models/model_a_{version}_features.json
  - models/model_a_{version}_metrics.json
  - a model_versions row with is_active=FALSE

Activation is a separate manual step via `asx model activate <version>`.
Refuses to clobber an existing version on disk — bump --version-suffix.

Usage:
    python jobs/retrain_model_a.py --version v1_6 --as-of 2026-05-20
"""
import argparse
import asyncio
import json
import logging
from datetime import date
from pathlib import Path

import joblib

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.models.train import train_model_a
from asxos.domain.models.validation import evaluate_gates
from asxos.domain.signals.feature_engine import MODEL_A_FEATURES, FeatureEngine
from asxos.domain.signals.loader import (
    FUNDAMENTAL_FEATURE_COLS,
    load_panel,
)
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def _baseline_auc(model: str) -> float | None:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT roc_auc FROM model_versions WHERE model = $1 AND is_active = TRUE",
            model,
        )
    if row is None or row["roc_auc"] is None:
        return None
    return float(row["roc_auc"])


async def _insert_candidate(
    model: str, version: str, auc: float, notes: str
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO model_versions (model, version, roc_auc, is_active, notes)
            VALUES ($1, $2, $3, FALSE, $4)
            ON CONFLICT (model, version) DO UPDATE SET
                roc_auc = EXCLUDED.roc_auc,
                notes   = EXCLUDED.notes
            """,
            model,
            version,
            auc,
            notes,
        )


async def main(version: str, as_of: date) -> None:
    model = "model_a"
    models_dir = Path(settings.asxos_models_dir)

    stem = models_dir / f"{model}_{version}"
    clf_path = Path(f"{stem}_classifier.pkl")
    reg_path = Path(f"{stem}_regressor.pkl")
    feat_path = Path(f"{stem}_features.json")
    metrics_path = Path(f"{stem}_metrics.json")
    for p in (clf_path, reg_path, feat_path, metrics_path):
        if p.exists():
            raise RuntimeError(f"refusing to overwrite existing artefact: {p}")

    await init_pool()
    try:
        async with JobMonitor(
            job_name="retrain_model_a",
            as_of=as_of,
            healthcheck_url=settings.healthcheck_url_retrain_model_a,
        ) as monitor:
            async with acquire() as conn:
                panel = await load_panel(conn, as_of)
            if panel.empty:
                raise RuntimeError(f"empty price panel for {as_of}")

            engine = FeatureEngine()
            enriched = engine.compute_all_features(panel)
            for col in FUNDAMENTAL_FEATURE_COLS:
                if col in enriched.columns:
                    enriched[col] = enriched[col].fillna(0.0)
            log.info(f"panel: {len(enriched)} rows, {enriched['symbol'].nunique()} symbols")

            result = train_model_a(enriched, MODEL_A_FEATURES)
            baseline = await _baseline_auc(model)
            verdict = evaluate_gates(result.auc_mean, result.n_samples, baseline)

            log.info(
                f"trained {model} {version}: AUC={result.auc_mean:.4f} "
                f"(per-fold {[f'{a:.4f}' for a in result.auc_per_fold]}), "
                f"samples={result.n_samples}, baseline_auc={baseline}, "
                f"degradation={verdict.degradation_pct}, passed={verdict.passed}"
            )

            if not verdict.passed:
                raise RuntimeError(
                    f"validation failed: {'; '.join(verdict.reasons)}"
                )

            # All gates passed — persist artefacts + DB row.
            joblib.dump(result.classifier, clf_path)
            joblib.dump(result.regressor, reg_path)
            feat_path.write_text(
                json.dumps(
                    {
                        "features": result.features,
                        "version": version,
                        "n_features": len(result.features),
                    },
                    indent=2,
                )
            )
            metrics_payload = {
                "auc_mean": result.auc_mean,
                "auc_std": result.auc_std,
                "auc_per_fold": result.auc_per_fold,
                "rmse_per_fold": result.rmse_per_fold,
                "n_samples": result.n_samples,
                "baseline_auc": baseline,
                "degradation_pct": verdict.degradation_pct,
            }
            metrics_path.write_text(json.dumps(metrics_payload, indent=2))

            notes = (
                f"Walk-forward AUC mean {result.auc_mean:.4f} "
                f"(std {result.auc_std:.4f}); n_samples={result.n_samples}; "
                f"degradation_pct={verdict.degradation_pct}"
            )
            await _insert_candidate(model, version, result.auc_mean, notes)

            monitor.rows_written = 1
            log.info(
                f"wrote {clf_path.name} + {reg_path.name} (inactive). "
                f"Activate with: asx model activate {version}"
            )
    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="Candidate version, e.g. v1_6")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="Lookback anchor (YYYY-MM-DD). Defaults to today.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.version, args.as_of or date.today()))
