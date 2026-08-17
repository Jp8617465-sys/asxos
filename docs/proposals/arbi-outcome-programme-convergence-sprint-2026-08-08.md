# Proposal — Arbi outcome-programme convergence sprint

**Status:** proposed work order; not canonical programme state or execution authority\
**Prepared:** 2026-08-08 (Australia/Brisbane)\
**Observed repository base:** `main@1b471b60cdaa176692cc5f987e8399acfdab03d9` at 2026-08-08 16:23 AEST\
**Outcome owner:** Arbi\
**Governor:** James\
**Delivery ceiling:** documentation, read-only verification, and ratification packet only\
**Authority ceiling:** invoked `I2` docs work plus `P0` read-only portfolio state; no `I3`–`I6`, recommendation, order, broker, or capital action

This work order brings the current ASXOS product, the investment-engine dossier, the
Arbi future-state proposal, and the August release-recovery work into one decision.
It deliberately does **not** create another roadmap or authorise S01 implementation.

---

## 1. Executive decision

ASXOS should converge around one product spine:

```text
governed investment question
  -> sourced thesis / broker report / falsifiers
  -> independent challenge and eligibility
  -> monitoring and revision events
  -> immutable investment truth (the proposed `DecisionView` logical role)
  -> CLI + brief (+ later cockpit / Ask Arbi) renderers
  -> exact delivery receipt
  -> separate James disposition
  -> separate paper / actual outcome learning
  -> Arbi continue | rework | pause | retire decision
```

The investment-engine dossier is valuable source material for this spine, but it is not
safe to merge or declare canonical wholesale. Its current remote PR, its expanded local
branch, the future-state branch, and current `main` describe different baselines and, in
some places, different authority and financial semantics.

The immediate sprint is therefore **D0 — Converge and Ratify**. D0 produces one
current-main adoption packet, an epic-level acceptance spine, and exactly one bounded first
work order: governed thesis intake/materialisation. It performs no product implementation.

D0 has three explicit result states:

- `NOT_READY` — a mandatory evidence, semantics, authority, or review gate is open;
- `PACKET_READY` — every D0 artifact is complete and challenged at one exact digest, but James
  has not ratified it; and
- `RATIFIED` — James has approved that exact digest and the canonical docs-only reduction patch
  has landed through James's normal merge authority.

No programme adoption or implementation mission becomes eligible at `PACKET_READY`. The actual
rail is:

```text
current-release operating proof
  -> D0 PACKET_READY
  -> James RATIFIED exact digest
  -> chosen authority mechanism implemented or repaired and independently accepted
     (or James records one explicit bounded exception)
  -> exactly one approved mission is uniquely consumed
  -> thesis-intake increment 1
```

---

## 2. Current truth and why D0 comes first

### Repository and delivery state observed on 2026-08-08

| Surface | Observed state | Consequence |
|---|---|---|
| `main` | `1b471b6...` after PR #75 merged at 16:22 AEST | This is the observed repository base, not proof of the production release. Re-freeze relevant identities before implementation. |
| PR #70 | open draft, remote head `b9c2f6f...`; GitHub mergeability returned `UNKNOWN` at 16:24 AEST | Original dossier is source material, not merge-ready programme truth. |
| Reviewed repair branch | `claude/investment-engine-dossier-review-ozg1ny@2257d12...` | Distinct R0 repair/review provenance; do not regress its artifact-ID, comparison, honesty, capacity, or AMBER-review fixes. |
| Expanded dossier / future-state branches | local `6cfaf15...` and `33eb00e...` | Much larger than PR #70 and includes later control-plane proposals; neither may silently substitute for the reviewed PR or repair branch. |
| Authority Gate0 candidate | local `agent/arbi-authority-gate0@eeed240...`, based before current `main` | Safe deny-only controls may be extraction candidates; its risk-tier review-policy cutover remains provisional and it grants no authority. Reconcile it in D0-05, not by branch merge. |
| PR #73 | open draft, head `2a456ce...`; checks green but mergeability `UNKNOWN` at 16:24 AEST | Must be dispositioned against already-merged news-state work; do not carry a duplicate repair lane. |
| PR #75 | merged, source head `3544629...`; required checks green | Its handoff/source map is now on `main`; D0 must reconcile its still-pre-merge wording and `cda6b1b...` baseline. |
| Daily brief canary | one successful manual run at `a4fb797...` | Useful operational evidence, but not exact-current-head proof and not a delivery/content receipt. |
| PR #76 / scheduler exit | code merged; current-head scheduled daily/weekly/backup proof not observed in this review | Gate 0 remains outcome-open until scheduler ownership, delivery, backup/restore, and no-duplicate execution are proven. |

