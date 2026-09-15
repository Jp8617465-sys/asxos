"""The bundled, sealed scenario pre-registration for the universe sweep.

The JSON beside this module IS the registration: it carries its own
`content_hash`, so `ScenarioPreregistration.model_validate` verifies the file
has not been edited since it was sealed (an edit is a NEW registration with a
new id, never a re-seal of the old one — 0054's table is append-only for the
same reason). The runner registers it in `valuation_scenario_preregistrations`
before the first run and refuses to proceed if the stored row for the same id
carries a different hash.
"""
from __future__ import annotations

import json
from importlib import resources
from typing import Final

from asxos.domain.valuation.contracts import ScenarioPreregistration

BUNDLED_PREREGISTRATION_FILE: Final[str] = "prereg_asx_universe_2026_09_16.json"


def load_bundled_preregistration() -> ScenarioPreregistration:
    """Load and hash-verify the shipped registration. Raises on any drift."""
    text = (
        resources.files("asxos.domain.valuation")
        .joinpath(BUNDLED_PREREGISTRATION_FILE)
        .read_text(encoding="utf-8")
    )
    raw = json.loads(text)
    if not raw.get("content_hash"):
        raise ValueError(
            f"{BUNDLED_PREREGISTRATION_FILE} is not sealed: content_hash is absent. "
            "A registration without a hash was never committed before a run."
        )
    return ScenarioPreregistration.model_validate(raw)
