# Mission / receipt / context schema freeze — SB3-01 (2026-08-22)

**Status:** current
**Mission:** SB3-01 — Freeze the mission, receipt and context schemas (second-brain lane).
**Packet:** `docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`
— SB3 section (`:555-593`), required mission fields (`:563-582`), `ContextManifest` description
(`:585-591`), acceptance (`:593`), work-order row SB3-01 (`:734`).
**Depends on:** SB1-01 (`docs/product/project-state-snapshot-freeze-2026-08-17.md`), whose freeze
record states that "SB3-01 (mission/receipt/context schemas) builds on this freeze — neither may
widen it in place." **It did not.** `ProjectStateSnapshot` is untouched by this work order;
`ContextManifest` references snapshot leaves by their dotted path only.
**Implementation:** `asxos/secondbrain/context.py` (new) · `asxos/secondbrain/_schema.py` (new,
shared frozen base — §1) · tests `tests/test_mission_context_schema.py`. No **field** on
`MissionEnvelope` / `MissionReceipt` / `CheckResult` was added, removed or renamed (§3); the only
edit to `execution.py`, `project_state.py` and `contradictions.py` is importing the shared base
instead of each declaring its own.

---

## 1. The freeze rule (closed set, version bump)

Identical in force to SB1-01's. **The field sets below are CLOSED at `schema_version = 1`. Any
field addition — on `MissionEnvelope`, `MissionReceipt`, `CheckResult`, `ContextManifest` or
`SourceRef` — is a schema revision and MUST bump the version**: a new `Literal` pin, a new freeze
record, and migration notes for consumers.

Two mechanisms, and they cover different directions:

- `extra="forbid"` on every model rejects an undeclared field arriving in **data**.
- Set-equality assertions in `tests/test_mission_context_schema.py` reject a field set drifting in
  **code**.

`ContextManifest` versions **independently** of `ProjectStateSnapshot`. That is why the constant is
`CONTEXT_SCHEMA_VERSION` rather than a second `SCHEMA_VERSION`.

It does **not** extend to the base class. `context.py` was first written with its own local
`_FrozenModel`, justified as keeping the two freezes from coupling. **That justification was wrong
on the mechanics** and the review loop removed it: pydantic resolves `model_config` through the MRO
and lets any subclass override it, so a schema needing different config simply declares its own.
Sharing the base costs a schema nothing.

`context.py` was the **fourth** module in this package to declare a byte-identical
`ConfigDict(extra="forbid", frozen=True)` — three as a private `_FrozenModel`
(`project_state`, `execution`, `context`) and one inline on `contradictions.Contradiction`. All
four now import `asxos/secondbrain/_schema.py::FrozenModel`. The reason this matters beyond
tidiness: with four copies, strengthening the freeze (adding `validate_assignment=True`, say) has
to be applied four times, and the copy that gets missed is a *silently weaker* freeze on a schema
that still claims to be frozen. Verified behaviour-preserving — 2543 passed before and after.

## 2. What the pins actually add — measured, not assumed

`MissionEnvelope` / `MissionReceipt` / `CheckResult` shipped in PR #124 already carrying
`schema_version: Literal[1]` and `extra="forbid"`. The obvious claim — "they had no freeze" — is
**wrong**, and was checked rather than asserted. Each mutation below was applied to
`execution.py` and the **pre-existing** `tests/test_secondbrain_execution.py` run against it:

| Mutation | Pre-existing suite | New pins |
|---|---|---|
| Remove a field (`independent_reviews`) | 2 failed — **caught** | caught |
| Remove a defaulted field (`max_repair_attempts`) | 1 failed — **caught** | caught |
| Rename a field, fixtures left stale | 2 failed — **caught** | caught |
| **Add** a field (`auto_merge: bool = False`) | **23 passed — blind** | **caught** |
| **Coordinated rename** (`rollback` → `rollback_plan`, field *and* every fixture) | **23 passed — blind** | **caught** |

So the honest summary is narrower than "there was no freeze":

- For **removals and uncoordinated renames** the pins add **legibility, not coverage**. The
  pre-existing failure is an `unexpected keyword argument` inside an unrelated behaviour test,
  which reads as "the fixture is stale" rather than "a frozen schema changed".
- For **additions** the pins add real coverage. A defaulted field costs no fixture a single edit,
  so the schema could grow silently — and this is the direction a freeze exists to stop.
