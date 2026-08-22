"""SB3-01 -- the freeze tests for the mission/receipt/context schemas.

SB3-01's job is to FREEZE three schemas. Two of them (``MissionEnvelope``,
``MissionReceipt``, plus ``CheckResult`` inside the receipt) shipped in PR #124
with ``schema_version: Literal[1]`` and ``extra="forbid"`` but no field-set
pin. The third (``ContextManifest``) is new in this work order.

What the pins actually add, measured rather than assumed. Mutating
``execution.py`` and running the pre-existing ``test_secondbrain_execution.py``
against each mutation:

* **Removing or renaming a field**: already caught (2 failed) -- its fixtures
  build full envelopes under ``extra="forbid"``, so a dropped field breaks
  them. But it breaks them as ``unexpected keyword argument`` inside an
  unrelated behaviour test, which reads as "the fixture is stale", not "a
  frozen schema changed". The pins add legibility here, not coverage.
* **ADDING a field** (``auto_merge: bool = False``): **23 passed -- entirely
  blind.** A defaulted field costs no fixture a single edit, so the schema can
  grow silently. This is the freeze direction that matters most and nothing
  guarded it.
* **A coordinated rename** (``rollback`` -> ``rollback_plan``, field and every
  fixture edited together): **23 passed -- also blind.**
  ``test_every_packet_required_mission_field_is_present`` is what catches this,
  because it asserts the packet's names rather than whatever the code happens
  to call them.

So this module does three things:

1. Pin every field set with set-equality, matching the established pattern in
   ``tests/test_project_state_snapshot_schema.py``.
2. Assert the packet's 17 required mission fields are all present, by name, so
   a future edit cannot drop one without a red test citing the packet line.
3. Exercise the ``ContextManifest`` rules that the packet states as prose and
   the schema encodes mechanically.

Packet: ``docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-
plan-2026-08-12.md`` -- mission fields lines 563-582, SB3 context manifest
lines 584-593. Freeze record:
``docs/product/mission-context-schema-freeze-2026-08-22.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from asxos.secondbrain.context import (
    CONTEXT_SCHEMA_VERSION,
    ContextManifest,
    SourceRef,
)
from asxos.secondbrain.execution import CheckResult, MissionEnvelope, MissionReceipt

SHA = "a" * 40
OTHER_SHA = "b" * 40
DIGEST = "sha256:" + "c" * 64
OTHER_DIGEST = "sha256:" + "d" * 64
COMPILED_AT = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)


def _ref(**overrides: object) -> SourceRef:
    base: dict[str, object] = {
        "kind": "authority",
        "locator": "docs/product/arbi-constitution.md",
        "digest": DIGEST,
    }
    return SourceRef.model_validate(base | overrides)


def _manifest(**overrides: object) -> ContextManifest:
    base: dict[str, object] = {
        "schema_version": 1,
        "manifest_id": "ctx-sb3-01",
        "mission_id": "sb3-01-2026-08-22",
        "baseline_sha": SHA,
        "compiled_at": COMPILED_AT,
        "refs": (_ref(),),
    }
    return ContextManifest.model_validate(base | overrides)


# ---------------------------------------------------------------------------
# 1. Field-set pins -- the half of the freeze extra="forbid" cannot provide.
# ---------------------------------------------------------------------------


def test_mission_envelope_field_set_is_frozen() -> None:
    # Packet lines 563-582 (the 17 required fields) + 3 implementation fields.
    assert set(MissionEnvelope.model_fields) == {
        "schema_version",
        "mission_id",
        "programme_id",
        "roadmap_item_id",
        "roadmap_stage",
        "source_authority",
        "objective",
        "baseline_sha",
        "scope",
        "allowed_actions",
        "forbidden_boundaries",
        "dependencies",
        "required_inputs",
        "expected_artifacts",
        "acceptance_checks",
        "independent_reviews",
        "stop_conditions",
        "rollback",
        "outcome_observation",
        "max_repair_attempts",
    }


def test_every_packet_required_mission_field_is_present() -> None:
    """The packet's list, by name. A rename must fail here citing the packet."""
    required = {
        "mission_id",
        "programme_id",
        "roadmap_stage",
        "source_authority",
        "objective",
        "baseline_sha",
        "scope",
        "allowed_actions",
        "forbidden_boundaries",
        "dependencies",
        "required_inputs",
        "expected_artifacts",
        "acceptance_checks",
        "independent_reviews",
        "stop_conditions",
        "rollback",
        "outcome_observation",
    }
    missing = required - set(MissionEnvelope.model_fields)
    assert not missing, f"packet lines 563-582 require these, and they are gone: {sorted(missing)}"


