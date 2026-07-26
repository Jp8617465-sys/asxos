# S12 — Expiring staged packages, James audit, CLI/brief, and shadow handoff

**Initiatives:** ENG-03, REL-02
**Phase:** complete hidden product and begin observation runway
**Weekly outcome:** the full typed lineage can produce one exact, expiring,
non-routable `ORDER_STAGED` package in hidden `PAPER_ONLY` mode, record James's
separate disposition, and render identical truth in CLI/brief
**Maximum evidence tier during programme:** `PAPER_ONLY`
**Acceptance rows:** AC-49–52
**Depends on:** S06 current monitoring; S07 valid proposal/sizing/staging policy;
S11 recomputable evaluator/gate service
**Unlocks:** James-authorised hidden prospective observation; later R2/R3 only
after elapsed clean sessions

## Outcome

Implement `staged-order-set-v1` as the terminal ASXOS capital artifact. It is
derived from one valid sizing decision plus a James-ratified staging policy and
resolves the complete investment-case lineage. The product never routes or
executes it.

The sprint also implements one shared persisted view model for CLI and morning
brief, plus a separate immutable James disposition (`APPROVED`, `REJECTED`,
`AMEND_REQUESTED`, `EXPIRED`). Approval does not mutate the package, create a
holding, imply placement or manufacture a fill.

## Deterministic stage construction

`staging-policy-v1` owns:

- quote/reference source and maximum age;
- side-specific price offset/formula;
- effective XASX tick-table reference and rounding direction;
- stage count and exact rational quantity split;
- earliest next eligible session and per-stage `not_before`;
- stage validity and set expiry;
- market-move/report/review/monitor/policy/data invalidation thresholds;
- worst-case fees/notional rule; and
- no in-place reprice rule.

The builder:

1. verifies `SIZED` and every typed identity/hash;
2. reloads the current point-in-time source manifest;
3. derives tick-rounded prices/stages/expiry from policy only;
4. floors stage quantities while preserving exact total through a stable residual
   allocation;
5. recomputes worst-case notional plus fees; and
6. rejects the entire set if it exceeds sizing, is stale or violates any hard rule.

Any price, policy, proposal, sizing, context or monitor change creates a new
artifact; a set is never repriced in place.

## Evidence and visibility

S12 proves **software capability**, not elapsed evidence:

- before R2, generated packages are `PAPER_ONLY`, `SHADOW_HIDDEN` and unavailable
  as James-actionable recommendations;
- after 30 consecutive clean post-S12 prospective sessions, R2 may mark staging
  eligible `UNCALIBRATED`;
- R3 requires James to review exact surface snapshots and explicitly authorise
  `JAMES_VISIBLE`;
- `EVIDENCE_BACKED` additionally needs S11 strategy decision plus an immutable
  James `promotion-decision-v1=APPROVED`.

The sprint must not include “30-session evidence” in its expected outputs. That
runway occurs in calendar time after final freeze.

## Typed lineage required

Each package resolves identities and hashes for:

```text
investment case/version
thesis revision
broker report version
review context
review eligibility decision
monitor watermark
construction policy + portfolio snapshot + proposal
risk policy + sizing decision
evaluator config + operational/strategy decisions
staging policy
price/security-master/source manifest
```

`EVIDENCE_BACKED` additionally requires the James promotion decision. Generic
source hashes cannot substitute for these typed references.

## Execution firewall

The package contains no broker account, external order ID, broker credential,
endpoint, route, submit/modify/cancel operation, screen automation or live-status
poll. Its fixed terminal state is `ORDER_STAGED`. A later James-supplied external
fill/reconciliation contract is outside this programme and requires separate
review.

## User surfaces

Proposed commands:

```text
asx invest shadow-status
asx invest staged
asx invest show <order-set-id>
asx invest decide <order-set-id> --approve|--reject|--amend-requested --reason ...
```

`stage` creation remains an internal/offline service until visibility authority
passes. CLI and brief consume the same persisted view model and show:

- package ID/hash/as-of/expiry, evidence tier and visibility;
- case/report/review/monitor lineage and citations;
- before/after exposure, loss-at-risk, binding constraints and exclusions;
- exact stages, simulated reference only, fees/tax caveat and invalidation;
- gate predicates, deficits, sample/missingness/capacity and evaluator version;
- explicit “James acts externally; ASXOS cannot place this”; and
- calm blocked/stale/expired/amendment states.

## Additive persistence

After preflight, add immutable set/order/stage/invalidation/expiry records, typed
lineage links, James disposition audit and shared view-model version. Do not add a
broker identifier or live holding mutation. Add jobs only after migration/code and
keep presentation hidden until authority gates.

