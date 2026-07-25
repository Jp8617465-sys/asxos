# S06 — Persistent report/thesis monitoring and revision proposals

**Initiative:** REL-01
**Phase:** persistent research product
**Window:** 12 hours
**Acceptance focus:** material-event durability, dedupe, alert latency, governed revision proposal
**Acceptance rows:** AC-23–26
**Depends on:** S03 immutable report version and S05 current review eligibility
**Unlocks:** current monitor watermark for S07 construction and S08 origins

## Outcome

Continuously compare each current governed report/thesis with newly available
point-in-time evidence. Persist material monitor events, surface them through the
existing alert path, measure event-to-alert latency in ASX trading-session time,
and produce a governed `ThesisProposalV1` revision candidate when warranted.
Monitoring never edits, approves, retires, or trades.

## Dependencies

- S03 current report version/claim/evidence/catalyst/falsifier identities and S05
  review/context/eligibility lineage.
- Existing `jobs/check_thesis_invalidations.py`, position checks, regulatory/news/
  financial-statement ingestion, `JobMonitor`, Healthchecks, Resend, and Render
  reconciliation.
- Existing `thesis_revisions`, invalidation conditions, discipline evaluator, and
  governance/agent-run proposal path.
- Trading-calendar/latest-complete-day convention.
- `docs/programs/investment-engine/operations-and-rollout.md`.

## In scope / out of scope

### In

- Material-event normalization, dedupe/supersession, persisted lifecycle, and source hash.
- Claim/catalyst/falsifier/discipline impact mapping to report versions.
- Deterministic materiality rule codes; AI may draft an explanation/revision only
  after an event is selected.
- Governed revision proposals routed through S01/S02 validation.
- Scheduled monitor job, deadman, user-visible alert, latency telemetry/report.

### Out

- Automatic report/thesis mutation, approval, position close, risk sizing, order
  staging, arbitrary web/news crawling, or a new UI.
- Treating absence of an event as proof the thesis is sound.
- Hiding duplicate delivery failures behind event dedupe.

## Existing code reuse

| Current component | Reuse decision |
|---|---|
| `jobs/check_thesis_invalidations.py` and AU/US position checks | Reuse loaders/check logic where current; consolidate outcomes into persistent monitor events. |
| regulatory/news/financial-statement stores | Reuse source timestamps/hashes and provider provenance; do not refetch from model knowledge. |
| `asxos/domain/theses/discipline.py` | Reuse deterministic revisit/trajectory/stop/target/data-sanity findings. |
| S03 report claims/catalysts/falsifiers | Watch explicit versioned objects, not unstructured whole-report similarity. |
| agent-run + `ThesisProposalV1` materializer | Revision proposals use the same governed path. |
| `JobMonitor`, Healthchecks, Resend, Render | Reuse hard-fail/idempotent job and delivery controls. |

## Contracts

`MonitorEventV1`:

```text
event_id, dedupe_key, source/type, symbol/thesis/report version,
published_at, available_at, observed_at, persisted_at, first_alerted_at,
source/content hashes, affected claim/catalyst/falsifier/discipline IDs,
materiality rule/severity, summary, state, supersedes/superseded_by,
revision_proposal_run_id?, acknowledgement/resolution audit
```

States are `OPEN`, `ALERTED`, `ACKNOWLEDGED`, `REVISION_PROPOSED`, `RESOLVED`,
or `SUPERSEDED`. Delivery retries do not create a second event. A corrected source
creates a linked superseding event.

Materiality selection is deterministic and versioned. AI receives only the event,
current report, linked evidence, and revision schema; it may draft a revision
proposal but cannot decide materiality, modify the report, or change governance.

Latency is accumulated exchange-open time from `published_at`/first observable time
to durable James-visible alert:

```text
P95(material_event_alert_latency_trading_sessions) < 1.0
```

Unknown publication time is excluded from percentile and reported as missing, never
assumed timely.

## Migration impact