def test_mission_receipt_field_set_is_frozen() -> None:
    assert set(MissionReceipt.model_fields) == {
        "schema_version",
        "mission_id",
        "roadmap_item_id",
        "baseline_sha",
        "head_sha",
        "changed_files",
        "checks",
        "review_receipts",
        "pr_url",
        "blockers",
        "readiness",
        "emitted_at",
    }


def test_check_result_field_set_is_frozen() -> None:
    assert set(CheckResult.model_fields) == {"name", "command", "status", "evidence"}


def test_context_manifest_field_set_is_frozen() -> None:
    # Packet lines 584-593.
    assert set(ContextManifest.model_fields) == {
        "schema_version",
        "manifest_id",
        "mission_id",
        "baseline_sha",
        "compiled_at",
        "refs",
        "snapshot_id",
        "excluded",
    }


def test_source_ref_field_set_is_frozen() -> None:
    assert set(SourceRef.model_fields) == {"kind", "locator", "digest", "lines", "derived_from"}


# ---------------------------------------------------------------------------
# 2. Closed set + version-bump rule.
# ---------------------------------------------------------------------------


def test_context_schema_version_constant_is_1() -> None:
    assert CONTEXT_SCHEMA_VERSION == 1


def test_context_schema_version_is_pinned_not_merely_defaulted() -> None:
    with pytest.raises(ValidationError):
        _manifest(schema_version=2)


def test_manifest_rejects_undeclared_fields() -> None:
    with pytest.raises(ValidationError):
        _manifest(priority="high")


def test_source_ref_rejects_undeclared_fields() -> None:
    with pytest.raises(ValidationError):
        _ref(weight=0.9)


def test_manifest_instances_are_immutable() -> None:
    manifest = _manifest()
    with pytest.raises(ValidationError):
        manifest.mission_id = "something-else"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. "Resolves to its underlying source, not only to a generated summary."
# ---------------------------------------------------------------------------


def test_compiled_index_without_derived_from_is_unrepresentable() -> None:
    with pytest.raises(ValidationError, match="derived_from"):
        _ref(kind="compiled_index", locator="docs/product/doc-truth-map-2026-08-13.md")


def test_compiled_index_with_derived_from_validates() -> None:
    ref = _ref(
        kind="compiled_index",
        locator="docs/product/doc-truth-map-2026-08-13.md",
        derived_from="docs/product/roadmap-state.md",
    )
    assert ref.derived_from == "docs/product/roadmap-state.md"


def test_non_compiled_kinds_may_omit_derived_from() -> None:
    """The rule is scoped to compiled views -- a real file needs nothing beneath it."""
    for kind in ("authority", "architecture", "contract", "test", "outcome_record"):
        assert _ref(kind=kind).derived_from is None


# ---------------------------------------------------------------------------
# 4. Boundedness is recorded, not assumed.
# ---------------------------------------------------------------------------


def test_excluded_defaults_to_empty_and_is_carried_verbatim() -> None:
    assert _manifest().excluded == ()
    manifest = _manifest(excluded=("docs/product/memory/", "docs/session-handoff-2026-08-20.md"))
    assert manifest.excluded == (
        "docs/product/memory/",
        "docs/session-handoff-2026-08-20.md",
    )


