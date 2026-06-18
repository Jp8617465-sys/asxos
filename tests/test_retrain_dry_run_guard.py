"""
Behavioural guard: the model_a v1_6 retrain --dry-run path performs NO writes.

This complements the source-inspection checks in test_retrain_wiring.py by
actually invoking jobs.retrain_model_a.main(..., dry_run=True) with every I/O
boundary mocked, and asserting that none of the write sinks fire:
  * joblib.dump (model artefacts)
  * _insert_candidate (the model_versions row)
  * build_artifact_metadata (the v1_6 metadata sidecar)
and that the models directory (a tmp_path) stays empty. A contrast test confirms
the non-dry path DOES persist + insert exactly one candidate (so the dry-run
guard is gating real writes), and that the only DB write is the candidate insert
for this model/version — no activation path is ever taken.

CI-only: jobs.retrain_model_a imports pandas/joblib at module load, so (like the
other jobs/*_job tests) this module is a collection gap in the lint-only sandbox
and runs on the ML-enabled targeted-ml-tests image. conftest.py puts the repo
root on sys.path so `import jobs.retrain_model_a` resolves.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, asynccontextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

import jobs.retrain_model_a as rj


def _fake_panel(*, include_adj_close: bool) -> pd.DataFrame:
    """A tiny non-empty panel carrying the columns main() touches."""
    data = {
        "symbol": ["AAA.AU", "AAA.AU"],
        "dt": [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-02")],
        "close": [10.0, 10.1],
    }
    if include_adj_close:
        data["adj_close"] = [100.0, 101.0]
    return pd.DataFrame(data)


class _FakeMonitor:
    """Stand-in for JobMonitor (async context manager, settable rows_written)."""

    def __init__(self, **kw: object) -> None:
        self.rows_written: int | None = None

    async def __aenter__(self) -> _FakeMonitor:
        return self

    async def __aexit__(self, *a: object) -> bool:
        return False


class _FakeEngine:
    """FeatureEngine stand-in: identity passthrough, no heavy compute."""

    def __init__(self, *a: object, **k: object) -> None:
        pass

    def compute_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        return df


@asynccontextmanager
async def _acquire_ctx():  # type: ignore[no-untyped-def]
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[{"symbol": "AAA.AU"}])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value=None)
    yield conn


def _fake_result(features: object) -> SimpleNamespace:
    return SimpleNamespace(
        classifier=object(),
        regressor=object(),
        features=list(features) if features else ["f"],
        auc_per_fold=[0.7],
        rmse_per_fold=[1.0],
        auc_mean=0.7,
        auc_std=0.0,
        n_samples=5000,
    )


def _build_patches(tmp_path, sinks):  # type: ignore[no-untyped-def]
    """Patch every I/O boundary of jobs.retrain_model_a so main() runs offline.

    Returns (patch_list, load_panel_mock, train_mock) — the two extra mocks let
    callers assert the v1_6 recipe was threaded through.
    """
    load_panel = AsyncMock(
        side_effect=lambda conn, as_of, *, symbols=None, include_adj_close=False, **k:
        _fake_panel(include_adj_close=include_adj_close)
    )
    train = MagicMock(side_effect=lambda panel, features, **kw: _fake_result(features))
    patches = [
        patch.object(rj, "init_pool", new=AsyncMock()),
        patch.object(rj, "close_pool", new=AsyncMock()),
        patch.object(rj, "acquire", new=lambda: _acquire_ctx()),
        patch.object(rj, "JobMonitor", new=_FakeMonitor),
        patch.object(rj, "FeatureEngine", new=_FakeEngine),
        patch.object(rj, "load_panel", new=load_panel),
        patch.object(rj, "train_model_a", new=train),
        patch.object(rj, "_baseline_auc", new=AsyncMock(return_value=None)),
        patch.object(
            rj, "evaluate_gates",
            new=MagicMock(return_value=SimpleNamespace(passed=True, degradation_pct=0.0, reasons=[])),
        ),
        patch.object(rj, "_insert_candidate", new=sinks["insert"]),
        patch.object(rj, "build_artifact_metadata", new=sinks["meta"]),
        patch.object(rj.joblib, "dump", new=sinks["dump"]),
        patch.object(
            rj, "settings",
            new=SimpleNamespace(asxos_models_dir=str(tmp_path), healthcheck_url_retrain_model_a=None),
        ),
    ]
    return patches, load_panel, train


def _fresh_sinks():  # type: ignore[no-untyped-def]
    return {
        "dump": MagicMock(),                                    # joblib.dump (sync)
        "insert": AsyncMock(),                                  # _insert_candidate (async)
        "meta": MagicMock(return_value={"model_version": "model_a_v1_6"}),  # metadata builder
    }


def test_v1_6_dry_run_performs_no_writes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """`--version v1_6 --dry-run` must call NO write sink and write NO file."""
    sinks = _fresh_sinks()
    patches, load_panel, train = _build_patches(tmp_path, sinks)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        asyncio.run(rj.main("v1_6", date(2026, 1, 10), dry_run=True))

    # No artefact dump, no model_versions insert, no metadata sidecar build.
    sinks["dump"].assert_not_called()
    sinks["insert"].assert_not_called()
    sinks["meta"].assert_not_called()
    # Nothing was written to the models directory.
    assert list(tmp_path.iterdir()) == []
    # The v1_6 recipe was genuinely selected and threaded (so the no-write
    # result is the dry-run gate, not a misconfigured no-op).
    assert train.call_args.kwargs == {"target_unit": "fraction", "price_basis": "adj_close"}
    assert load_panel.call_args.kwargs.get("include_adj_close") is True


def test_non_dry_run_persists_and_inserts_inactive_candidate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Contrast: the real (non-dry) path DOES persist + insert exactly one
    candidate, proving the dry-run guard gates real writes. The only DB write is
    the candidate insert for this model/version — no activation path."""
    sinks = _fresh_sinks()
    patches, _load_panel, _train = _build_patches(tmp_path, sinks)
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        asyncio.run(rj.main("v1_6", date(2026, 1, 10), dry_run=False))

    assert sinks["dump"].call_count == 2          # classifier + regressor
    assert sinks["insert"].await_count == 1       # exactly one model_versions candidate
    assert sinks["meta"].call_count == 1          # v1_6 metadata sidecar built
    # The candidate insert is for this model/version (is_active=FALSE is pinned in
    # the SQL, asserted at source level in test_retrain_wiring.py).
    assert sinks["insert"].await_args.args[:2] == ("model_a", "v1_6")
    # JSON sidecars landed in the models dir; artefact .pkl writes go via the
    # mocked joblib.dump (no real pickle).
    written = sorted(p.name for p in tmp_path.iterdir())
    assert "model_a_v1_6_features.json" in written
    assert "model_a_v1_6_metrics.json" in written
    assert "model_a_v1_6_metadata.json" in written
