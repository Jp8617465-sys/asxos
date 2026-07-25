# S01 — Programme guardrails and proposal registry

**Initiative:** GOV-01
**Phase:** governance and harness
**Window:** one outcome week: one bounded 8-hour registry mission plus one
bounded 12-hour read-only Model A inventory/archive/decision mission; approved
runtime decommission continues in separately bounded missions
**Acceptance focus:** programme boundary, proposal routing, repair/PR controls
**Acceptance rows:** AC-01–05, AC-26–27
**Depends on:** `main@9d442de287e123ae090b95838155dc41d76ee5f3` or a freshly verified successor
**Maximum evidence tier:** `PAPER_ONLY`
**Unlocks:** implementation of the S02 proposal consumer; it does not unlock
tailored output

## Outcome

Create one code-owned proposal registry and one executable programme harness.
Every supported agent proposal persists an explicit version and every producer
and governed materializer resolves the same object type, version, producer
allowlist, subject validator, complete citation walker, and consumer. CI proves
the James-only execution firewall, Model A isolation, an explicitly approved
runtime retirement or typed `NOT READY`, contract/schema/fixture alignment,
roadmap links, and mission controls before feature work begins.

S01 is a `PAPER_ONLY` dossier and guardrail implementation. It does not amend
the repository constitution, enable tailored recommendations, create an
advice-ready or staged-order surface, or claim live financial semantics.

## Dependencies

- `CLAUDE.md`, `docs/programs/investment-engine/{decisions,current-state,architecture}.md`.
- `docs/product/roadmap.yaml` and its JSON Schema.
- `docs/programs/investment-engine/contracts/proposal-registry.md`.
- `docs/programs/investment-engine/model-a-decommission.md`.
- `docs/programs/investment-engine/contracts/model-a-archive-manifest-v1.md`
  and `model-a-archive-restore-evidence-v1.md`.
- Current `asxos/domain/governance/agent_run_service.py`,
  `agent_run_guards.py`, and `transitions.py`.
- Current proposal models in `asxos/domain/theses/schemas.py`.
- Existing `_KNOWN_AGENTS`, `_PROPOSAL_MODELS`, top-level citation resolver,
  and object-specific materializers.
- Current `/pm-review` command and its five legacy review agents.
- Current Model A job definitions in `render.yaml`, job entry points, CLI/model
  and signal surfaces, allocator/opportunity-cost readers, model artifacts,
  data classes, `job_runs`, and product-health/deadman dependencies.
- Current runtime authority: `CLAUDE.md`,
  `docs/product/north-star.md`,
  `docs/product/portfolio-manager-charter.md`,
  `docs/product/portfolio-policy.md`,
  `docs/product/recommendation-schema.md`,
  `docs/product/arbi-permission-model.md`, and
  `.claude/rules/portfolio-conventions.md`.
- All versioned programme schemas and synthetic fixtures present when the
  mission starts.

## In scope / out of scope

### In

- A typed `ProposalContract`/registry under the governance domain.
- Registry entries for the three currently supported proposal object types:
  macro thesis, theme, and theme holding.
- An explicit version envelope inside `agent_runs.proposed_object`, with
  read-only compatibility for legacy bare payloads and no row rewrite.
- One recursive citation walker shared by logging and consumers.
- Dossier validator and tests for roadmap, contracts, schemas, fixtures,
  filenames, links, and lifecycle vocabulary.
- Capital-path import/source deny tests, immutable Model A archive/restore
  evidence, explicit approval state, and mission-window checks. A fail-closed
  legacy `/pm-review` surface and shutdown/no-write evidence are conditional
  outputs of separately approved M-A2/M-A3 missions.
- A read-only deployed inventory and deterministic archive manifest covering
  Model A jobs, data, artifacts, healthchecks, writers, and readers.
- After an explicit James approval record: separate attended changes that
  first amend the current authority documents, then disable Model A
  schedules/writers and fail closed legacy product surfaces.
- An authority-ratification packet that identifies the exact constitutional
  changes James would need to approve in a separate reviewed change before
  tailored output can be enabled.

### Out

- Materializing a thesis, adding review persistence, changing finance semantics,
  migrations, new scheduled jobs, CLI/brief investment output, risk policy, sizing,
  or orders.
