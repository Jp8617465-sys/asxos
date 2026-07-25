# S05 — Blind multi-role review and deterministic eligibility

**Initiative:** EVAL-01
**Phase:** evidence-controlled review
**Window:** 12 hours
**Acceptance focus:** immutable blind assessments, findings, deterministic synthesis
**Acceptance rows:** AC-19–22
**Depends on:** S04 frozen `ReviewContextV1` over one S03 report
**Unlocks:** persistent monitoring in S06 and construction eligibility in S07

## Outcome

Persist one blind review cycle over one immutable context. Five independent roles
submit immutable first passes without seeing peers. Stable findings remain visible.
A deterministic `ReviewEligibilityDecisionV1` synthesizer—not an LLM vote—returns
`BLOCKED`, `FAIL`, or `PAPER_ELIGIBLE` from completeness, freshness and open
severities. The James-only `/pm-review` user-facing command is reintroduced as a
thin v2 client of this new service only when the separately approved M-A2/M-A3
retirement lane has closed and the cutover is explicitly approved. Otherwise
the independent service remains available only through its hidden v2 entry
point and `/pm-review` retains its current quarantined authority state. In
either case v2 has no import, query, fallback, or semantic compatibility path to
the Model A implementation.

## Dependencies

- `docs/programs/investment-engine/contracts/{review-context-v1,reviewer-assessment-v1,review-eligibility-v1}.md`
  and normative schemas.
- S04 controlled context loader/hash and role adapters.
- Existing governance/audit and single-user/personal-use conventions.
- Live migration ledger and `asxos/api/main.py::REQUIRED_MIGRATIONS`.
- Existing job/service transaction and Decimal/JSONB conventions.

## In scope / out of scope

### In

- Additive review-cycle, context-snapshot, assessment, finding, and decision persistence.
- Exactly five first-pass roles: evidence/claims, valuation/scenarios,
  thesis adversary, portfolio risk fit, implementation/liquidity/tax.
- Blind submission, explicit abstention record/replacement, role/rubric versions,
  context/report-hash enforcement.
- Deterministic completeness/severity/eligibility synthesis.
- A hidden v2 command that can open, status, show, and close the governed cycle
  only through the new review service and immutable contracts; aliasing the
  `/pm-review` name is a conditional cutover gated on closed M-A2/M-A3 evidence.
- Read-only CLI for cycle open/status/show and explicit James disposition where
  governance requires it.

### Out

- Peer debate/chat, majority scoring, averaged confidence, automatic finding
  downgrade, report-version edits, monitoring, shadow book, risk sizing, staged
  orders, or brief release.
- Treating `PAPER_ELIGIBLE` as shadow activation, advice readiness, or capital approval.
- Letting reviewers query beyond the S04 context.
- Any Model A input or broker account/credential/route/action; both boundaries
  remain structural and fail closed.

## Existing code reuse

| Current component | Reuse decision |
|---|---|
| `ReviewContextV1` | Persist exact canonical bytes/hash; never reconstruct at review time. |
| governance transitions/events | Reuse audit ordering and actor/reason conventions. |
| `agent_runs` patterns | Reuse run/model/prompt metadata where appropriate, but keep review records first-class. |
| Typer/Rich personal-use conventions | Reuse for attended cycle operations and safe rendering. |
| `JobMonitor` transaction/idempotency patterns | Reuse service patterns; no scheduled job yet. |

## Contracts

One `review_cycle` identifies thesis/report revision, context hash, required role set,
rubric bundle version, status, opened/closed times, and deterministic decision.

`ReviewerAssessmentV1` requires:

```text
cycle_id, context_hash, role, reviewer model/prompt version,
verdict={PASS,CHALLENGE,FAIL,ABSTAIN}, confidence (descriptive only),
findings[], submitted_at, assessment_hash
```

The cycle freezes one James-approved role bundle containing exact
agent/model/prompt/rubric IDs, versions, and content hashes. Runtime verification
resolves that bundle from immutable stored bytes; self-declared identity copies
cannot satisfy the gate. In v1 the report candidate digest equals the canonical
broker-report root. A future blinded transformation requires its own immutable,
hash-resolved artifact and cannot be introduced as an unbound digest.

Each finding has stable code, severity `{info,low,medium,high,critical}`, claim/evidence
references, description, required action, uncertainty, state, and resolution link.
First passes are immutable and hidden from peer roles until all required roles
submit. An abstention is retained but does not satisfy a mandatory role; a valid
replacement assessment must be linked.

Deterministic synthesis:

- missing/stale/invalid context → `BLOCKED`;
- missing mandatory role or abstention without a replacement → `BLOCKED`;
- any unresolved critical finding → `FAIL`;
- any unresolved high finding → cannot become `PAPER_ELIGIBLE`;
- all hard gates pass and no critical/high open finding → `PAPER_ELIGIBLE`;
- dissent, abstentions, replacement links, medium/low findings, accepted risks, and James decisions remain
  visible and never disappear from history.

## Migration impact

