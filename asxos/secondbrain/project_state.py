"""Frozen ``ProjectStateSnapshot`` schema -- SB1-01 (arbi second-brain lane).

Typed models for the project-state snapshot that gives arbi fresh, cited
input instead of asking it to reconstruct state from prose. The field set
implements the SB1 minimum observation shape from
``docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md``
(shape: lines 495-522; rules: lines 524-526; acceptance: lines 528-530)
verbatim and only that.

THE FREEZE RULE (closed set, version bump)
    The frozen field set is CLOSED at ``schema_version`` 1. Any field
    addition -- at the top level, in any section, on the probe record, or
    on the leaf wrapper -- is a schema revision and MUST bump ``schema_version`` (a new Literal
    pin, a new freeze record, and migration notes for consumers). At
    version 1, ``extra="forbid"`` on every model mechanically rejects
    undeclared fields, so data cannot be smuggled into a v1 snapshot.
    SB2-01 (event/projection semantics) and SB3-01 (mission/receipt/context
    schemas) both build on this freeze; see
    ``docs/product/project-state-snapshot-freeze-2026-08-17.md``.

Packet rules encoded here (packet lines 524-526):
    * **No write probes.** This module is pure data -- it performs no I/O
      of any kind. Probe execution is SB1-02's job and must stay read-only.
    * **No secret values.** ``ProbeRecord.error_class`` is a short error
      *category* (e.g. ``"network_timeout"``), never a raw error message,
      stderr capture, or URL -- raw failure text is where credentials leak.
      Observation ``value`` payloads must never carry secrets; adapters are
      responsible for redaction before construction.
    * **``unavailable`` is first-class.** Every observed leaf is a
      :class:`FieldObservation` whose ``status`` says explicitly whether
      the value was observed. ``status="observed"`` REQUIRES a non-null
      value; ``status="unavailable"``/``"error"`` FORBID one. "Observed but
      null" and "unavailable but valued" are both unrepresentable, so a
      missing probe can never silently become zero/green, and an accidental
      null can never masquerade as an observation.
    * **Branch-only is never main truth.** The schema records branch
      identity (``repository.branch``, ``repository.base_sha``,
      ``repository.dirty_state``) so consumers can apply this rule; the
      schema itself records and never judges.
    * **Snapshots are artifacts, not authority.** A validated snapshot is
      evidence with a timestamp, not a source-of-truth document.

Named deferrals (do not add these as fields at v1):
    * ``sb2_deferred_contradiction_fields`` -- doc-truth / contradiction
      detection items (two sources disagreeing, branch-only described as
      merged, claims past their freshness window, ...) are SB2's job. The
      v1 schema deliberately VALIDATES a self-contradictory snapshot: SB1
      records faithfully; SB2 detects.
    * ``sb2_deferred_staleness_evaluation`` -- ``freshness`` values are
      carried verbatim and never evaluated here; staleness judgment is
      SB2's contradiction/staleness checker.
    * ``sb1_02_deferred_probe_linkage`` -- how a section leaf links to the
      raw :class:`ProbeRecord` entries backing it ("derived claims link to
      raw observations", packet line 525) is deferred to SB1-02, which owns
      the adapters that create both. Candidate convention: probe ``name``
      equals the dotted field path (e.g. ``"github.open_prs"``), which
      needs no new field; a structural link field would bump the version.
    * ``sb1_02_deferred_payload_typing`` -- per-leaf ``value`` payloads
      (PR entries, workflow-run entries, migration inventories, ...) are
      untyped ``JsonValue`` at v1 because the packet names no sub-shapes.
      Refining any payload into a typed sub-model is a version bump.

Placement: ``asxos/secondbrain/`` is a new top-level package OUTSIDE
``asxos/domain/`` by vet ruling -- every ``asxos/domain/*`` package is
product domain (signals, tax, portfolio, ...); this is arbi machinery.
Precedent: ``asxos/prototype/`` is already a non-domain top-level package.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from asxos.secondbrain._schema import FrozenModel

SCHEMA_VERSION: Final = 1
"""The frozen schema version. Any field addition bumps this (see module docstring)."""

ObservationStatus = Literal["observed", "unavailable", "error"]
"""The single status vocabulary, verbatim from the packet's probe record (line 516).