- Destructive Model A table/artifact deletion, historical row rewrites, or
  “fixing”/reviving the legacy signal allocator.
- Database-configurable routing, dynamic imports from stored data, broker
  research, credentials, routes, or execution states.
- Ratifying or activating tailored-output semantics. S01 records the required
  authority work; it does not perform that authority change.

## Existing code reuse

| Current component | Reuse decision |
|---|---|
| `agent_run_service.log_agent_run()` | Retain the atomic evidence/run write; replace its parallel maps and shallow citation assumption with the registry. |
| `agent_run_guards.load_unacted_run()` / `mark_run_acted()` | Canonical lock/idempotency preamble for materializers. |
| `asxos/domain/theses/schemas.py` proposal models | Register existing models; do not invent duplicate wire shapes. |
| `agent_runs.proposed_object JSONB` from migration 0033 | Persist a version envelope in the existing column; do not add a column or rewrite legacy rows. |
| `asxos/domain/governance/transitions.py` | Keep governance event-before-status-update ordering. |
| `tests/test_agent_run_service.py` and existing materializer tests | Extend as regression anchors. |
| `docs/programs/investment-engine/schemas/roadmap.schema.json` | Validate the canonical roadmap, not a generated checklist. |
| Existing review gate, `make check`, CI, and agent routing | Reuse as delivery controls. |

## Contracts

`ProposalContractV1` is an immutable code record:

```text
object_type
schema_version
pydantic_model
allowed_agent_names
subject_validator
citation_walker
materializer | None
```

The registry key is `(object_type, schema_version)`. Unknown/duplicate keys,
unauthorized producer/object pairs, subject mismatch, unknown versions, or
missing validators fail before a database write. It is code-reviewed, not
database-configured.

### Persisted version envelope

No S01 migration is permitted. New proposal writes use the existing
`agent_runs.object_type` column plus this value in
`agent_runs.proposed_object`:

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

`object_type`, `producer`, and `subject` must exactly match the values on the
`agent_runs` row, including `null`. `payload` is the existing validated
proposal model dump. The service requires an explicit proposal
`schema_version`; the attended CLI and discovery commands pass `1.0.0`.
Registry lookup plus outer metadata and raw-payload validation happen before
any write. Evidence insertion, citation resolution, normalized payload
validation, envelope assembly, and the run insert occur in one transaction;
any failure rolls back all rows. Consumers lock the run, validate the same
envelope and registry key, then pass only `payload` to the existing
materializer.

A pre-S01 `proposed_object` without `envelope_version` is read through the
closed, read-only key `(object_type, legacy-v0)`. `legacy-v0` accepts only the
three baseline object types and pinned compatibility validators below. It is
never a write target, never reserialized as `1.0.0`, and never silently
reinterpreted by a later model. A bare `thesis` payload, an unknown type, or a
partially formed envelope is `DOSSIER_DRIFT`. This preserves historical rows
without a schema migration or data rewrite.

### Producer and consumer inventory

These are the only producer/object pairs that exist on the baseline:

| Object type | Versions read | Version written | Allowed producers | Subject rule | Validator | Consumer |
|---|---|---|---|---|---|---|
| `macro_thesis` | `legacy-v0`, `1.0.0` | `1.0.0` | `macro-economist` | `null` | pinned `MacroThesisProposal` compatibility adapter | `create_macro_thesis_from_agent_run()` |
| `theme` | `legacy-v0`, `1.0.0` | `1.0.0` | `sector-screener`, `theme-researcher` | `null` or exact `payload.theme_code` | pinned `ThemeProposal` compatibility adapter | `create_theme_from_agent_run()` |
| `theme_holding` | `legacy-v0`, `1.0.0` | `1.0.0` | `sector-screener`, `theme-researcher` | `null`, exact `payload.symbol`, or exact `payload.theme_code` | pinned `ThemeHoldingProposal` compatibility adapter | `create_theme_holding_from_agent_run()` |

Evidence-only runs may still be logged by those three known agents without an
object type or registry key. `thesis` is deliberately not registered in S01:
there is no baseline producer or validating model and its existing consumer is
unreachable. S02 must add a reviewed, versioned `thesis` contract and a real
producer mapping; it may not infer either from a fixture name.

