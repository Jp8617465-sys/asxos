"""Fail-closed compiler for the structured ASXOS execution-backlog table."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from asxos.secondbrain.execution import CompiledRoadmap, RoadmapItem

_SECTION_HEADING = "## 7. Candidate execution backlog"
_TABLE_HEADER = ("ID", "Work item", "Route", "Depends on", "Completion proof")
_WORK_ORDER_ID = re.compile(r"^[A-Z][A-Z0-9]*-\d{2}$")
_WORK_ORDER_SEARCH = re.compile(r"\b[A-Z][A-Z0-9]*-\d{2}\b")
_RANGE = re.compile(r"\b([A-Z][A-Z0-9]*-)(\d{2})\.\.(\d{2})\b")


class RoadmapCompileError(ValueError):
    """The source cannot be compiled without guessing."""


def _cells(line: str) -> tuple[str, ...]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise RoadmapCompileError("roadmap table row must start and end with '|'")
    return tuple(cell.strip() for cell in stripped[1:-1].split("|"))


def _plain(value: str) -> str:
    return value.replace("`", "").replace("**", "").strip()


def _slug_gate(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _parse_dependencies(raw: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    value = _plain(raw)
    if value.lower() == "none":
        return (), ()

    dependencies: list[str] = []

    def expand_range(match: re.Match[str]) -> str:
        prefix, start_text, end_text = match.groups()
        start = int(start_text)
        end = int(end_text)
        if end < start:
            raise RoadmapCompileError(f"descending dependency range is invalid: {match.group(0)}")
        dependencies.extend(f"{prefix}{number:02d}" for number in range(start, end + 1))
        return " "

    residual = _RANGE.sub(expand_range, value)
    dependencies.extend(_WORK_ORDER_SEARCH.findall(residual))
    residual = _WORK_ORDER_SEARCH.sub(" ", residual)
    residual = re.sub(r"[,;/()+]", " ", residual)
    residual = re.sub(r"\s+", " ", residual).strip(" .-")

    external_gates: tuple[str, ...] = ()
    if residual:
        gate = _slug_gate(residual)
        if not gate:
            raise RoadmapCompileError(f"dependency text cannot be normalized: {raw!r}")
        external_gates = (gate,)

    return tuple(dict.fromkeys(dependencies)), external_gates


def compile_execution_plan(
    text: str,
    *,
    source: str,
    authority: Literal[
        "candidate_backlog", "canonical_queue", "direct_instruction"
    ] = "candidate_backlog",
) -> CompiledRoadmap:
    """Compile the exact five-column backlog table and reject ambiguity."""

    lines = text.splitlines()
    section_indexes = [index for index, line in enumerate(lines) if line == _SECTION_HEADING]
    if not section_indexes:
        raise RoadmapCompileError(f"missing exact section heading: {_SECTION_HEADING}")
    if len(section_indexes) != 1:
        raise RoadmapCompileError(f"ambiguous duplicate section heading: {_SECTION_HEADING}")
    section_index = section_indexes[0]

    header_index: int | None = None
    for index in range(section_index + 1, len(lines)):
        line = lines[index]
        if line.startswith("## "):
            break
        if line.strip().startswith("|") and _cells(line) == _TABLE_HEADER:
            header_index = index
            break
    if header_index is None:
        raise RoadmapCompileError("missing exact candidate-backlog table header")
    if header_index + 1 >= len(lines):
        raise RoadmapCompileError("candidate-backlog table has no separator row")

    separator = _cells(lines[header_index + 1])
    if len(separator) != len(_TABLE_HEADER) or any(
        not re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        raise RoadmapCompileError("candidate-backlog table separator is malformed")

    items: list[RoadmapItem] = []
    for line_index in range(header_index + 2, len(lines)):
        line = lines[line_index]
        if not line.strip().startswith("|"):
            break
        cells = _cells(line)
        if len(cells) != len(_TABLE_HEADER):
            raise RoadmapCompileError(
                f"line {line_index + 1}: expected five cells, found {len(cells)}"
            )
        item_id, objective, route, depends_on, completion_proof = map(_plain, cells)
        if not _WORK_ORDER_ID.fullmatch(item_id):
            raise RoadmapCompileError(f"line {line_index + 1}: invalid work-order ID {item_id!r}")
        dependencies, external_gates = _parse_dependencies(depends_on)
        items.append(
            RoadmapItem(
                item_id=item_id,
                objective=objective,
                route=route,
                dependencies=dependencies,
                external_gates=external_gates,
                completion_proof=completion_proof,
                order=len(items),
                source=source,
                source_line=line_index + 1,
            )
        )

    if not items:
        raise RoadmapCompileError("candidate-backlog table contains no work orders")

    try:
        return CompiledRoadmap(
            source=source,
            source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            authority=authority,
            items=tuple(items),
        )
    except ValidationError as exc:
        raise RoadmapCompileError(f"compiled roadmap graph is invalid: {exc}") from exc


def compile_execution_plan_file(path: Path) -> CompiledRoadmap:
    """Read and compile one UTF-8 execution-plan file."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RoadmapCompileError(
            f"cannot read roadmap source {path}: {exc.__class__.__name__}"
        ) from exc
    return compile_execution_plan(text, source=str(path))
