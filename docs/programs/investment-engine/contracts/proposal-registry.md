# Proposal Registry Contract

**Contract version:** 1.0
**Introduced:** S01
**S01 evidence ceiling:** `PAPER_ONLY`

## Purpose

Replace divergent `_KNOWN_AGENTS`, `_PROPOSAL_MODELS`, citation handling, and
consumer assumptions with one registry shared by agent-run logging and governed
materializers. This contract governs proposal integrity only. It grants no
approval, tailored-output, sizing, staging, broker, or execution authority.

```text
ProposalContract
  object_type
  schema_version
  pydantic_model
  allowed_agent_names
  subject_validator
  citation_walker
  materializer
```

The immutable key is `(object_type, schema_version)`. The registry is code, not
a database-configurable routing table. Unknown or duplicate keys, unauthorized
producer/object pairs, invalid subjects, missing validators, and unknown versions
fail before any evidence or run write.

## Persistence contract

S01 uses the existing `agent_runs.object_type` and
`agent_runs.proposed_object JSONB` fields. It adds no migration and rewrites no
legacy row.

Every new proposal value in `proposed_object` has this exact outer shape:

```json
{
  "envelope_version": "1.0",
  "object_type": "theme",
  "schema_version": "1.0.0",
  "producer": "sector-screener",
  "subject": null,
  "payload": {}
}
```

Rules:

1. `envelope_version` is exactly `1.0`.
2. `object_type` exactly equals `agent_runs.object_type`.
3. `schema_version` participates in the registry key and is explicitly supplied
   by the attended proposal writer.
4. `producer` exactly equals `agent_runs.agent_name`.
5. `subject` exactly equals `agent_runs.subject`, including `null`.
6. `payload` is the validated model dump after recursive citation resolution.
7. No other outer property is accepted.

The write service resolves the full registry contract and validates the outer
metadata and raw payload shape before any write. Inside one transaction it then
inserts evidence, resolves citations, validates the normalized payload,
assembles the final envelope, and inserts the run. Any failure rolls back all
evidence and run writes. A consumer locks the run, resolves and validates the
same key and metadata, and supplies only `payload` to the existing
object-specific materializer.

### Legacy rows

An existing bare `proposed_object` with no `envelope_version` resolves only to
`(agent_runs.object_type, legacy-v0)`. `legacy-v0` is a closed, read-only
compatibility path:

- it accepts only `macro_thesis`, `theme`, and `theme_holding`;
- it uses a pinned adapter for the baseline model shape;
- it enforces the producer allowlist below;
- it is never selected for a new write;
- it never rewrites or reserializes a stored row; and
- a later contract may not reinterpret it under a new schema version.

A bare `thesis` value, unknown type, unknown producer/object pair, partially
formed envelope, or unsupported version is `DOSSIER_DRIFT`. No inference from
the payload shape or fixture filename is allowed.

## Registered baseline pairs

| Object type | Read versions | Write version | Allowed agent names | Subject rule | Validator | Materializer |
|---|---|---|---|---|---|---|
| `macro_thesis` | `legacy-v0`, `1.0.0` | `1.0.0` | `macro-economist` | `null` | pinned `MacroThesisProposal` adapter | `create_macro_thesis_from_agent_run()` |
| `theme` | `legacy-v0`, `1.0.0` | `1.0.0` | `sector-screener`, `theme-researcher` | `null` or exact `payload.theme_code` | pinned `ThemeProposal` adapter | `create_theme_from_agent_run()` |
| `theme_holding` | `legacy-v0`, `1.0.0` | `1.0.0` | `sector-screener`, `theme-researcher` | `null`, exact `payload.symbol`, or exact `payload.theme_code` | pinned `ThemeHoldingProposal` adapter | `create_theme_holding_from_agent_run()` |

These subject rules preserve the current optional CLI contract while rejecting
a contradictory identity. A future subject meaning requires a new version.
Evidence-only runs from the three named agents have no proposal registry key.

`thesis` is intentionally absent in S01. The baseline logger rejects it, there is
no `ThesisProposal` model or actual producer, and its existing consumer is
unreachable. S02 must add a reviewed schema/version, producer mapping, subject
rule, and compatibility test before a thesis proposal can be written.

## Citation contract

`evidence_citation_ids` may occur at any depth inside `payload`, including
report sections and figures. Logging:

1. Parses with `json.loads(..., parse_float=Decimal)`.
2. Walks the complete proposal model/tree for every field named `evidence_citation_ids`.
3. Resolves `local:N` references against evidence created in the same transaction.
4. Deduplicates the resolved union for database verification while retaining field-local order.
5. Verifies every ID exists and is non-speculative.
6. Rejects agent self-use of `james_input` provenance.
7. Validates the normalized proposal with the registered Pydantic model.
8. Persists evidence and run atomically.

Top-level-only resolution, a citation outside `payload`, or an envelope inserted
before validation is a contract failure.

## S02 thesis materializer contract

Once S02 registers a real thesis proposal pair, its consumer:

1. Locks `agent_runs` with `FOR UPDATE`.
2. Validates unacted/type/version/allowed agent/subject, the envelope metadata,
   and the complete citation union.
3. Inserts a `research` thesis with `governance_status='draft'` and `source_run_id`.
4. Writes the initial revision and valid draft theme placeholders.
5. Copies cited evidence into `thesis_evidence`, preserving snapshots, hashes, provenance, and
   source-as-of.
6. Marks source evidence promoted.
7. Emits `draft -> evidence_complete -> pending_review` governance events.
8. Marks the run acted-on with the resulting thesis ID.
9. Commits as one transaction.

An exact retry returns the existing thesis with `created=false`. An acted-on run with a missing or
different result raises `AgentRunIntegrityError`. Invalid input leaves no partial state.

## Versioning

Adding, removing, renaming, or changing the meaning of a payload field requires
a new semantic schema version and compatibility test. A materializer declares
every accepted version and never silently reinterprets a stored proposal under
a newer schema. Only one write version per object type may be current.

Changing the outer envelope requires a new `envelope_version`; it is not a
payload schema bump. Changing an allowlist, subject rule, validator, citation
semantics, or materializer for an existing version is forbidden unless the old
behavior remains registered as a pinned compatibility entry.

## Capital and authority quarantine

Registry membership does not make output capital-authoritative. The legacy
Model-A-driven `/pm-review` and coupled agents are not registered producers and,
after the approved M-A2 authority amendment and closed M-A3 runtime/surface
retirement, return `MODEL_A_DECOMMISSIONED`. This is a fail-closed tombstone:
they cannot feed proposal eligibility, review,
lifecycle, risk, sizing, or staging. Model A, signals, probabilities, SHAP, and
derived rankings are prohibited in every registered payload and consumer
dependency.

S01 remains `PAPER_ONLY`. Direct tailored output requires a separate
James-ratified authority change covering `CLAUDE.md`,
`docs/product/north-star.md`,
`docs/product/portfolio-manager-charter.md`,
`docs/product/portfolio-policy.md`,
`docs/product/recommendation-schema.md`,
`docs/product/arbi-permission-model.md`, and
`.claude/rules/portfolio-conventions.md`. Until all seven are ratified together,
the stricter current runtime constitution wins.
