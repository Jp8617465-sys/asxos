# S02 — ThesisProposal validation and governed materializer

**Initiative:** DISC-01
**Phase:** governed thesis intake (decision 3A)
**Window:** 12 hours
**Acceptance focus:** complete proposal validation, evidence promotion, atomic draft materialization
**Acceptance rows:** AC-06–10
**Depends on:** S01 registry/harness; existing migration 0040
**Unlocks:** immutable broker report in S03

## Outcome

Make the existing `ThesisProposal` path real. A permitted research agent can log a
versioned, fully cited proposal; the governed consumer can then atomically create a
`research` thesis with a preserved report-section draft projection, initial revision, evidence links, and
`draft → evidence_complete → pending_review` events. The source run is marked acted
on exactly once. The result is a governed draft, never an approval or capital action.

## Dependencies

- S01 `ProposalContract` registry and recursive citation walker.
- `docs/programs/investment-engine/contracts/{thesis-proposal-v1,proposal-registry}.md`
  and normative schema.
- Existing `ThesisProposal`, `ReportSection`, and `ReportFigure` in
  `asxos/domain/theses/schemas.py`.
- Stubbed `asxos/domain/theses/service.py::create_thesis_from_agent_run()`.
- Existing `agent_runs`, `agent_evidence`, `theses`, `thesis_revisions`,
  `thesis_evidence`, `governance_events`, migration 0040 `report_sections`,
  and transaction helpers.
- Existing `asx thesis open --from-agent-run` personal-use path.

## In scope / out of scope

### In

- Add the missing `instrument-thesis-drafter` agent contract and register it as the
  sole producer of `thesis-proposal-v1`. It does not exist on the baseline and must
  not be described as already allowed.
- Validate subject, flavour, Decimal strings, sections, figures, formulas,
  provenance, and every nested citation.
- Replace the documented hard-fail stub with the governed, idempotent transaction.
- Correct stale CLI help/docstrings that say no schema exists.
- Preview, success, rejection, retry, concurrency, and rollback tests.

### Out

- Human approval, active position creation, immutable report-version tables, blind review,
  persistent monitor records, portfolio proposals, risk/sizing, staged orders,
  brief/email, scheduler, or a new discovery agent.
- Letting an agent emit `james_input`, speculative-only basis, Model A inputs, or
  broker/order content.

## Existing code reuse

| Current component | Reuse decision |
|---|---|
| `ThesisProposal` / report models | Adopt and version; amend only if the normative schema exposes a proven gap. |
| `agent_run_service.log_agent_run()` | Reuse S01 registry validation and atomic evidence capture. |
| `agent_run_guards` | Lock an unacted `thesis` run and mark the single result. |
| `theses.service` human create/revision helpers | Reuse row mapping, validation, revision/audit conventions; do not duplicate SQL semantics. |
| `governance.transitions` | Emit governance event before each status update. |
| migration 0040 / `report_sections` | Preserve the proposal's initial section projection for compatibility; this is not `BrokerReportVersionV1`. S03 creates the canonical immutable report from the exact projection/revision/evidence hash. |
| `asx thesis` personal-use/escaped rendering | Reuse for the command; service owns writes. |

## Contracts

The registry accepts exactly the versioned `ThesisProposalV1` contract. Required
semantic checks include:

- uppercase subject equals proposal symbol and uses supported suffix/flavour;
- Decimal-safe entry/stop/target/figures; entry lower ≤ entry upper;
- unique ordered section kinds;
- cited/derived figure provenance and displayed formulas;
- `james_input` prohibited for agent output;
- the normative closed payload contains no `monitor_only` or Model A field.
  Baseline Pydantic-only monitor fields are rejected at the v1 adapter; existing
  historical values remain only in the checksummed read-only Model A archive;
- at least one valid non-speculative evidence citation, including nested citations;
- no Model A/signal/SHAP/allocator or broker/order field.

The materializer transaction:

1. locks the run `FOR UPDATE`;
2. validates unacted/type/version/producer/subject and proposal hash;
3. re-resolves the complete evidence union;
4. inserts one `research` thesis with governance status `draft`;
5. persists the governed thesis, initial revision, evidence links and compatibility
   report-section projection, clearly not an immutable report version;
