"""Smoke test: all V2 domain stub packages import and expose their types."""
from __future__ import annotations

import dataclasses


def _field_names(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def test_theses_types_importable() -> None:
    from asxos.domain.theses import types
    assert dataclasses.is_dataclass(types.Thesis)
    assert "thesis_id" in _field_names(types.Thesis)
    assert "status" in _field_names(types.Thesis)


def test_themes_types_importable() -> None:
    from asxos.domain.themes import types
    assert dataclasses.is_dataclass(types.Theme)
    assert "theme_id" in _field_names(types.Theme)
    assert "stage_suggested" in _field_names(types.Theme)


def test_regime_types_importable() -> None:
    from asxos.domain.regime import types
    assert dataclasses.is_dataclass(types.RegimeSnapshot)
    assert "label" in _field_names(types.RegimeSnapshot)


def test_underlyings_types_importable() -> None:
    from asxos.domain.underlyings import types
    assert dataclasses.is_dataclass(types.ThesisUnderlying)
    assert "thesis_id" in _field_names(types.ThesisUnderlying)


def test_brief_domain_types_importable() -> None:
    from asxos.domain.brief import types
    assert dataclasses.is_dataclass(types.BriefRun)
    assert "sections_enabled" in _field_names(types.BriefRun)
