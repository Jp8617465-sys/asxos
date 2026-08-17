# ProjectStateSnapshot schema freeze — SB1-01 (2026-08-17)

**Mission:** SB1-01 — Freeze the `ProjectStateSnapshot` schema (second-brain lane, wave 2).
**Packet:** `docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`
— SB1 section (shape `:495-522`, rules `:524-526`, acceptance `:528-530`), lane framing (`:687-694`),
work-order row SB1-01 (`:730`).
**Implementation:** `asxos/secondbrain/project_state.py` ·
tests `tests/test_project_state_snapshot_schema.py` ·
fixtures `tests/fixtures/project_state_snapshot/`.

**Parallel authorization:** this mission ran alongside P3-01 under the Amendment B rider —
"Rider — parallel authorization (James, 2026-08-17)" in `docs/product/roadmap-state.md`
(recorded verbatim, merged via PR #116), quoting: "Approved parallel: SB1-01 and P3-01".
The `arbi-red-team` CHALLENGE's three conditions precedent were satisfied before build start.

---

## The freeze rule (closed set, version bump)

**The frozen field set below is CLOSED at `schema_version = 1`. Any field addition — top level,
any section, the probe record, or the leaf wrapper — is a schema revision and MUST bump
`schema_version`.** A bump means: a new `Literal` pin, a new freeze record, and migration notes
for consumers. At v1, `extra="forbid"` on every model mechanically rejects undeclared input, and
`ProjectStateSnapshot.schema_version` is pinned `Literal[1]`, so a v2 payload cannot validate
against the v1 schema by accident. The contract tests pin the field set by **set equality**
(hardcoded expected sets in the test file, not imported), so any drift fails CI.

SB2-01 (event/projection semantics) and SB3-01 (mission/receipt/context schemas) both build on
this freeze — neither may widen it in place.

## Frozen field table (every field ↔ packet citation)

Citations are line numbers in
`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`.

| Model | Field | Type at v1 | Packet citation |
|---|---|---|---|
| `ProjectStateSnapshot` | `snapshot_id` | `str` (non-empty) | `:496` |
| `ProjectStateSnapshot` | `schema_version` | `Literal[1]` (required, pinned) | `:497` |
| `ProjectStateSnapshot` | `observed_at` | `AwareDatetime` (tz-aware required) | `:498` |
| `ProjectStateSnapshot` | `repository` | `RepositoryState` | `:499` |
| `ProjectStateSnapshot` | `github` | `GithubState` | `:503` |
| `ProjectStateSnapshot` | `production` | `ProductionState` | `:507` |
| `ProjectStateSnapshot` | `data` | `DataState` | `:510` |
| `ProjectStateSnapshot` | `probes` | `list[ProbeRecord]` (required; may be empty) | `:514` |
| `RepositoryState` | `base_sha` | `FieldObservation` | `:500` |
| `RepositoryState` | `branch` | `FieldObservation` | `:501` |
| `RepositoryState` | `dirty_state` | `FieldObservation` | `:502` |
| `GithubState` | `open_prs` | `FieldObservation` | `:504` |
| `GithubState` | `recent_merges` | `FieldObservation` | `:505` |
| `GithubState` | `workflow_runs` | `FieldObservation` | `:506` |
| `ProductionState` | `release_identity` | `FieldObservation` | `:508` |
| `ProductionState` | `scheduler_owners` | `FieldObservation` | `:509` |
| `DataState` | `migrations` | `FieldObservation` | `:511` |
| `DataState` | `freshness` | `FieldObservation` | `:512` |
| `DataState` | `coverage` | `FieldObservation` | `:513` |
| `ProbeRecord` | `name` | `str` (non-empty) | `:515` |
| `ProbeRecord` | `status` | `Literal["observed","unavailable","error"]` | `:516` |
| `ProbeRecord` | `source` | `str` (non-empty) | `:517` |
| `ProbeRecord` | `observed_at` | `AwareDatetime` | `:518` |
| `ProbeRecord` | `value` | `JsonValue` (iff `observed`) | `:519` |
| `ProbeRecord` | `freshness` | `JsonValue` (optional; only if `observed`) | `:520` |
| `ProbeRecord` | `error_class` | `str` (required iff `error`; category only) | `:521` |
| `FieldObservation` | `status` | `ObservationStatus` (vocabulary from `:516`) | rules `:524` |
| `FieldObservation` | `value` | `JsonValue` (iff `observed`, non-null) | rules `:524` |

**Design note — the leaf wrapper.** The packet's shape gives bare keys with no value types.
`FieldObservation` is the typing of those values, not a field addition: the field SET is exactly
the packet's names, and each leaf's *type* is a `{status, value}` observation so that
`unavailable` is first-class (rules `:524`). The status vocabulary is reused verbatim from the
packet's only status enum — the probe record's `observed | unavailable | error` (`:516`) — so the
whole snapshot speaks one language. Constraints (test-pinned): `observed` REQUIRES a non-null
value (falsy-but-real `0`/`False`/`""`/`[]` are valid); `unavailable`/`error` FORBID one.
"Observed but null" and "unavailable with a value" are unrepresentable — an accidental null can
never masquerade as an observation, and a missing probe can never become zero/green (`:528-529`).
No leaf has a default: a section that was never probed does not validate at all.

## Packet rules, as encoded

- **No write probes** (`:524`): the schema module is pure data — zero I/O. Probe execution is
  SB1-02 and must stay read-only.
- **No secret values** (`:524`): `error_class` is a short error *category* (`"network_timeout"`),
  never a raw message/stderr/URL — raw failure text is where credentials leak. Adapters redact
  before construction. All fixtures are synthetic with obviously-fake placeholders (40×`a` SHAs,
  PR numbers 8999/900x, `fake-cron-host`, `0012_fake_example`) — never live data.
- **Unavailable is first-class** (`:524`): see the leaf-wrapper design note; test-pinned.
- **Branch-only is never main truth** (`:524-525`): a consumer rule. The schema records branch
  identity (`repository.branch`/`base_sha`/`dirty_state`, open-vs-merged PR state) so consumers
  can apply it; the `branch_only` fixture demonstrates the recording.
- **Derived claims link to raw observations** (`:525`): structurally deferred —
  see `sb1_02_deferred_probe_linkage` below.
- **Snapshots are artifacts, not authority** (`:525-526`): a validated snapshot is timestamped
  evidence, never a source-of-truth document. Stated in the module docstring.

## Named deferrals (not fields at v1)

| Deferral | What it defers | Owner |
|---|---|---|
| `sb2_deferred_contradiction_fields` | Doc-truth / contradiction items (two sources disagreeing, branch-only described as merged, claims past freshness windows, …). The vet struck these from SB1-01 by name: detection is SB2's job. The v1 schema deliberately VALIDATES a self-contradictory snapshot — SB1 records faithfully; SB2 detects. Pinned by the `contradictory` fixture test. | SB2-01/SB2-02 |
| `sb2_deferred_staleness_evaluation` | Judging `freshness` values. The v1 schema carries them verbatim and never evaluates age. Pinned by the `stale` fixture test. | SB2-02 |
| `sb1_02_deferred_probe_linkage` | The structural link from a section leaf to the raw `ProbeRecord`(s) backing it (packet rule `:525`). Candidate convention needing NO new field: probe `name` == dotted field path (e.g. `"github.open_prs"`), used by the fixtures. A structural link field would be a version bump. | SB1-02 |
| `sb1_02_deferred_payload_typing` | Typed sub-schemas for leaf/probe `value` payloads (PR entries, workflow runs, migration inventories, …). The packet names no sub-shapes, so payloads are `JsonValue` at v1; refining any payload into a typed sub-model is a version bump. | SB1-02+ |

Anything else tempting goes through the `probes[]` generic extension point — a probe entry, never
a new field.

## Placement: `asxos/secondbrain/`, outside `asxos/domain/`

Vet ruling, folded into the mission envelope: **every `asxos/domain/*` package is product domain**
(signals, tax, portfolio, themes, …) — subject to product conventions, conformance agents, and the
personal-advice firewall. The project-state snapshot is **arbi machinery**: it observes the
project itself, not the market. Placing it in `domain/` would misclassify it for every guard that
keys on that path (e.g. `portfolio-invariant-guard`, `tax-spec-conformance` routing) and would
entangle arbi's second brain with product release discipline. `asxos/secondbrain/` is a new
top-level package; precedent for non-domain top-level packages already exists (`asxos/prototype/`).
SB2/SB3 machinery lands in the same package.

## Acceptance evidence (packet `:528-530`)

- **Determinism:** same fixture input → identical model and identical `model_dump_json()`
  (test-pinned per fixture, plus lossless round-trip).
- **Missing probes do not become zero/green:** no defaults on any leaf; `unavailable` fixture
  is honest everywhere; test-pinned.
- **Source-addressable figures:** every probe carries `source` (non-empty, required); leaf↔probe
  linkage convention deferred by name (above).
- **Synthetic coverage:** five fixtures — `stale`, `unavailable`, `branch_only`, `partial`,
  `contradictory` — all validate; per-fixture semantic pins in
  `tests/test_project_state_snapshot_schema.py` (50 tests).

No live probes were run for field discovery; the packet text was the sole field source, so this
record contains no example observations.
