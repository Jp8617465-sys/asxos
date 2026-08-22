"""Frozen ``ContextManifest`` schema -- SB3-01 (arbi second-brain lane).

The third of the three schemas SB3-01 freezes. ``MissionEnvelope`` and
``MissionReceipt`` already exist in :mod:`asxos.secondbrain.execution`; this
module adds the one the packet names but nothing had yet built -- the
*compiled retrieval view* recording exactly what context a mission run
selected, and what it deliberately did not load.

**A manifest is a declaration, not a boundary.** Nothing in v1 binds a run's
actual reads to ``refs``, and ``excluded`` is not a denylist -- it is compared
by exact string equality, so ``excluded=("docs/",)`` does not exclude
``docs/x.md``. Both fields exist so a run's context selection can be *audited*
after the fact, not so it can be *enforced* during. Whatever eventually
enforces context bounds is a different mechanism from this schema; describing
a manifest as saying what a run "is allowed to" read would overstate it.

Packet source (``docs/proposals/asxos-outcome-engine-and-arbi-second-brain-
execution-plan-2026-08-12.md``, section SB3, lines 555-593):

    "The ``ContextManifest`` is a compiled retrieval view. It should select the
    constitution/permission references, relevant target architecture section,
    exact source contracts, current snapshot fields, tests, compiled
    indexes/backlinks, and prior outcome records. Every selected current claim
    resolves to its underlying source, not only to a generated summary. It
    should not load the entire roadmap, all handoffs, or all memory into every
    run."

Two of those sentences are encoded mechanically rather than left as prose:

* **"resolves to its underlying source, not only to a generated summary"** ->
  a :class:`SourceRef` of kind ``compiled_index`` MUST carry ``derived_from``.
  A compiled or summarised view that cannot name the source beneath it is
  *unrepresentable*, the same way ``status="observed"`` with a null value is
  unrepresentable in :mod:`asxos.secondbrain.project_state`.
* **"should not load the entire roadmap, all handoffs, or all memory"** ->
  ``excluded`` records what was deliberately left out. Boundedness that is
  never written down cannot be audited; a manifest that selected three files
  because it *chose* to and one that selected three because it *could only
  find* three are different artifacts, and only ``excluded`` tells them apart.

THE FREEZE RULE (closed set, version bump)
    Identical to :mod:`asxos.secondbrain.project_state`: the field set is
    CLOSED at ``schema_version`` 1. Any field addition -- here or on
    :class:`SourceRef` -- is a schema revision requiring a new ``Literal``
    pin, a new freeze record, and migration notes. ``extra="forbid"`` is the
    mechanical half. See
    ``docs/product/mission-context-schema-freeze-2026-08-22.md``.

Deliberate non-goals (SB3-01 is shape only):
    * ``sb3_02_deferred_compile_manifest`` -- selecting the refs (walking the
      repo, reading the snapshot, resolving the architecture section) is
      SB3-02, whose acceptance is "mission executes without full-repo context
      dump". This module performs no I/O and compiles nothing.
    * ``sb3_02_deferred_verify_manifest`` -- checking a manifest against a live
      tree (do the digests still match? is the baseline still reachable?) is
      likewise SB3-02. The schema records ``digest`` and ``baseline_sha`` so
      that check has something to verify; it does not perform it.
    * ``sb3_deferred_retrieval_infrastructure`` -- the packet is explicit that
      "file indexes and brief summaries remain the default until a versioned
      query set proves a named recall, citation, freshness, context-size, or
      latency failure that justifies more search infrastructure." No embedding
      store, no ranking, no query language. A tuple of refs is the whole
      retrieval model at v1.
"""

from __future__ import annotations

from collections import Counter
from typing import Final, Literal

from pydantic import AwareDatetime, Field, model_validator

from asxos.secondbrain._schema import FrozenModel

CONTEXT_SCHEMA_VERSION: Final = 1
"""The frozen schema version. Any field addition bumps this (see module docstring).

Named distinctly from :data:`asxos.secondbrain.project_state.SCHEMA_VERSION`
because both are re-exported from the package namespace and the two schemas
version independently -- a ``ContextManifest`` revision must not imply a
``ProjectStateSnapshot`` revision.
"""

SourceKind = Literal[
    "authority",
    "architecture",
    "contract",
    "snapshot_field",
    "test",
    "compiled_index",
    "outcome_record",
]
"""The seven selection categories, verbatim from the packet's SB3 sentence.

``authority`` (constitution/permission references) · ``architecture`` (the
relevant target-architecture section) · ``contract`` (exact source contracts) ·
``snapshot_field`` (current snapshot fields) · ``test`` (tests) ·
``compiled_index`` (compiled indexes/backlinks) · ``outcome_record`` (prior
outcome records). An eighth category is a schema revision, not a new string.
"""