def test_a_locator_cannot_be_both_selected_and_excluded() -> None:
    with pytest.raises(ValidationError, match="both selected and excluded"):
        _manifest(excluded=("docs/product/arbi-constitution.md",))


# ---------------------------------------------------------------------------
# 5. Unanchored claims.
# ---------------------------------------------------------------------------


def test_snapshot_field_ref_requires_a_named_snapshot() -> None:
    with pytest.raises(ValidationError, match="snapshot_id"):
        _manifest(refs=(_ref(kind="snapshot_field", locator="data.migrations"),))


def test_snapshot_field_ref_validates_once_the_snapshot_is_named() -> None:
    manifest = _manifest(
        refs=(_ref(kind="snapshot_field", locator="data.migrations"),),
        snapshot_id="snap-2026-08-22",
    )
    assert manifest.snapshot_id == "snap-2026-08-22"


def test_snapshot_id_is_optional_when_no_snapshot_field_is_selected() -> None:
    """A docs-only mission selects no snapshot leaf and owes no snapshot id."""
    assert _manifest().snapshot_id is None


def test_snapshot_field_locators_use_the_same_vocabulary_as_leaves() -> None:
    """The dotted path is the project_state leaf key, not a second spelling."""
    from asxos.secondbrain.probes import FIELD_PATHS

    manifest = _manifest(
        refs=tuple(
            _ref(kind="snapshot_field", locator=path, digest=f"sha256:{i:064x}")
            for i, path in enumerate(FIELD_PATHS)
        ),
        snapshot_id="snap-2026-08-22",
    )
    assert {ref.locator for ref in manifest.refs} == set(FIELD_PATHS)


# ---------------------------------------------------------------------------
# 6. Structural rules.
# ---------------------------------------------------------------------------


def test_duplicate_refs_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate refs"):
        _manifest(refs=(_ref(), _ref()))


def test_same_locator_at_different_line_spans_is_not_a_duplicate() -> None:
    """Two sections of one document are two distinct selections."""
    manifest = _manifest(
        refs=(
            _ref(kind="architecture", locator="docs/target-architecture.md", lines=(15, 40)),
            _ref(kind="architecture", locator="docs/target-architecture.md", lines=(120, 145)),
        )
    )
    assert len(manifest.refs) == 2


def test_an_empty_manifest_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _manifest(refs=())


@pytest.mark.parametrize("span", [(0, 5), (10, 4)])
def test_malformed_line_spans_are_rejected(span: tuple[int, int]) -> None:
    with pytest.raises(ValidationError):
        _ref(lines=span)


def test_baseline_sha_must_be_a_full_sha() -> None:
    """Packet SB3 acceptance: invalid or stale baselines fail closed."""
    for bad in ("", "abc123", SHA.upper(), SHA[:39]):
        with pytest.raises(ValidationError):
            _manifest(baseline_sha=bad)


def _sha_pattern(model: type, field: str) -> str:
    """The literal regex pinned on a field, dug out of pydantic's metadata."""
    patterns = [
        c.pattern for c in model.model_fields[field].metadata if hasattr(c, "pattern")
    ]
    assert len(patterns) == 1, f"expected exactly one pattern on {model.__name__}.{field}"
    return str(patterns[0])


# ---------------------------------------------------------------------------
# 7. Containment and integrity (from the security review of this diff).
#
# All four are validation TIGHTENINGS on existing fields, not new fields, so
# none bumps CONTEXT_SCHEMA_VERSION -- which is exactly why they land at the
# freeze rather than after it. Once SB3-02 writes manifests to disk, tightening
# invalidates stored artifacts; today it costs nothing.
#
# The argument that carried them: `execution.py` already applies the equivalent
# rules on the WRITE side (`MissionReceipt.changed_files` rejects absolute paths
# and `..`; `MissionEnvelope` rejects blank tuple entries;
# `CompiledRoadmap.source_sha256` is pattern-pinned). `SourceRef` is the READ
# side and had none of them.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "locator",
    [
        "/etc/passwd",
        "/home/user/.config/gh/hosts.yml",
        "../../root/.ccr/ca-bundle.crt",
        "docs/../../secrets.txt",
        "https://attacker.example/payload",
        "file:///etc/shadow",
        "docs\\product\\some-doc.md",
        "   ",
    ],
)
def test_locator_cannot_escape_the_repository(locator: str) -> None:
    """The READ-side twin of the containment ``MissionReceipt.changed_files``
    already applies on the write side. A ``locator`` is an instruction to open
    something and paste it into an agent context, so it needs this more."""
    with pytest.raises(ValidationError):
        _ref(locator=locator)


