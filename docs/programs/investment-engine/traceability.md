# Investment engine traceability

**Status:** canonical crosswalk
**Roadmap:** `docs/product/roadmap.yaml`
**Baseline:** `Jp8617465-sys/asxos@9d442de287e123ae090b95838155dc41d76ee5f3`

This crosswalk tells a fresh Claude why a requirement exists, where it is built,
which contract controls its shape, which executable acceptance rows close it, and
how it changes the north star. The roadmap controls order; schemas control wire
shape; the acceptance matrix controls completion.

## Repository fact trace

| Baseline fact | Treatment |
|---|---|
| PRs #67–#69 are merged; #64 is closed/superseded; zero open PRs were observed | Refresh before every mission; do not plan another #64 salvage. |
| Migration 0041 is applied and required count is 95 | Refresh live ledger before numbering; stale DRAFT prose is not live truth. |
| Existing `ThesisProposal` Pydantic shape exists; agent-run logging and materialiser reject/stub `object_type='thesis'` | S01 versions the envelope/registry; S02 adds the real sole producer and closes both write/consume seams. |
| Migration 0040 report sections exist but are a latest projection | S03 creates a separate immutable report-version identity/hash; review follows it. |
| `/pm-review` and deployed job definitions still use Model A/SHAP/signals | S01 M02 prepares a typed immutable archive/restore and records the decision without runtime mutation; separately approved M-A2/M-A3 work aligns authority and disables legacy jobs/surfaces; S04 replaces review input with immutable Model-A-free context. |
| Holdings/lots/tax/portfolio primitives exist; signal allocator also exists | Reuse deterministic primitives; mechanically exclude signal allocator/ranking from capital. |
| No canonical target producer, evaluator lineage or staged-price policy exists | S07 supplies target/risk/staging policy; S08–S11 build recomputable evidence; S12 packages only. |

## Decision-to-delivery trace

| Decisions | Requirement | Initiatives / sprints | Acceptance | North star |
|---|---|---|---|---|
| DEC-001, 007 | James-only tailored CLI/brief; exact staging; no broker capability | GOV-01 S01; ENG-03/REL-02 S12 | AC-01–02, AC-49–52 | NS-CUD |
| DEC-002, 006, 018 | AI qualitative research; deterministic target/risk/tax/evaluation/staging | PORT-01/ENG-02 S07; EVAL-02–05 S08–S11 | AC-04, AC-27–48 | NS-CUD, NS-EDGE |
| DEC-003, 025 | Model A always absent from capital/evidence decisions; runtime-off/read-only retention is the pending approval-gated recommendation | GOV-01 S01; separate M-A2/M-A3 if approved; GOV-02 S04; EVAL-02 S08; REL-02 S12 | AC-03, AC-18, AC-33, AC-40, AC-48 | NS-CUD, NS-ALERT, NS-EDGE |
| DEC-004 | Safe proposal materialiser before expansion | GOV-01 S01; DISC-01 S02 | AC-06–10 | NS-CUD |
| DEC-005, 019 | Immutable report before context/review; then persistent monitoring | ENG-01 S03; GOV-02 S04; EVAL-01 S05; REL-01 S06 | AC-11–26 | NS-CUD, NS-ALERT |
| DEC-008, 009 | Canonical repository roadmap; 12 outcome weeks | GOV-01 S01 and all sprints | Dossier validator plus sprint close evidence | All |
| DEC-010, 023 | Post-freeze operational evidence and deterministic staging | S07, S11–S12, post-program R1–R3 | AC-27, AC-48–52 | NS-CUD, NS-EDGE |
| DEC-011, 021–022 | Recomputable prospective strategy evidence and separate promotion | EVAL-02–05 S08–S11, post-program R4 | AC-33–48, AC-51 | NS-EDGE |
| DEC-012 | CUD, alert latency and prospective active return are separate outcomes | REL-01, PORT-01, EVAL-02–05, REL-02 | AC-23–52 | All |
| DEC-013–015 | Model routing, repair escalation and PR ceilings | Every mission | Mission/close records and cross-cutting gate | All |
| DEC-016 | Current GitHub baseline and supersession truth | GOV-01 and every preflight | Refreshed read-only evidence | All |
| DEC-017 | V1 capital is long-only XASX/AUD | PORT-01 S07 onward | AC-29 | NS-CUD, NS-EDGE |
| DEC-020 | Typed lineage and separate state machines | S03–S12 | AC-11, AC-22, AC-33, AC-50–52 | NS-CUD |
| DEC-024 | Canonical financial bytes and honest tax estimate | S01, S03–S12 | AC-05, AC-14, AC-42–48 | NS-CUD, NS-EDGE |

## Initiative dependency trace

