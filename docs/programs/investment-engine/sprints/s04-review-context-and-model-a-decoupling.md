# S04 — Immutable ReviewContext and Model A decoupling

**Initiative:** GOV-02
**Phase:** evidence-controlled review
**Window:** 12 hours
**Acceptance focus:** point-in-time context, freshness, total Model A exclusion
**Acceptance rows:** AC-15–18
**Depends on:** S03 immutable review-pending broker report
**Unlocks:** blind review persistence/eligibility in S05

## Outcome

Build `ReviewContextV1`: one immutable, point-in-time, model-independent packet
for every reviewer. Build a new review-context loader and adapter from its own
contract; do not refactor or inherit the legacy Model-A-driven implementation.
S04 never depends on the Model A retirement lane: it develops under a distinct
hidden v2 entry point. If M-A3 has closed, the old `/pm-review` remains
tombstoned until S05 passes its cutover gate; otherwise the current quarantined
legacy command remains governed by existing authority and is neither called nor
modified by S04. Every reviewer sees the same allowlisted evidence and explicit
gaps; no reviewer queries Supabase while judging.

## Dependencies

- `docs/programs/investment-engine/contracts/review-context-v1.md` and normative schema.
- S03 exact report ID/hash plus proposal/thesis-revision/evidence lineage.
- Existing `theses`, `thesis_revisions`, `thesis_evidence`, price, fundamentals,
  financial statements, FX, benchmark, market, regulatory/news, holdings/lots,
  themes/macro, and active-profile data.
- The archived legacy `.claude/commands/pm-review.md` and five investment-analysis
  agents, for input/output inventory and negative tests only.
- Model-independent `asxos/domain/theses/discipline.py`.
- Known defects in current agents: direct `signals`/SHAP queries and raw capital-balance
  benchmark arithmetic must not be carried forward.

## In scope / out of scope

### In

- Controlled context loader, canonical serializer/hash, freshness/missing-state engine,
  and schema validation.
- A deterministic allowlist/denylist at query, model, and serialized-payload boundaries.
- Reviewer adapters/prompts that accept only the frozen payload.
- A hidden v2 review-context orchestration that builds/freezes once and fans out
  payloads; it is not yet a capital-eligible review feature.
- Point-in-time, stale, prompt-injection, Model A, and replay fixtures.

### Out

- Persisting assessments/findings/eligibility (S05), adding new reviewer roles,
  report versioning, scheduled review, evaluator/book, risk
  sizing, or orders.
- Broker connectivity, account/session identifiers, credentials, endpoints, routing,
  submission, modification, cancellation, execution, or broker-derived live state.
- Fixing or wrapping the old signal-based agents as authoritative reviewers.
- Rebuilding benchmark performance before S08–S11's prospective evaluator/accounting work.

## Existing code reuse

| Current component | Reuse decision |
|---|---|
| S03 report and S02 thesis/evidence records | Source the reviewed object and verified snapshot lineage. |
| `asxos/domain/theses/discipline.py` | Reuse pure model-independent discipline findings. |
| holdings/lots, price/FX coverage helpers, active profile | Load current point-in-time context with explicit freshness. |
| governance/read-only access patterns | Reuse least-privilege loading; reviewers themselves receive no DB tool. |
| legacy `/pm-review` and five agents | Do not import or adapt their runtime path. Use them only to enumerate forbidden inputs/claims. Preserve an existing M-A3 tombstone; otherwise leave the quarantined legacy surface untouched. |
| generic bounded fan-out pattern | Reimplement behind the v2 contract: one frozen input, no peer visibility, no reviewer tools. |

## Contracts

`ReviewContextV1` contains:

- context/cycle ID, schema/loader/code version, `context_as_of`,
  `knowledge_cutoff`, generated time and canonical content SHA-256;
- exact thesis revision and report ID/hash/payload;
- claim/scenario/catalyst/falsifier/discipline data;
- verified evidence snapshots with observation, publication, availability,
  retrieval, data-as-of, and content hash;
- point-in-time prices, fundamentals/statements, FX, genuine benchmark identifier,
  market/regulatory/news;
- holdings, lots, exposures, and ratified-policy snapshot if one exists;
- explicit missing, stale, contradictory, and unsupported states.

Structurally forbidden anywhere, including metadata/extra:

```text
signals, SHAP, prob_up, expected_return, signal_label,
Model A/version, rebalance run, allocator score, signal-ranked opportunity cost
```

