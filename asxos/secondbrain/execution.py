"""Typed execution contracts for the attended ASXOS roadmap controller.

The models in this module are deliberately pure: they perform no I/O, dispatch,
GitHub mutation, production write, or capital action.  They make roadmap and
mission state machine-checkable so an executor cannot claim progress by prose.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from asxos.secondbrain._schema import FrozenModel


class MissionState(StrEnum):
    PROPOSED = "PROPOSED"
    CHALLENGED = "CHALLENGED"
    APPROVED = "APPROVED"
    RUNNING = "RUNNING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    BLOCKED = "BLOCKED"
    STOPPED = "STOPPED"
    MERGED_BY_JAMES = "MERGED_BY_JAMES"
    OBSERVED = "OBSERVED"
    LEARNED = "LEARNED"


_ALLOWED_TRANSITIONS: dict[MissionState, frozenset[MissionState]] = {
    MissionState.PROPOSED: frozenset({MissionState.CHALLENGED, MissionState.STOPPED}),
    MissionState.CHALLENGED: frozenset(
        {MissionState.APPROVED, MissionState.BLOCKED, MissionState.STOPPED}
    ),
    MissionState.APPROVED: frozenset({MissionState.RUNNING, MissionState.STOPPED}),
    MissionState.RUNNING: frozenset(
        {
            MissionState.READY_FOR_REVIEW,
            MissionState.BLOCKED,
            MissionState.STOPPED,
        }
    ),
    MissionState.READY_FOR_REVIEW: frozenset(
        {
            MissionState.RUNNING,
            MissionState.MERGED_BY_JAMES,
            MissionState.STOPPED,
        }
    ),
    MissionState.BLOCKED: frozenset({MissionState.APPROVED, MissionState.STOPPED}),
    MissionState.STOPPED: frozenset(),
    MissionState.MERGED_BY_JAMES: frozenset({MissionState.OBSERVED}),
    MissionState.OBSERVED: frozenset({MissionState.LEARNED}),
    MissionState.LEARNED: frozenset(),
}

_EVIDENCE_REQUIRED_STATES = frozenset(
    {
        MissionState.READY_FOR_REVIEW,
        MissionState.BLOCKED,
        MissionState.STOPPED,
        MissionState.MERGED_BY_JAMES,
        MissionState.OBSERVED,
        MissionState.LEARNED,
    }
)


class RoadmapItem(FrozenModel):
    """One compiled work order from an explicitly structured source row."""

    item_id: str = Field(pattern=r"^[A-Z][A-Z0-9]*-\d{2}$")
    objective: str = Field(min_length=1)
    route: str = Field(min_length=1)
    dependencies: tuple[str, ...] = ()
    external_gates: tuple[str, ...] = ()
    completion_proof: str = Field(min_length=1)
    order: int = Field(ge=0)
    source: str = Field(min_length=1)
    source_line: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_dependencies(self) -> RoadmapItem:
        if self.item_id in self.dependencies:
            raise ValueError(f"{self.item_id} cannot depend on itself")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError(f"{self.item_id} has duplicate dependencies")
        if len(set(self.external_gates)) != len(self.external_gates):
            raise ValueError(f"{self.item_id} has duplicate external gates")
        return self


class CompiledRoadmap(FrozenModel):
    """Validated dependency graph compiled from one source artifact."""

    schema_version: Literal[1] = 1
    source: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority: Literal["candidate_backlog", "canonical_queue", "direct_instruction"]
    items: tuple[RoadmapItem, ...]

    @model_validator(mode="after")
    def _validate_graph(self) -> CompiledRoadmap:
        by_id = {item.item_id: item for item in self.items}
        if len(by_id) != len(self.items):
            raise ValueError("roadmap contains duplicate work-order IDs")

        declared = set(by_id)
        for item in self.items:
            missing = set(item.dependencies) - declared
            if missing:
                names = ", ".join(sorted(missing))
                raise ValueError(f"{item.item_id} depends on undeclared work orders: {names}")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(item_id: str) -> None:
            if item_id in visiting:
                raise ValueError(f"roadmap dependency cycle includes {item_id}")
            if item_id in visited:
                return
            visiting.add(item_id)
            for dependency in by_id[item_id].dependencies:
                visit(dependency)
            visiting.remove(item_id)
            visited.add(item_id)

        for item in self.items:
            visit(item.item_id)
        return self

    def item(self, item_id: str) -> RoadmapItem:
        for item in self.items:
            if item.item_id == item_id:
                return item
        raise KeyError(item_id)


class MissionEvent(FrozenModel):
    """One append-only state transition with source-addressable evidence."""

    mission_id: str = Field(min_length=1)
    roadmap_item_id: str = Field(pattern=r"^[A-Z][A-Z0-9]*-\d{2}$")
    sequence: int = Field(ge=1)
    state: MissionState
    observed_at: AwareDatetime
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _require_evidence_for_claim_states(self) -> MissionEvent:
        if self.state in _EVIDENCE_REQUIRED_STATES and not self.evidence:
            raise ValueError(f"state {self.state} requires at least one evidence reference")
        if any(not value.strip() for value in self.evidence):
            raise ValueError("evidence references must be non-empty")
        return self


class MissionTimeline(FrozenModel):
    """A validated append-only mission history."""

    events: tuple[MissionEvent, ...]

    @model_validator(mode="after")
    def _validate_timeline(self) -> MissionTimeline:
        if not self.events:
            raise ValueError("mission timeline must contain at least one event")

        mission_ids = {event.mission_id for event in self.events}
        roadmap_ids = {event.roadmap_item_id for event in self.events}
        if len(mission_ids) != 1 or len(roadmap_ids) != 1:
            raise ValueError("all timeline events must describe one mission and roadmap item")

        if self.events[0].state != MissionState.PROPOSED:
            raise ValueError("mission timeline must start at PROPOSED")

        for expected_sequence, event in enumerate(self.events, start=1):
            if event.sequence != expected_sequence:
                raise ValueError("mission event sequences must be contiguous and start at 1")

        for previous, current in zip(self.events, self.events[1:], strict=False):
            if current.state not in _ALLOWED_TRANSITIONS[previous.state]:
                raise ValueError(f"invalid mission transition: {previous.state} -> {current.state}")
        return self

    @property
    def mission_id(self) -> str:
        return self.events[0].mission_id

    @property
    def roadmap_item_id(self) -> str:
        return self.events[0].roadmap_item_id

    @property
    def current_state(self) -> MissionState:
        return self.events[-1].state


class MissionEnvelope(FrozenModel):
    """Executable mission input; candidate backlog text alone cannot create one."""

    schema_version: Literal[1] = 1
    mission_id: str = Field(min_length=1)
    programme_id: str = Field(min_length=1)
    roadmap_item_id: str = Field(pattern=r"^[A-Z][A-Z0-9]*-\d{2}$")
    roadmap_stage: str = Field(min_length=1)
    source_authority: Literal["canonical_queue", "direct_instruction"]
    objective: str = Field(min_length=1)
    baseline_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    scope: tuple[str, ...] = Field(min_length=1)
    allowed_actions: tuple[str, ...] = Field(min_length=1)
    forbidden_boundaries: tuple[str, ...] = Field(min_length=1)
    dependencies: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()
    expected_artifacts: tuple[str, ...] = Field(min_length=1)
    acceptance_checks: tuple[str, ...] = Field(min_length=1)
    independent_reviews: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = Field(min_length=1)
    rollback: str = Field(min_length=1)
    outcome_observation: str = Field(min_length=1)
    max_repair_attempts: int = Field(default=2, ge=0, le=2)

    @model_validator(mode="after")
    def _validate_envelope(self) -> MissionEnvelope:
        tuple_fields = {
            "scope": self.scope,
            "allowed_actions": self.allowed_actions,
            "forbidden_boundaries": self.forbidden_boundaries,
            "dependencies": self.dependencies,
            "required_inputs": self.required_inputs,
            "expected_artifacts": self.expected_artifacts,
            "acceptance_checks": self.acceptance_checks,
            "independent_reviews": self.independent_reviews,
            "stop_conditions": self.stop_conditions,
        }
        for name, values in tuple_fields.items():
            if len(set(values)) != len(values):
                raise ValueError(f"{name} contains duplicate entries")
            if any(not value.strip() for value in values):
                raise ValueError(f"{name} contains an empty entry")

        broad_scope = {".", "./", "/", "*", "**", "**/*"}
        if broad_scope.intersection(self.scope):
            raise ValueError("mission scope must name bounded repository paths")
        if self.roadmap_item_id in self.dependencies:
            raise ValueError("mission cannot depend on its own roadmap item")
        return self


class CheckResult(FrozenModel):
    name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    status: Literal["PASS", "FAIL", "SKIPPED"]
    evidence: str = Field(min_length=1)


class MissionReceipt(FrozenModel):
    """Machine-verifiable result emitted at a mission transaction boundary."""

    schema_version: Literal[1] = 1
    mission_id: str = Field(min_length=1)
    roadmap_item_id: str = Field(pattern=r"^[A-Z][A-Z0-9]*-\d{2}$")
    baseline_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    changed_files: tuple[str, ...]
    checks: tuple[CheckResult, ...] = Field(min_length=1)
    review_receipts: tuple[str, ...]
    pr_url: str | None = None
    blockers: tuple[str, ...] = ()
    readiness: Literal["READY_FOR_REVIEW", "BLOCKED", "STOPPED"]
    emitted_at: AwareDatetime

    @model_validator(mode="after")
    def _validate_receipt(self) -> MissionReceipt:
        if len(set(self.changed_files)) != len(self.changed_files):
            raise ValueError("changed_files contains duplicates")
        for path in self.changed_files:
            if not path or path.startswith("/") or ".." in path.split("/"):
                raise ValueError("changed_files must contain bounded repository-relative paths")
        check_names = [check.name for check in self.checks]
        if len(set(check_names)) != len(check_names):
            raise ValueError("checks contains duplicate names")
        if any(not value.strip() for value in (*self.review_receipts, *self.blockers)):
            raise ValueError("receipt references and blockers must be non-empty")

        if self.readiness == "READY_FOR_REVIEW":
            failed = [check.name for check in self.checks if check.status != "PASS"]
            if failed:
                raise ValueError(
                    "READY_FOR_REVIEW requires every check to pass; non-passing: "
                    + ", ".join(failed)
                )
            if not self.pr_url:
                raise ValueError("READY_FOR_REVIEW requires a draft PR URL")
            if self.blockers:
                raise ValueError("READY_FOR_REVIEW cannot carry blockers")
        elif not self.blockers:
            raise ValueError(f"{self.readiness} requires at least one blocker")

        if self.changed_files and self.baseline_sha == self.head_sha:
            raise ValueError("a receipt with changed files requires a distinct head SHA")
        return self


class RoadmapSelection(FrozenModel):
    """Deterministic controller result; no work is dispatched by this object."""

    status: Literal["READY", "ACTIVE", "BLOCKED", "COMPLETE", "NO_ACTIVATION"]
    item_id: str | None = None
    blockers: tuple[str, ...] = ()


def select_next_item(
    roadmap: CompiledRoadmap,
    *,
    activated_item_ids: Collection[str],
    timelines: Mapping[str, MissionTimeline] | None = None,
    completed_item_ids: Collection[str] = (),
    satisfied_external_gates: Collection[str] = (),
) -> RoadmapSelection:
    """Select one eligible item without inferring authority from a backlog.

    Candidate-backlog rows are inert until their ID is explicitly activated by
    the canonical queue or a direct James instruction.  Dependencies count as
    complete only after OBSERVED/LEARNED evidence, not merely green CI or merge.
    """

    declared = {item.item_id for item in roadmap.items}
    activated = set(activated_item_ids)
    unknown_activations = activated - declared
    if unknown_activations:
        names = ", ".join(sorted(unknown_activations))
        raise ValueError(f"activated work orders are not declared: {names}")
    if not activated:
        return RoadmapSelection(status="NO_ACTIVATION")

    by_timeline = dict(timelines or {})
    unknown_timelines = set(by_timeline) - declared
    if unknown_timelines:
        names = ", ".join(sorted(unknown_timelines))
        raise ValueError(f"mission timelines reference undeclared work orders: {names}")

    completed = set(completed_item_ids)
    completed.update(
        item_id
        for item_id, timeline in by_timeline.items()
        if timeline.current_state in {MissionState.OBSERVED, MissionState.LEARNED}
    )
    unknown_completed = completed - declared
    if unknown_completed:
        names = ", ".join(sorted(unknown_completed))
        raise ValueError(f"completed work orders are not declared: {names}")

    active_states = {
        MissionState.PROPOSED,
        MissionState.CHALLENGED,
        MissionState.APPROVED,
        MissionState.RUNNING,
        MissionState.READY_FOR_REVIEW,
        MissionState.BLOCKED,
        MissionState.MERGED_BY_JAMES,
    }
    active = [
        (roadmap.item(item_id).order, item_id, timeline)
        for item_id, timeline in by_timeline.items()
        if item_id in activated and timeline.current_state in active_states
    ]
    if active:
        _, item_id, timeline = min(active)
        if timeline.current_state == MissionState.BLOCKED:
            return RoadmapSelection(
                status="BLOCKED",
                item_id=item_id,
                blockers=("mission state is BLOCKED",),
            )
        return RoadmapSelection(status="ACTIVE", item_id=item_id)

    stopped = [
        (roadmap.item(item_id).order, item_id)
        for item_id, timeline in by_timeline.items()
        if item_id in activated and timeline.current_state == MissionState.STOPPED
    ]
    if stopped:
        _, item_id = min(stopped)
        return RoadmapSelection(
            status="BLOCKED",
            item_id=item_id,
            blockers=("mission state is STOPPED; explicit reactivation is required",),
        )

    gates = set(satisfied_external_gates)
    blocked_results: list[tuple[int, str, tuple[str, ...]]] = []
    for item in sorted(roadmap.items, key=lambda candidate: candidate.order):
        if item.item_id not in activated or item.item_id in completed:
            continue
        blockers = tuple(
            [
                f"dependency not observed: {dependency}"
                for dependency in item.dependencies
                if dependency not in completed
            ]
            + [
                f"external gate not satisfied: {gate}"
                for gate in item.external_gates
                if gate not in gates
            ]
        )
        if not blockers:
            return RoadmapSelection(status="READY", item_id=item.item_id)
        blocked_results.append((item.order, item.item_id, blockers))

    remaining = activated - completed
    if not remaining:
        return RoadmapSelection(status="COMPLETE")
    _, item_id, blockers = min(blocked_results)
    return RoadmapSelection(status="BLOCKED", item_id=item_id, blockers=blockers)