### Conflicts D0 must settle

1. The original dossier labels much of the programme accepted or locked; later review and
   the 2026-08-08 handoff classify it as conditional source material and explicitly reject
   wholesale adoption.
2. The dossier defaults to a B00/external authority-plane prerequisite; the later handoff
   requires proof that the smallest in-repository contract is insufficient before a new
   control plane is built.
3. The dossier baseline predates the GitHub Actions scheduler transition, release recovery,
   and current `main`.
4. Some dossier fixtures retain stale financial or product semantics, including a fixed
   `365`-day holding-period representation and `ADVICE_READY` wording.
5. Current code has a `ThesisProposal` schema, while the agent-run registry, materialiser,
   CLI prose, tests, and roadmap still contain "no ThesisProposal schema" assumptions.
6. `brief_runs` stores rendered HTML and operational metadata, but does not yet prove one
   immutable decision truth, exact cross-surface identity, actual delivery, or James's
   disposition.
7. Dossier proposal invalidation items and live thesis invalidation rows use incompatible
   shapes; the retained contract must round-trip through current domain parsing before any
   materialiser can be admitted.
8. Current thesis domain mappings omit some source-run/revision provenance and the proposal
   registry does not validate every nested report-section/figure citation. A root citation
   list is not complete lineage.
9. The 2026-08-08 handoff is now merged, but its embedded status, baseline, and completion
   condition still describe PR #75 as branch-only. D0 must preserve its substantive boundary
   while correcting that provenance; a merged stale sentence is not current operational truth.

These are not reasons to discard the dossier. They are the reason to extract its good
contracts through a controlled current-main adoption packet.

---

## 3. How the external repository review changes the dossier

The Prime Agent and finance-repository review mostly **validates existing dossier ideas**.
It does not justify new platforms or another artifact family.

| Reviewed pattern | Dossier decision | Treatment in ASXOS |
|---|---|---|
| Durable goal, continuation, checkpoint, and explicit completion | Existing `mission-template.yaml`, mission close record, and `mission-outcome-evidence-v1` already cover the core lifecycle | **Keep; gap-check only.** Consider elapsed time, continuation count, bounded token/cost usage, and next-safe-action later. Do not add another mission schema in D0. |
| Evidence pack and reproducible report | Existing lineage, broker-report, review-context, and shared-view work provide the right direction | **Keep and narrow to one thesis.** Map those contracts onto the proposed investment-decision view role before considering any new runtime type; the programme dossier specifies how the role is built and proved. |
| Deterministic replay, evidence cutoff, fill/cost/FX/benchmark versions | Existing evaluator config/origin, paper intent/order/fill, ledger/NAV, and episode-outcome contracts are substantially stronger than the reviewed examples | **Keep.** Reconcile their semantics and implement only when the one-thesis programme reaches its separately authorised paper-evaluation increment. |
| Decision quality separate from P&L | `james-brief-disposition-v1`, thesis revisions/invalidation, and later outcome learning already contain most of the needed separation | **Adapt, do not duplicate.** Extend or project these contracts after a field-gap test; do not create a second generic journal. |
| Cognitive-bias challenge | The S05 thesis-adversary rubric already checks base-rate bias and disconfirming events | **Keep advisory.** A bias label or question cannot control eligibility, sizing, or approval. Missing mandatory evidence may block only through an existing deterministic evidence-quality gate. |
| Portfolio research libraries such as skfolio | Useful only as an offline comparison once a deterministic in-house policy exists | **Park.** No runtime dependency or current sprint work. |
| `awesome-ai-in-finance` and similar catalogues | Useful discovery radar, not validated product architecture | **Park as research input.** Admit an item only against a named ASXOS consumer, licence check, reproducible test, and measurable gap; do not bulk-ingest the catalogue or add dependencies in D0. |
| Persistent executable agent runtime | Conflicts with current secret, authority, and single-user risk boundaries | **Reject for now.** No persistent Python kernel, executable third-party skills, broker MCP, or autonomous daemon. |

