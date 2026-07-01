"""
Contamination-isolation gate (governance architecture Section 4.4 Step B).

The production model is whichever model_versions row is BOTH is_active AND
explicitly approved_for_allocation — never a hardcoded name. Hard-fails on
0 rows (nothing approved) or >1 rows (multi-sleeve blending is out of v1
scope — see portfolio-conventions.md).

Pure function over already-fetched rows: build.py and compose.py each run
their own ``SELECT ... FROM model_versions WHERE is_active = TRUE AND
approved_for_allocation = TRUE`` (column lists differ — build.py also needs
``version`` for rebalance_runs) and pass the result here so the gate
condition and error messages live in exactly one place.
"""
from __future__ import annotations

from typing import Any


def resolve_production_model(model_rows: list[Any]) -> str:
    """Return the single approved production model name, or raise RuntimeError.

    ``model_rows`` must come from a query already filtered to
    ``is_active = TRUE AND approved_for_allocation = TRUE`` and each row
    must expose a ``"model"`` key.
    """
    if len(model_rows) == 0:
        raise RuntimeError(
            "no model_version is both active and approved_for_allocation; "
            "run `asx model approve <model> <version>` first "
            "(plan H.1 CRITICAL-4)"
        )
    if len(model_rows) > 1:
        raise RuntimeError(
            "multiple models are active+approved_for_allocation "
            f"({[r['model'] for r in model_rows]}); multi-sleeve blending "
            "is out of v1 scope (portfolio-conventions.md) — demote all "
            "but one via `asx model revoke <model> <version>`"
        )
    return str(model_rows[0]["model"])