The citation walker traverses the complete parsed raw tree and collects every field
named `evidence_citation_ids`, at any depth. It resolves `local:N`, retains
field-local order, verifies the deduplicated union against persisted evidence,
then validates the normalized payload and rejects speculative evidence or
agent-authored `james_input`.

The harness freezes these global constants:

```text
user = James
capital terminal = ORDER_STAGED (non-routable)
broker execution = prohibited
Model A capital use = prohibited
AI roles = research and review
deterministic roles = quant, tax, accounting, risk, evaluation, sizing
evidence tiers = PAPER_ONLY | UNCALIBRATED | EVIDENCE_BACKED
```

The active S01 ceiling is exactly `PAPER_ONLY`; listing later programme tiers
does not grant them.

## Model A archive and runtime decommission

The governing plan is
[`../model-a-decommission.md`](../model-a-decommission.md); the machine records
are
[`model-a-archive-manifest-v1`](../contracts/model-a-archive-manifest-v1.md) and
[`model-a-archive-restore-evidence-v1`](../contracts/model-a-archive-restore-evidence-v1.md).
Before any shutdown,
the M02 mission resolves deployed—not merely repository-declared—state, produces
a deterministic checksummed archive manifest, proves an attended
restore/reproduction path, and records James's approval or returns `NOT READY`.

The inventory must map `model_a`, `model_a_ml`, and `v1_5` identities before any
irreversible step. It covers `generate_signals`, `retrain_model_a`,
`build_portfolio`, `compute_opportunity_cost`, `check_model_staleness`, and
`track_signal_outcomes`; active routes/commands/brief readers; health/deadman
expectations; model artifacts; `signals`; `signal_outcomes`; allocator-derived
records; and every downstream freshness dependency.

Only after approval, implementation PRs disable the exact deployed Model A
schedules, remove them from current product-health denominators, deny new Model
A writes before database initialisation, and fail closed the legacy command and
coupled agents. Existing rows and artifacts become read-only audit evidence. If
a named job is shared with a non-Model-A responsibility, the mission separates
that responsibility or returns `NOT READY`; it never silently disables unrelated
controls.

## Conditional legacy `/pm-review` retirement

This dossier does not itself retire `/pm-review`. Until DEC-025 and the exact
authority amendment are James-approved, the current command remains governed by
`CLAUDE.md`, the portfolio-manager charter, portfolio policy, Arbi permission
model, recommendation schema, north star, and portfolio conventions, with Model
A excluded by standing rule #11.

After that approval and authority change, the Model-A-coupled `/pm-review` path
and the five agents it orchestrates are retired from active use:

- `thesis-coherence-guard`;
- `thesis-milestone-monitor`;
- `benchmark-performance-analyst`;
- `portfolio-coherence-reviewer`; and
- `market-context-narrator`.

The approved replacement command returns a stable
`MODEL_A_DECOMMISSIONED` tombstone with a link to
the programme status. It does not run a synthesis, query signals, register a
capital proposal, persist into the new review path, change a thesis lifecycle,
establish review eligibility, choose a verdict, affect risk or sizing, or appear
as tailored/advice-ready/staged output. Model A labels, probabilities, SHAP
values, signals, and derived rankings remain excluded from every capital
dependency.

S04 builds the independent immutable context and S05 builds the first
deterministic persistent eligibility path. Neither is an alias or continuation
of the legacy signal-driven semantics.

## Tailored-output authority gate

Before any runtime output may be described as direct, tailored,
recommendation-ready, `ADVICE_READY`, or `ORDER_STAGED`, James must ratify one
separate reviewed authority change covering every one of:

1. `CLAUDE.md`;
2. `docs/product/north-star.md`;
3. `docs/product/portfolio-manager-charter.md`;
4. `docs/product/portfolio-policy.md`;
5. `docs/product/recommendation-schema.md`;
6. `docs/product/arbi-permission-model.md`; and
7. `.claude/rules/portfolio-conventions.md`.

The same change must update the tests that enforce those documents and retain
James-only use, non-reliance wording, the no-broker firewall, manual external
execution, and Model A exclusion. Missing ratification of any listed authority
is `NOT READY`; the stricter current repository wording wins. The S01 output is
an inventory/ratification packet only, not that semantic change.

