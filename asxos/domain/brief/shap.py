"""SHAP factor formatting for brief surfaces.

Shared by the V1 signal-change line (`asxos/brief/compose.py::_signal_changes`)
and the V2 steady-state thesis cards
(`asxos/domain/brief/collectors/active_theses.py`).

`signals.shap_factors` is a flat JSONB ``{feature: float}`` map (see
migration 0001 and `asxos/domain/signals/.../writer.py`). The ``bias`` term is
the model intercept and is never a *driver*, so it is excluded from display.
asyncpg may hand the JSONB back either as a ``dict`` (normal codec) or as a raw
``str`` (no JSON codec registered for the connection); both are normalised here
so call sites do not each re-implement the parse.
"""
from __future__ import annotations

import json
from typing import Any


def _normalize(shap: dict[str, Any] | str | None) -> dict[str, Any]:
    """Coerce a raw shap_factors value (dict | JSON str | None) to a dict."""
    if not shap:
        return {}
    if isinstance(shap, str):
        try:
            parsed = json.loads(shap)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return shap


def rank_shap_factors(
    shap: dict[str, Any] | str | None, n: int = 3
) -> list[tuple[str, float]]:
    """Top-``n`` ``(feature, value)`` pairs by absolute SHAP value.

    Excludes the ``bias`` intercept and any ``None``/non-numeric values.
    Returns fewer than ``n`` pairs when the map is smaller, and an empty list
    when nothing ranks (so the caller can omit the drivers line entirely).
    """
    factors: list[tuple[str, float]] = []
    for k, v in _normalize(shap).items():
        if k == "bias" or v is None:
            continue
        try:
            fv = float(v)
        except (ValueError, TypeError):
            continue
        factors.append((k, fv))
    factors.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return factors[:n]


def format_top_factors(
    shap: dict[str, Any] | str | None, n: int = 3, sep: str = ", "
) -> str:
    """Format the top-``n`` SHAP drivers as ``"feat+0.123, feat2-0.045"``.

    Returns an empty string when no factor ranks — call sites treat the empty
    string as "no drivers to show" and skip the line.
    """
    return sep.join(f"{k}{v:+.3f}" for k, v in rank_shap_factors(shap, n))