### Programme dossier versus proposed runtime roles

The project needs two clearly different concepts:

- **Programme dossier:** implementation contracts, sprint acceptance, schemas, fixtures,
  traceability, operations, and delivery evidence. It tells Arbi, James, implementers, and
  reviewers how the product is allowed to be built and proved.
- **Investment-decision view role:** the immutable, evidence-linked investment truth presented
  to James for one case/as-of. `DecisionView` is a proposed target name for that logical role,
  not a current-main schema or permission to create one.

The same rule applies to the proposed logical roles `SurfaceRender`, `DeliveryReceipt`,
`Disposition`, `StagedOrderSet`, and outcome record. D0 must first map them field-by-field onto
the existing broker-report, review-context, shared-view, `brief_runs`,
`james-brief-disposition-v1`, mission-outcome, thesis-revision, and paper-evaluator contracts.
Only a demonstrated consumer requirement that none of those contracts can express may justify a
new type. The names in this proposal do not predetermine separate services or tables.

If D0 admits these roles, they share a stable proposed `investment_case_id` correlation key and
resolve one another through exact typed identities and hashes; none is a giant mutable dossier
row. D0-06 must freeze identifier creation and cardinality, canonical serialization, schema
version, hash algorithm, evidence-cutoff semantics, immutable predecessor links, delivery-receipt
statuses, and what constitutes observed delivery.

The admitted investment-decision view contains only prior, content-addressed facts and
references. A later James disposition points back to the exact view and render bytes; it never
rewrites the view. A still-later outcome record points to both. This prevents a circular hash and
prevents hindsight from changing what James actually saw.

The existing `decisions` table and journal CLI are legacy inputs/adapters, not automatically the
future investment-decision view. Their useful concepts must be mapped to admitted disposition and
thesis-revision fields. The current automatic attachment of the latest Model A signal must not
survive into the model-independent investment-case path.

---

## 4. Sprint D0 — Converge and Ratify

### Problem statement

ASXOS has strong product code and strong candidate contracts, but its current truth is split
across `main`, two relevant open draft PRs, several clean local worktrees, an oversized dossier,
a future-state proposal, a distinct reviewed repair branch, and a newly merged closeout whose
embedded pre-merge status is now stale. Starting S01 or building a cockpit now would force
implementation to choose among contradictory baselines and could turn a source document into
accidental authority.

### Sprint goal

Produce one current-main, reviewable adoption packet that lets James decide exactly what
ASXOS will build next, which dossier assets it will reuse, which semantics require repair,
and what observable outcome will close the first governed-thesis increment and later epic.

### User stories

- As James, I want one concise programme decision so I can approve the next product outcome
  and bounded work order without approving 324 files or a new authority platform implicitly.
- As Arbi, I want every retained capability to trace upward to one investment outcome and
  downward to a consumer, canary, disposition, and learning record.
- As an implementer, I want one exact current-main contract and acceptance set so I do not
  infer financial or authority semantics while coding.
- As a reviewer, I want every retained dossier artifact classified with provenance and a
  reason so obsolete contracts cannot re-enter through a later cherry-pick.

### Non-goals

- No S01–S12 product implementation.
- No migration, production write, deploy, scheduler change, or Render retirement.
- No merge or close action on PR #70 or #73; D0 prepares exact dispositions for James. PR #75
  is already merged and is provenance to reconcile, not open work.
