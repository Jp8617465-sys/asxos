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
  - models/model_a_{version}_metadata.json   (v1_6 recipe only; self-describing)
  - a model_versions row with is_active=FALSE

The training recipe is selected by version via select_training_config: any
version other than v1_6 resolves to the v1_5 baseline (raw close, basis-point
target, no adj_close) — byte-identical to the legacy path. `--version v1_6`
opts into the adj_close / fractional-target recipe and additionally writes the
self-describing metadata sidecar. Liquidity dollar-volume stays raw close in
every recipe.

Activation is a separate manual step via `asx model activate <version>`; this
job only ever inserts a candidate row with is_active=FALSE. `--dry-run` trains
and evaluates the gates but skips every artefact and DB write. Refuses to
clobber an existing version on disk.

Usage:
    python jobs/retrain_model_a.py --version v1_6 --as-of 2026-05-20
    python jobs/retrain_model_a.py --version v1_6 --as-of 2026-05-20 --dry-run
"""
import argparse
import asyncio
import json
import logging
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from asxos.config import settings
from asxos.db import acquire, close_pool, init_pool
from asxos.domain.models.metadata import build_artifact_metadata
from asxos.domain.models.train import train_model_a
from asxos.domain.models.training_config import (
    MODEL_A_V1_5_CONFIG,
    select_training_config,
    training_panel_columns,
)
from asxos.domain.models.validation import evaluate_gates
from asxos.domain.signals.feature_engine import MODEL_A_FEATURES, FeatureEngine
from asxos.domain.signals.loader import (
    FUNDAMENTAL_FEATURE_COLS,
    load_panel,
)
from asxos.jobs.utils.job_monitor import JobMonitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Batch 300 symbols at a time so peak memory stays within the 512MB Render free-tier.
# Unlike generate_signals (which keeps only target-date rows), retraining needs ALL dates
# per symbol (build_target uses groupby("symbol")["close"].shift(-5)). We compensate by
# slimming each batch to only the columns needed before concatenating.
_TRAIN_BATCH_SIZE = 300
_KEEP_COLS_BASE = {"symbol", "dt", "close"}


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


async def main(version: str, as_of: date, *, dry_run: bool = False) -> None:
    model = "model_a"
    # Recipe is selected by version. Unknown/v1_5 versions resolve to the v1_5
    # baseline (raw close, basis points, no adj_close) — byte-identical to the
    # legacy path. Only `--version v1_6` opts into the adj_close/fraction recipe.
    config = select_training_config(f"{model}_{version}")
    write_metadata = config is not MODEL_A_V1_5_CONFIG
    log.info(
        "retrain %s_%s: price_basis=%s target_unit=%s include_adj_close=%s "
        "dry_run=%s",
        model, version, config.price_basis, config.target_unit,
        config.include_adj_close, dry_run,
    )
    models_dir = Path(settings.asxos_models_dir)

    stem = models_dir / f"{model}_{version}"
    clf_path = Path(f"{stem}_classifier.pkl")
    reg_path = Path(f"{stem}_regressor.pkl")
    feat_path = Path(f"{stem}_features.json")
    metrics_path = Path(f"{stem}_metrics.json")
    meta_path = Path(f"{stem}_metadata.json")
    artefact_paths = [clf_path, reg_path, feat_path, metrics_path]
    if write_metadata:
        artefact_paths.append(meta_path)
    # Dry-run never writes, so the no-clobber guard does not apply.
    if not dry_run:
        for p in artefact_paths:
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
                sym_rows = await conn.fetch(
                    "SELECT symbol FROM universe WHERE is_active = TRUE AND security_kind = 'au_equity' ORDER BY symbol"
                )
            all_symbols = [r["symbol"] for r in sym_rows]
            if not all_symbols:
                raise RuntimeError(f"no active symbols found for {as_of}")

            engine = FeatureEngine(price_basis=config.price_basis)
            keep_cols = training_panel_columns(
                config, MODEL_A_FEATURES, base_cols=tuple(_KEEP_COLS_BASE)
            )
            enriched_batches: list[pd.DataFrame] = []
            n_batches = (len(all_symbols) - 1) // _TRAIN_BATCH_SIZE + 1
            for batch_start in range(0, len(all_symbols), _TRAIN_BATCH_SIZE):
                batch = all_symbols[batch_start : batch_start + _TRAIN_BATCH_SIZE]
                async with acquire() as conn:
                    batch_panel = await load_panel(
                        conn, as_of, symbols=batch, **config.load_panel_kwargs
                    )
                if batch_panel.empty:
                    log.warning(
                        "batch %d/%d: empty panel, skipping",
                        batch_start // _TRAIN_BATCH_SIZE + 1,
                        n_batches,
                    )
                    continue
                batch_enriched = engine.compute_all_features(batch_panel)
                del batch_panel
                for col in FUNDAMENTAL_FEATURE_COLS:
                    if col in batch_enriched.columns:
                        batch_enriched[col] = batch_enriched[col].fillna(0.0)
                enriched_batches.append(
                    batch_enriched[[c for c in keep_cols if c in batch_enriched.columns]]
                )
                del batch_enriched
                log.info(
                    "retrain batch %d/%d done",
                    batch_start // _TRAIN_BATCH_SIZE + 1,
                    n_batches,
                )

            if not enriched_batches:
                raise RuntimeError(f"all batches empty — no enriched features for {as_of}")
            enriched = pd.concat(enriched_batches, ignore_index=True)
            del enriched_batches
            log.info(f"panel: {len(enriched)} rows, {enriched['symbol'].nunique()} symbols")

            result = train_model_a(
                enriched, MODEL_A_FEATURES, **config.train_model_a_kwargs
            )
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

            metrics_payload = {
                "auc_mean": result.auc_mean,
                "auc_std": result.auc_std,
                "auc_per_fold": result.auc_per_fold,
                "rmse_per_fold": result.rmse_per_fold,
                "n_samples": result.n_samples,
                "baseline_auc": baseline,
                "degradation_pct": verdict.degradation_pct,
            }
            notes = (
                f"Walk-forward AUC mean {result.auc_mean:.4f} "
                f"(std {result.auc_std:.4f}); n_samples={result.n_samples}; "
                f"degradation_pct={verdict.degradation_pct}"
            )

            if dry_run:
                planned = ", ".join(p.name for p in artefact_paths)
                log.info(
                    "[dry-run] gates passed (AUC=%.4f, n=%d) — would write %s and "
                    "insert an is_active=FALSE model_versions row for %s; skipping "
                    "all artefact and DB writes. Never activates.",
                    result.auc_mean, result.n_samples, planned, version,
                )
                monitor.rows_written = 0
            else:
                # All gates passed — persist artefacts + DB row (is_active=FALSE).
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
                metrics_path.write_text(json.dumps(metrics_payload, indent=2))
                if write_metadata:
                    # Self-describing v1_6 artefact metadata (closes P0-A: units +
                    # price basis are recorded, never inferred). Sidecar only —
                    # nothing reads it yet; the v1_5 path writes no metadata.
                    train_start = pd.Timestamp(enriched["dt"].min()).date().isoformat()
                    train_end = pd.Timestamp(enriched["dt"].max()).date().isoformat()
                    meta_path.write_text(
                        json.dumps(
                            build_artifact_metadata(
                                model_version=f"{model}_{version}",
                                target_unit=config.target_unit,
                                price_basis=config.price_basis,
                                liquidity_price_basis=config.liquidity_price_basis,
                                label_horizon_days=config.label_horizon_days,
                                purge_embargo_days=config.purge_embargo_days,
                                train_start=train_start,
                                train_end=train_end,
                            ),
                            indent=2,
                        )
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Train and evaluate gates but skip ALL artefact and model_versions "
        "writes (no joblib dump, no DB row). Never activates.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.version, args.as_of or date.today(), dry_run=args.dry_run))