That packet must explicitly repair the current `portfolio-policy.md`
contradictions rather than silently carry them forward:

- remove `0.6 prob_up / 0.4 expected_return` composite scoring as capital policy;
- retire signal-allocator/inverse-vol/position-count heuristics as authority for
  the new engine;
- mark unresolved cash, leverage, loss, concentration, liquidity, construction,
  sizing and staging values `JAMES_INPUT_REQUIRED`; and
- replace accepted “risk-blind v1” language with the S07 ratified policy,
  diagnostic risk and explicit remaining gaps.

Only James may ratify those capital-policy changes.

## Migration impact

None. Version identity is stored in a JSON envelope in the existing
`agent_runs.proposed_object` column. Legacy bare payloads use the closed
`legacy-v0` mapping above. S01 adds no column and rewrites no row. A stored
proposal that is not representable by the registry is `DOSSIER_DRIFT`.

## Runtime ownership, outputs, and tests

The registry mission instance is copied to
`docs/programs/investment-engine/missions/S01/M01/mission.yaml`; its close record
is `docs/programs/investment-engine/missions/S01/M01/close.md`, and its authority
inventory is
`docs/programs/investment-engine/missions/S01/M01/authority-ratification.md`.
The bounded read-only Model A M-A1 mission uses
`docs/programs/investment-engine/missions/S01/M02/mission.yaml`,
`model-a-inventory.json`, `model-a-archive-manifest.json`,
`model-a-restore-evidence.json`, `model-a-approval.md`, and `close.md` in the
same M02 directory. Shutdown, surface retirement, and the elapsed no-write
observation belong to later immutable M-A2/M-A3 mission directories and reviewed
changes. The template is never edited in place.

| Owner | Exact implementation paths | Required output | Exact tests |
|---|---|---|---|
| Opus/Ultra — registry and capital boundary | `asxos/domain/governance/proposal_registry.py`, `asxos/domain/governance/agent_run_service.py`, `asxos/domain/governance/agent_run_guards.py` | immutable registry, envelope/legacy decoder, recursive citation walker, fail-closed lookup | `tests/test_proposal_registry.py`, `tests/test_agent_run_service.py` |
| Fable-low — frozen adapters | `asxos/cli/agent_run.py`, `.claude/commands/discover-macro.md`, `.claude/commands/discover-sector.md`, `.claude/commands/discover-theme.md`, `asxos/domain/macro_theses/service.py`, `asxos/domain/themes/service.py` | explicit `1.0.0` writer flag and registry-backed consumer payload adapters | `tests/test_cli_agent_run.py`, `tests/test_macro_theses_service.py`, `tests/test_theme_from_agent_run.py` |
| Opus/Ultra — authority and Model A evidence | `docs/programs/investment-engine/missions/S01/M01/authority-ratification.md`, `docs/programs/investment-engine/missions/S01/M02/{model-a-inventory.json,model-a-archive-manifest.json,model-a-restore-evidence.json,model-a-approval.md,close.md}` | complete authority inventory; reproducible archive/restore; explicit approval or `NOT READY`; no production mutation | `tests/test_investment_engine_boundaries.py`, `tests/test_model_a_decommission.py` |
| Opus/Ultra — approved authority amendment | `CLAUDE.md`, `docs/product/{ml-engine-shelf-2026-07-11.md,north-star.md,portfolio-manager-charter.md,portfolio-policy.md,recommendation-schema.md,arbi-permission-model.md}`, `.claude/rules/portfolio-conventions.md` | one coherent James-approved replacement of passive-monitor and legacy `/pm-review` authority; no implicit allocator revival | authority-link and contradictory-policy tests in `tests/test_model_a_decommission.py` |
| Fable-low — approved Model A shutdown adapter | `render.yaml`, Model A job entry points, current health/deadman inventory, `asxos/cli/{model,signal}.py`, `.claude/commands/pm-review.md`, the two Model-A-coupled reviewer agents | after authority approval: zero enabled schedules, pre-DB `MODEL_A_DECOMMISSIONED` denial, tombstoned product/review surfaces; no data deletion | `tests/test_model_a_decommission.py`, existing job/CLI/agent boundary tests |
| Fable-low — dossier harness | `scripts/validate_investment_program.py`, `tests/test_investment_program_dossier.py` | schema/fixture/link/UTC/boundary/mission validation | `tests/test_investment_program_dossier.py` |