- No authority-plane App, receipt broker, cockpit, Ask Arbi, persistent daemon, or autonomy
  promotion.
- No Model A revival, allocator reuse, trade recommendation, staged real order, or broker
  integration.
- No new generic dossier, journal, replay, mission, or feedback schema unless the reuse map
  proves an unfillable field gap.

### Entry gates

D0 read-only inventory may start immediately. D0 may not call the programme ready for
implementation until all of the following are evidenced:

- the current production/release identity is frozen;
- the daily chain has run at that release and the exact delivered brief is observed;
- valid items, valid empty, degraded/unmatched, upstream error, and malformed-payload states
  cannot collapse into the same green result;
- scheduled ownership is explicit and there is no duplicate GitHub/Render execution;
- the handoff's incorrect 13:30 UTC US-position timing is corrected or explicitly re-decided,
  and exact-release US-position, pipeline-health, thesis-invalidation, and post-brief scoring
  receipts are observed;
- the first required weekly chain is green;
- backup output is produced and independently restorable; and
- Render retirement, if performed, is separately authorised and evidenced; otherwise the
  retained Render state and single scheduler owner are explicit.

An unmet entry gate is a typed `NOT_READY` result, not permission to soften the gate.

Closing these operating gates makes D0 eligible for ratification; it does not create mission
authority. The selected in-repo or external authority mechanism must then be implemented or
repaired and independently accepted, or James must record a narrow, time-bounded exception,
before increment 1 can be approved and uniquely consumed.

### Deliverables and acceptance criteria

| ID | Deliverable | Effort | Acceptance criteria |
|---|---|---:|---|
| D0-01 | **Exact current-truth packet** | S | Records `observed_runtime_base_sha`, every source PR/branch SHA (including `2257d12...`), `packet_commit_sha`, and later `implementation_base_sha` separately; captures changed-file counts, CI, migrations, scheduler inventory, workflow runs, production release identity, data/brief freshness, and unavailable probes. Every claim is observed, inferred, or unverified with timestamp. A docs-only packet commit does not invalidate runtime evidence; a relevant source ref, implementation base, runtime path, deployment, or live state change does. |
| D0-02 | **Open-work disposition packet** | S | Gives open PR #70 and #73 exactly one recommendation—merge, extract, close as superseded, or hold—with file-level rationale, conflicts, prerequisites, and James-owned action; records merged PR #75 as current provenance. For PR #70 it must choose one coherent route: **(a)** reconcile and propose it for merge, or **(b)** name a successor bootstrap PR and atomically amend every contract, schema, validator, fixture, and test that hardcodes “merged PR #70.” “Archive PR #70” plus unchanged B00/S01 gates is invalid. D0 performs none of the external actions. |
| D0-03 | **Dossier source manifest and extraction register** | M | Freezes a machine-readable denominator of exact commit/path pairs across PR #70, repair branch `2257d12...`, expanded dossier `6cfaf15...`, and future-state `33eb00e...`, then classifies each path `KEEP`, `ADAPT`, `PARK`, or `RETIRE`. The validator proves `manifest_path_count == KEEP + ADAPT + PARK + RETIRE`, every admitted path has destination + consumer + acceptance IDs, there are no destination collisions, and no unclassified file is admitted by branch or directory merge. D0 adds no new validator tooling; it specifies a deterministic check for the later docs patch or names an existing command. |
| D0-04 | **Product and financial-semantics correction sheet** | M | Resolves or explicitly blocks the calendar CGT holding-period representation, accounting/tax rounding alignment, `ADVICE_READY` conflict, benchmark identity/licence, sizing policy defaults, Model A exclusions, paper-vs-actual outcome labels, invalidation-condition shape, source-run provenance, nested citation resolution, and the independent `agent_evidence` → `thesis_evidence` ID namespaces. It freezes typed references, a persisted source→promoted mapping, or an explicit dual-reference rule; hash matching alone is not identity. Each result cites the governing current code/spec and exact dossier contracts/fixtures/tests affected. |
| D0-05 | **Authority and harness decision sheet** | M | Compares the smallest in-repo mission/receipt contract with the proposed external B00 plane against current harness evidence. It names the threat/control gap, consumer, operating cost, rollback, bypass/invocation findings, implementation work, and independent canary required for acceptance. Its default is `NOT_READY`: neither architecture is accepted until evidenced. It may recommend one route, but cannot grant it. |
| D0-06 | **One-thesis epic spine plus one intake work order** | M | Freezes the full programme outcome from question through later observation, but emits exactly one implementable work order: one permitted producer → validated `ThesisProposal` and recursive citation union → one explicit `research`/`draft` thesis → exactly-once evidence promotion + initial revision → ordered `evidence_complete`/`pending_review` transitions → deterministic intake receipt. It maps every proposed runtime role and proposal field onto current contracts before proposing a new type; freezes evidence-ID mapping, identifiers, serialization, hashes, cutoff, predecessor links, receipt states, baseline, target, canary, rollback, kill condition, non-goals, and authority ceiling; and defines the receipt as a projection over existing run/thesis/revision/evidence/governance/mission identities unless reuse is proven insufficient. Later report, challenge, delivery, disposition, and learning increments remain independently gated. |
| D0-07 | **Canonical programme reduction patch candidate** | S | Supplies the exact docs-only candidate that amends one existing canonical roadmap/queue, explicitly retains or supersedes the macro-brief queue, marks superseded sources non-authoritative, links the admitted provenance, selects exactly one next work order, and creates no second roadmap. It names validation, PR ceiling, rollback, and James decisions. The D0 programme surface is capped at one amended queue plus one linked ratification record, with zero dossier directories or source files copied wholesale. Landing remains a James-owned merge. |
| D0-08 | **Independent exact-packet challenge** | S | A fresh reviewer checks the final digest for source-of-truth precedence, financial semantics, Model A isolation, personal-use boundary, authority readiness, missing consumers, over-engineering, net programme reduction, and observable acceptance. All critical/high findings are resolved or D0 is `NOT_READY`. Passing review produces `PACKET_READY`, never `RATIFIED`. |

