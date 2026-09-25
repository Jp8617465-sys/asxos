"""The three issue forms and Layer 1 must agree on what "required" means.

`REQUIRED_SECTIONS` in `issue_eligibility.py` is the forms' `required: true` labels,
verbatim and in order. If a form gains or loses a required field without this table
moving, Layer 1 would hold every issue at needs-info (or wave one through) — this pins
the two together. The `Depends on` / `Provenance` inputs are what Layer 1 reads for
dependencies and the arbi-authored citation, so their labels are pinned too.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from asxos.domain.governance.issue_eligibility import (
    DEPENDS_SECTION,
    PROVENANCE_SECTION,
    REQUIRED_SECTIONS,
    TYPE_LABELS,
)

_FORMS = Path(__file__).resolve().parents[1] / ".github" / "ISSUE_TEMPLATE"
_BY_TYPE = {
    "type:product": "product.yml",
    "type:data-infra": "data-infra.yml",
    "type:research": "research.yml",
}


def _form(name: str) -> dict:
    return yaml.safe_load((_FORMS / name).read_text(encoding="utf-8"))


def _fields(name: str) -> list[dict]:
    return [f for f in _form(name)["body"] if f.get("type") != "markdown"]


def test_every_type_label_has_a_form() -> None:
    assert set(_BY_TYPE) == TYPE_LABELS == set(REQUIRED_SECTIONS)
    assert {p.name for p in _FORMS.glob("*.yml")} == set(_BY_TYPE.values()) | {"config.yml"}


def test_required_form_labels_match_required_sections() -> None:
    for type_label, name in _BY_TYPE.items():
        required = tuple(
            f["attributes"]["label"]
            for f in _fields(name)
            if (f.get("validations") or {}).get("required")
        )
        assert required == REQUIRED_SECTIONS[type_label], name
        assert type_label in _form(name)["labels"], name


def test_every_form_carries_the_optional_depends_on_and_provenance_inputs() -> None:
    for name in _BY_TYPE.values():
        by_id = {f["id"]: f for f in _fields(name)}
        assert by_id["depends_on"]["attributes"]["label"] == DEPENDS_SECTION, name
        assert by_id["provenance"]["attributes"]["label"] == PROVENANCE_SECTION, name
        for field_id in ("depends_on", "provenance"):
            assert not (by_id[field_id].get("validations") or {}).get("required"), name
            assert by_id[field_id]["type"] == "input", name


def test_data_infra_no_longer_claims_james_applies_migrations() -> None:
    text = (_FORMS / "data-infra.yml").read_text(encoding="utf-8")
    assert "never by an agent" not in text and "never the agent" not in text
    assert "AGENTS.md §8" in text and "never by a headless lane" in text