def test_a_plain_repo_relative_path_still_validates() -> None:
    """The rule rejects escapes, not ordinary paths."""
    assert _ref(locator="asxos/domain/tax/positions.py").locator.endswith("positions.py")


def test_dotted_and_named_locators_survive_the_containment_rule() -> None:
    """Why the rule needs no per-kind gate: neither shape trips any check."""
    assert _ref(kind="snapshot_field", locator="data.migrations").locator == "data.migrations"
    assert _ref(kind="outcome_record", locator="job_runs id 913").locator == "job_runs id 913"


def test_dotfiles_are_not_special_cased() -> None:
    """A credentials file is reachable by a relative path; containment alone does not stop it.

    Recorded deliberately so nobody reads the containment rule as a secrets
    guard. It bounds the manifest to the repository; deciding that a bounded
    path is nonetheless off-limits is a policy layer that does not exist yet.
    """
    assert _ref(locator=".env").locator == ".env"


@pytest.mark.parametrize(
    "digest",
    [
        "deadbeef",
        "sha256:deadbeef",
        "md5:" + "a" * 32,
        "crc32:12345678",
        "sha1:" + "a" * 40,
        "SHA256:" + "a" * 64,
        "sha256:" + "A" * 64,
        "sha256:" + "a" * 63,
    ],
)
def test_digest_algorithm_is_pinned_not_caller_chosen(digest: str) -> None:
    """A free-form digest invites ``hashlib.new()`` dispatch -- a downgrade oracle."""
    with pytest.raises(ValidationError):
        _ref(digest=digest)


def test_one_locator_cannot_carry_two_digests() -> None:
    with pytest.raises(ValidationError, match="two digests"):
        _manifest(
            refs=(
                _ref(kind="contract", locator="asxos/x.py"),
                _ref(kind="test", locator="asxos/x.py", digest=OTHER_DIGEST),
            )
        )


def test_two_sections_of_one_file_share_its_digest_and_validate() -> None:
    """The uniqueness key excludes digest on purpose; this is the case proving the
    two rules coexist rather than contradict."""
    manifest = _manifest(
        refs=(
            _ref(kind="architecture", locator="docs/target-architecture.md", lines=(15, 40)),
            _ref(kind="architecture", locator="docs/target-architecture.md", lines=(120, 145)),
        )
    )
    assert len({ref.digest for ref in manifest.refs}) == 1


@pytest.mark.parametrize("entry", ["", "   ", "\t"])
def test_excluded_rejects_blank_entries(entry: str) -> None:
    """A blank can never collide with a locator, so disjointness would pass it in silence."""
    with pytest.raises(ValidationError, match="blank entry"):
        _manifest(excluded=(entry,))


def test_manifest_and_envelope_baselines_share_one_pattern() -> None:
    """Same regex on both, so SB3-02 can compare them without normalisation.

    Not decorative: if one side ever accepts uppercase or a short sha and the
    other does not, a manifest/envelope mismatch becomes a formatting artifact
    instead of the real staleness signal it is supposed to be.
    """
    assert _sha_pattern(ContextManifest, "baseline_sha") == _sha_pattern(
        MissionEnvelope, "baseline_sha"
    ) == _sha_pattern(MissionReceipt, "baseline_sha") == r"^[0-9a-f]{40}$"
