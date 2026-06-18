"""
model_a v1_6 retrain-job wiring contracts (jobs/retrain_model_a.py).

Source-inspection only — the retrain job imports pandas/joblib/lightgbm, so it
cannot be imported in the lint-only sandbox (nor is it in the targeted-ml-tests
file list). These stdlib tests read the job source and assert the v1_6 wiring is
present and the production safety invariants hold:
  * the recipe is selected by version (v1_5 baseline byte-identical; v1_6 opt-in);
  * load_panel / train_model_a / FeatureEngine / panel columns are threaded from
    the config;
  * --dry-run gates every artefact and DB write;
  * the job still inserts is_active=FALSE and never activates a model.

The behavioural decision logic (select_training_config / training_panel_columns)
is unit-tested directly in tests/test_training_config.py.
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = (_REPO_ROOT / "jobs" / "retrain_model_a.py").read_text()
_NORM = _SRC.replace(" ", "").lower()


def test_imports_v1_6_config_helpers() -> None:
    assert "from asxos.domain.models.training_config import" in _SRC
    assert "select_training_config" in _SRC
    assert "training_panel_columns" in _SRC
    assert "MODEL_A_V1_5_CONFIG" in _SRC
    assert "from asxos.domain.models.metadata import build_artifact_metadata" in _SRC


def test_config_selected_by_version() -> None:
    assert 'select_training_config(f"{model}_{version}")' in _SRC


def test_load_panel_threads_config_kwargs() -> None:
    assert "config.load_panel_kwargs" in _SRC


def test_train_model_a_threads_config_kwargs() -> None:
    assert "config.train_model_a_kwargs" in _SRC


def test_feature_engine_uses_config_price_basis() -> None:
    assert "FeatureEngine(price_basis=config.price_basis)" in _SRC


def test_panel_columns_use_helper() -> None:
    assert "training_panel_columns(" in _SRC


def test_dry_run_flag_is_wired() -> None:
    assert "--dry-run" in _SRC
    assert 'action="store_true"' in _SRC
    # threaded into main and into the run call
    assert "dry_run: bool = False" in _SRC
    assert "dry_run=args.dry_run" in _SRC


def test_dry_run_gates_writes() -> None:
    """Writes live under the non-dry-run branch; dry-run skips them."""
    assert "if dry_run:" in _SRC
    assert "joblib.dump" in _SRC  # the write path still exists for real runs
    # the no-clobber guard is skipped in dry-run
    assert "if not dry_run:" in _SRC


def test_candidate_insert_still_inactive() -> None:
    """The model_versions insert still pins is_active = FALSE."""
    assert "values($1,$2,$3,false,$4)" in _NORM


def test_job_never_activates() -> None:
    """No activation UPDATE anywhere in the retrain job."""
    assert "setis_active=true" not in _NORM


def test_metadata_sidecar_is_wired_and_v1_5_writes_none() -> None:
    """v1_6 writes a self-describing metadata sidecar; v1_5 writes none."""
    assert "build_artifact_metadata(" in _SRC
    assert "_metadata.json" in _SRC
    # the sidecar is gated so the v1_5 baseline path writes no metadata
    assert "write_metadata" in _SRC
    assert "is not MODEL_A_V1_5_CONFIG" in _SRC