Ownership is disjoint by row. Any additional runtime path is scope change and
must be rejected after the cutoff. The only mission records written outside
those rows are the exact M01/M02 paths above.

## Implementation sequence

1. Verify main, open PRs, migration count, roadmap, current registry-like maps,
   proposal producers, and object-specific consumers.
2. Opus/Ultra freezes the envelope, `legacy-v0` adapters, exact producer pairs,
   recursive citation semantics, decommission boundary denylist, and harness
   oracle.
3. Add failing registry/harness fixtures before implementation.
4. Fable-low extracts the shared registry/walker and adapts agent-run logging.
5. Prove every legacy valid proposal reads without mutation, every new proposal
   round-trips with an explicit version, and every invalid nested citation
   fails atomically.
6. Add dossier validation and exact model/PR-window metadata checks.
7. M02 captures deployed Model A state, archive bytes/hashes, restore evidence,
   exact downstream dependencies, and James's approval status.
8. Close M02 without production mutation. Only when approved, open separate
   M-A2 then M-A3 mission/change sets: M-A2 lands the coherent authority
   amendment; M-A3 performs scheduler/writer/health and surface retirement and
   observes one formerly scheduled window with no new writes. Elapsed
   observation time is not charged to or fabricated inside the 12-hour M02 work
   window.
9. Run targeted tests, full CI, and Opus/Ultra architecture/capital red-team
   over M01 and M02 together.

## Required outputs

- Shared proposal registry and recursive citation walker.
- Version envelope, closed legacy mapping, and exact producer/consumer inventory.
- Dossier validation command and test suite.
- Model A, broker, lifecycle, single-user, Decimal-string, nested-citation, and
  roadmap-drift negative fixtures.
- M02 Model A deployed inventory, read-only archive manifest, restore proof, and
  explicit approval/`NOT APPROVED` record.
- If approved, separately scoped M-A2/M-A3 authority amendment,
  scheduler/writer/surface shutdown evidence, natural-window no-write
  observation, and fail-closed `/pm-review` retirement. These are not M02
  outputs.
- `PAPER_ONLY` M01/M02 mission and close records with baseline, PR, routing,
  repair count, and clean worktree.

## Negative and stale behavior

- Unknown agent/object/version/subject: typed rejection and no rows.
- Missing/malformed envelope, producer/object mismatch, or a new bare payload:
  typed rejection and no rows.
- Citation hidden in a nested section/figure but absent/invalid: whole transaction
  rolls back.
- Conflicting roadmap, contract, and schema vocabulary: `DOSSIER_DRIFT`, not an
  implementation guess.
- Main/schema state cannot be verified: `NOT READY`.
- Model A field/import/query or broker capability in a capital contract: circuit
  breaker.
- Model A identity mapping, deployed inventory, archive hash, downstream
  dependency, or James approval unresolved: `NOT READY`; no shutdown.
- Model A writer/schedule still active after an approved shutdown, or a new
  post-watermark write appears: circuit breaker.
- After an approved authority amendment and retirement, legacy `/pm-review`
  invocation does anything other than fail closed: circuit breaker. Before
  approval, current stricter authority remains in force.
- Any tailored-output authority document above without James's ratification:
  `NOT READY`.
- A third local patch after two failed Fable cycles is forbidden; escalate.

## Tests

- Registry has unique keys and deterministic lookup.
- All current `legacy-v0` proposal types read exactly as before without row
  mutation; all new writes persist and validate the `1.0.0` envelope.
- Producer/object cross-pairs and unregistered `thesis` writes fail before any
  evidence or run insert.
- Recursive local and existing-ID citations resolve at every nesting depth.
- Missing/speculative/unauthorized/agent-`james_input` citations roll back evidence
  and run rows.
- Boundary scan rejects `signals`, SHAP, `prob_up`, Model A versions, broker
  endpoints/credentials/routes, submit/modify/cancel/execute methods, auth,
  RLS, tenancy, and multi-user fields in programme contracts.
