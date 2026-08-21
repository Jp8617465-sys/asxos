"""Compiler tests against both synthetic corruption and the real execution plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from asxos.cli import main as cli_main
from asxos.secondbrain.roadmap import RoadmapCompileError, compile_execution_plan

PLAN = Path(
    "docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md"
)
RUNNER = CliRunner()


def synthetic_plan(*rows: str) -> str:
    return "\n".join(
        [
            "# Synthetic",
            "",
            "## 7. Candidate execution backlog",
            "",
            "| ID | Work item | Route | Depends on | Completion proof |",
            "|---|---|---|---|---|",
            *rows,
            "",
            "## 8. Next section",
        ]
    )


def test_real_plan_compiles_all_35_work_orders() -> None:
    source_text = PLAN.read_text()
    roadmap = compile_execution_plan(source_text, source=str(PLAN))
    assert len(roadmap.items) == 35
    assert roadmap.items[0].item_id == "GOV-01"
    assert roadmap.items[-1].item_id == "P8-01"
    assert roadmap.source_sha256 == hashlib.sha256(source_text.encode()).hexdigest()


def test_real_plan_expands_dependency_ranges() -> None:
    roadmap = compile_execution_plan(PLAN.read_text(), source=str(PLAN))
    assert roadmap.item("P1-05").dependencies == ("P1-02", "P1-03", "P1-04")
    assert roadmap.item("P3-03").dependencies == ("P3-01", "P3-02")
    assert roadmap.item("P3-03").external_gates == ("approvals",)


def test_real_plan_preserves_source_lines_and_completion_proof() -> None:
    roadmap = compile_execution_plan(PLAN.read_text(), source=str(PLAN))
    item = roadmap.item("SB6-01")
    assert item.source_line == 750
    assert item.completion_proof == "Retry, stop, blocker, and receipt tests"


def test_missing_exact_heading_fails_closed() -> None:
    source = synthetic_plan("| SB1-01 | Build | arbi | none | tests |")
    source = source.replace("## 7. Candidate execution backlog", "## Candidate backlog")
    with pytest.raises(RoadmapCompileError, match="missing exact section heading"):
        compile_execution_plan(source, source="synthetic.md")


def test_header_drift_fails_closed() -> None:
    source = synthetic_plan("| SB1-01 | Build | arbi | none | tests |")
    source = source.replace("Completion proof", "Done when")
    with pytest.raises(RoadmapCompileError, match="missing exact candidate-backlog table header"):
        compile_execution_plan(source, source="synthetic.md")


def test_duplicate_exact_heading_fails_as_ambiguous() -> None:
    source = synthetic_plan("| SB1-01 | Build | arbi | none | tests |")
    source = f"{source}\n\n{source}"
    with pytest.raises(RoadmapCompileError, match="ambiguous duplicate section"):
        compile_execution_plan(source, source="synthetic.md")


def test_malformed_row_fails_closed() -> None:
    source = synthetic_plan("| SB1-01 | Build | arbi | none |")
    with pytest.raises(RoadmapCompileError, match="expected five cells"):
        compile_execution_plan(source, source="synthetic.md")


def test_descending_dependency_range_fails_closed() -> None:
    source = synthetic_plan(
        "| P1-04 | Build four | arbi | none | tests |",
        "| P1-05 | Build five | arbi | P1-04..02 | tests |",
    )
    with pytest.raises(RoadmapCompileError, match="descending dependency range"):
        compile_execution_plan(source, source="synthetic.md")


def test_undeclared_dependency_fails_graph_validation() -> None:
    source = synthetic_plan("| SB1-02 | Build | arbi | SB1-01 | tests |")
    with pytest.raises(RoadmapCompileError, match="undeclared work orders: SB1-01"):
        compile_execution_plan(source, source="synthetic.md")


def test_compilation_is_deterministic() -> None:
    text = PLAN.read_text()
    first = compile_execution_plan(text, source=str(PLAN))
    second = compile_execution_plan(text, source=str(PLAN))
    assert first.model_dump_json() == second.model_dump_json()


def test_cli_compile_emits_machine_readable_json() -> None:
    result = RUNNER.invoke(cli_main.app, ["arbi", "compile", str(PLAN)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["authority"] == "candidate_backlog"
    assert len(payload["items"]) == 35


def test_cli_next_requires_explicit_activation() -> None:
    result = RUNNER.invoke(cli_main.app, ["arbi", "next", str(PLAN)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "blockers": [],
        "item_id": None,
        "status": "NO_ACTIVATION",
    }


def test_cli_next_enforces_observed_dependencies() -> None:
    blocked = RUNNER.invoke(
        cli_main.app,
        ["arbi", "next", str(PLAN), "--activate", "P2-04"],
    )
    ready = RUNNER.invoke(
        cli_main.app,
        [
            "arbi",
            "next",
            str(PLAN),
            "--activate",
            "P2-04",
            "--completed",
            "P2-02",
        ],
    )
    assert blocked.exit_code == 0, blocked.output
    assert json.loads(blocked.output)["status"] == "BLOCKED"
    assert ready.exit_code == 0, ready.output
    assert json.loads(ready.output)["status"] == "READY"