Reused for section leaves so the whole snapshot speaks one language:
``observed`` (a real value was read), ``unavailable`` (the surface could not
be read -- explicitly first-class, packet line 524), ``error`` (the read was
attempted and failed; detail lives in the backing probe's ``error_class``).
"""


class FieldObservation(FrozenModel):
    """One observed leaf: an explicit status plus (iff observed) a value.

    Makes ``unavailable`` first-class and distinct from absent/null-by-
    accident (packet line 524):

    * ``status="observed"`` -> ``value`` must be present and non-null.
      Falsy-but-real values (``0``, ``False``, ``""``, ``[]``) are valid
      observations; only ``None`` is rejected.
    * ``status="unavailable"`` / ``"error"`` -> ``value`` must be ``None``
      (omitted). Error detail belongs on the backing :class:`ProbeRecord`
      (``sb1_02_deferred_probe_linkage``), never smuggled into a leaf.
    """

    status: ObservationStatus
    value: JsonValue = None

    @model_validator(mode="after")
    def _value_matches_status(self) -> FieldObservation:
        if self.status == "observed" and self.value is None:
            raise ValueError(
                "status='observed' requires a non-null value; "
                "use status='unavailable' for a surface that could not be read"
            )
        if self.status != "observed" and self.value is not None:
            raise ValueError(
                f"status={self.status!r} must not carry a value; "
                "a value is only valid on status='observed'"
            )
        return self


class ProbeRecord(FrozenModel):
    """One raw probe observation -- the packet's ``probes[]`` entry, verbatim
    (packet lines 514-521). Also the generic extension point: anything the
    named sections do not cover is recorded here as a probe, never as a new
    field (freeze rule).

    Status constraints mirror :class:`FieldObservation` and extend them:

    * ``observed`` -> ``value`` required non-null; ``freshness`` optional;
      ``error_class`` forbidden.
    * ``unavailable`` -> ``value``/``freshness``/``error_class`` all ``None``.
    * ``error`` -> ``error_class`` required (a short category such as
      ``"network_timeout"``, NEVER a raw message -- no-secret-values rule);
      ``value``/``freshness`` ``None``.
    """

    name: str = Field(min_length=1)
    status: ObservationStatus
    source: str = Field(min_length=1)
    observed_at: AwareDatetime
    value: JsonValue = None
    freshness: JsonValue = None
    error_class: str | None = None

    @model_validator(mode="after")
    def _fields_match_status(self) -> ProbeRecord:
        if self.status == "observed":
            if self.value is None:
                raise ValueError(
                    "status='observed' requires a non-null value; "
                    "use status='unavailable' for a surface that could not be read"
                )
            if self.error_class is not None:
                raise ValueError("error_class is only valid on status='error'")
        elif self.status == "unavailable":
            if self.value is not None or self.freshness is not None:
                raise ValueError("status='unavailable' must not carry value or freshness")
            if self.error_class is not None:
                raise ValueError("error_class is only valid on status='error'")
        else:  # status == "error"
            if self.value is not None or self.freshness is not None:
                raise ValueError("status='error' must not carry value or freshness")
            if not self.error_class:
                raise ValueError(
                    "status='error' requires a non-empty error_class "
                    "(a short category, never a raw error message)"
                )
        return self


class RepositoryState(FrozenModel):
    """``repository`` section, verbatim (packet lines 499-502)."""

    base_sha: FieldObservation
    branch: FieldObservation
    dirty_state: FieldObservation


class GithubState(FrozenModel):
    """``github`` section, verbatim (packet lines 503-506)."""

    open_prs: FieldObservation
    recent_merges: FieldObservation
    workflow_runs: FieldObservation


class ProductionState(FrozenModel):
    """``production`` section, verbatim (packet lines 507-509)."""

    release_identity: FieldObservation
    scheduler_owners: FieldObservation


class DataState(FrozenModel):
    """``data`` section, verbatim (packet lines 510-513)."""

    migrations: FieldObservation
    freshness: FieldObservation
    coverage: FieldObservation


class ProjectStateSnapshot(FrozenModel):
    """The frozen top-level snapshot, verbatim (packet lines 496-514).

    Every field is required -- there are no defaults anywhere in the tree
    except the frozen ``None`` on optional observation payloads, so a
    section that was never probed cannot validate at all, and a probed-but-
    unreadable surface must say ``unavailable`` out loud ("missing probes
    do not become zero/green", packet lines 528-529).

    ``schema_version`` is pinned ``Literal[1]``: a snapshot claiming any
    other version does not validate against THIS schema. Version 2, if it
    ever exists, is a new pin plus a new freeze record (freeze rule, module
    docstring).
    """

    snapshot_id: str = Field(min_length=1)
    schema_version: Literal[1]
    observed_at: AwareDatetime
    repository: RepositoryState
    github: GithubState
    production: ProductionState
    data: DataState
    probes: list[ProbeRecord]


_SECTIONS: Final = ("repository", "github", "production", "data")
"""The four section names, in packet order. The leaf set is these sections' fields."""


def leaves(snapshot: ProjectStateSnapshot) -> dict[str, FieldObservation]:
    """Every schema leaf keyed by its dotted path, read off the models themselves.

    The canonical projection. It had been reimplemented three times — in
    ``contradictions.py`` and in two test modules — which is one spelling per
    consumer of a thing that has exactly one correct definition.

    Reflection, not a literal list, because this must follow the schema: if a
    section gains a field, every consumer sees it immediately rather than
    silently reading a stale hardcoded set. The *pinning* job belongs to the
    tests (``probes.FIELD_PATHS`` and the schema module's own field-set
    assertions), which is the right split — reflect to read, enumerate to pin.

    NOT a widening of the frozen schema: this adds no field and changes no
    validation. The freeze rule (module docstring) governs the field set, and a
    pure read-only projection over it leaves that set untouched.
    """
    return {
        f"{section}.{field}": getattr(getattr(snapshot, section), field)
        for section in _SECTIONS
        for field in type(getattr(snapshot, section)).model_fields
    }
