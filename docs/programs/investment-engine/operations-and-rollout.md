# Investment engine operations, Arbi control loop, and rollout

**Operating mode:** James-only; long-only XASX/AUD capital path
**Programme build ceiling:** hidden `PAPER_ONLY`
**Terminal system action:** persist non-routable `ORDER_STAGED`
**Never in scope:** broker connectivity, placement, modification, cancellation or
execution

This runbook turns the dossier into an operating programme. It distinguishes
building software, observing it prospectively, making it visible to James and
making an evidence claim. Calendar time never substitutes for a gate.

## Chief-of-staff operating model

Arbi is the programme chief of staff.

| Role | Owns | Cannot |
|---|---|---|
| James | Ratify authority/policy/case risk anchors; approve migrations, rollout, promotion, merges/deploys where required; act externally | Delegate capital/broker authority |
| Arbi | Reconcile repo/live/GitHub truth; sequence initiatives; commission bounded missions; assign model tier; enforce dossier/PR/gate ceilings; stop drift; report readiness and north-star movement | Invent financial policy, originate/approve a capital action, self-merge/deploy or waive evidence |
| Guilfoyle / mission lead | Turn one accepted mission into disjoint implementation lanes and assemble evidence | Reprioritise the roadmap or change semantics |
| Claude implementation lane | Implement frozen contracts, tests, persistence and surfaces inside owned files | Fill a missing financial meaning or broaden authority |
| Opus/Ultra reviewer | Own architecture, finance/tax/accounting/statistics, migrations, capital boundaries and fresh red-team | Grade its own implementation diff as the sole reviewer |
| Fable-low worker | Fast bounded implementation, fixtures, adapters, rendering and repairs after semantics freeze | Choose architecture/financial semantics or continue after two failed repairs |

Arbi's north-star report must state:

```text
what changed
which AC rows moved
which north-star numerator/denominator can now be measured
what remains unbuilt
what evidence clock is running
which gate is false and why
the single next highest-leverage mission
```

Feature count, PR count and code volume are never the north star.

## Orthogonal state machines

```text
case:
  DRAFT -> REPORT_READY -> IN_REVIEW -> PAPER_ELIGIBLE
  -> CHALLENGED | CLOSED

artifact:
  VALID | BLOCKED | REJECTED | EXPIRED | SUPERSEDED

shadow:
  CONFIGURED -> SHADOW_ACTIVE -> INCOMPLETE | GATE_FAILED | GATE_PASSED

evidence:
  PAPER_ONLY -> UNCALIBRATED -> EVIDENCE_BACKED

visibility:
  OFFLINE -> SHADOW_HIDDEN -> STAGING_ELIGIBLE -> JAMES_VISIBLE

staged package:
  ORDER_STAGED -> INVALIDATED | EXPIRED

James disposition:
  PENDING -> APPROVED | REJECTED | AMEND_REQUESTED | EXPIRED
```

No arrow crosses dimensions implicitly. In particular, James disposition does not
change evidence tier, place an order or create a holding.

## Programme cadence

There are twelve outcome weeks. A week may contain several 8/12-hour missions.
The sprint closes only when its named AC rows and all continuously regressed rows
pass on the combined head. Unfinished work remains on draft PRs or is re-scoped;
elapsed Friday does not close a sprint.

### Delivery capacity

The programme carries an explicit, falsifiable capacity model. It is a planning
instrument, not a commitment, and every input below is stated so it can be
disproved by observed throughput.

| Input | Value | Basis |
|---|---|---|
| Declared mission-hours, S01–S12 | ~368 | summed from the sprints' own declared windows |
| R0 dossier repair gate | 72 | 7 missions across 3 concurrent lanes |
| Concurrent agent lanes | 2–3 | limited by intra-sprint file conflicts and review context-switching, not by compute |
| Overnight frozen missions | permitted for the DEC-013 `frozen` tier only | DEC-013's own definition |
| Independent reviewer | a separate agent session, never James | costs agent time, not governor time |
| PR review, financial-dense (S07/S09/S10/S11) | ~40 min | diff density of the quantitative sprints |
| PR review, structural/docs/evidence (S01–S06) | ~15 min | diff density of the contract sprints |

