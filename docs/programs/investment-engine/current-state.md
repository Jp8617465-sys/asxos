# ASXOS investment engine — current state

**Status:** implementation baseline
**Observed:** 2026-07-24 (Australia/Brisbane)
**Repository:** `Jp8617465-sys/asxos` (private)
**Baseline ref:** `main@9d442de287e123ae090b95838155dc41d76ee5f3`
**Grounding method:** read-only GitHub repository, branch, commit, file, and pull-request inspection

This document records what exists before the 12-sprint investment-engine
programme starts. It separates repository facts from the accepted target state
so that a planned capability is never mistaken for a shipped one.

## Baseline truth

- `main` points to `9d442de2…`, the merge commit for PR #69.
- PR #68 is merged. It cleanly extracted PR #64's two net-new units: the
  brief-truth/unrealised-return correction and persistent broker-report thesis
  sections. Those units are shipped and must not be described as still needing
  salvage.
- PR #64 is closed without merge because its remaining work was superseded.
- PR #69 is merged. It landed the docs-only `/arbi-close` handoff and reconciled
  `REQUIRED_MIGRATIONS` to 95 after migration 0041 was applied.
- GitHub returned zero open pull requests at the observation point.
- The prior main commit, `a1d30f52…` (PR #67), contains the materialised
  sector/theme discovery work and the source side of the macro-thesis learning
  loop.
- Migration `0040_thesis_report_sections.sql` records an already-applied
  production migration. Migration `0041_macro_thesis_learning_loop.sql` is also
  applied, and `asxos/api/main.py` requires the observed migration count of 95.
  Its file header still says **DRAFT — NOT applied**, which is stale prose.
  The `asxos-score-macro-theses` Render cron was not found and remains the
  controlled follow-up.

Pull-request state is time-sensitive. Re-run the same read-only GitHub checks
before opening an implementation PR; do not infer it from a local worktree or
from a stale handoff.

## Product and runtime shape already present

| Area | Current fact on `main` | Programme consequence |
|---|---|---|
| User and surface | Single user; Python 3.12; FastAPI; Supabase Postgres 16; Typer/Rich CLI; daily email brief; no v1 frontend | Keep CLI + brief as the delivery surfaces. Do not add auth, RLS, multi-tenancy, or a web UI. |
| Arithmetic and storage | Decimal-only capital-domain policy and `NUMERIC(18,6)` database convention | Reuse for risk, sizing, tax, costs, and order staging. Reject float inputs at contract boundaries. |
| Personal-use controls | CLI/job personal-use gates and governance controls exist | Preserve every current gate. Reconcile the accepted direct-tailored-output target with the current decision-support wording before enabling it. |
| Governance | `agent_runs`, `agent_evidence`, `governance_events`, governed statuses, shared transition ordering, and human approve/reject flows exist | Reuse; no second governance state machine. Agent output remains a proposal until James acts. |
| Thesis discipline | `theses`, `thesis_revisions`, entry/stop/target/timeline, invalidation checks, and active-thesis monitoring exist | Extend into the canonical investment proposal, sizing, staged-order, review, and monitoring chain. |
| Broker-report representation | `ThesisProposal`, `ReportSection`, `ReportFigure`, ordered section kinds, provenance guards, and monitor-only Model A restrictions exist | Adopt and harden the existing schema; do not invent a parallel broker-report model. |
| Broker-report persistence | `theses.report_sections`, `add_report_section()`, `asx thesis add-section`, and `asx thesis show --full-report` are shipped | Reuse for persistent reports. Add governed agent materialisation and review snapshots rather than another report store. |
| Tax | The spec-first deterministic tax engine is implemented, including CGT/Medicare, Div 296, and franking warnings | Reuse for after-tax evaluation and staged-order consequences. Tax remains deterministic and spec-cited. |
| Portfolio | Holdings, lots, snapshots, constraints, and an older signal-driven build/allocator path exist | Reuse holdings/lots/snapshots and deterministic primitives. Exclude the signal-driven capital path. |
| Discovery | Macro, sector, theme, and agent-run proposal patterns exist; agents read through a read-only Supabase surface | Reuse evidence provenance and human materialisation patterns. Add instrument-thesis discovery only behind the safe materialiser. |
| Evaluation | Signal outcomes, paper/evaluation code, job monitoring, and benchmark fields exist, but no accepted frozen investment-engine evaluator contract exists | Build one canonical prospective evaluator against genuine `XJO-TR`; historical Model A evaluation is not the new strategy evidence. |
| Operations | Render cron definitions, `JobMonitor`, Healthchecks, drift checks, and hard-fail conventions exist | Extend for investment review and alert latency; measure the material-event SLO rather than assuming job green means alert timely. |

The current `/pm-review` implementation and several of its five agents still
query/use signals or SHAP. It is therefore prohibited as capital review. The
recommended target is to disable that legacy entry point at S01, retain its
history in Git/archive evidence, replace its input boundary at S04, and create
the first eligible persistent review decision at S05.

## Important seam: schema shipped, consumer still stubbed

`asxos/domain/theses/schemas.py` already defines the full `ThesisProposal`
keystone, including:

- report-section and report-figure provenance;
- Decimal-safe capital figures;
- a prohibition on `monitor_only` Model A figures as entry, stop, target, or
  other capital levers;
- evidence citation requirements; and
- unique ordered broker-report sections.

However, `asxos/domain/theses/service.py::create_thesis_from_agent_run()` still
hard-fails and says no `ThesisProposal` schema exists. The corresponding
`asx thesis open --from-agent-run` help and docstring carry the same stale
assumption. This is the safe, bounded seam for S01–S02:

1. register the proposal version, permitted producers, nested citation walker,
   and materializer in one code registry;
2. verify and freeze the existing proposal shape as `ThesisProposalV1`;
3. validate `agent_runs.proposed_object` through it;
4. resolve every nested evidence ID and reject speculative-only/stale-invalid
   material;
5. persist the thesis, revision, evidence links, governance events, and
   acted-on linkage transactionally and idempotently; and
6. leave approval and every capital action to James.

The programme must not call the materialiser "new schema work" unless the
existing schema genuinely needs a reviewed amendment.

## Reuse, extend, retire

### Reuse as load-bearing foundations

| Existing component | Reuse rule |
|---|---|
| `asxos/domain/theses/schemas.py` | Canonical proposal/report provenance types. Amend only through financial-semantics and adversarial review. |
| `asxos/domain/theses/service.py` and `thesis_revisions` | Canonical individual-thesis lifecycle and append-only discipline history. |
| `asxos/domain/governance/transitions.py` | Canonical governance event-before-status-update sequence. |
| `agent_runs` / `agent_evidence` / `governance_events` | Canonical AI proposal, cited evidence, and human disposition trail. |
| `asxos/domain/macro_theses/*`, themes, and governed views | Existing macro/theme context and governed discovery inputs. |
| `asxos/domain/tax/*` and the tax spec | Canonical after-tax calculations. Never duplicate tax math in evaluator or sizing code. |
| holdings, lots, and portfolio snapshots | Canonical capital state inputs, subject to freshness and reconciliation checks. |
| `asxos/brief/*`, Typer CLI, and Rich rendering safety | V1 presentation layer. Preserve personal-use gates and escaped user text. |
| `JobMonitor`, Render manifests, Healthchecks, and drift checks | Operational foundation for scheduled evaluation and alerts. |

### Extend through explicit contracts

| Gap | Contract or outcome |
|---|---|
| Agent-run thesis materialisation is stubbed | The proposal registry plus `thesis-proposal-v1` and the existing `ThesisProposal`, persisted as a governed research thesis |
| No immutable report header precedes capital review | `broker-report-v1`; created from one thesis revision/evidence manifest before any review context |
| No typed end-to-end investment-case lineage | `investment-case-lineage-v1`; stable identities plus canonical hashes at every capital boundary |
| No deterministic target-weight producer | `portfolio-construction-policy-v1` plus `portfolio-proposal-v1`; transparent James-ratified loss-at-risk budgeting |
| James-set risk inputs are not a ratified machine contract | `risk-policy-v1`; absent/unratified policy produces `REJECTED_NO_POLICY` |
| No canonical deterministic sizing decision | `sizing-decision-v1`; result is `SIZED`, `REJECTED_NO_POLICY`, or `REJECTED_POLICY_VIOLATION` |
| No deterministic staged-price/split/expiry source | `staging-policy-v1`; missing/unratified policy blocks the staged package |
| No exact non-executable order package | `staged-order-set-v1`; state `ORDER_STAGED`, with no broker endpoint |
| No frozen investment-engine evidence protocol | `evaluation-policy-v1`, lower-level evaluator/accounting contracts and derived `paper-evaluator-v1`, benchmark `XJO-TR` |
| Review history is fragmented across thesis revisions, runs, and briefs | Persistent review record linking proposal, thesis revision, sizing decision, staged order, evaluator result, and alerts |
| Alert timeliness is not a measured product SLO | Material-event timestamp, alert timestamp, trading-calendar latency, and P95 computation |

### Retire from capital contracts

| Component or idea | Target treatment |
|---|---|
| Model A `v1_5` training/inference/outcome jobs | Disable under the attended `model-a-decommission.md` mission; retain deterministic archive evidence read-only. |
| `PortfolioService.build()` signal-driven allocator path | Make unreachable from active routes/jobs; it must not back the new engine or be wrapped as thesis-led sizing. |
| Signal-ranked `compute_opportunity_cost` output | Disable its job and current product surface; retain prior results only as historical evidence. |
| Model A labels in CLI, brief, agents, and `/pm-review` | Remove or fail closed; S04/S05 introduce an independent replacement review path. |
| Web/mobile UI for this programme | Not built. CLI + brief first. |
| Broker API, credentials, connectivity, and execution | Not built, requested, stored, or simulated as a live integration. James manually places every trade. |
| Historical roadmaps that frame Model A as the product | Retain as historical evidence, but do not use as current sequencing authority. |

Runtime retirement means zero enabled Model A jobs, product-health requirements,
capital/evaluator imports, runtime queries, fields, or fallbacks. It does not
mean destructive evidence deletion. The complete implementation and rollback
contract is [`model-a-decommission.md`](model-a-decommission.md).

## Current-to-target boundary changes

The current north-star text describes the product as single-user
decision-support that does not represent itself as licensed advice. The
accepted programme target allows direct, tailored output and exact order
staging for James while retaining the execution firewall.

That is a material semantic change. S01 must reconcile the repository's
constitution, personal-use wording, output labels, audit record, and acceptance
tests before tailored outputs are enabled. Until that reviewed amendment lands,
the stricter current repository wording remains the runtime authority. The
target never permits:

- automatic submission, modification, cancellation, or routing of an order;
- broker credentials, tokens, sessions, or screen automation;
- an agent choosing unratified risk values;
- Model A entering a capital-relevant field; or
- a second user or public advice surface.

## Locked implementation dependency chain

The architecture and additive migration plan fix the programme order. Later
sprints may not be pulled forward merely because their contract prose is ready:

1. S01 — programme guardrails, proposal registry, and harness;
2. S02 — ThesisProposal validation, nested citation walker, and governed
   idempotent materializer;
3. S03 — immutable versioned broker report;
4. S04 — immutable ReviewContext and PM-review decoupling from Model A;
5. S05 — blind multi-role review and deterministic eligibility;
6. S06 — persistent report/thesis monitoring and revision proposals;
7. S07 — James-ratified portfolio construction, risk, sizing, and staging
   policies plus deterministic target/sizing kernels;
8. S08 — evaluator configs, pre-registered origins, continuous shadow book, and
   frozen episodes;
9. S09 — paper intents/orders, simulated fills, settlement, and append-only
   branch ledgers;
10. S10 — corporate-action, FX, tax, fee, stress-cost accounting, and daily NAV;
11. S11 — outcomes, cohort statistics, and recomputed evidence gates; and
12. S12 — expiring staged orders, James approval audit, shared CLI, and morning
    brief.

This order is load-bearing: review context needs a real immutable report ID/hash;
paper eligibility needs independent review; evaluator evidence cannot start
before the actual construction/risk/sizing lineage exists; NAV needs orders,
fills and complete accounting; staged orders need all of them.

## Evidence and release gaps

The programme begins and ends its twelve-week build in hidden `PAPER_ONLY`. The
following are not true merely because the 12 sprints complete:

1. **Risk policy ready.** Every James-set risk and sizing value must be explicitly
   ratified and versioned. Missing values fail closed.
2. **Operationally staged.** After S12 freezes the complete production-shaped
   lineage, the evaluator must record at least 30 consecutive prospective
   complete sessions with bit-identical replay, at least 99.5%
   priced NAV-days, no unresolved material accounting/data defects, genuine
   XJO-TR, the effective broker fee schedule, Model A isolation, and a
   James-ratified risk policy before a staged output may be labelled
   `UNCALIBRATED`.
3. **Evidence backed.** No edge claim is allowed until the same prospective
   protocol has at least 252 sessions and at least 20 matured episodes, each
   observed through 63 sessions, plus the frozen strategy gate's stress-cost,
   one-sided 90% moving-block-bootstrap, fill, policy, and drawdown bars.
4. **Benchmark honest.** Active return must be prospective, after tax and costs,
   and compared with genuine XJO total return, with drawdown, sample size, and a
   hold comparison shown. It is a conservative hurdle, not benchmark-neutral
   "alpha"; portfolio time-weighted return is the primary series and overlapping
   episode outcomes are dependency-aware diagnostics.
5. **Alerts timely.** P95 material-event-to-alert latency must be below one
   trading day and measured from persisted timestamps.

If any gate is unmet, the correct outcome is an explicit non-promotion, not a
waiver, a backfilled claim, or a shifted denominator.

## Quantitative scope correction

The initial planning pass had four implementation-blocking holes that this
dossier now closes:

1. it consumed target weights without producing them;
2. it attempted to create a review context before its required report version;
3. it opened evaluator evidence before the real policy/sizer existed; and
4. it described full lineage without requiring typed resolvable references.

The repaired target is a long-only XASX/AUD engine. Foreign securities remain
research-only. Construction is a reproducible loss-at-risk budget under
James-ratified policies, not a generic weighted score or Model A allocator.
Twenty 63-session episode origins may overlap; their schedule and dependency
groups are pre-registered because twenty non-overlapping episodes would require
at least 1,260 sessions.

## Canonical sources for implementation

- Programme sequencing: `docs/product/roadmap.yaml`
- Roadmap validation: `docs/programs/investment-engine/schemas/roadmap.schema.json`
- Accepted decisions: `docs/programs/investment-engine/decisions.md`
- Requirement mapping: `docs/programs/investment-engine/traceability.md`
- Contract specifications: `docs/programs/investment-engine/contracts/`
- Acceptance evidence: `docs/programs/investment-engine/acceptance-matrix.md`
- Sprint outcomes: `docs/programs/investment-engine/sprints/`
- Operations and rollout: `docs/programs/investment-engine/operations-and-rollout.md`
