# S03 — Immutable, versioned broker report

**Initiative:** ENG-01
**Phase:** persistent research product
**Window:** 12 hours
**Acceptance focus:** immutable report versions, evidence/claim lineage, no history rewrite
**Acceptance rows:** AC-11–14
**Depends on:** S02 governed thesis materializer
**Unlocks:** immutable review context in S04

## Outcome

Turn the current mutable `theses.report_sections` projection into an immutable,
versioned broker-report history without replacing it. Each review-pending report
version freezes the thesis view, qualitative capital intent, claims, scenarios,
figures, catalysts, falsifiers, evidence and producer versions that existed at
one point in time. S04 and S05 bind review artifacts to this exact immutable
version; they never mutate it.

## Dependencies

- `docs/programs/investment-engine/contracts/broker-report-v1.md` and normative schema.
- S02 proposal/run/evidence/thesis lineage.
- Existing migration 0040 `theses.report_sections`, `thesis_revisions`, and
  `thesis_evidence`.
- Current `asxos/domain/theses/{schemas.py,service.py}` and
  `asx thesis show --full-report`.
- Live migration ledger and shared-Supabase dependency audit.

## In scope / out of scope

### In

- `BrokerReportVersionV1` semantic validator and canonical hash.
- Immutable report-version header/payload/evidence/proposal/revision linkage.
- Bear/base/bull scenarios, claim register, executive view, valuation/payoff,
  risks, unanswered questions, catalysts/falsifiers, and discipline wrapper.
- A current-report projection kept compatible with existing thesis CLI.
- Create/list/show/diff version services and attended CLI.

### Out

- Monitoring/scheduling, revision proposals, paper evaluation, risk sizing, staged
  orders, web UI, broker integration, or auto-approval.
- Rewriting old report versions when evidence is corrected.
- Smuggling figures into prose or treating reviewer confidence as a forecast.

## Existing code reuse

| Current component | Reuse decision |
|---|---|
| migration 0040 `theses.report_sections` | Keep as the latest governed projection for current CLI/brief compatibility. |
| `ReportSection`, `ReportFigure`, `ThesisProposal` | Reuse section order, Decimal/provenance/formula, prose-only, and monitor-only guards. |
| `thesis_revisions` | Link report-version creation to the append-only discipline event; do not use it as the only full snapshot. |
| `thesis_evidence` | Reuse verified snapshots and hashes; add version linkage, not copied untraceable citations. |
| `asx thesis show --full-report` | Render a selected immutable version and default safely to latest. |

## Contracts

`BrokerReportVersionV1` requires:

```text
report_version_id, investment_case_id/case_version, thesis_id, version_number,
previous_version_id?, proposal_id/run_id, thesis_revision_id,
data_as_of, knowledge_cutoff, created_at, producer/prompt/schema/code versions,
executive_view, claims[], scenarios{bear,base,bull},
valuation_payoff, catalysts[], falsifiers[], risks[], unanswered_questions[],
discipline_wrapper, qualitative_intent, james_ratified_risk_anchor?,
sections[], evidence_refs[], governance_state=REVIEW_PENDING, content_sha256
```

Every capital-relevant figure is a Decimal string with units/currency and one of:

- `cited`: valid evidence IDs;
- `derived`: valid evidence IDs plus displayed formula; or
- `james_input`: a recorded human source, never agent-emitted.

The hash is SHA-256 over RFC 8785/JCS payload bytes excluding the outer
`content_sha256` field. Creation is compare-and-swap against the current
thesis/report version. A changed
claim, figure, scenario, catalyst, falsifier, discipline input, evidence snapshot,
qualitative intent or risk anchor creates `version_number + 1`. Review and
approval are separate append-only artifacts; neither changes this payload/hash.

## Migration impact

An additive Opus/Ultra migration introduces a logical `broker_report_versions`
header with immutable JSONB payload/hash and unique `(thesis_id, version_number)`,
plus version-evidence linkage if existing `thesis_evidence` cannot express it.
Version-linked section/figure tables are added only if querying/constraints cannot
be satisfied by the canonical JSONB payload. Do not duplicate migration 0040.

Allocate the next migration number from live truth, not assumed `0042`; inspect
`pg_depend`, apply full chain to clean Postgres, and require James for production.

## Implementation sequence

1. Map migration-0040 projection and proposal/revision/evidence links.
2. Opus/Ultra freezes report semantics, scenario/claim completeness, immutability,
   version-CAS, governance, and migration shape.
3. Build golden V1, changed-evidence V2, rejected draft, and conflict fixtures.
4. Author/test additive migration and compatible current projection.
5. Fable-low implements validator, version service, projection update, CLI/show/diff,
   and snapshot tests.
6. Exercise concurrent version creation, failure after header/projection/revision,
   old-version render, and evidence correction.
7. Opus/Ultra migration, financial/valuation provenance, and adversarial review.

## Required outputs

- Normative/implemented `BrokerReportVersionV1`.
- Additive migration and forward-recovery evidence.
- Immutable create/list/show/diff service and CLI.
- Latest-report compatibility projection.
- Full lineage from proposal/evidence/thesis revision to report version.
- S04 context input and S06 monitor input specifying the exact version/hash watched.

## Negative and stale behavior

- Missing mandatory claim/scenario/evidence/proposal/revision lineage: blocked; no
  review-pending report version.
- Stale mandatory evidence: version remains auditable but is ineligible.
- Current version changed since base hash: conflict; create a new candidate.
- Hash mismatch or duplicate version with different content: integrity error.
- Corrected source never rewrites old evidence/version; it proposes V+1.
- Model A capital figure or broker/order content: reject.
- Failed transaction leaves neither version nor current-projection/revision update.

## Tests

- Complete equity and ETF/fund report versions validate.
- Decimal/provenance/formula and prose-only guards.
- Immutable V1 remains byte-identical after V2.
- CAS/concurrent writers create one next version.
- Exact retry is idempotent; conflicting hash errors.
- A future S04 context must match this exact report ID/hash.
- Stale/missing evidence blocks review readiness.
- Old/latest CLI rendering and safe Rich escaping.
- Migration apply/full-chain/constraints/compatibility and failure rollback.
- Model A randomization has no effect.

## Observability

Emit case/thesis/report/previous version IDs, payload hash, evidence/claim/section
counts, governance state, projection-update result, duration and stable error
code. Never log report bodies.

## Rollback

Stop version writers, retain additive immutable rows, deploy compatible prior code
against `theses.report_sections`, and mark suspect versions ineligible via an audit
record. Forward-fix; never edit/delete historical versions. James controls remote
migration/recovery.

## PR structure and model routing

- **PR1 product:** migration, validator/version service, lineage/immutability tests.
- **PR2 product:** current projection and CLI version list/show/diff.
- **PR3 evidence/ops if required:** migration preflight/apply/recovery evidence.
- 12h ceiling: two product + one evidence/ops, two lanes; cutoff hour 6, freeze 10.
- Opus/Ultra owns report/financial semantics, migration, version boundary, red-team.
- Fable-low owns frozen persistence/adapters/rendering/tests.
- Two failed repair cycles escalate with version/hash, DB trace, and both diffs.

## Definition of Done

- [ ] Every report state is reproducible by immutable version/hash.
- [ ] Current projection and historical versions agree.
- [ ] Figures/claims/scenarios have complete evidence/provenance.
- [ ] Proposal, thesis revision and evidence lineage resolve.
- [ ] Corrections create a new version, never a rewrite.
- [ ] Migration and forward recovery pass.
- [ ] Opus/Ultra red-team/full CI pass; combined worktree is clean.