**Agent hours are not the same resource as James hours, and neither is the
binding constraint.**

*Critical-path agent hours* (mission hours ÷ achievable concurrency), by stage:

```text
S01 ~16 · S02 12 · S03 ~14 · S04 ~14 · S05 ~14 · S06 ~14
S07 ~28 · S08 ~24 · S09 ~24 · S10 ~32 · S11 ~32 · S12 ~20
brownfield survey (proposed, unscheduled) 8
total ~252 critical-path agent-hours
```

The brownfield survey is a *proposed* mission from the review packet, not a
sprint: `docs/product/roadmap.yaml` declares `S01`–`S12` only and there is no
`S06.5`. It is costed here because the work is real and unpriced, not because it
has been scheduled.

At 10–14 effective agent-hours/day (one day lane plus one overnight frozen
lane) that is ~18–25 working days of pure execution.

*James hours* ≈ **45h ± 15h across the whole programme**: ~25h of PR review
(≈25 dense reviews × 40 min plus ≈30 light reviews × 15 min) and ~20h of
decisions (R0 acceptance ~2h; the DEC-025 M02 packet ~2h; DEC-SHEET policy
values ~5h; DC-06 ~1h; NS-02 ~1h; twelve migration-apply gates ~4h; R1
authorisation ~2h; residual gates ~3h). At 6 h/week that is roughly 7.5 weeks
of governor time spread across the programme.

**The binding constraint is dependency-chain latency and James's review
turnaround — not agent hours.** Execution time is ~4–5 weeks; per-stage gate
latency (review plus the James-gated migration apply) at ~1.5 days across
thirteen stages is another ~4 weeks; ~25% slack for `NOT_READY` returns and
rework is ~2 more. Buying more agent throughput without shortening review
turnaround moves almost nothing.

| Case | Duration | Requires (all of) |
|---|---|---|
| **Aggressive** | **12–13 weeks** | 3 concurrent lanes; overnight frozen missions actually running; ≤24h review turnaround; ~10 James h/wk; migration applies same-day; ≤1 `NOT_READY` return per sprint; PROC-01 resolved before S08; DEC-025 answered at S01 |
| **Nominal** | 16–18 weeks | 2 concurrent lanes; 48–72h review turnaround; ~6 James h/wk |
| **Degraded** | 22–26 weeks | 1 lane, or weekly review batching, or a stall on PROC-01 / M-A2–M-A3 |

The two stalls that convert aggressive into degraded are both external to
engineering and both are calendar time no lane can compress: **PROC-01**
(a vendor/licensing timeline) and **M-A2/M-A3** (Model A shutdown, including a
*naturally elapsed* no-write observation window). Both are therefore scheduled
lanes with named owners, not mission sub-tasks — see below.

Arbi reports observed lane concurrency, observed review turnaround, and the
implied band at every sprint close. A band is a measurement, not a target: if
the observed inputs no longer support the declared band, Arbi restates the band
rather than compressing scope.

### Work-in-progress and review-throughput budget

**WIP rule (binding):** *no sprint starts while more than two of the previous
sprint's product PRs are unmerged.* Evidence and operations PRs do not count
against the cap; product PRs do. When the cap is exceeded, Arbi's only
permitted next action is to drive the open PRs to merge, close, or explicit
supersession — not to open a new lane.

The rule exists because review is the scarce resource. A peak sprint (S10 or
S11: four 12-hour missions plus one 8-hour) can generate up to fourteen draft
PRs under the DEC-015 ceilings of three per 12-hour mission and two per
8-hour one; an unbounded queue converts
into review batching, which is exactly the input that produces the degraded
band. Arbi tracks unmerged product-PR count as a first-class reconcile output
and surfaces it in the north-star report when it reaches the cap.

### Weekly Arbi loop