An Opus/Ultra-designed additive migration creates logical tables equivalent to:

```text
investment_review_cycles
investment_review_contexts
investment_reviewer_assessments
investment_review_findings
investment_review_decisions
```

Names/numbers are allocated only after re-reading `migrations/`, the live Supabase
ledger, and `REQUIRED_MIGRATIONS`; do not assume `0042`. Constraints enforce unique
role per cycle, immutable hashes, explicit states, and foreign keys. No `user_id`,
auth/RLS, floats, destructive rewrite, or production apply without James.

## Implementation sequence

1. Verify live schema/count/dependencies and write migration preflight/forward recovery.
2. Opus/Ultra freezes table semantics, blind-visibility boundary, role/rubric versions,
   severities, synthesis truth table, and lifecycle meaning.
3. Add full truth-table, visibility, idempotency, and migration tests.
4. Author/apply migration only in a safe integration target.
5. Fable-low implements repositories/services/CLI against frozen contracts.
6. Exercise simultaneous submissions, abstention, duplicate/conflict, stale context,
   findings resolution, and failure injection.
7. Opus/Ultra migration, financial/tax interpretation, privacy, and adversarial review.

## Required outputs

- Additive migration with comments/constraints/indexes and recovery runbook.
- Blind review-cycle service and attended CLI.
- Hidden v2 snapshot/help tests, plus conditional `/pm-review` cutover tests
  proving an existing legacy tombstone is replaced only after closed M-A2/M-A3
  evidence and never by a compatibility fallback.
- Five role fixtures plus complete deterministic truth table.
- Durable chain: thesis/report → context → assessments → findings → decision.
- S06/S07 input contract naming exactly which report/context/decision lineage is
  eligible for monitoring and deterministic construction.

## Negative and stale behavior

- Context hash/rubric mismatch: reject submission.
- Duplicate same role/same hash: idempotent return; different content: conflict.
- Peer output requested before blind close: access denied.
- Missing/late role or unresolved mandatory abstention: `BLOCKED`; no synthetic pass.
- Stale/invalid context: cycle blocked and must be reopened with a new context.
- Reviewer-produced `eligible` field is ignored/rejected; service recomputes.
- Critical/high finding cannot be hidden, averaged away, or silently downgraded.
- Dangling claim/evidence IDs, forged reviewer bundles, unbound candidate hashes,
  cross-case eligibility replay, and producer-labelled freshness all fail closed.
- Accepted-risk/resolution state resolves an append-only James/governance record;
  a copied actor, timestamp, type, or hash cannot clear a finding.
- Migration mismatch/dependency uncertainty: no apply and sprint `NOT READY`.

## Tests

- Full synthesis truth table, including each missing/abstain/severity combination.
- Blind first-pass access boundary.
- Unique role, immutable assessment, idempotent retry, and conflict paths.
- Context/rubric/version/hash mismatch.
- Stable finding references and append-only resolution history.
- Transaction failure leaves no partial close/decision.
- Model A fields remain impossible through context and assessment schemas.
- Static/runtime dependency tests prove `/pm-review` v2 cannot import, query, or
  fall back to the archived legacy agents, signals, SHAP, or allocator.
- Migration applies from clean chain; invalid rows/constraints fail.
- Compatibility with prior code during additive rollout.

## Observability

Emit cycle/context/report IDs/hashes, required/submitted/abstained role counts,
finding counts by severity/state, deterministic result/reasons, duration, code/schema/
rubric versions, and error code. Never log assessment bodies before blind close.

## Rollback

Stop new cycle writers, retain additive tables/audit rows, deploy compatible prior
code, and forward-fix. Mark suspect cycles `BLOCKED`; do not delete or rewrite
assessments. Remote apply and corrective migration require James.

## PR structure and model routing

- **PR1 product:** migration + persistence/services + integration tests.
- **PR2 product:** blind orchestration/CLI + truth-table tests.
- **PR3 evidence/ops only if needed:** preflight/apply/recovery evidence.
- Hard 12h ceiling: two product plus one evidence/ops, two lanes; no scope after
  hour 6; freeze hour 10.
- Opus/Ultra owns migration, review/eligibility/financial semantics, blind boundary,
  and red-team. Fable-low implements frozen repositories/adapters/tests.
- Two failed repair cycles escalate with cycle fixture, DB trace, and both diffs.

## Definition of Done

- [ ] Five blind roles operate on one frozen report/context.
- [ ] First passes are immutable and hidden until all mandatory roles complete.
- [ ] Deterministic truth table—not reviewer vote—controls eligibility.
- [ ] Critical/high findings cannot disappear.
- [ ] Additive migration/recovery evidence passes.
- [ ] `PAPER_ELIGIBLE` grants no later lifecycle permission.
- [ ] The hidden v2 client is a thin client of the new service and has zero
      legacy Model A dependencies; the `/pm-review` alias is required only when
      the approved M-A2/M-A3 cutover gate has closed.
- [ ] Opus/Ultra red-team and full CI pass; combined worktree is clean.