- Roadmap validates and every initiative and every roadmap-declared contract
  links an existing sprint/spec/schema.
- Mission YAML enforces 8h/12h lane, PR, scope-cutoff, and freeze ceilings.
- Date-time validation rejects timezone-less and non-UTC values.
- S01 mission, command, prompts, and close evidence remain `PAPER_ONLY`.
- All deployed Model A surfaces map to the inventory; the archive hash and
  restore drill reproduce.
- M02 itself performs no runtime mutation and closes with reproducible archive
  and restore evidence plus explicit approval status.
- Separate approved M-A2/M-A3 evidence proves zero Model A
  schedules/writers/health dependencies, one naturally elapsed formerly
  scheduled window with no new writes, and fail-closed `/pm-review`/coupled
  agents that cannot enter registry or capital modules.
- No new auth, RLS, tenancy, `user_id`, float capital field, or execution state.
- `.venv/bin/python scripts/validate_investment_program.py`,
  `.venv/bin/python -m pytest tests/test_investment_program_dossier.py -q`,
  targeted runtime tests, and `make check` pass under the documented Python
  3.12 project environment.

## Observability

CI emits registry version, registered key count, legacy/new envelope counts,
unsupported consumer count, schema/fixture/link/contract count,
prohibited-boundary matches, deployed/enabled Model A job count, post-watermark
write count, archive/restore status, and pass/fail. Runtime semantics stay
within the current decision-support constitution; no new job, tailored-output
mode, or broker capability is introduced.

## Rollback

Revert the registry adapters if compatibility fails; because no migration or row
rewrite occurs, legacy rows remain readable by the prior code. New enveloped
rows are quarantined from prior materializers during rollback and must not be
rewritten.

Model A rollback may restore an archive/reproduction reader or tombstone after
James approval; it never restores inference, allocation, product authority, or
investment-engine inputs. An unexpected consumer returns the decommission lane
to `NOT READY` rather than silently re-enabling a writer. S02 is blocked until
M01 and the read-only M02 close. A `NOT APPROVED` M02 leaves the current passive
monitor untouched but does not weaken the engine's absolute Model A isolation
boundary. Approved M-A2/M-A3 work proceeds as a separately tracked lane.

## PR structure and model routing

- **M01 PR1:** registry, recursive walker, adapters, harness, and tests.
- **M02 evidence PR:** immutable inventory/archive/restore/approval packet; no
  runtime mutation.
- **Later M-A2/M-A3 PRs:** separately approved authority alignment, exact
  scheduler/writer/health shutdown, surface retirement, and naturally elapsed
  no-write evidence. Each gets its own mission, cutoff, diff, review, and close.
- M01 uses an 8-hour lane; no scope after hour 4 and freeze at hour 6.5. M02
  uses a 12-hour evidence lane; no scope after hour 6 and freeze at hour 10.
- Opus/Ultra owns architecture, capital boundary, registry semantics, and red-team.
- Fable-low owns frozen extraction, adapters, fixtures, and validator code.
- After two failed repair cycles, attach the failing fixture and both diffs to an
  Opus/Ultra escalation.

## Definition of Done

- [ ] One registry replaces divergent routing/citation assumptions.
- [ ] Every current producer/object pair is exact and every stored/current
      proposal type has explicit `legacy-v0` or `1.0.0` behavior.
- [ ] Nested citation failures are atomic.
- [ ] Dossier/roadmap/schema/fixture validation is green.
- [ ] James-only, Model A, broker, deterministic-domain, and lifecycle gates are
      mechanically enforced.
- [ ] The complete deployed Model A inventory and reproducible read-only archive
      exist; James's approval or `NOT READY` is explicit.
- [ ] When approved, Model A jobs/writers/health dependencies are disabled, the
      no-write window passes, and `/pm-review` fails closed.
- [ ] The seven authority documents are inventoried for later James ratification;
      no live tailored-output semantics are enabled.
- [ ] S01 evidence and all mission records are labelled `PAPER_ONLY`.
- [ ] Model routing and mission ceilings are recorded.
- [ ] Opus/Ultra red-team passes, CI is green, and worktree is clean.