1. **Reconcile:** default branch/head, open/merged/superseded PRs, worktrees, CI,
   migrations/live count, jobs/deploy and prior close record.
2. **Gate:** find the earliest incomplete dependency and exact failing AC rows.
3. **Frame:** instantiate one mission with outcome, contracts, file ownership,
   negative fixtures, model routing, rollback and PR ceiling.
4. **Dispatch:** at most two disjoint product lanes; one integration owner.
5. **Observe:** review evidence, not worker confidence; stop on scope/semantic drift.
6. **Red-team:** a fresh context attacks the combined diff and capital boundaries.
7. **Close:** update canonical roadmap evidence/close record; report next mission.

If live truth contradicts the dossier on authority, finance, dependency or data
shape, Arbi returns `DOSSIER_DRIFT`; it does not ask the implementer to choose.

### Model A retirement control

S01 contains a dedicated 12-hour attended, read-only M02/M-A1 mission governed
by `model-a-decommission.md`. Arbi coordinates the deployed inventory, typed
deterministic archive/restore proof and explicit approval packet. M02 performs
no production mutation. James alone authorises production configuration, merge,
deploy, and retention-policy changes.

S01 cannot close while the identity mapping (`model_a`, `model_a_ml`, `v1_5`),
deployed schedules, writers/readers, health/deadman dependencies, archive
hashes, restore evidence, or approval state are indeterminate. If approved,
authority alignment, scheduler/writer/surface shutdown, and a real elapsed
no-write observation proceed in separately bounded M-A2/M-A3 changes. After
that shutdown, any new Model A write or re-enabled schedule is a SEV-1 boundary
incident. The programme never drops or rewrites Model A evidence.

**M-A2 and M-A3 are scheduled lanes, not implied work.** Release gate R1 cannot
depend on a shutdown that no unit of the plan owns. Under a DEC-025 `APPROVED`
outcome, M-A2 (authority amendment and retirement authorisation) and M-A3
(runtime and surface retirement, including a real elapsed no-write observation
window) are separate attended missions carried as their own roadmap manifest
rows, sequenced no later than alongside S04 and closed before R1 is evaluated.
M-A3's observation window is elapsed calendar time, not work time: the mission
records its start and returns only after the formerly scheduled window has
actually passed. Under a `NOT APPROVED` outcome neither mission is scheduled at
all, and R1 takes its second branch (see below). Nothing in the twelve-sprint
build is permitted to assume the shutdown happened.

### PROC-01 — market-data procurement lane

**Owner: James. Starts week 1, in parallel with S01. Not a mission; no agent
session can complete it.**

Deliverable: a **provider manifest** naming the resolved source, licence terms,
point-in-time availability guarantee, delivery mechanism and effective start
date for each of:

1. **XJO-TR** — a genuine point-in-time S&P/ASX 200 *total-return* (accumulation)
   series;
2. **prices and volumes** for the tradeable universe;
3. **corporate actions** across the action kinds S10 must cover;
4. **the XASX trading calendar** (sessions, holidays, half-days).

The manifest is a fixture-shaped artifact consumed by S08's entry criteria.

**PROC-01 is proposed as an explicit entry criterion for S08**, so that S08 does
not start — and no evaluator lineage is frozen — until the manifest resolves for
all four items. Procurement sitting inside a 12-hour mission is a planning
defect: a vendor negotiation runs on an external party's clock, it gates four
downstream sprints, and no mission window can absorb it.

This is a proposal, and the sprint file still says otherwise. Mission S08-A in
`sprints/s08-evaluator-and-shadow-foundations.md` currently opens with "Resolve
actual XJO-TR, price/volume, corporate-action and calendar providers, series
identifiers, revision/availability semantics and licensing constraints" — i.e.
S08-A *does* source data today, and s08's `Depends on:` names only the S07
bundle and the S06 monitor watermark, not PROC-01. Splitting sourcing out of
S08-A and adding the entry criterion is unlanded work; until those edits are
made, this section describes the target, not the plan of record.