| Initiative | Outcome | Depends on | Sprint | Primary contracts |
|---|---|---|---|---|
| GOV-01 | Model A archive/restore/decision plan, authority quarantine, versioned proposal registry and harness | — | S01 | model-a archive manifest/restore evidence, decommission plan, proposal registry |
| DISC-01 | Completely cited governed thesis draft | GOV-01 | S02 | thesis-proposal-v1 |
| ENG-01 | Immutable review-pending report version | DISC-01 | S03 | broker-report-v1 |
| GOV-02 | Exact point-in-time context and Model A decoupling | ENG-01 | S04 | review-context-v1 |
| EVAL-01 | Blind assessments and conjunctive eligibility | GOV-02 | S05 | reviewer-assessment-v1, review-eligibility-v1 |
| REL-01 | Material-event watermark, alert and revision proposal | ENG-01, EVAL-01 | S06 | monitor persistence |
| PORT-01 | Deterministic desired portfolio | EVAL-01, REL-01 | S07 | security classification snapshot, construction policy, portfolio proposal, lineage |
| ENG-02 | Ratified risk/staging policy and exact sizing | PORT-01 | S07 | risk policy, sizing policy/decision, staging policy, trading calendar |
| EVAL-02 | Frozen evaluator/config/origin/branch protocol | ENG-02, REL-01 | S08 | evaluation policy/config/origin, portfolio snapshot, dependency-isolation evidence |
| EVAL-03 | Causal paper fill/settlement/branch ledger | EVAL-02 | S09 | fill model, intent/order/fill, ledger |
| EVAL-04 | Point-in-time accounting/tax/benchmark/NAV | EVAL-03 | S10 | accounting/benchmark policy, benchmark snapshot, tax profile, branch NAV |
| EVAL-05 | Outcomes/statistics/gate decisions | EVAL-04 | S11 | outcome, cohort statistics, evaluator, promotion |
| ENG-03 | Exact expiring non-routable staged package | ENG-02, EVAL-05, REL-01 | S12 | lineage, staged order set |
| REL-02 | Shared CLI/brief and shadow handoff | ENG-03 | S12 | shared view model, operations |

## Sprint artifact and acceptance trace

| Sprint | Work order | Depends on | AC rows | Observable result |
|---|---|---|---|---|
| S01 | `sprints/s01-programme-guardrails-and-proposal-registry.md` | — | AC-01–05 | Read-only Model A inventory/archive/restore/decision mission and proposal/harness boundaries are executable; approved shutdown remains a separate mission lane. |
| S02 | `sprints/s02-thesis-proposal-materializer.md` | S01 | AC-06–10 | New sole producer logs/materialises one governed draft atomically. |
| S03 | `sprints/s03-versioned-broker-report.md` | S02 | AC-11–14 | Real immutable report ID/hash exists before review. |
| S04 | `sprints/s04-review-context-and-model-a-decoupling.md` | S03 | AC-15–18 | Complete Model-A-free point-in-time reviewer packet. |
| S05 | `sprints/s05-blind-review-and-eligibility.md` | S04 | AC-19–22 | Five blind first passes and typed conjunctive eligibility. |
| S06 | `sprints/s06-persistent-monitoring-and-revision-proposals.md` | S05 | AC-23–26 | Durable material-event watermark, alert SLO and non-mutating revision proposal. |
| S07 | `sprints/s07-portfolio-construction-risk-policy-and-sizing.md` | S05, S06 | AC-27–32 | Engine-produced target vector and whole-portfolio exact sizing or typed rejection. |
| S08 | `sprints/s08-evaluator-and-shadow-foundations.md` | S07 | AC-33–36 | Fully pinned empty/open evaluator and pre-registered five-branch origin. |
| S09 | `sprints/s09-paper-orders-fills-and-ledger.md` | S08 | AC-37–40 | Later-event paper fills/settlement and balanced branch ledger. |
| S10 | `sprints/s10-corporate-actions-fx-tax-cost-accounting.md` | S09 | AC-41–44 | Recomputed pre-tax/after-tax-estimate NAV/TWR and honest XJO-TR/capacity. |
| S11 | `sprints/s11-nav-outcomes-and-evidence-gates.md` | S10 | AC-45–48 | Derived outcomes/counts/statistics/gate decisions with no aggregate spoof. |
| S12 | `sprints/s12-staged-orders-cli-brief-release.md` | S06, S07, S11 | AC-49–52 | Hidden `PAPER_ONLY` exact staged package, separate James audit and shared truth. |

## Contract introduction trace