## Existing code reuse

Brownfield survey per review finding DR-04. Every path and table named below was
read in the repository; where the repository cannot supply what this sprint
assumes, the row says so plainly rather than assuming a capability.

| What exists today | What this sprint needs | Gap | Decision required |
|---|---|---|---|
| `asxos/cli/main.py` (Typer app, `add_typer` registrations) and `asxos/cli/portfolio.py` — `asx portfolio show`/`history`/`paper-review`/`signoff`, plus root-level `asx build-portfolio` and `asx propose-trades` registered at `asxos/cli/main.py:43-44`; all gated by `_require_personal_use()` in `asxos/cli/_common.py` | `asx invest shadow-status` / `staged` / `show` / `decide` | No `invest` sub-app is registered. The existing `asx portfolio` surface is shaped around the legacy allocator's `rebalance_runs` output | James: a new `asx invest` namespace versus extending `asx portfolio`. A new namespace is cleaner precisely because the legacy one is model-shaped and its disposition is still open from S07 |
| `asxos/brief/compose.py` (V1: `collect`, `render_html`, `_portfolio_section`, `_discipline_findings`) **and** `asxos/domain/brief/composer.py` (V2: `compose`, 10 collectors under `asxos/domain/brief/collectors/`, `renderer.py`, `brief_v2.html.j2`), driven by `jobs/compose_brief.py` with a V2→V1 fallback; `brief_runs` (`migrations/0015_brief_runs.sql`); `asx brief` in `asxos/cli/brief.py` | One shared persisted view model rendered identically in CLI and brief | **There are two live composition paths, not one.** `jobs/compose_brief.py` imports and calls the V2 composer unconditionally; the V2→V1 fallback lives inside `asxos/domain/brief/composer.py:88-98` and is gated on `ASXOS_V2_BRIEF_ENABLED` — which is set nowhere in `render.yaml`, so V2 collectors run and persist while **V1 renders the email that actually reaches James**. `brief_runs` records the run, not a versioned view model. The CLI and the email do not today share a persisted artifact, so "CLI/brief mismatch withdraws both surfaces" has nothing to compare | James: which composer owns the staged-package section, and whether the V1 path is retired before S12 or the view model is attached to V2 only. Do not add a third rendering path |
| Brief gating as implemented: `ASXOS_PERSONAL_USE=1` (s766B firewall) **and** `ASXOS_PORTFOLIO_BRIEF_ENABLED=1`, plus the freshness gate requiring a `build_portfolio` `job_runs` success with `as_of >= brief_date - 2`; section omitted entirely when any gate fails | A third, artifact-level visibility axis: `SHADOW_HIDDEN` → `UNCALIBRATED` (R2) → `JAMES_VISIBLE` (R3) | The existing gates are process-level env booleans, not per-artifact tiers, and they are attached to the legacy allocator's freshness. Review finding AS-06 records that this dossier relabels the `ASXOS_PORTFOLIO_BRIEF_ENABLED` unlock condition as superseded while `.claude/rules/portfolio-conventions.md` still states the original four-week paper-trade condition | James: reconcile the two unlock conditions (the review's position is "whichever is stricter"), and decide whether the visibility tier replaces the env flag or stacks on it. `.claude/rules/portfolio-conventions.md` is an authority document — it is not amended by this sprint |
| `decisions` table (`0001_initial.sql`) and `asx journal` (`asxos/cli/journal.py`) | An immutable, typed James disposition (`APPROVED` / `REJECTED` / `AMEND_REQUESTED` / `EXPIRED`) bound to a package hash | `decisions` is a free-text journal, mutable, with no typed lineage. It also writes live `signals` references (review finding MI-05), so it is inside the Model A trace surface, not outside it | None. New immutable disposition table; `asxos/cli/journal.py` belongs in the M-A1 inventory and the all-entry-point trace roots |
| `asxos/domain/governance/transitions.py::apply_governance_transition` + the `0034`/`0036` BEFORE UPDATE audit triggers | A disposition that cannot be written without a paired audit row | Directly applicable pattern. Each governed table needs its own trigger function, and the emitted statement order must be live-fire verified in a rolled-back transaction (the Phase 2a lesson: a wrong-order version passed mocked tests and two review loops) | None. Adopt the pattern; James applies the migration |
| Operations: `render.yaml`, `make check-drift` (Render REST API), Healthchecks deadman URLs per job, `jobs/check_cron_health.py`, `.claude/rules/job-conventions.md` | The hidden session job, its deadman, and drift evidence | Fully reusable. Every service change goes `render.yaml` → `git push` → `make check-drift`; the dashboard is never edited (CLAUDE.md non-negotiable #2) | None. The migration apply and the Render deploy are James-gated calendar items, not mission steps |
| `asxos/domain/theses/schemas.py` (`ReportSection`, `ReportFigure`, Decimal/provenance/prose-only guards) and `asx thesis show --full-report` rendering with Rich escaping | Safe rendering of the staged package and its lineage citations | Reusable rendering discipline, including the existing prose-only and figure-provenance guards | None. Reuse |
| Execution firewall — current state | "No broker account, external order ID, credential, endpoint, route, submit/modify/cancel" | Verified: the repository contains **no broker or order-routing code**. Every "broker" occurrence is `holding_lots.broker_ref` (free text) or the phrase "broker report". `ORDER_STAGED` remains terminal by construction | None. Pin this in the static deny test and exclude `broker_ref` so it does not false-positive |
| Trading calendar for per-stage `not_before` (review finding PC-07) | `not_before` validated against XASX sessions | Still no holiday calendar in the repository (`asxos/domain/prices/coverage.py` states this is intentional for v1) | James: XASX trading-calendar source. This is the fourth sprint to need it — it should be resolved once, at PROC-01, not four times |

## Mission decomposition

### Mission S12-A — builder and invalidation kernel (12h, product PR)

- Golden valid/no-policy/stale/price-move/new-event/changed-report/changed-policy/
  overlap/quantity/notional/tick/expiry/tamper fixtures.
- Implement staging-policy selection, price/stage derivation, full lineage,
  worst-case reconciliation and every invalidation trigger.
- Static/dynamic broker, Model A and live-holding deny tests.

### Mission S12-B — persistence, James audit and shared surfaces (12h, product PR)

- Add immutable stores and separate disposition service.
- Implement commands/shared view model/brief snapshots and safe rendering.
- Hidden `PAPER_ONLY`, future `UNCALIBRATED` and `EVIDENCE_BACKED` fixtures prove
  visibility/promotion refs are structural, not copied booleans.

### Mission S12-C — programme integration and recovery (12h, evidence/ops PR)

- Run all schema/fixture/contract/migration/programme acceptance and full CI.
- Production-shaped hidden session, expiry/invalidation, deadman/drift and rollback
  rehearsal.
- Emit exact post-program observation activation checklist and reset lineage.
- Fresh-context Opus/Ultra capital/security/reliability/red-team.

### Mission S12-D — James shadow authorisation (governor action, no fabricated data)

- James reviews the exact hidden CLI/brief snapshots, policies, boundary proof and
  rollback.
- If approved, enable only `SHADOW_HIDDEN` prospective observation.
- Record the frozen bundle and session-zero timestamp. R2/R3 remain pending.

## Negative behavior

- non-`SIZED`, rejected line, missing/unratified policy, unresolved lineage, failed
  required gate, stale/changed input, open high/critical finding or newer material
  event: no valid actionable package;
- expired/invalidated set cannot receive an approval disposition;
- conflicting disposition/hash is an integrity error;
- CLI/brief mismatch withdraws both surfaces;
- insufficient samples show exact deficits and keep `PAPER_ONLY`;
- broker capability or live-holding mutation triggers a circuit breaker.

## Observability

Emit set/stage/lineage/policy/evaluator hashes, tier/visibility/gate references,
line/stage counts, worst-case notional/fees, expiry/invalidation reason, James
disposition state, view-model version, job/deadman/delivery status, duration and
boundary-violation counts. Do not log private reason/report/policy bodies.

## Rollback

Stop hidden staging/invalidation/presentation jobs, retain immutable packages and
audits, append invalidations, deploy prior compatible code and forward-fix. Any
capital/evidence semantic defect restarts the post-programme clean-session count.

## Definition of Done

- [ ] Exact prices, stages and expiry derive only from ratified staging policy.
- [ ] Every applicable typed lineage reference resolves and hash-tamper fails.
- [ ] Worst-case notional plus fees never exceeds sizing.
- [ ] `ORDER_STAGED` is non-routable and the final system action.
- [ ] James disposition is separate audit, never execution or holding mutation.
- [ ] CLI and brief render one persisted version/state/tier.
- [ ] Programme-end ceiling remains hidden `PAPER_ONLY`.
- [ ] Post-program 30/252-session runways and resets are executable and explicit.
- [ ] Migration/job/drift/recovery/full CI and fresh Opus/Ultra red-team pass.
- [ ] James alone may authorise shadow observation; combined worktree is clean.
