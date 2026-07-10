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

from typing import Any, Literal, overload


@overload
def resolve_production_model(
    model_rows: list[Any], *, required: Literal[True] = ...
) -> str: ...
@overload
def resolve_production_model(
    model_rows: list[Any], *, required: Literal[False]
) -> str | None: ...


def resolve_production_model(
    model_rows: list[Any], *, required: bool = True
) -> str | None:
    """Return the single approved production model name.

    ``model_rows`` must come from a query already filtered to
    ``is_active = TRUE AND approved_for_allocation = TRUE`` and each row
    must expose a ``"model"`` key.

    ``required=True`` (default) hard-fails on 0 rows (nothing approved) or
    >1 rows (multi-sleeve out of v1 scope). This is the capital-safety
    invariant the allocator (``build.py``) relies on — it is rule #11's real
    enforcement point (revoke approval → 0 rows → the allocator refuses to
    run). Never relax it there.

    ``required=False`` returns ``None`` in those two cases instead of raising.
    Use it for **display-only** consumers — the brief's cosmetic "Model A"
    line. Under a deliberate Model A quarantine (rule #11 →
    ``approved_for_allocation`` revoked → 0 approved rows) the
    model-INDEPENDENT brief (tax, regulatory, job-failure, portfolio, and the
    thesis discipline cards) must still render rather than hard-fail and hide
    the Model-A-independent discipline layer. See risk-register R9.
    """
    if len(model_rows) == 0:
        if not required:
            return None
        raise RuntimeError(
            "no model_version is both active and approved_for_allocation; "
            "run `asx model approve <model> <version>` first "
            "(plan H.1 CRITICAL-4)"
        )
    if len(model_rows) > 1:
        if not required:
            return None
        raise RuntimeError(
            "multiple models are active+approved_for_allocation "
            f"({[r['model'] for r in model_rows]}); multi-sleeve blending "
            "is out of v1 scope (portfolio-conventions.md) — demote all "
            "but one via `asx model revoke <model> <version>`"
        )
    return str(model_rows[0]["model"])
