"""Read-only CLI for compiling and selecting ASXOS roadmap work orders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from asxos.secondbrain.execution import CompiledRoadmap, select_next_item
from asxos.secondbrain.roadmap import RoadmapCompileError, compile_execution_plan_file

DEFAULT_PLAN = Path(
    "docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md"
)

arbi_app = typer.Typer(
    help="Compile and inspect the bounded roadmap execution graph.",
    no_args_is_help=True,
    add_completion=False,
)


def _compile_or_exit(path: Path) -> CompiledRoadmap:
    try:
        return compile_execution_plan_file(path)
    except RoadmapCompileError as exc:
        raise typer.BadParameter(str(exc), param_hint="plan") from exc


@arbi_app.command("compile")
def compile_roadmap(
    plan: Annotated[Path, typer.Argument(help="Execution-plan Markdown file")] = DEFAULT_PLAN,
) -> None:
    """Compile the structured backlog to deterministic JSON."""

    roadmap = _compile_or_exit(plan)
    typer.echo(roadmap.model_dump_json(indent=2))


@arbi_app.command("next")
def next_work_order(
    plan: Annotated[Path, typer.Argument(help="Execution-plan Markdown file")] = DEFAULT_PLAN,
    activate: Annotated[
        list[str] | None,
        typer.Option("--activate", help="Canonically activated work-order ID; repeatable"),
    ] = None,
    completed: Annotated[
        list[str] | None,
        typer.Option("--completed", help="Observed-complete dependency ID; repeatable"),
    ] = None,
    external_gate: Annotated[
        list[str] | None,
        typer.Option("--external-gate", help="Satisfied external-gate slug; repeatable"),
    ] = None,
) -> None:
    """Select one activated, dependency-complete work order without dispatching it."""

    roadmap = _compile_or_exit(plan)
    try:
        selection = select_next_item(
            roadmap,
            activated_item_ids=activate or (),
            completed_item_ids=completed or (),
            satisfied_external_gates=external_gate or (),
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(selection.model_dump(mode="json"), indent=2, sort_keys=True))
