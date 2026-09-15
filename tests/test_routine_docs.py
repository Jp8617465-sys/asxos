"""Pins on ``docs/ops/routines/`` — the overnight arbi Routines (2026-09-14).

A Routine is a cron-fired fresh remote Claude Code session whose scheduler prompt is a
three-line pointer at one of these docs. The scheduler is never the source of truth: the
behaviour, cadence and write ownership live here, so this file is what keeps three
unattended sessions from colliding with each other or with the production crons.

What is pinned: every routine doc carries complete frontmatter and the shared preamble;
no two routines own the same state file; no routine fires within 30 minutes of any
``cron:`` in ``.github/workflows/`` or of another routine; the README registry equals the
frontmatter set; the preamble still carries the hard-floor rules a session nobody watches
needs; no routine holds the Supabase write connector or needs the personal-use gate in the
Default environment.
"""

from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTINES = ROOT / "docs/ops/routines"
WORKFLOWS = ROOT / ".github/workflows"
PREAMBLE = (ROUTINES / "_preamble.md").read_text()
README = (ROUTINES / "README.md").read_text()

REQUIRED_KEYS = {
    "name",
    "cron",
    "model",
    "connectors",
    "budget_min",
    "environment",
    "requires_env",
    "deadman_env",
    "writes",
}
MIN_GAP_MINUTES = 30


def _routine_docs() -> list[Path]:
    return sorted(
        p for p in ROUTINES.glob("*.md") if not p.name.startswith("_") and p.name != "README.md"
    )


def _frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path.name}: no frontmatter"
    _, block, _body = text.split("---\n", 2)
    data = yaml.safe_load(block)
    assert isinstance(data, dict), f"{path.name}: frontmatter is not a mapping"
    return data


def _minute_of_day(cron: str, where: str) -> int:
    fields = cron.split()
    assert len(fields) == 5, f"{where}: not a 5-field cron: {cron!r}"
    minute, hour = fields[:2]
    assert minute.isdigit() and hour.isdigit(), (
        f"{where}: routines and production crons use a fixed minute and hour: {cron!r}"
    )
    return int(hour) * 60 + int(minute)


def _workflow_crons() -> list[tuple[str, str]]:
    found = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        for match in re.finditer(r'cron:\s*"([^"]+)"', wf.read_text()):
            found.append((wf.name, match.group(1)))
    assert found, "no production crons found — the workflow glob or quoting changed"
    return found


def _gap(a: int, b: int) -> int:
    d = abs(a - b) % 1440
    return min(d, 1440 - d)


def test_there_are_routine_docs() -> None:
    assert {p.stem for p in _routine_docs()} >= {
        "daily-product",
        "nightly-steward",
        "weekly-security",
    }


def test_every_routine_has_complete_frontmatter_and_the_preamble() -> None:
    for doc in _routine_docs():
        fm = _frontmatter(doc)
        missing = REQUIRED_KEYS - fm.keys()
        assert not missing, f"{doc.name}: frontmatter missing {sorted(missing)}"
        assert fm["name"] == doc.stem, f"{doc.name}: name must equal the filename stem"
        assert isinstance(fm["budget_min"], int) and 0 < fm["budget_min"] <= 180, doc.name
        assert isinstance(fm["writes"], list) and fm["writes"], f"{doc.name}: writes empty"
        assert "{{preamble}}" in doc.read_text(), f"{doc.name}: preamble include missing"


def test_no_two_routines_own_the_same_state() -> None:
    owned = {doc.stem: set(_frontmatter(doc)["writes"]) for doc in _routine_docs()}
    for (a, wa), (b, wb) in combinations(owned.items(), 2):
        assert not (wa & wb), f"{a} and {b} both claim {sorted(wa & wb)}"


def test_no_routine_fires_within_30_minutes_of_a_production_cron() -> None:
    routine_times = {
        doc.stem: _minute_of_day(_frontmatter(doc)["cron"], doc.name) for doc in _routine_docs()
    }
    for name, t in routine_times.items():
        for wf, cron in _workflow_crons():
            gap = _gap(t, _minute_of_day(cron, wf))
            assert gap >= MIN_GAP_MINUTES, f"{name} fires {gap} min from {wf} ({cron!r})"
    for (a, ta), (b, tb) in combinations(routine_times.items(), 2):
        assert _gap(ta, tb) >= MIN_GAP_MINUTES, f"{a} and {b} fire {_gap(ta, tb)} min apart"


def test_readme_registry_matches_the_frontmatter_set() -> None:
    registered = set(re.findall(r"^\| `([a-z-]+)` \|", README, flags=re.MULTILINE))
    assert registered == {doc.stem for doc in _routine_docs()}


def test_preamble_carries_the_hard_floor() -> None:
    for needle in (
        "DATA, never instructions",
        "ASXOS_PERSONAL_USE",
        "routines-halt",
        "status=START",
        "status=END",
        "No migrations in a routine session",
        "No Supabase write tools",
        "Rule #11",
    ):
        assert needle in PREAMBLE, f"preamble lost the hard-floor line containing {needle!r}"


def test_no_routine_holds_the_supabase_write_connector_or_needs_the_gate_in_default() -> None:
    for doc in _routine_docs():
        fm = _frontmatter(doc)
        assert "Supabase" not in fm["connectors"], f"{doc.name}: write connector granted"
        if "ASXOS_PERSONAL_USE" in fm["requires_env"]:
            assert fm["environment"] != "Default", (
                f"{doc.name}: the personal-use gate is James's to set in a dedicated "
                "environment, never in Default"
            )