| Sprint | Contracts introduced | Persistence role |
|---|---|---|
| S01 | model-a-archive-manifest-v1, model-a-archive-restore-evidence-v1; proposal registry (code contract) | Reproducible read-only evidence inventory/restore plus version/producer/validator/citation/materialiser routing |
| S02 | thesis-proposal-v1 | Existing agent run/evidence/thesis/revision/governance graph |
| S03 | broker-report-v1 | Immutable report header/payload/hash and exact source links |
| S04 | review-context-v1 | Review cycle and immutable point-in-time snapshot |
| S05 | reviewer-assessment-v1, review-eligibility-v1 | Blind assessments/findings/replacements/decision |
| S07 | security-classification-snapshot-v1, investment-case-lineage-v1, portfolio-construction-policy-v1, portfolio-proposal-v1, risk-policy-v1, sizing-policy-v1, sizing-decision-v1, staging-policy-v1, trading-calendar-v1 | Effective identity/taxonomy/trading rules, policy ratifications, frozen portfolio/calendar, proposal/checks, sizing/checks and typed lineage |
| S08 | evaluation-policy-v1, evaluator-config-v1, dependency-isolation-evidence-v1, evaluation-origin-v1, portfolio-snapshot-v1 | Protocol/config/book/session/origin/branch/input manifests and structural isolation proof |
| S09 | fill-model-v1, paper-intent-v1, paper-order-v1, paper-fill-v1, branch-ledger-v1 | Intent/state/fill/settlement and balanced event/leg history |
| S10 | accounting-policy-v1, benchmark-policy-v1, benchmark-snapshot-v1, branch-nav-v1, tax-profile-v1 | Accounting/source/profile policy, immutable benchmark observations and daily reconciled branch NAV |
| S11 | episode-outcome-v1, cohort-statistics-v1, paper-evaluator-v1, promotion-decision-v1 | Derived outcomes/statistics/gate decisions and James promotion audit |
| S12 | staged-order-set-v1 | Immutable set/stages/invalidation/expiry and separate James disposition |

The proposal registry is deliberately not a JSON payload contract. Every versioned
roadmap contract must have a spec, closed Draft 2020-12 schema and at least one
valid/negative semantic fixture at implementation time.

## North-star calculation trace

### NS-CUD

```text
governed thesis/report (S02–S03)
  + exact independent review (S04–S05)
  + current monitor watermark (S06)
  + ratified deterministic proposal/sizing (S07)
  + reconciled capital/accounting state (S09–S10)
  = disciplined eligible invested NAV
```

Each failed link excludes the affected holding with a typed reason; an incomplete
denominator makes the ratio unavailable.

### NS-ALERT

S06 persists publication/availability/observation/durable/delivery/acknowledgement/
disposition. S12 renders the same record. Exchange-closed time does not accrue.
Empty sample, unknown publication or missed delivery is explicit.

### NS-EDGE

```text
frozen target/risk/sizing semantics (S07)
  -> pre-registered evaluator/origins (S08)
  -> causal paper fills/ledger (S09)
  -> accounting/tax/XJO-TR/NAV (S10)
  -> outcomes/paired bootstrap/gates (S11)
  -> final hidden bundle (S12)
  -> genuine post-programme 30/252-session observation
```

S08–S12 development records cannot count. Episode origins may overlap; the paired
daily portfolio series is primary and dependency/effective-sample diagnostics are
reported.

## Release-gate trace

| Gate | Earliest real input | Effect | Failure |
|---|---|---|---|
| R1 shadow authorisation | Complete S12 frozen bundle plus James decision | Begin hidden prospective session zero | Remain offline/PAPER_ONLY |
| Operational / R2 | 30 consecutive clean post-R1 sessions | Staging eligible `UNCALIBRATED` | Reset/remain PAPER_ONLY |
| Visibility / R3 | R2, alert SLO, recovery and James surface approval | James-visible `UNCALIBRATED` | Remain hidden |
| Strategy / R4 | 252 clean sessions, 20 matured origins and all financial/statistical predicates | Eligible for promotion review | Remain UNCALIBRATED |
| Promotion | R2/R4 packet plus James promotion-decision | `EVIDENCE_BACKED` language only | Remain UNCALIBRATED |

No gate changes broker or execution authority.

## Mission trace

Every mission instantiates `mission-template.yaml` and records:

- current SHA/GitHub/live/migration preflight;
- exact sprint/initiative/AC/contracts;
- owned and prohibited files for each lane;
- 8h/12h clock, model routing, repair counter and PR ceiling;
- golden/negative/stale/failure fixtures;
- migration/recovery when applicable;
- targeted/full verification and independent review; and
- final PRs plus combined clean status.

The canonical start/close/8h/12h prompts are under `prompts/`. A conflict that
changes authority, finance, dependency or data semantics returns
`DOSSIER_DRIFT`; no implementer silently chooses.