### Required dossier extraction register groups

At minimum D0-03 must classify these groups separately:

1. programme overview, current-state, decisions, architecture, traceability, acceptance,
   operations, migration plan, and roadmap;
2. S01–S12 sprint specifications;
3. mission, bootstrap, approval, close, and outcome-evidence contracts;
4. thesis, report, review, monitor, and eligibility contracts;
5. portfolio policy, risk, sizing, staging, and classification contracts;
6. evaluator, origin, intent, order, fill, ledger, NAV, benchmark, tax, and outcome
   contracts;
7. James brief/disposition and shared-view semantics;
8. schemas, fixtures, validators, and tests paired with each retained contract;
9. Arbi/Guilfoyle agents, commands, skills, hooks, permissions, and CI changes; and
10. future-state cockpit, Ask Arbi, risk-router, persistent autonomy, and broader-wealth
    candidates.

### Wave structure

```text
Wave A — may run in parallel, read-only
  A1 current runtime / scheduler / delivery proof
  A2 branch and PR collision map
  A3 dossier contract and finance-semantic audit
  A4 current product/code reuse map

Wave B — after Wave A truth is frozen
  B1 extraction register
  B2 one-thesis epic spine + one intake work order
  B3 authority/harness decision sheet

Wave C — after B1–B3 agree
  C1 canonical reduction patch candidate
  C2 independent challenge
  C3 PACKET_READY exact digest

Wave D — James only
  D1 ratify or reject the exact digest
  D2 merge the docs-only reduction patch if ratified
  D3 record RATIFIED only after main readback
```

The waves may share evidence but may not share conclusions by copying. Wave C uses exact
digests of the Wave B artifacts it reviews.

### Success measures

#### Sprint success threshold

- 100% of the frozen source-manifest paths classified, with the count invariant passing.
- 100% of artifacts admitted for the intake work order name a real consumer, acceptance IDs,
  and an observable canary.
