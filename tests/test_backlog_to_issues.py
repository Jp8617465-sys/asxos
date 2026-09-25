"""scripts/backlog_to_issues.py — the bridge from the archived YAML queue to Issues.

The body it renders must pass Layer 1 unchanged, or the bridge would file issues the
loop immediately marks needs-info. Module-loading follows tests/test_workflow_effects.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from asxos.backlog import Item
from asxos.domain.governance import issue_eligibility as el

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "backlog_to_issues", _ROOT / "scripts" / "backlog_to_issues.py"
)
assert _SPEC is not None and _SPEC.loader is not None
b2i = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(b2i)

OWNER = "Jp8617465-sys"


def _item(**overrides: Any) -> Item:
    base: dict[str, Any] = {
        "id": "E-11",
        "title": "Retire the last unattended-fence comment",
        "phase": "E",
        "owner": "arbi",
        "status": "open",
        "depends_on": (),
        "route": "build",
        "paths": ("asxos/backlog.py", "tests/test_backlog_next.py"),
        "source": "roadmap-state.md 2026-09-14",
    }
    base.update(overrides)
    return Item(**base)


def test_rendered_body_passes_layer_1_with_backlog_provenance() -> None:
    body = b2i.render_body(_item())
    record = el.IssueRecord(
        number=1, author_login=OWNER, labels=frozenset({"type:product"}), title="t", body=body
    )
    seen: list[el.ProvenanceRef] = []

    def resolve(ref: el.ProvenanceRef) -> bool:
        seen.append(ref)
        return ref == el.ProvenanceRef("backlog", "E-11")

    verdict = el.evaluate(record, owner_login=OWNER, open_issues=(), resolve_provenance=resolve)
    assert verdict.verdict == "eligible", verdict
    assert el.is_arbi_authored(body) and seen == [el.ProvenanceRef("backlog", "E-11")]
    assert el.files_to_touch(el.parse_sections(body)) == (
        "asxos/backlog.py",
        "tests/test_backlog_next.py",
    )


def test_a_denied_row_is_denied_by_layer_1_not_laundered_by_the_bridge() -> None:
    body = b2i.render_body(_item(paths=("migrations/0063_x.sql",)))
    record = el.IssueRecord(
        number=1, author_login=OWNER, labels=frozenset({"type:product"}), title="t", body=body
    )
    verdict = el.evaluate(
        record, owner_login=OWNER, open_issues=(), resolve_provenance=lambda ref: True
    )
    assert verdict.rule == "files-denied:migrations/0063_x.sql"


def test_area_follows_the_first_recognised_path_prefix() -> None:
    assert b2i.area_for(("asxos/cli/mandate.py",)) == "cli"
    assert b2i.area_for(("jobs/x.py", "asxos/cli/y.py")) == "cron"
    assert b2i.area_for(("asxos/domain/screening/evaluator.py",)) == "screens"
    assert b2i.area_for(("docs/product/x.md",)) == "pipeline"


class _Client:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self.hits = hits
        self.queries: list[str] = []
        self.ref = type("Ref", (), {"slug": "Jp8617465-sys/asxos"})()

    def search_issues(self, query: str) -> list[dict[str, Any]]:
        self.queries.append(query)
        return self.hits


def test_already_filed_matches_the_provenance_line_not_just_the_search_hit() -> None:
    client = _Client(
        [
            {"number": 40, "body": "### Provenance\n\nbacklog:E-110\n"},
            {"number": 41, "body": "### Provenance\n\nbacklog:E-11\n"},
        ]
    )
    assert b2i.already_filed(client, "E-11") == 41  # type: ignore[arg-type]
    assert '"backlog:E-11"' in client.queries[0] and "repo:Jp8617465-sys/asxos" in client.queries[0]
    assert b2i.already_filed(_Client([]), "E-11") is None  # type: ignore[arg-type]


def test_main_validates_limit() -> None:
    assert b2i.main(["--limit", "11"]) == 2