**Why this is load-bearing, stated from the live repo rather than asserted:**
today the repository has only the *price-only* index `AXJO.INDX`, and
`jobs/snapshot_portfolio.py` fills `benchmark_tr_level` from a hardcoded
constant dividend-yield approximation (`_ASX200_TR_YIELD = Decimal("0.04")`,
~4%/yr) whenever the real accumulation series `AXJOA.INDX` is absent — which is
always, because it is not ingested. That approximation is honestly documented in
the job as a stopgap, but
[`benchmark-policy-v1`](contracts/benchmark-policy-v1.md) **forbids it
outright**: "Missing genuine XJO-TR or cash-rate data makes that comparison
unavailable; no price-only index or constant remembered rate may substitute."
R2 and R4 both require genuine point-in-time XJO-TR. Without PROC-01 the
programme reaches S12, starts its prospective clock, and then cannot pass R2 —
the most expensive possible time to discover it. Until the real series is
ingested, the engine's benchmark branch fails closed (comparison unavailable);
it must never inherit the snapshot job's approximation.

Arbi's decision-latency monitor surfaces PROC-01 as overdue from the moment S06
closes without a resolved manifest.

## Deployment and evidence lifecycle

```text
branch_only
  -> merged_offline
  -> shadow_hidden
  -> staging_eligible_uncalibrated
  -> james_visible_uncalibrated
  -> james_visible_evidence_backed
```

- `branch_only`: incomplete or under review.
- `merged_offline`: complete library/contracts, no scheduler or visible output.
- `shadow_hidden`: final frozen S12 bundle observing prospectively, no actionable
  staged output.
- `staging_eligible_uncalibrated`: R2 passed after 30 clean sessions.
- `james_visible_uncalibrated`: R3 James visibility decision.
- `james_visible_evidence_backed`: R4 plus promotion decision; language changes,
  execution authority does not.

## Release gates

### R0 — merge one sprint

- sprint AC rows and all regression rows pass;
- scoped diff/PR ceiling/model routing are satisfied;
- migration and recovery evidence exists when applicable;
- fresh-context review is recorded;
- combined head/worktree is clean; and
- no gate/evidence label is advanced by prose.

### R1 — begin hidden prospective observation

R1 can occur only after S12:

- construction/risk/sizing/staging/fill/accounting/tax/calendar/benchmark/evaluator/
  code/schema versions are frozen;
- all lower-level artifact hashes resolve through the integrated chain;
- production-shaped replay and boundary tests pass;
- the Model A archive is reproducible, and the **Model A predicate for the
  applicable DEC-025 branch** below is satisfied;
- required jobs have durable `job_runs`, deadmen and failure behavior;
- CLI/brief remain hidden/non-actionable; and
- James explicitly authorises `SHADOW_HIDDEN` and session zero is recorded.

Any material semantic change returns to R1 with a new lineage.

#### R1 Model A predicate — both DEC-025 branches

DEC-025 (Model A runtime decommission) is **pending** and is decided by James at
S01-M02. This document does not decide it. R1 must be evaluable either way, so
it carries an explicit predicate under each branch. Exactly one branch applies,
selected by the recorded DEC-025 decision artifact; if DEC-025 is still
undecided when S12 closes, R1 is **not** evaluable and the branch selection is
itself the blocking gate.

**Branch A — DEC-025 `APPROVED` (runtime decommission authorised).** All of:

- the M-A2 mission is closed: the authority amendment is merged and the
  `/pm-review` tombstone is non-contradictory;
- the M-A3 mission is closed: every deployed Model A schedule is disabled, every
  writer is stopped, and every legacy CLI/agent/brief/API surface fails closed
  or is removed;
- a **real elapsed** no-write observation window covering at least one formerly
  scheduled run has passed, with the no-write proof captured after the recorded
  shutdown watermark — never a simulated or asserted window;
- zero Model A jobs remain in any product-health or deadman denominator;
- the archive is reproducible and an attended restore or reproduction check
  passed; and