class SourceRef(FrozenModel):
    """One selected piece of context, resolved to where it actually lives.

    ``locator`` is deliberately untyped-as-string and polymorphic by ``kind``:
    a repo-relative path for a file (``docs/product/arbi-constitution.md``), a
    dotted leaf path for a snapshot field (``data.migrations`` -- the same
    vocabulary :func:`asxos.secondbrain.project_state.leaves` keys on), or a
    named observation for anything with no file. Constraining it further would
    need a per-kind sub-model, which is a version bump, not a v1 refinement.

    ``digest`` lets SB3-02 detect staleness without this module doing any I/O.
    The algorithm is pinned into the field rather than left to the writer,
    matching ``CompiledRoadmap.source_sha256``; a free-form digest invites
    ``hashlib.new()`` dispatch, which would make the manifest a downgrade
    oracle. Freeze record §5.1 has the full argument.

    ``derived_from`` is the packet's "resolves to its underlying source, not
    only to a generated summary" rule, made mechanical: REQUIRED when ``kind``
    is ``compiled_index``, so a backlink table or generated index can never
    enter a manifest as a free-floating claim.
    """

    kind: SourceKind
    locator: str = Field(min_length=1)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    lines: tuple[int, int] | None = None
    derived_from: str | None = None

    @model_validator(mode="after")
    def _locator_is_bounded(self) -> SourceRef:
        """Reject anything that escapes the repository -- the READ-side twin of
        the containment ``MissionReceipt.changed_files`` already applies.

        Uniform across ``kind`` rather than gated on it, because these are
        escape patterns and not path syntax: a dotted snapshot leaf
        (``data.migrations``) and a named observation trip none of them.

        Containment against the repo root is ALL this does. A relative path
        with no ``..`` is still only as bounded as the directory the consumer
        resolves it against, and a bounded path is not thereby a safe one --
        ``.env`` validates. SB3-02 owns resolution and any allow/deny policy.
        """
        locator = self.locator
        if not locator.strip():
            raise ValueError("locator must not be blank")
        if locator.startswith("/"):
            raise ValueError(f"locator must be repository-relative, got absolute {locator!r}")
        if ".." in locator.split("/"):
            raise ValueError(f"locator must not escape the repository, got {locator!r}")
        if "://" in locator:
            raise ValueError(f"locator must not be a URL, got {locator!r}")
        if "\\" in locator:
            raise ValueError(f"locator must use forward slashes, got {locator!r}")
        return self

    @model_validator(mode="after")
    def _compiled_views_name_their_source(self) -> SourceRef:
        if self.kind == "compiled_index" and not self.derived_from:
            raise ValueError(
                "kind='compiled_index' requires derived_from: a compiled or summarised "
                "view must resolve to the underlying source it was built from, never "
                "stand alone as a current claim"
            )
        return self

    @model_validator(mode="after")
    def _line_span_is_ordered(self) -> SourceRef:
        if self.lines is None:
            return self
        start, end = self.lines
        if start < 1:
            raise ValueError(f"lines start at 1, got {start}")
        if end < start:
            raise ValueError(f"line span must be ordered, got ({start}, {end})")
        return self


class ContextManifest(FrozenModel):
    """The compiled retrieval view for exactly one mission run.

    ``baseline_sha`` is what lets a stale manifest fail closed (packet SB3
    acceptance: "invalid or stale baselines fail closed"). It is pinned to the
    same 40-hex pattern as ``MissionEnvelope.baseline_sha`` so the two can be
    compared without normalisation; a manifest whose baseline differs from its
    envelope's is a mismatch SB3-02 detects, not something this schema can
    permit or forbid on its own.

    ``snapshot_id`` is optional because a manifest may legitimately select no
    snapshot fields (a docs-only mission). When any ref of kind
    ``snapshot_field`` IS present, the snapshot it came from must be named --
    otherwise the leaf path is an unanchored claim, which is the exact failure
    ``derived_from`` closes for compiled views.
    """

    schema_version: Literal[1]
    manifest_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    baseline_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    compiled_at: AwareDatetime
    refs: tuple[SourceRef, ...] = Field(min_length=1)
    snapshot_id: str | None = None
    excluded: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _refs_are_unique(self) -> ContextManifest:
        counts = Counter((ref.kind, ref.locator, ref.lines) for ref in self.refs)
        duplicates = sorted(
            f"{kind}:{locator}" for (kind, locator, _), n in counts.items() if n > 1
        )
        if duplicates:
            raise ValueError(f"duplicate refs in manifest: {duplicates}")
        return self

    @model_validator(mode="after")
    def _one_locator_has_one_digest(self) -> ContextManifest:
        """Two refs to the same file must agree on its content hash.

        Uniqueness is keyed on ``(kind, locator, lines)`` so two sections of
        one document stay two distinct selections -- but that key omits
        ``digest``, which would otherwise let a single manifest assert two
        different hashes for one file at one ``baseline_sha``. That is
        internally contradictory, and it hands SB3-02's verifier an undefined
        resolution rule: short-circuit on first match and staleness detection
        for that file is bypassed.
        """
        by_locator: dict[str, set[str]] = {}
        for ref in self.refs:
            by_locator.setdefault(ref.locator, set()).add(ref.digest)
        conflicting = sorted(loc for loc, digests in by_locator.items() if len(digests) > 1)
        if conflicting:
            raise ValueError(
                f"one locator cannot carry two digests at one baseline_sha: {conflicting}"
            )
        return self

    @model_validator(mode="after")
    def _excluded_entries_are_non_blank(self) -> ContextManifest:
        """Matches the blank-entry rejection every tuple field in ``execution.py`` applies.

        A blank entry is not merely untidy: ``locator`` is non-blank by
        construction, so ``""`` in ``excluded`` can never collide with a
        selection, and the disjointness check below would pass over it in
        silence.
        """
        if any(not entry.strip() for entry in self.excluded):
            raise ValueError("excluded contains a blank entry")
        return self

    @model_validator(mode="after")
    def _snapshot_fields_name_their_snapshot(self) -> ContextManifest:
        if any(ref.kind == "snapshot_field" for ref in self.refs) and not self.snapshot_id:
            raise ValueError(
                "a ref of kind='snapshot_field' requires snapshot_id: a leaf path with no "
                "snapshot behind it is an unanchored claim"
            )
        return self

    @model_validator(mode="after")
    def _excluded_is_disjoint_from_refs(self) -> ContextManifest:
        selected = {ref.locator for ref in self.refs}
        both = sorted(selected & set(self.excluded))
        if both:
            raise ValueError(
                f"locators cannot be both selected and excluded: {both}; "
                "excluded records what was deliberately NOT loaded"
            )
        return self