- Zero unresolved contradictions in the chosen tax, accounting, benchmark, sizing,
  Model A, advice-label, and authority semantics. An explicit `NOT_READY` is an honest terminal
  result, not sprint success.
- Zero product/runtime changes and zero implicit authority increases in D0.
- One James decision packet containing only the decisions that cannot be derived from code,
  tests, live state, or existing policy.
- One intake-only work order small enough for bounded, reversible implementation.
- One candidate that amends the canonical queue plus at most one linked ratification record;
  zero copied dossier directories or wholesale source files; all superseded programme sources
  clearly marked.
- `PACKET_READY` and `RATIFIED` are reported separately, each against its exact digest/commit.

### Definition of Done

D0 is `PACKET_READY` only when:

- operational Gate 0 evidence is closed; otherwise D0 is `NOT_READY`, not `PACKET_READY`;
- every deliverable D0-01 through D0-08 exists and cross-references the same frozen identities;
- the machine-readable manifest count invariant and destination-collision check pass;
- the dossier/future-state/closeout conflicts have one explicit recommendation each;
- PR #70 has one internally consistent merge-or-successor route, including every hardcoded
  bootstrap dependency;
- the epic acceptance spine and intake-only work order have measurable baseline, target,
  consumer, canary, rollback, and kill conditions;
- independent review ran against the final packet digest;
- James has a short ratification sheet and no decision is hidden inside implementation prose;
- no merge, deployment, migration, production write, authority grant, or capital action is
  represented as completed; and
- the candidate amends one existing canonical queue, marks superseded sources, selects exactly
  one next work order, and adds no parallel roadmap or wholesale dossier content.

D0 becomes `RATIFIED` only when James approves the exact `PACKET_READY` digest, the associated
docs-only reduction patch lands through James's authority, and the `main` readback matches the
approved identities. Ratification still does not authorise implementation. The authority route
must next be implemented or repaired and independently accepted (or explicitly excepted by
James), followed by unique approval and consumption of the intake mission.

### Kill conditions

Stop D0 and return `NOT_READY` if:

- live scheduler or delivery state cannot be distinguished from repository state;
- the proposed programme epic requires a second financial truth store;
- the extraction grows into a directory-level dossier merge;
- an external authority service is proposed without an evidenced in-repo insufficiency;
- retained contracts require unresolved tax/accounting/benchmark semantics;
- the packet, investment-decision view, or render can be changed after James sees its recorded
  digest;
- disposition or usefulness can feed investment scoring, eligibility, sizing, or staging;
- Model A reaches the capital-evidence path; or
- two repair attempts fail the same acceptance condition.

---

## 5. One-thesis programme epic after D0 — not yet authorised

### Outcome

One James-selected, non-Model-A investment thesis eventually travels from governed evidence to
an immutable investment-decision view James actually receives, challenges, dispositions, and
later evaluates. This is the **programme epic outcome**, not one sprint or one implementation
mission.

The target is not “wire `create_thesis_from_agent_run`” or “build a dossier.” The target is
an observed decision practice that can answer:

- What was known at the time?
- What was the thesis, plan, horizon, invalidation, and uncertainty?
- What challenged the thesis?
- What exactly did James see?
- What did James decide and why?
- Was the process followed?
- What happened later, separately from whether the decision process was sound?

### Exactly one candidate first work order: governed intake

```text
one permitted producer
  -> one D0-admitted and repaired ThesisProposal
  -> one recursively validated citation union
  -> one thesis inserted with status='research'
     and governance_status='draft'
  -> exactly-once evidence promotion with source-to-target identity mapping
  -> one initial revision
  -> draft -> evidence_complete -> pending_review
  -> one deterministic intake receipt
```

`PAPER_ONLY` is not a thesis database state and must not be written as one. Portfolio behavior
for this later mission remains non-executing by authority policy; D0 itself remains at P0
read-only.

The intake work order must meet all of these observable criteria:

1. **Validation boundary.** Use the D0-admitted, repaired proposal schema plus database-aware
   validation; do not claim the current schema is sufficient. Every root, section, figure, and
   invalidation citation resolves to permitted non-speculative evidence.