- the new engine has zero Model A import, runtime query, payload field, prompt
  input or fallback.

Post-M-A3, any new Model A write or re-enabled schedule is a SEV-1 boundary
incident.

**Branch B — DEC-025 `NOT APPROVED` (Model A keeps running as a dormant passive
monitor).** M-A2 and M-A3 do not happen, so R1 must **not** require shutdown.
R1 instead requires **zero Model A reachability from the new engine**, all of:

- a static dependency graph proves no active investment-engine module imports
  any Model A package;
- a runtime query trace proves no engine job, CLI path, brief section, reviewer
  packet or staged-package renderer reads a Model A table;
- no engine artifact carries a Model A field, and every closed schema rejects
  one (`prob_up`, `shap_factors`, `ml_prob`, `approved_for_allocation` as an
  input);
- archive/monitor perturbation — randomising or removing Model A data — leaves
  every canonical engine output bit-identical;
- no Model A job appears in the engine's product-health or deadman denominators,
  even though it continues to run in its own; and
- Model A history cannot enter a promotion denominator, benchmark,
  counterfactual or feature.

Under Branch B the passive monitor **continuing to run and continuing to write
its own tables is not an R1 failure**, and the standing `CLAUDE.md` rule #11
quarantine remains in force by its own authority. The SEV-1 condition narrows
accordingly: it is not "a Model A write occurred", it is *a Model A value
reached an investment-engine artifact, gate, surface or evidence claim*.
`model-a-decommission.md`'s S12 reachability proof reports the decommission lane
`NOT COMPLETE` without weakening engine isolation, and that report is a
compliant R1 input rather than a blocker.

Both branches share the archive-reproducibility and engine-isolation
requirements; they differ only in whether shutdown of the legacy runtime is also
required. Neither branch may be satisfied by prose.

### R2 — uncalibrated staging eligibility

All predicates:

- 30 consecutive clean prospective sessions after R1;
- bit-identical replay for all 30;
- at least 99.5% required NAV-days priced;
- zero unresolved material price, FX, corporate-action, tax, cost, accounting,
  general-data or reconciliation defects;
- genuine point-in-time XJO-TR and effective fee schedule;
- complete tax/accounting coverage for the cohort;
- Model A structural plus perturbation isolation;
- zero broker-boundary breach; and
- unique effective James-ratified construction/risk/staging policies.

A dirty/indeterminate session resets the streak. R2 permits
`STAGING_ELIGIBLE`/`UNCALIBRATED`, not visibility or an edge claim.

### R3 — James-visible uncalibrated release

- R2 is passed by immutable decision;
- SLO report shows P95 material-event delivery below one XASX session with sample,
  maximum, misses and unknown times;
- James reviews exact positive/blocked/stale/expired CLI/brief snapshots;
- disaster/forward-recovery rehearsal passes; and
- James explicitly changes visibility to `JAMES_VISIBLE`.

### R4 — strategy evidence and promotion

R4 is identical to the normative strategy gate:

- at least 252 clean prospective paired daily sessions;
- at least 20 matured pre-registered 63-session origins; overlap is allowed and
  dependency/effective-sample diagnostics are reported;
- one frozen pre-registered primary candidate lineage;
- positive stress after-tax-estimate/after-cost active return versus hold and
  genuine XJO-TR;
- positive one-sided 90% paired circular moving-block-bootstrap lower bound for
  both comparisons under the frozen protocol;
- at least 95% intended notional filled within five eligible sessions;
- zero policy breaches;
- drawdown inside James's ratified maximum;
- full open/rejected/no-action/unfilled/missingness/capacity/regime/selection
  reporting; and
- passed R2 plus explicit James `promotion-decision-v1=APPROVED`.

Failing R4 keeps `UNCALIBRATED` and prohibits alpha/edge/market-beating language.

## Daily hidden operating sequence after R1