6. copies cited snapshots/hashes/provenance into `thesis_evidence`;
7. marks cited evidence promoted;
8. emits `draft → evidence_complete → pending_review` in canonical order;
9. marks the run acted on with its thesis ID; and
10. commits all or none.

An exact retry returns the existing thesis with `created=false`. An acted-on run
whose resulting object is absent/different raises `AgentRunIntegrityError`.

## Migration impact

None planned. Migration 0040 and governance/evidence tables are reused. If a required
unique constraint is genuinely absent, stop and assign an additive migration through
the migration plan; never implement race-prone application-only uniqueness.

## Implementation sequence

1. Verify the actual existing schema/model/stub and live migration 0040 shape.
2. Opus/Ultra freezes the exact sole producer
   `instrument-thesis-drafter`, its new agent file, proposal adapter, transition
   order, transaction, idempotency, and evidence-promotion semantics.
3. Write valid/invalid proposal and failure-injection tests.
4. Fable-low registers the contract and implements the frozen service/CLI adapters.
5. Exercise normal, exact retry, conflict, two-writer, and failure-after-each-write
   paths on Postgres-shaped tests.
6. Verify human approval remains a separate existing governance operation.
7. Opus/Ultra architecture/financial-provenance/security red-team.

## Required outputs

- New `instrument-thesis-drafter` contract plus registered, versioned sole
  thesis-proposal producer/consumer.
- Working `create_thesis_from_agent_run()` and corrected CLI help.
- Provenance chain from agent run/evidence to thesis/revision/governance and the
  exact S03 report input projection.
- Valid equity and ETF/fund fixtures plus all stable failure-code fixtures.
- Atomicity/idempotency/concurrency evidence.

## Negative and stale behavior

- Unknown version/producer, subject mismatch, malformed/absent/speculative citation,
  agent `james_input`, invalid Decimal/report shape, Model A, or broker field:
  reject before persistence or roll back the whole transaction.
- Evidence whose snapshot/hash cannot replay: reject.
- Already acted on with matching result: idempotent return; mismatched/missing result:
  integrity error.
- Any transaction step failure leaves no thesis, evidence promotion, transition, or
  acted-on flip.
- Output remains `pending_review`; no inferred active/approved state.

## Tests

- Registry logging accepts complete `ThesisProposalV1`.
- Recursive citations resolve in proposal, sections, and figures.
- All named normative failure codes are pinned.
- Exact retry returns same thesis and no duplicate revision/event.
- Concurrent consumers produce one result.
- Failure injection at every write rolls back.
- Governance events precede status updates.
- Report Decimal/formula/provenance round-trip is exact.
- CLI personal-use gate and escaped preview remain intact.
- Model A randomization/removal leaves materialized result unchanged.
- No capital, portfolio, order, approval, or broker state is written.

## Observability

Structured fields: run/proposal/version/hash, subject, evidence/section/figure counts,
result thesis/revision IDs, final governance status, idempotent replay, duration, and
stable error code. Do not log private proposal bodies.

## Rollback

Deploy prior compatible code to disable the consumer. Valid created drafts remain
auditable and may be rejected/retired through governance; never delete them. A faulty
materialization is corrected by an append-only revision/event. No schema rollback.

## PR structure and model routing

- **PR1 product:** registry entry, complete validation/citation path, service,
  transaction/idempotency tests.
- **PR2 product only if separation helps review:** CLI/help/preview adapter and
  rendering tests.
- Maximum two product PRs, two disjoint lanes; no scope after hour 6; freeze hour 10.
- Opus/Ultra owns proposal/provenance/transaction semantics and red-team.
- Fable-low implements the frozen service, adapter, fixtures, and tests.
- Two failed repair cycles escalate with run fixture, DB trace, and both diffs.

## Definition of Done

- [ ] The stale “no ThesisProposal schema” stub and help are gone.
- [ ] A valid run creates exactly one governed pending-review draft.
- [ ] Every nested citation is verified and promoted with replayable provenance.
- [ ] All failure, concurrency, and retry paths are atomic.
- [ ] Human approval and all capital states remain separate.
- [ ] No migration was guessed.
- [ ] Opus/Ultra red-team and full CI pass; combined worktree is clean.