2. **Negative fixtures.** Reject unknown fields, agent-authored `james_input`, any Model A or
   `monitor_only` content for this strict non-Model-A lane, malformed invalidations,
   subject/symbol mismatch, invalid decimals, and missing, speculative, or unauthorised nested
   citations.
3. **Evidence promotion and identity.** Copy the recursive citation union exactly once from
   `agent_evidence` to `thesis_evidence`, preserving claim, tier, source/as-of, snapshot, and
   content hash, then mark each source row promoted. Preserve identity through D0's admitted typed
   reference, persisted source→promoted mapping, or explicit dual-reference rule; bare integer
   equality and hash matching are insufficient across the two ID namespaces.
4. **Atomic idempotency and ordered audit.** Use `agent_runs.run_id` as the idempotency key. The
   first call explicitly inserts `governance_status='draft'` (never relying on the current
   `approved` column default), creates exactly one thesis, initial revision, evidence/identity
   mapping, and receipt, then records both ordered events `draft → evidence_complete` and
   `evidence_complete → pending_review`. A materialiser retry with the same `run_id`, identical
   canonical proposal hash, and matching existing `resulting_object_id` returns that result with
   no writes and no second mission-receipt consumption; concurrent identical consumers still
   produce one thesis. Injected failure after each write leaves zero partial rows.
5. **Lossless field and provenance round trip.** Thesis text, flavour, conviction, themes,
   entry/stop/target, timeline, repaired invalidations, sections, figures, formulas,
   `source_run_id`, revision source/agent/confidence/citations, and nested evidence references
   survive database, domain, and CLI round trips. Reuse current `theses.report_sections` as the
   compatibility projection; list every intentionally deferred or rejected proposal field.
6. **Receipt reuse.** The deterministic intake receipt is a canonical logical projection/hash
   over existing `agent_runs.resulting_object_id`, thesis, revision, promoted-evidence mapping,
   governance-event, and approved-mission-receipt identities. Add no receipt schema unless D0's
   field-gap proof shows this cannot serve the consumer.
7. **Authority.** The result is research pending review, never approved, recommended, eligible,
   staged, ordered, or attached to a Model A signal. The first authorised invocation consumes the
   approved mission receipt exactly once. The idempotent recovery path above does not re-consume
   it; any new execution using the consumed receipt, changed proposal/hash, or mismatched/missing
   result is rejected as a replay or integrity failure.
8. **Reversibility.** The implementation is isolated, has a deterministic rollback, makes no
   production migration or write under this work order, and closes on tests plus one authorised
   shadow canary—not merely on file or PR existence. Pre-commit failure rolls back atomically;
   post-commit correction disables the consumer and appends an auditable correction rather than
   deleting a successfully materialised thesis.

### Later increments require separate ratification

| Later increment | User-visible outcome | Independent exit gate |
|---|---|---|
| **Report, challenge, and monitor** | The thesis becomes a versioned broker-report-quality case with falsifiers and independent challenge | Exact report/evidence identities persist; review sees a frozen context; bias labels remain advisory while missing mandatory evidence can block through deterministic evidence gates; material events append revisions/invalidation. |
| **Investment-decision view and surfaces** | CLI and morning brief render the same frozen investment truth | D0's reuse map proves whether a new type is necessary; both renders embed the same admitted view ID and hash; exact as-of/cutoff, citations, deficits, expiry, and invalidation are visible; renderers contain no financial logic. |
| **Delivery and disposition** | ASXOS proves what James received and records his separate response | Exact view/render bytes resolve; observed delivery is not inferred from job success; disposition cannot mutate the view or feed eligibility, sizing, staging, or other capital logic. |
| **Paper learning and replay** | A later review separates process quality from paper outcome | Evidence/fill/cost/FX/benchmark/accounting versions are frozen; deterministic replay is bit-identical; missingness stays visible; process and financial outcome remain separate; actual outcome remains `ACTUAL_OUTCOME_UNBUILT` until the accepted manual reconciliation lane exists. |