1. Resolve the latest complete XASX session from the pinned calendar.
2. Verify expected source arrivals and point-in-time availability.
3. Ingest price/volume, benchmark, action, FX, fee, tax-profile, regulatory/news/
   filing and holdings inputs; missing mandatory input blocks.
4. Persist/dedupe monitoring events and alert delivery.
5. Invalidate challenged report/review/proposal/staged lineage.
6. Build any new report context; run blind review only on frozen bytes.
7. Freeze current eligible cases, policies, portfolio/reservations and construct/
   size deterministically.
8. Open pre-registered evaluator origin; advance paper intents/fills/settlements/
   ledgers/accounting/NAV.
9. Mature eligible outcomes; derive cohort statistics/gate decisions.
10. Persist shared view model. Before R3 it remains hidden.
11. Record job/session status and ping deadmen only after durable completion.

## Clean-session materiality

A session is `CLEAN` only if every required step completed on one version bundle,
all source/accounting coverage is complete, hashes/replay match, no material defect
or boundary violation exists and all expected scheduled origins are accounted for.

Defect materiality is deterministic and versioned:

- any amount changing NAV, tax/cost, a target, size, fill, gate or evidence
  language beyond the policy's exact tolerance is material;
- any unknown amount in those fields is material;
- presentation-only defects are non-material only if persisted semantic bytes and
  all decisions are unchanged.

An operator cannot relabel a dirty session clean. A correction creates a new audit
record and, if semantic, a new lineage.

## Freshness and fail-closed behavior

| Condition | Required behavior |
|---|---|
| Price/volume/FX/benchmark/action unavailable or stale | Block affected construction, fill, NAV and gate; never substitute zero/latest. |
| New material event after report review | Challenge case; invalidate proposal/sizing/staged package until new report/context/review. |
| Citation/hash cannot replay | Mark artifact invalid and block downstream lineage. |
| Missing/ambiguous/unratified policy or risk anchor | Typed rejection; no target/quantity/stage. |
| Multiple required active thesis/policy records | Hard error; never choose one. |
| Unsupported tax/action/distribution | Pre-tax diagnostics may render; after-tax/strategy gate blocked. |
| Model A schedule/writer reactivates or reaches a capital/evidence boundary | SEV-1 circuit breaker, stop affected writer/surface, invalidate/reset cohort, preserve evidence, independent review. |
| Broker capability/credential/route detected | Circuit breaker and release stop. |
| LLM writes deterministic field | Reject artifact; repair twice maximum, then Ultra escalation. |
| Delivery fails after durable event | Session incomplete; deadman unpinged; idempotent retry. |

## 8-hour mission recipe

Use for one frozen vertical slice with one implementation lane.

### Required input

- one sprint/initiative and 1–3 AC rows;
- frozen contract/schema/golden/negative fixtures;
- exact owned files and prohibited files;
- baseline SHA/live preflight;
- one rollback trigger/action;
- one PR normally, hard maximum two.

### Clock

| Time | Work | Mandatory artifact |
|---|---|---|
| 0:00–0:30 | Reconcile baseline, dependencies, dirty worktrees, CI and migration truth | Preflight block in mission instance |
| 0:30–1:00 | Restate outcome/invariants; prove contract is frozen; allocate owner/files | Scope/ownership map |
| 1:00–3:30 | Implement pure kernel/adapter plus nearest tests | Small coherent diff |
| 3:30–4:00 | Checkpoint; no new scope after hour 4 | Variance/descoping note |
| 4:00–5:30 | Negative, stale, idempotency and failure-injection tests | Evidence matrix |
| 5:30–6:30 | Integration/compatibility check; docs/observability/recovery | Handoff-ready product |
| 6:30 | Code/content freeze | Frozen head SHA |
| 6:30–7:20 | Independent review and targeted/full verification | Review + commands/counts |
| 7:20–8:00 | Repair inside scope, final diff/PR/close record | Draft PR + clean status |

If semantics are not frozen by hour 1, stop and route an Opus/Ultra design mission.
Do not spend the window letting Fable invent them.

## 12-hour mission recipe