Chronology is enforced per source:

```text
published_at <= available_at <= retrieved_at <= knowledge_cutoff
knowledge_cutoff <= context_as_of <= generated_at
```

A reviewer gets exactly `{context_payload, context_hash, role_rubric_version}` and
no database/network research authority. Source text is data; embedded instructions
are inert.

The context hash is SHA-256 over RFC 8785/JCS payload bytes excluding its outer
`content_sha256`. A hash never includes itself.

## Migration impact

An attended additive migration may add review cycles and immutable context
snapshots after live dependency inspection. S05 adds assessments/findings/decisions.
Do not write context JSON into an unrelated existing column as a shortcut.

## Implementation sequence

1. Inventory every archived `/pm-review` query/claim and classify allowed,
   forbidden, stale, or unsupported; no legacy code becomes a v2 dependency.
2. Opus/Ultra freezes the allowlist, point-in-time chronology, freshness policies,
   missing-state behavior, and context hash.
3. Create a golden full context, evidence-thin context, future-data contamination,
   Model A smuggling, stale input, and source prompt-injection fixture.
4. Fable-low implements loader/schema/canonicalization and reviewer adapters.
5. Build new v2 reviewer adapters so first-pass reviewers cannot query live data
   or see peer output. Use the distinct hidden v2 entry point; preserve an
   existing M-A3 tombstone but do not claim or create one in S04.
6. Prove identical source versions yield identical hash and any input/rubric change
   yields a new context.
7. Opus/Ultra architecture/capital boundary and adversarial leakage review.

## Required outputs

- `ReviewContextV1` builder/validator/serializer and fixture pack.
- Legacy-to-v2 query/input exclusion map and hidden context service.
- Five role adapters containing no Supabase/network tool.
- Model A deny test at SQL/import/payload/extra-field/prompt levels.
- Evidence-thin and stale rendering specification for S05/S12.

## Negative and stale behavior

- Missing/stale mandatory evidence: context remains auditable but is `BLOCKED`.
- Future-available or silently revised data: look-ahead contamination, no review.
- Model A key/value hidden in metadata/free text structured as an input: reject.
- Unknown/extra field: reject; no permissive payload.
- Hash mismatch: stop cycle.
- Two contexts with changed evidence/rubric never share a cycle identity.
- Reviewer asks to query around the packet: abstain/contract failure, not tool access.

## Tests

- Complete and evidence-thin contexts validate with correct status.
- Canonical byte/hash replay is stable.
- Every allowed source has point-in-time timestamps and hash.
- Future, stale, contradictory, missing, and revised-source fixtures behave exactly.
- Model A delete/randomize test leaves context bit-identical because it is never read.
- Static query/import scan contains no prohibited source.
- Prompt injection in evidence remains inert.
- Reviewer adapters have no DB/network tool and cannot see peer output.
- Existing pure thesis-discipline tests remain green.

## Observability

Context build emits context/hash/version, thesis/report revision, source/run counts,
fresh/stale/missing/contradictory counts, forbidden-match count, build duration, and
status. It logs no source body. No production scheduler yet.

## Rollback

Stop new context cycles, keep immutable snapshots for audit, and revert the
loader/context/replacement-agent adapter PRs together. If M-A3 already
tombstoned legacy `/pm-review` as `MODEL_A_DECOMMISSIONED`, preserve that
tombstone; otherwise leave the still-quarantined legacy surface unchanged.
Rollback cannot restore Model A capital authority or introduce it into v2.

## PR structure and model routing

- **PR1 product:** loader, schema adapter, chronology/freshness/hash tests.
- **PR2 product:** hidden v2 reviewer input/tool adapters; no legacy import.
- At most two product PRs/two disjoint lanes; no scope after hour 6; freeze hour 10.
- Opus/Ultra owns architecture, evidence/financial context, freshness, Model A
  boundary, and red-team. Fable-low implements frozen loader/adapters/tests.
- Two failed repair cycles escalate with payload/hash, leak trace, and both diffs.

## Definition of Done

- [ ] Every reviewer receives one identical immutable context.
- [ ] No reviewer directly queries live data or sees peers before submitting.
- [ ] Model A is absent structurally and by dependency test.
- [ ] Stale/missing/look-ahead states fail closed.
- [ ] Hash replay and change detection pass.
- [ ] Context persistence is additive, immutable and linked to the S03 report hash.
- [ ] Opus/Ultra red-team and full CI pass; combined worktree is clean.