- For a **coordinated rename** the packet-name assertion
  (`test_every_packet_required_mission_field_is_present`) is what catches it, because it asserts
  the packet's 17 names rather than whatever the code currently calls them.

## 3. `MissionEnvelope` and `MissionReceipt` are frozen AS THEY STAND — no field was added

The reconciliation (§4) surfaced one candidate addition, `required_citations`. **It was rejected.**
The reasoning is recorded here because "we considered adding a field at the freeze and decided not
to" is exactly the kind of decision that becomes invisible a month later:

`.claude/commands/arbi-mission.md:35` lists `required_citations` on its envelope
("carried from arbi's NEXT PROMPT; the implementer preserves them"), and its readiness pass
(`:64`) checks "citations preserved". The envelope schema has no such field, so on first reading
the harness has a readiness criterion the frozen shape cannot express.

It can. **`ContextManifest.refs` is the citation carrier** — that is the packet's own design
("Every selected current claim resolves to its underlying source, not only to a generated
summary", `:587-588`). The envelope↔manifest link is `ContextManifest.mission_id`. Adding
`required_citations` to the envelope would have created a second, weaker citation channel
(bare strings, no digest, no source resolution) beside the one built for the purpose, and would
have widened a schema at the very moment of freezing it.

`MissionEnvelope` field count stands at 20: the packet's 17 (`:566-582`) plus `schema_version`,
`roadmap_item_id` and `max_repair_attempts`. All three extras predate this work order.

## 4. Command / harness reconciliation review

SB3-01's completion proof in the packet (`:734`) is *"Existing command/harness reconciliation
review."* This is it. `.claude/commands/arbi-mission.md:26-36` documents an 8-field envelope; the
code implements 20.

| Command field (`arbi-mission.md`) | Schema field | Finding |
|---|---|---|
| `mission_id` | `mission_id` | ✅ agree |
| `source` | `source_authority` | **R1 — naming divergence.** Code also constrains it to `Literal["canonical_queue", "direct_instruction"]`; the command's prose ("arbi's ranked #1, or James directly") maps onto exactly those two, so this is a rename, not a semantic gap. |
| `objective` | `objective` | ✅ agree |
| `scope` | `scope` | ✅ agree |
| `allowed_actions` | `allowed_actions` | ✅ agree |
| `forbidden_boundaries` | `forbidden_boundaries` | ✅ agree |
| `stop_condition` (singular, prose) | `stop_conditions` (plural, `tuple[str, ...]`, min 1) | **R2 — shape divergence.** The command's single blob bundles definition-of-done *and* the hard stops; the schema wants them enumerated. |
| `required_citations` | *(none — by decision)* | **R3 — resolved to `ContextManifest.refs`**, see §3. |
| *(absent)* | 12 further fields | **R4 — an envelope written to the command's documented shape cannot validate as a `MissionEnvelope`.** Missing: `programme_id`, `roadmap_item_id`, `roadmap_stage`, `baseline_sha`, `dependencies`, `required_inputs`, `expected_artifacts`, `acceptance_checks`, `independent_reviews`, `rollback`, `outcome_observation`, `schema_version`. |

**R4 is the substantive finding.** `baseline_sha` in particular is what makes the packet's
acceptance criterion — *"invalid or stale baselines fail closed"* (`:593`) — mechanical, and the
command's envelope has no baseline at all. Note the practical blast radius is currently **zero**:
`MissionEnvelope` and `MissionReceipt` have **no production consumer** (verified 2026-08-22 —
referenced only by `execution.py`, `__init__.py` and tests), so `/arbi-mission` runs today are
prose-driven and nothing validates them. That is why R4 is a documented divergence rather than a
live defect — and also why it must be closed before anything starts validating envelopes, or the
first real use will fail closed on twelve missing fields at once.

### Owed follow-up — James's, not arbi's

**`.claude/commands/arbi-mission.md` was NOT edited by this work order.** It is an authority path:
`.claude/commands/` is enumerated in `authority-guard.sh`'s `AUTHORITY_FRAGMENTS` and mirrored in
`.claude/settings.json`'s `Edit(...)` deny array. It is **not** in `.github/CODEOWNERS`, which
lists only `/CLAUDE.md`, `/.claude/settings.json`, `/.claude/hooks/` and `/.claude/agents/arbi.md`
among the `.claude` paths (checked 2026-08-22) — and CODEOWNERS is inert here in any case, since
the sole code owner authors every PR. The hook, not the review gate, is what actually holds this
boundary. James's authorisation this session covered `CLAUDE.md` and
`docs/product/james-inbox.md` specifically; it did not name `.claude/commands/`, and a general
grant is not treated as covering an unnamed authority path.

So R1–R4 are recorded here as a review, which is what the packet asks for, and the edit that would
land them in the command is owed and named:

1. Rename `source` → `source_authority`; state the two permitted values.
2. Split `stop_condition` into enumerated `stop_conditions`.
3. Replace `required_citations` with a pointer to `ContextManifest.refs`.
4. Add the 12 missing fields, `baseline_sha` first.

## 5. Frozen field table — `ContextManifest` and `SourceRef`

Citations are line numbers in the packet.

| Model | Field | Type at v1 | Basis |
|---|---|---|---|
| `ContextManifest` | `schema_version` | `Literal[1]` (required, pinned) | freeze rule |
| `ContextManifest` | `manifest_id` | `str` (non-empty) | identity |
| `ContextManifest` | `mission_id` | `str` (non-empty) | design: one manifest per mission run; the packet names no link field |
| `ContextManifest` | `baseline_sha` | `str`, `^[0-9a-f]{40}$` | `:593` "invalid or stale baselines fail closed" |
| `ContextManifest` | `compiled_at` | `AwareDatetime` | "compiled retrieval view", `:585` |
| `ContextManifest` | `refs` | `tuple[SourceRef, ...]`, min 1 | `:585-587` |
| `ContextManifest` | `snapshot_id` | `str \| None` | `:587` "current snapshot fields" |
| `ContextManifest` | `excluded` | `tuple[str, ...]`, default `()` | `:588-589` "should not load the entire roadmap…" |
| `SourceRef` | `kind` | `Literal[7 categories]` | `:586-587`, verbatim |
| `SourceRef` | `locator` | `str`, non-blank, repo-relative, no `..`/scheme/backslash | path, dotted leaf path, or named observation — see §5.1 |
| `SourceRef` | `digest` | `str`, `^sha256:[0-9a-f]{64}$` | staleness detection for SB3-02 — see §5.1 |
| `SourceRef` | `lines` | `tuple[int, int] \| None` | "relevant target architecture **section**", `:586` |
| `SourceRef` | `derived_from` | `str \| None` | `:587-588` "resolves to its underlying source" |

The seven `kind` values are the packet's own list, one-for-one: `authority`
(constitution/permission references) · `architecture` (relevant target-architecture section) ·
`contract` (exact source contracts) · `snapshot_field` (current snapshot fields) · `test` (tests) ·
`compiled_index` (compiled indexes/backlinks) · `outcome_record` (prior outcome records). **An
eighth category is a version bump, not a new string.**

### Three packet sentences made mechanical rather than left as prose

| Packet prose | Encoding | Test |
|---|---|---|
| "resolves to its underlying source, not only to a generated summary" (`:587-588`) | `kind="compiled_index"` REQUIRES `derived_from` — a compiled view that cannot name its source is unrepresentable | `test_compiled_index_without_derived_from_is_unrepresentable` |
| "should not load the entire roadmap, all handoffs, or all memory" (`:588-589`) | `excluded` records what was deliberately left out, and a locator may not be both selected and excluded | `test_a_locator_cannot_be_both_selected_and_excluded` |
| "current snapshot fields" (`:587`) | a `snapshot_field` ref REQUIRES `snapshot_id` — a leaf path with no snapshot behind it is an unanchored claim | `test_snapshot_field_ref_requires_a_named_snapshot` |

The first of these is the same technique SB1-01 used to make "observed but null" unrepresentable:
push the rule into the type so it cannot be forgotten, rather than into a docstring where it can.

### 5.1 Containment and integrity — four tightenings landed AT the freeze

From the security review of this diff. All four constrain **existing** fields, so per §1 none of
them bumps `CONTEXT_SCHEMA_VERSION` — a version bump is reserved for field *additions*. That is
precisely why they belong here: the moment SB3-02 writes a manifest to disk, tightening
invalidates stored artifacts. Today it costs nothing.

The argument that carried them is in-package precedent, not general security advice.
`execution.py` already applies the equivalent rules on the **write** side — `changed_files` rejects
absolute paths and `..` segments, `MissionEnvelope` rejects blank tuple entries and broad scope
globs, and `CompiledRoadmap.source_sha256` is pattern-pinned. `SourceRef` is the **read** side and
had none of them. That is backwards: `changed_files` records what already happened, whereas a
`locator` is an instruction to go open something and paste it into an agent's context, which is
then summarised into a PR.

| # | Tightening | Why |
|---|---|---|
| F1 | `locator` must be non-blank, repository-relative, with no `..` segment, no `://` scheme, no backslash | Applied uniformly rather than gated on `kind`: these are escape patterns, not path syntax, so a dotted snapshot leaf (`data.migrations`) and a named observation pass unchanged. |
| F2 | `digest` pinned to `^sha256:[0-9a-f]{64}$` | Free-form invites the obvious verifier shape — split on `:` and dispatch to `hashlib.new()` — turning the manifest into a downgrade oracle where `md5:`, `crc32:` or a truncated `sha256:deadbeef` is accepted and staleness detection silently no-ops. |
| F3 | Two refs sharing a `locator` must share its `digest` | The uniqueness key is `(kind, locator, lines)` so two sections of one document stay distinct — but that omits `digest`, letting one manifest assert two hashes for one file at one `baseline_sha`. SB3-02's verifier would have no defined resolution. |
| F6 | `excluded` rejects blank entries | `locator` is non-blank by construction, so `""` in `excluded` can never collide with a selection and the disjointness check would pass over it in silence. |

**What F1 is NOT.** It bounds a manifest to the repository. It does **not** make a bounded path
safe: `.env` is reachable by a plain relative path and validates. `test_dotfiles_are_not_special_cased`
pins that explicitly so the containment rule is never mistaken for a secrets guard. Deciding that
a bounded path is nonetheless off-limits is a policy layer that does not exist yet, and is SB3-02's
to build or to name as owed.

**F4 (`excluded` reads like a control) was fixed in prose, not code.** `_excluded_is_disjoint_from_refs`
is a self-consistency check, not an enforcement boundary — nothing binds a run's actual reads to
`refs`, and `excluded` is compared by exact string equality, so `excluded=("docs/",)` does not
exclude `docs/x.md`. The module docstring now states outright that a manifest is a **declaration,
not a boundary**. The original wording ("says exactly what context a mission run is allowed to
consume") was an authorisation claim the schema does not back.

**F5 was raised and rejected as a non-finding.** Interpolating locators into `ValueError` text does
not violate the no-secret-values rule in `project_state.py`: that rule's scope is `ProbeRecord.error_class`
and persisted observation payloads — data produced from I/O, which is where credentials leak — not
exception text from pure validation. The interpolated values are caller-supplied and already fully
present in the manifest object, `execution.py` does the same in three places, and pydantic's
`ValidationError` echoes input values regardless.

Each of F1, F2, F3 and F6 was mutation-tested: the rule was deleted from `context.py` and the suite
re-run. All four produced red tests (2, 8, 1 and 3 failures respectively).

Every one of these was mutation-tested — the rule was removed from `context.py` and the suite
re-run — and each mutation produced a red test. A rule that passes when deleted is not a rule.

## 6. Explicitly out of scope

SB3-01 is **shape only**. `context.py` performs no I/O and compiles nothing.

- `sb3_02_deferred_compile_manifest` — selecting the refs (walking the repo, reading the snapshot,
  resolving the architecture section) is SB3-02, whose acceptance is "mission executes without
  full-repo context dump" (`:735`).
- `sb3_02_deferred_verify_manifest` — checking a manifest against a live tree (do the digests still
  match? is the baseline still reachable?) is likewise SB3-02. The schema records `digest` and
  `baseline_sha` so that check has something to verify; it does not perform it.
- `sb3_deferred_retrieval_infrastructure` — the packet is explicit that "file indexes and brief
  summaries remain the default until a versioned query set proves a named recall, citation,
  freshness, context-size, or latency failure that justifies more search infrastructure"
  (`:589-591`). No embedding store, no ranking, no query language. A tuple of refs is the whole
  retrieval model at v1.

**SB3-02 remains HELD**, along with SB4-02, SB5-01, SB5-02 and SB6-01, under the packet's §9 kill
condition ("pause on more orchestration work than product evidence work"). Freezing the schema is
the prerequisite those rows named; building the compiler is not authorised by having frozen it.