### Programme-epic observation gate

The epic is outcome-proven only when a real James-visible canary proves the full chain across its
separately authorised releases:

```text
evidence -> governed thesis -> frozen review -> investment-decision view
         -> delivered render -> James disposition -> replayable paper learning
```

Increment 1 closes at its implementation/shadow-canary gate. The programme epic closes later at
the observation gate after delivery, disposition, and the defined paper-observation horizon.
Tests, schemas, commits, agents, PRs, and a green job are necessary evidence, but none alone closes
either outcome.

### Explicitly deferred until the programme epic proves useful

- Generalising all S01–S12 contracts or loading the full dossier.
- Portfolio construction, sizing, staged packages, and promotion gates beyond what the
  selected thesis needs for paper observation.
- A loopback cockpit. If James later selects it as the daily mastery surface, it must render
  the same admitted investment-decision view ID/hash and pass a separate consumer-admission gate.
- Ask Arbi. Its first acceptable form is cited, read-only explanation over an exact admitted
  investment-decision view.
- Persistent Arbi, autonomous dispatch, review-router cutover, and external authority plane.
- skfolio or other portfolio-framework dependencies.
- Commercial, multi-user, network-exposed, broker-connected, or broader-wealth expansion.

---

## 6. Programme ownership and source-of-truth rule

| Concern | Owner | Source after ratification |
|---|---|---|
| Outcome priority and whether software should exist | Arbi, bounded by James and current authority | One reconciled product roadmap/state entry |
| Product and financial semantics | James + governing tax/portfolio specifications | Typed contracts and acceptance matrix admitted by D0 |
| Delivery sequencing | Guilfoyle/main execution loop after an approved mission | One mission graph tied to the retained acceptance IDs |
| Implementation | Bounded builder | Exact approved files in an isolated reversible branch/worktree |
| Mechanical correctness | Deterministic CI | Tests, schema validation, replay, static boundaries |
| Independent judgment challenge | Routed specialist/reviewer | Frozen context and exact-head findings |
| Merge, deploy, migration, authority, capital | James | Explicit James decision and external readback |
| Usefulness and learning | James disposition + Arbi observation | Separate immutable disposition/outcome records |

One rule brings the project together: **an artifact is current only when the canonical
current-main programme admits it**. A clean local worktree, draft PR, future-state proposal,
approved-looking fixture, green test, or agent statement is evidence to consider—not an
automatic addition to the programme.

---

## 7. Decisions required from James

D0 should return these as a short ratification sheet, with recommendations and exact impact:

1. Should PR #73 be closed as superseded or does it contain a verified net-new behavior not
   present on current `main`? Decide from an exact diff, not title similarity.
2. Which coherent PR #70 route should govern: reconcile and propose PR #70 for merge, or archive
   it and name a successor bootstrap PR that atomically replaces every PR70-bound B00/S01
   contract, validator, fixture, and test? Recommended: the successor route; never archive PR #70
   while retaining a “PR #70 merged” prerequisite.
3. Is the first mastery surface CLI + email, or does James genuinely require a thin local
   read-only cockpit before the observation window? Default: CLI + email until the epic
   is useful.
4. After D0-05, which authority route should be implemented or repaired and independently
   accepted for the intake mission? Default: `NOT_READY`; neither the present in-repo mechanism
   nor B00 is presumed accepted. James may instead record one explicit bounded exception with
   expiry and rollback.
5. Which one governed thesis should be the first real programme canary? The choice must be
   James's and must not be derived from Model A.

No capital decision is requested by D0.

---

## 8. Immediate next action

Complete D0-01 through D0-05 as one evidence packet before presenting open-work,
financial-semantics, and authority choices to James. Then produce D0-06 and the exact D0-07
reduction patch candidate, run D0-08 against their final digest, and stop at `PACKET_READY`.
Do not bundle D0 ratification with B00, S01, or intake implementation: a `RATIFIED` packet is an
input to the later authority and mission gates, not their substitute.