An additive Opus/Ultra migration creates logical monitor-event, event-impact, alert-
delivery, and revision-proposal linkage records. Use unique dedupe/delivery keys,
immutable source hashes, explicit timestamps/states, and indexes for open events and
SLO windows. No destructive change to current invalidation fields.

Allocate from live migration truth, test full chain, inspect shared dependencies, and
sequence production: migration → code → job/Render → drift check. James applies.

## Implementation sequence

1. Inventory current sources/jobs, event timestamps, delivery paths, and blind spots.
2. Opus/Ultra freezes materiality taxonomy, event/dedupe/state/SLO/revision contracts,
   migration, and fail-closed behavior.
3. Create duplicate, correction, late, missing-time, prompt-injection, impacted, and
   irrelevant event fixtures.
4. Author/test migration and pure event-impact/latency functions.
5. Fable-low implements repository/service/job/delivery and revision adapter.
6. Deploy only after migration; verify JobMonitor/deadman/Render drift and a synthetic
   end-to-end alert.
7. Opus/Ultra reliability/security/capital-boundary red-team.

## Required outputs

- Persistent monitor/event/delivery schema and service.
- Scheduled idempotent job with hard upstream/freshness guards and deadman.
- Deterministic impact/materiality and ASX trading-latency functions.
- Governed revision-proposal flow using S02.
- Operator queries/dashboard for P50/P95/max/misses/sample.
- Incident/forward-recovery rehearsal.

## Negative and stale behavior

- Missing/stale required upstream: job/session fails loudly; no “all clear.”
- Unknown event time: missing cohort, not SLO pass.
- Duplicate source event: one event, idempotent delivery attempts.
- Correction: linked superseding event, original retained.
- Source prompt injection: inert data.
- Revision draft invalid/citation incomplete: reject; original report unchanged.
- Delivery fails after persistence: event remains open, deadman fails, idempotent retry.
- Unmapped material event: alert as unclassified/needs review, do not discard.

## Tests

- Event normalization/dedupe/correction/supersession.
- Trading-session latency across close, weekend, holiday, and missing timestamp.
- P50/P95/max/sample/miss computation with boundary samples.
- Claim/catalyst/falsifier impact mapping.
- Job rerun and delivery idempotency.
- Failure injection between event persistence, proposal, delivery, and completion.
- Stale upstream and absent source do not produce clean status.
- Revision proposal cannot write/approve report or capital state.
- Migration chain/constraints/compatibility.
- Model A/broker boundary remains green.

## Observability

Per run: code/schema/rule versions, source watermark/counts, events new/duplicate/
corrected/open, affected reports, revision proposals, deliveries/retries/failures,
latency distribution, missing timestamps, duration, and status. Deadman pings only
after durable event and delivery-state completion.

## Rollback

Pause only the new monitor writer/job, preserve events/delivery attempts, deploy prior
compatible code, and forward-fix. Existing thesis invalidation jobs remain only if
their writes/delivery do not duplicate the new job. Mark affected sessions dirty and
replay from source hashes after repair.

## PR structure and model routing

- **PR1 product:** migration + event/impact/revision services/tests.
- **PR2 product:** scheduled job/delivery/SLO instrumentation.
- **PR3 evidence/ops:** Render/Healthchecks/preflight/recovery evidence.
- 12h maximum two product + one ops, two disjoint lanes; cutoff 6, freeze 10.
- Opus/Ultra owns event/materiality/SLO/migration/capital semantics and red-team.
- Fable-low owns frozen job/adapters/rendering/tests.
- Two failed cycles escalate with event fixture, timestamps, logs, and both diffs.

## Definition of Done

- [ ] Material events are durable, deduped, linked, and auditable.
- [ ] Monitoring proposes revisions but never mutates/approves/trades.
- [ ] P95 latency calculation is honest about sample/missingness.
- [ ] Job/deadman/delivery failure is loud and replayable.
- [ ] Migration/Render/recovery evidence passes.
- [ ] Model A and broker boundaries remain intact.
- [ ] Opus/Ultra red-team/full CI pass; combined worktree is clean.
