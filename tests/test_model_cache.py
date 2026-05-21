"""
Tests for asxos.domain.models.cache.

Synthetic pickles in a tmp dir — no DB or network. asxos.db.acquire is
patched to return rows from an in-memory list so the test controls what
the cache sees as the active version.
"""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import joblib
import pytest

from asxos.domain.models.cache import ModelCache, _load_artefacts


class _FakeModel:
    """Stand-in for an LGBMClassifier — joblib-pickleable, no ML deps needed."""

    def __init__(self, tag: str) -> None:
        self.tag = tag


def _seed_artefacts(models_dir: Path, model: str, version: str, tag: str) -> None:
    stem = f"{model}_{version}"
    joblib.dump(_FakeModel(f"clf-{tag}"), models_dir / f"{stem}_classifier.pkl")
    joblib.dump(_FakeModel(f"reg-{tag}"), models_dir / f"{stem}_regressor.pkl")
    (models_dir / f"{stem}_features.json").write_text(
        json.dumps({"features": ["f1", "f2", "f3"], "version": version})
    )


class _FakeConn:
    """Minimal asyncpg.Connection stand-in returning whatever the harness set."""

    def __init__(self, harness: _DBHarness) -> None:
        self._harness = harness

    async def fetchrow(self, _query: str, model_name: str) -> dict | None:
        self._harness.calls += 1
        version = self._harness.active.get(model_name)
        return {"version": version} if version else None


class _DBHarness:
    def __init__(self) -> None:
        self.active: dict[str, str] = {}
        self.calls = 0

    @asynccontextmanager
    async def acquire(self) -> Any:
        yield _FakeConn(self)


@pytest.fixture
def models_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "asxos.domain.models.cache.settings",
        type("S", (), {"asxos_models_dir": tmp_path})(),
    )
    return tmp_path


@pytest.fixture
def harness() -> _DBHarness:
    return _DBHarness()


@pytest.fixture(autouse=True)
def patch_acquire(harness: _DBHarness) -> Any:
    with patch("asxos.domain.models.cache.acquire", harness.acquire):
        yield


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


# ---------------------------------------------------------------------------
# happy paths
# ---------------------------------------------------------------------------

def test_get_loads_active_version_and_features(models_dir: Path, harness: _DBHarness) -> None:
    _seed_artefacts(models_dir, "model_a", "v1_5", "a")
    harness.active["model_a"] = "v1_5"
    cache = ModelCache(ttl=60.0)

    loaded = _run(cache.get("model_a"))

    assert loaded.name == "model_a"
    assert loaded.version == "v1_5"
    assert loaded.features == ["f1", "f2", "f3"]
    assert loaded.classifier.tag == "clf-a"  # type: ignore[attr-defined]
    assert loaded.regressor.tag == "reg-a"  # type: ignore[attr-defined]


def test_second_get_within_ttl_skips_db(models_dir: Path, harness: _DBHarness) -> None:
    _seed_artefacts(models_dir, "model_a", "v1_5", "a")
    harness.active["model_a"] = "v1_5"
    cache = ModelCache(ttl=60.0)

    _run(cache.get("model_a"))
    _run(cache.get("model_a"))
    _run(cache.get("model_a"))

    assert harness.calls == 1


def test_ttl_expiry_triggers_db_recheck(models_dir: Path, harness: _DBHarness) -> None:
    _seed_artefacts(models_dir, "model_a", "v1_5", "a")
    harness.active["model_a"] = "v1_5"
    cache = ModelCache(ttl=0.01)

    _run(cache.get("model_a"))
    time.sleep(0.02)
    _run(cache.get("model_a"))

    assert harness.calls == 2


def test_same_version_after_ttl_keeps_cached_object(
    models_dir: Path, harness: _DBHarness
) -> None:
    _seed_artefacts(models_dir, "model_a", "v1_5", "a")
    harness.active["model_a"] = "v1_5"
    cache = ModelCache(ttl=0.01)

    first = _run(cache.get("model_a"))
    time.sleep(0.02)
    second = _run(cache.get("model_a"))

    assert first is second  # identity preserved across re-checks


def test_version_flip_reloads_artefacts(models_dir: Path, harness: _DBHarness) -> None:
    _seed_artefacts(models_dir, "model_a", "v1_5", "a")
    _seed_artefacts(models_dir, "model_a", "v1_6", "b")
    harness.active["model_a"] = "v1_5"
    cache = ModelCache(ttl=0.01)

    first = _run(cache.get("model_a"))
    assert first.version == "v1_5"

    harness.active["model_a"] = "v1_6"
    time.sleep(0.02)
    second = _run(cache.get("model_a"))

    assert second.version == "v1_6"
    assert second.classifier.tag == "clf-b"  # type: ignore[attr-defined]
    assert first is not second


# ---------------------------------------------------------------------------
# failure modes — hard-fail per ml-conventions
# ---------------------------------------------------------------------------

def test_no_active_row_raises(models_dir: Path) -> None:
    cache = ModelCache(ttl=60.0)
    with pytest.raises(RuntimeError, match="no active version for model_a"):
        _run(cache.get("model_a"))


def test_missing_artefact_raises(models_dir: Path, harness: _DBHarness) -> None:
    harness.active["model_a"] = "v1_5"  # row exists but no pickle on disk
    cache = ModelCache(ttl=60.0)
    with pytest.raises(RuntimeError, match="active model artefact missing"):
        _run(cache.get("model_a"))


def test_features_json_without_features_list_raises(
    models_dir: Path, harness: _DBHarness
) -> None:
    stem = "model_a_v1_5"
    joblib.dump(_FakeModel("clf"), models_dir / f"{stem}_classifier.pkl")
    joblib.dump(_FakeModel("reg"), models_dir / f"{stem}_regressor.pkl")
    (models_dir / f"{stem}_features.json").write_text(json.dumps({"version": "v1_5"}))
    harness.active["model_a"] = "v1_5"

    with pytest.raises(RuntimeError, match="no 'features' list"):
        _load_artefacts("model_a", "v1_5")


def test_clear_drops_cached_state(models_dir: Path, harness: _DBHarness) -> None:
    _seed_artefacts(models_dir, "model_a", "v1_5", "a")
    harness.active["model_a"] = "v1_5"
    cache = ModelCache(ttl=60.0)

    _run(cache.get("model_a"))
    cache.clear()
    _run(cache.get("model_a"))

    assert harness.calls == 2
