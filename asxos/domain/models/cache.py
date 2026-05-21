"""
Process-local model cache.

A 60s TTL re-reads model_versions.is_active so an out-of-band activation
(M9 retrain flip) is picked up without a process restart, while predict
loops in the same minute pay zero overhead.

Artefact paths follow a convention against settings.asxos_models_dir:
  {models_dir}/{model}_{version}_classifier.pkl
  {models_dir}/{model}_{version}_regressor.pkl
  {models_dir}/{model}_{version}_features.json

Hard-fails: a missing active row, missing pickle, or features.json shape
mismatch raises RuntimeError. M1 rule — no graceful warnings in infra code.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from asxos.config import settings
from asxos.db import acquire


@dataclass(frozen=True)
class LoadedModel:
    name: str
    version: str
    classifier: Any
    regressor: Any
    features: list[str]


class ModelCache:
    """One in-memory copy per model_name, re-validated every `ttl` seconds."""

    def __init__(self, ttl: float = 60.0) -> None:
        self.ttl = ttl
        self._loaded: dict[str, LoadedModel] = {}
        self._last_check: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, model_name: str) -> LoadedModel:
        now = time.monotonic()
        async with self._lock:
            cached = self._loaded.get(model_name)
            if cached is not None and now - self._last_check.get(model_name, 0.0) < self.ttl:
                return cached

            async with acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT version FROM model_versions "
                    "WHERE model = $1 AND is_active = TRUE",
                    model_name,
                )
            if row is None:
                raise RuntimeError(f"no active version for {model_name}")

            version = row["version"]
            if cached is not None and cached.version == version:
                self._last_check[model_name] = now
                return cached

            loaded = _load_artefacts(model_name, version)
            self._loaded[model_name] = loaded
            self._last_check[model_name] = now
            return loaded

    def clear(self) -> None:
        """Test hook — drop all cached state."""
        self._loaded.clear()
        self._last_check.clear()


def _artefact_paths(model_name: str, version: str) -> tuple[Path, Path, Path]:
    base = Path(settings.asxos_models_dir)
    stem = f"{model_name}_{version}"
    return (
        base / f"{stem}_classifier.pkl",
        base / f"{stem}_regressor.pkl",
        base / f"{stem}_features.json",
    )


def _load_artefacts(model_name: str, version: str) -> LoadedModel:
    clf_path, reg_path, feat_path = _artefact_paths(model_name, version)
    for p in (clf_path, reg_path, feat_path):
        if not p.exists():
            raise RuntimeError(f"active model artefact missing: {p}")

    classifier = joblib.load(clf_path)
    regressor = joblib.load(reg_path)
    features_doc = json.loads(feat_path.read_text())
    features = features_doc.get("features")
    if not isinstance(features, list) or not features:
        raise RuntimeError(f"{feat_path} has no 'features' list")

    return LoadedModel(
        name=model_name,
        version=version,
        classifier=classifier,
        regressor=regressor,
        features=list(features),
    )


_cache = ModelCache()


def get_cache() -> ModelCache:
    return _cache