Use for one cross-layer outcome with at most two disjoint product lanes.

### Required input

- one sprint/initiative and no more than one architectural outcome;
- exact shared contract/golden vectors before lanes split;
- two non-overlapping ownership maps plus an integration owner;
- maximum two product PRs plus one evidence/operations PR.

### Clock

| Time | Work | Mandatory artifact |
|---|---|---|
| 0:00–0:45 | Repo/GitHub/live/migration preflight and dependency gate | Reconciled baseline |
| 0:45–1:30 | Opus/Ultra contract/financial invariant freeze | Signed semantic checklist |
| 1:30–2:00 | Red tests/golden vectors and lane interface | Shared failing harness |
| 2:00–5:00 | Parallel lane A pure/domain; lane B persistence/adapter | Disjoint diffs |
| 5:00–6:00 | First integration, DB/fixture/contract resolution | Integrated checkpoint |
| 6:00 | Scope cutoff | Deferred-work list |
| 6:00–8:30 | Complete implementation, negatives, migrations/recovery | Product candidates |
| 8:30–9:30 | Combined production-shaped replay/failure injection | Combined evidence |
| 9:30–10:00 | Docs/observability/rollback and code freeze | Frozen combined SHA |
| 10:00–11:00 | Fresh-context Ultra red-team + full CI | Independent verdict |
| 11:00–12:00 | Bounded repairs, PR assembly, combined close | Draft PR(s), evidence PR, clean status |

The integration owner does not grade their own work. A red-team failure that changes
financial meaning returns to design; it is not squeezed into a wording patch.

## Mission slicing inside heavy quantitative sprints

S07–S11 intentionally contain several missions:

```text
contract + golden vectors
  -> pure deterministic kernel
  -> additive persistence/migration
  -> integration/replay/recovery
  -> fresh independent red-team
```

One weekly outcome may therefore span multiple PRs across multiple days while still
respecting each mission's PR ceiling. Never combine portfolio construction,
fill/ledger, tax/accounting and statistics into one “12-hour build.”

## Model routing

Use Fable-low only when all are present:

- closed schema/contract and exact invariants;
- golden and negative fixtures;
- fixed file scope and interface;
- no migration or financial/statistical meaning to choose.

Use Opus/Ultra for:

- target/risk/staging semantics;
- tax/accounting/fill/benchmark/statistics;
- data/migration design;
- capital/authority/security boundary;
- cross-system root-cause diagnosis; and
- fresh-context red-team.

After two failed Fable repair cycles on the same evidence failure, attach both
attempts, failure output, fixture, contract and diff, then escalate. Changing the
test/denominator/gate does not reset the counter.

## Automation lanes

Governing principle: **automate verification and preparation, never decisions.**
Every lane below is governed by this document; a lane assignment is not a
capability grant, and moving work up a lane requires the same governor decision
as any other authority change.

### GREEN — unattended, no acceptance step

Mechanical verification that produces no artifact a human must trust. **None of
the following is wired yet — this is the target lane, not a description of
today.** Standing them up is R0/S01 work:

- CI running `scripts/validate_investment_program.py` plus the mutation tests
  added in R0-A1/R0-A2 on every PR. *Not yet wired: no workflow in
  `.github/workflows/` invokes the dossier validator.*
- nightly drift validation of `main` and every open sprint branch. *Not yet
  wired.*
- a PR steward that autofixes CI failures on `claude/**` branches. *Today
  `.github/workflows/pr-review-agent.yml` is comment-only, with `contents: read`
  and `pull-requests: read`; it cannot push a fix. Granting write is a James
  decision, not a wiring detail.*
- a decision-latency monitor surfacing overdue DEC-SHEET, PROC-01 and
  `james-inbox` items. *Not yet wired.*

A GREEN job may only fail loudly, open an issue, or push a fix to a
`claude/**` branch. It may not merge, label a gate, or write an evidence field.

### AMBER — unattended execution, attended acceptance

Work is *performed* without a human present; its output is *accepted* only by
an attended session. Conditions are cumulative and all must hold:

- only DEC-013 `frozen`-tier missions qualify — closed contract, golden and
  negative fixtures, fixed file scope, no financial or statistical meaning left
  to choose;
- the run sets `ARBI_UNATTENDED=1`, so `.claude/hooks/unattended-guard.sh`
  mechanically blocks every irreversible tier;
- the session's database grants are scoped read-only;
- the run terminates at a **draft PR** and nothing further — no merge, no
  deploy, no migration apply, no gate label;
- an automated fresh-context adversarial pass runs against every product PR,
  which is what closes the self-grading gap: the closer never grades its own
  work.

Acceptance of an AMBER output is an attended act. This lane is what makes the
aggressive capacity band reachable; read-only DB role scoping is its enabler,
not an optional hardening.

### RED — never automated, mechanically blocked

Reserved to James, or to an attended session acting under a recorded James
decision. These are blocked by mechanism (`unattended-guard.sh`, the review
gate, CODEOWNERS plus branch protection), not by instruction:

- applying any migration;
- ratifying any policy;
- writing any `ratified_by` or `decided_by` artifact;
- any promotion, evidence-tier, visibility or model-tier decision;
- every M-A2 and M-A3 step;
- editing any authority document; and
- merge, deploy, and release-gate authorisation.

An automated run that finds itself needing a RED action stops and reports. It
never routes around the block, and a blocked RED action is a successful outcome
of the guard, not a failure of the run.

## Observability

Every run/session emits:

```text
run_id, session_id, code_sha, contract_bundle_hash, evaluator_config_id,
as_of, latest_complete_session, artifact_status, evidence_tier, visibility,
input/fresh/stale/missing counts, origin/proposal/sizing/staged counts,
defect counts by class/materiality, model_a_boundary_violations,
broker_boundary_violations, replay_match, duration_ms, status, reason_codes
```

Every alert adds source/publication/availability/observed/durable/delivered
timestamps, trading-session latency, delivery key/attempt/status. Logs contain no
secret or full private report/policy/tax body.

## Forward recovery

Production rollback for additive shared-Supabase migrations means:

1. stop only affected writers/presentation;
2. preserve every immutable record;
3. append invalidation where user-visible truth is affected;
4. deploy the last compatible code;
5. inspect `pg_depend` and apply an additive forward fix with James authority;
6. replay from earliest affected origin using original source hashes;
7. compare original/replay and record irrecoverable gaps;
8. reset prospective cohort for material semantics; and
9. resume only after targeted/full checks and applicable James decision.

Never drop an audit table or rewrite history to imitate a code rollback.

## Incident classes

| Severity | Example | Immediate action |
|---|---|---|
| SEV-1 boundary | Broker capability, secret exposure, Model A capital leak, unaudited capital transition | Stop affected writers/surfaces; preserve evidence; notify James; Ultra red-team |
| SEV-2 correctness | Wrong target/tax/cost/fill/NAV/statistic/gate or stale artifact shown valid | Invalidate outputs; stop staging; forward-fix/replay/reset |
| SEV-3 reliability | Missing/delayed/duplicate job/event/deadman with explicit fail-closed state | Keep blocked; repair; measure SLO |
| SEV-4 presentation | CLI/brief mismatch without semantic decision change | Withdraw surfaces; fix shared model/snapshots |

## Programme handoff to Claude

For each mission give Claude only:

1. repository `CLAUDE.md`;
2. accepted decisions and architecture;
3. canonical roadmap entry for the active sprint;
4. that one sprint file;
5. named contract/schema/fixtures;
6. named AC rows;
7. instantiated mission file and exact ownership;
8. current preflight evidence.

Claude must return:

```text
outcome verdict
changed files
contract/AC mapping
tests and exact counts
migration/live actions (normally none unless authorised)
negative evidence
open risk
rollback/recovery
draft PR URL(s)
clean combined status
```

Arbi then reconciles and decides the next programme action. Claude does not
self-promote the sprint.
