# Investment-Engine Dossier — Adversarial Review Packet

**Subject:** PR #70 `docs: add investment-engine implementation dossier` (draft)
**Branch/commit reviewed:** `agent/investment-engine-dossier` @ `b9c2f6f82f51dc91ffa0d954b7452cc61d3bb1ce`, single commit atop the exact stated baseline `main@9d442de2`
**Reviewer:** arbi (Claude session), branch `claude/investment-engine-dossier-review-ozg1ny`
**Date:** 2026-07-25
**Method:** direct validation (validator, tests, hashes, ruff under CI-pinned toolchain) + eight parallel adversarial review agents (north-star, model independence, review integrity, evaluator, construction/sizing, data contracts, delivery, authority), with every P0 and load-bearing P1 claim independently re-verified by the synthesizing session against the PR bytes.
**Actions taken:** none beyond reading and validation. No merge, no migration, no deployment, no production mutation, no Model A change, no edit to the dossier.

---

## A. Executive verdict

### AMBER

**The dossier is NOT ready to become implementation authority as shipped. It is one bounded repair sprint away from being ready.** The architecture, boundary design, and honesty culture are institutionally credible — several review dimensions found the *design* sound under direct attack. The blocking problems are concentrated in (1) the acceptance harness not enforcing what the contracts promise on the capital path, (2) delivery arithmetic, (3) ratification mechanics, and (4) four financial-semantics defects baked into ratified contract fixtures. All are correctable at the contracts/fixtures/validator layer — the cheapest moment this programme will ever have, before any implementation exists.

### The five most important reasons

1. **The semantic validator does not enforce what the contracts promise on the capital path — proven by live attack.** Three separate stageability attacks were reproduced against the shipped harness and re-validated PASS: a staged order at a 10% adverse limit (20× the ratified policy's 0.005) with notional above the sized amount (PC-01); sizing limit checks that are producer-attested — the shipped `sizing-valid.json` itself contains `LOSS_HEADROOM observed=15000.000000, limit=0.000000, action=PASS`, and `limit_value` is read **zero** times by the validator (PC-02, verified); no liquidity/ADV/spread enforcement at all (PC-03). Separately, the paper-intent fixture's `sizing_line_sha256` binding hash matches **nothing in the dossier** — recomputed to `1511834c…` vs the stored `8eb3140d…` — and the validator never checks line-level bindings (`sizing_line_sha256`: 0 occurrences, verified) (DC-01). The dossier's central claim — "recomputed, never asserted" — is true for the review/lineage chain and false for the sizing/staging/measurement chain.

2. **Delivery arithmetic fails under the dossier's own numbers.** The sprints' own declared mission windows sum to ~368 attended hours across 12 weeks, peaking at 52–56 h/week in S07/S10/S11 — for one supervising human, before PR review, migration applies, and policy ratification (DR-01). S01's declared 20 hours does not cover its own deliverable table (DR-02). S07–S12 name **zero** existing asxos modules (grep-verified), leaving brownfield integration with the live allocator, tax engine, and brief unpriced (DR-04). Two unscheduled lanes sit on the critical path: the Model A M-A2/M-A3 shutdown that release gate R1 hard-depends on (DR-08), and licensed XJO-TR data procurement buried inside a 12-hour mission (DR-05).

3. **Authority mechanics are prose where they need to be mechanical.** The dossier repeatedly labels itself "accepted"/"locked" while no acceptance record exists on main (`decision-log.md` and `james-inbox.md` verified untouched) — acceptance is what this review and James's merge decide (AS-02). Every "James decision" artifact is authenticated by a `const: "James"` string any session can write; the S01 plan has an LLM lane authoring the Model A approval record; CODEOWNERS does not cover `docs/programs/investment-engine/**`, `roadmap.yaml`, or four of the seven authority documents the ratification gate depends on (AS-01, AS-03). The `ADVICE_READY` case state is baked into canonical schemas and the golden staged-order fixture ahead of the authority ratification the dossier itself requires (NS-01).

4. **Four financial-semantics defects are baked into ratified contract fixtures, two of them sign-definite in the strategy's favour.** The tax profile pins day-count CGT eligibility (`minimum_holding_days: "365"`) in direct violation of CLAUDE.md non-negotiable #6 / spec §5.1 — calendar arithmetic is structurally inexpressible in the schema as shipped (EV-01/PC-08, independently found by two agents, re-verified). There is no 45-day franking rule although the host repo already implements it (TC-21) — dividend-capture episodes harvest credits s 207-145 denies (EV-06). The "economically meaningful hurdle" is instantiated as epsilon (`0.000001`) (EV-04). And no pre-registered gate-evaluation schedule exists, so optional stopping inflates the nominal 10% one-sided error to an estimated 20–30% over two years of daily looks (EV-03).

5. **The measurement half of the evidence engine exists only as null/degenerate fixtures with claimed-but-absent recomputation.** Six contracts state "the semantic validator recomputes X" where no such code exists (episode-outcome returns, benchmark `session_return`, portfolio-snapshot NAV totals, paper-fill causality/participation/limit rule, paper-order chronology, branch-NAV Dietz/rollforward/source-hash equality) (EV-02, DC-02, DC-03). Every outcome-measurement fixture is UNAVAILABLE/null/empty; the strategy-gate statistics have zero worked numeric examples in 42 fixtures, and the promotion decision's `gate_decision_ref` is a `"3333…"` placeholder that could contradict the in-dossier evaluator gate and still validate (DC-04, DC-08). By contrast the decision half (report→context→review→eligibility→lineage) is genuinely recomputed and survived attack.

### What implementing it unchanged would actually produce

A 25–35-week build (not 12) ending PAPER_ONLY, whose green acceptance harness cannot detect a mis-priced, over-sized, cash-insolvent, or naked-sell staged order; whose after-tax active returns carry two systematic upward biases (CGT day-count, missing 45-day franking rule) feeding a `>0` gate that can also be passed by optional stopping and self-asserted fill/NAV booleans; whose zero-defect operational gate is likely unreachable against real ASX corporate actions (EV-07); and whose "James approved" records are unauthenticated strings. No capital would be directly lost — the execution firewall is genuinely intact (verified: no broker field exists anywhere; `ORDER_STAGED` is terminal; `additionalProperties:false` throughout; DEC-025 correctly pending) — but the programme's actual product, *trustworthy evidence*, would not be trustworthy, and the first sprint would halt on day one anyway: `s01:9` claims acceptance rows AC-26–27 that the matrix locks at S06/S07, which is `DOSSIER_DRIFT` by the dossier's own stop rule (NS-05/DR-07, verified).

### What holds up under attack (for balance — verified, not asserted)

- Root fixture hashes are genuinely recomputed and enforced (0 repairs; regenerated roadmap view byte-identical; 111/111 tests; ruff clean under CI-pinned 0.7.0).
- The review chain's plumbing: copied verdicts, cross-case replay, future-dated evidence, unbound report-candidate hashes, dangling claim/evidence refs, and finding-resolution laundering are all **rejected** by recomputation (each attack replayed live).
- Model independence of the new engine is proven at design level: injected `prob_up`/`shap_factors`/`ml_prob` fields are mechanically rejected by every closed schema; `approved_for_allocation` appears only as a prohibition; construction/sizing exclude every model input by contract.
- The execution firewall is absolute in the bytes: zero broker/routing/credential fields; `automatic_approval_permitted: const false`; `user_approval.approved_at: type null`.
- The Model A archive/restore contracts rejected all seven adversarial spoofs; the decommission is correctly gated on a pending James decision (DEC-025), and the 0-approved-models state is already safe (`ModelGateDormant` blocks before the staleness check).
- The migration plan pre-authorises nothing, is additive-only, and James-gates every apply.
- The dossier's honesty culture is real: fail-closed nulls instead of fabricated numbers, PAPER_ONLY ceiling, "the twelve-sprint build ends PAPER_ONLY" stated plainly, DEC-011 correctly rejecting the mathematically inconsistent non-overlap reading.

---

## B. Evidence-backed findings

62 findings across eight dimensions. Full per-finding detail (evidence quotes, failure scenarios, corrections, acceptance tests) is in the per-dimension reports; this register is the consolidated, deduplicated index. Merges: EV-01=PC-08 (same defect, found independently twice); NS-05=DR-07; EV-02 overlaps DC-02/DC-03 (one family, three angles); AS-02 subsumes the synthesizer's own self-ratification observation.

### P0 — blocking (7)

| ID | Finding | Evidence anchor | Violated invariant | Consequence |
|---|---|---|---|---|
| **DC-01** | Paper-intent→sized-line hash binding unenforced AND shipped fixture's `sizing_line_sha256` provably wrong (matches nothing; correct value `1511834c…`) | `fixtures/paper-intent-valid.json`; validator has 0 occurrences of `sizing_line_sha256` (verified) | Dossier's own opacity rule (lineage contract): in-dossier artifacts must resolve | Intent can bind to a trade sizing never approved; the golden chain demonstrates the exact tamper the lineage exists to prevent |
| **PC-01** | Staging validator uses the order's own `max_adverse_fraction`, never the ratified staging policy; no staged-notional ≤ sized check; no tick-band binding | `validate_investment_program.py:3503-3510` (verified); attack re-validated PASS at 10% adverse, 11,000 > 10,000 | staging-policy-v1 "buy limit = reference × (1+policy fraction)"; AC-49 worst-case-notional rule | The terminal James-facing artifact can exceed risk-approved size at an unratified price |
| **PC-02** | Sizing `NUMERIC_LIMIT` checks producer-attested: `limit_value` read 0 times; `observed ≤ limit` never asserted; shipped fixture has `LOSS_HEADROOM obs=15000 > lim=0 → PASS` (verified in bytes) | `fixtures/sizing-valid.json:339-344`; validator sizing block | sizing-policy-v1 "numeric steps may only pass or reduce" | Cash/ADV/spread/loss-headroom/minimum-order violations self-certify PASS and become stageable |
| **PC-03** | `risk_policy.liquidity_limits` (min ADV, participation, spread, price age) never referenced in portfolio/sizing semantics (grep = 0) | validator `_validate_portfolio_semantics` | risk-policy-v1 liquidity mandate | Unfillable size in illiquid names is stageable with fabricated ADV |
| **DR-01** | 12-week cadence arithmetically impossible: ~368 declared mission-hours, peaks 52–56 h/wk (S07/S10/S11) for one supervising human | Sums from the sprints' own declared windows | Sprint closure rule vs `week: N` binding | Realistic 25–35 weeks; all downstream dates (R1, evidence clocks) misdated by ~2 quarters |
| **DR-02** | S01's declared 8h+12h window doesn't cover its own deliverable table (validator alone ≈ a full 8h mission; ~10 runtime files; 8 test files) | `s01:5-7` vs `s01:312-317, 388-416` | 8h-prompt's own "reduce the mission" rule | Programme's credibility mechanism (bounded missions) dies in week 1 |
| **DR-04** | S07–S12 name zero existing asxos modules (grep-verified: all 14 real-path hits are in S01–S06); tax engine, brief compose, legacy-allocator disposition, security-master fields unpriced | sprint docs S07–S12 | The dossier's own reuse-table discipline (S01–S06 have real paths) | Back half carries all quantitative risk with the least grounded estimates; mid-sprint discovery of multi-mission refactors |

### P1 — must fix before the affected sprint starts (18)

| ID | Finding | Anchor | Fix before |
|---|---|---|---|
| **NS-01** | `ADVICE_READY` baked into canonical schemas + golden staged-order fixture ahead of the S01 authority-ratification gate; absent from architecture's state table; schema wins by the dossier's own precedence rule | `investment-case-lineage-v1.schema.json:321-327`; `staged-order-set-v1.schema.json:59-63` (verified) | S00 |
| **NS-02** | AI agent is the *sole* registered thesis producer; no governed intake for James-authored theses; no migration of existing holdings' theses → Capital-Under-Discipline structurally ≈ 0 over the real portfolio; "his own conviction" criterion inverted | `roadmap.yaml:487`; AC-07 | S02 |
| **MI-01** | review-context schema omits the freeze fields its own sprint mandates: no `knowledge_cutoff`, no report `sha256`, no loader/code version, no `published_at`/`available_at` on evidence | schema vs `s04:72-96` | S04 |
| **MI-02** | dependency-isolation-evidence `covered_outputs` is a closed 10-enum (evaluator only) — cannot represent the review/staging isolation proofs AC-18/architecture demand | schema `:140-158` | S04 |
| **RI-01** | Assessment content unauthenticated: reviewer identity = constant-table equality; fabricated PASS assessment passed the validator (attack replayed); no bundle registry binds content→reviewer→prompt bytes | validator `:73-104, 1962-1979` | S05 |
| **RI-02** | Freshness threshold producer-supplied and unanchored (`policy_id: "review-freshness-v1"` resolves to nothing); 2020-era evidence re-validated FRESH → PAPER_ELIGIBLE (attack replayed) | validator `:1862-1878` | S04 |
| **RI-04** | ReviewContext omits catalysts/falsifiers/discipline wrapper that the contract allowlist and AC-15 promise to bind; the report's `critical` falsifier is structurally invisible to all five reviewers | schema `required` + `additionalProperties:false` | S04 |
| **EV-01 (=PC-08)** | Day-count CGT (`minimum_holding_days: "365"`, basis const) violates rule #6 / spec §5.1; calendar rule structurally inexpressible; sign-definite upward bias on after-tax returns | `tax-profile-valid.json:40-41` (verified); schema `:157,169-175` | S00 (contract), S10 (adapter) |
| **EV-02 (family with DC-02/DC-03)** | Six contracts claim validator recomputation that does not exist (episode-outcome, benchmark session_return, portfolio-snapshot totals, paper-fill rules, paper-order chronology, branch-NAV Dietz/rollforward/digest-equality); fill-fraction only equality-checked between two fixtures | greps verified per item | S00 (honesty fix), S09–S11 (implementation) |
| **EV-03** | No pre-registered gate-evaluation schedule → optional stopping (zero-skill pass probability ~20–30% over 2y of daily looks vs nominal 10%); Holm family of 1 degenerate | evaluation-policy fixture; contract silence | S08 |
| **AS-01** | James-decision artifacts structurally unauthenticated (`decided_by`/`ratified_by` const `"James"`); S01 lane has the LLM authoring the Model A approval record; CODEOWNERS doesn't cover `programs/**` or `roadmap.yaml` | schemas; `.github/CODEOWNERS` | S00 |
| **AS-02** | Dossier self-ratifies ("accepted"/"locked"/"Decision date 2026-07-24") with no acceptance artifact on main (decision-log/james-inbox verified untouched); DEC-025 is the honourable exception | `decisions.md:3-5`; `CLAUDE.md:13` | S00 (merge = acceptance, recorded) |
| **PC-04** | No oversell/sellable-quantity reconciliation; `current_weight` self-declared, never derived from snapshot holdings → naked sell of an unheld name stageable | validator `:2837, :3276`; grep sellable/held = 0 | S07 |
| **PC-05** | No cash-solvency floor at sizing: `projected_cash_aud` checked for equality with summary, never ≥ 0 or ≥ cash buffer | validator `:3305` | S07 |
| **PC-06** | Stale price basis never rejected: `max_price_age_seconds=900` never enforced at proposal, sizing, or staging | grep = 0 | S07 |
| **DR-03** | S02–S06 have no mission decomposition — one 12h window carries migration+service+CLI+ops, the exact pattern the ops doc forbids for S07–S11 | `s05:5,110-116,190`; `ops:311-325` | S00 (re-plan) |
| **DR-05** | Licensed XJO-TR/price/action/calendar procurement sits inside 12h mission S08-A; a vendor negotiation no Claude session can complete gates 4 sprints | `s08:122-124` | S00 (hoist to week-1 James lane) |
| **DR-06 / DR-08** | Exit gates self-asserted (no AC→test manifest; closer grades own work) / M-A2/M-A3 unscheduled while release gate R1 hard-depends on them, with no defined path under a NOT APPROVED decommission decision | `acceptance-matrix.md:8-11`; `ops:146-148` | S00 |

### P2 — fix within the programme (24)

NS-03 (programme north stars unmapped to ratified charter; "changes the north star" wording; amendment unscheduled) · NS-04 (initiative→NS attribution inflated: GOV-01/PORT-01 claim NS-ALERT with no mechanism) · NS-05=DR-07 (s01 claims AC-26–27, locked S06/S07 — shipped `DOSSIER_DRIFT`, week-1 halt; verified) · NS-06 (moat layer 3 zero sprints, layer 1 only S12 — deliberate deferral unrecorded) · MI-03 (perturbation targets archive, not live tables; deny list prose-only and divergent; `model_versions` in no forbidden list) · MI-04 (no maturation grace window / final post-shutdown archive append — sealed-while-ACTIVE manifest is a mid-stream snapshot presented as the retirement record; last ~21 sessions of outcomes never mature) · MI-05 (`asx journal` writes live `signals` refs into `decisions` rows; in no inventory; survives every decommission predicate — verified `cli/journal.py:40-51`) · MI-06 (legacy `monitor_only` Model A figures in live `theses.report_sections`: no archive class covers them; S03 strip/block/launder trilemma unpicked) · RI-03 (freshness covers 2 of 8 source types) · RI-05 (context scenarios unbound to report scenarios — rewritten bear narrative passed) · RI-06 (blindness = asserted constant booleans; sequential timestamps consistent with non-blind) · EV-04 (strategy bar = epsilon; IR-0.5 strategy passes only ~22% at N=252; packet carries no power/MDE statement) · EV-05 (dirty-session exclusion NMAR; gap re-entry semantics undefined) · EV-06 (no 45-day franking rule — repo already implements TC-21) · EV-07 (7-kind corporate-action coverage vs S10's "at least" list; zero-defect 30-session gate likely unreachable → liveness failure or perpetual clock resets) · DC-04 (measurement pipeline only null/degenerate fixtures; no bootstrap reference vector — needs a CI job under pinned NumPy; no non-initial lifecycle state exercised anywhere) · DC-05 (duplicate artifact IDs silently disable reference checking; repair can launder) · DC-06 (hash canonicalization normative for full JCS, implemented for ASCII subset; NFC undefined) · DC-07 (TAX linkage prose-only: no TAX fixture event; interval/digest rules unchecked) · DC-08 (promotion `gate_decision_ref` = `"3333…"` placeholder; gate booleans self-asserted, could contradict the in-dossier evaluator and pass) · PC-07 (staged `not_before` never validated against trading calendar) · PC-09 (no ETF/LIC/stapled look-through in concentration aggregation; caps are issuer-of-record, not economic exposure) · DR-09 (James ratification latency inside mission clocks; S08 could freeze the evaluator over placeholder policies → post-week-12 cohort-reset trap) · DR-10 (James PR-review throughput absent: up to 15 draft PRs/week at peak; no WIP cap) · AS-03 (four of seven authority docs outside CODEOWNERS; branch-protection enforcement UNRESOLVED) · AS-04 (migration/DB-write authority prose-only while write-capable Supabase MCP grants remain in sessions — pre-existing `m14_candidate_agent_db_role_scoping`, now load-bearing).

### P3 — record and schedule (13)

NS-07 (dependency-isolation contract speculative if decommission approved) · NS-08 (README CUD summary laxer than canonical — omits sizing proof + reconciled accounting) · MI-07 (restore-drill rebuild source unspecified; re-hash tautology reading possible) · MI-08 (float8 export canonicalization unspecified for `signal_outcomes` DOUBLE PRECISION columns) · MI-09 (decay-bundle "queries **or** results" — require AND + reproduction drill) · MI-10 (post-retirement `approved_for_allocation` revival has no mechanical backstop — one additive BEFORE UPDATE trigger, 0034 pattern, live-fire verified per the Phase 2a lesson) · RI-07 (context lacks `investment_case_id`; case binding transitive via lineage only) · EV-08 (20-episode gate false breadth: daily cadence → effective sample ≈1.3; gate on `effective_episode_sample_size`; s11 status-taxonomy drift) · EV-09 (conviction recorded, never scored — no calibration measurement of the question that killed Model A) · EV-10 (policy↔evaluator threshold correspondence not cross-checked; defect-key check vacuous on empty dict) · DC-09 (trading-calendar semantics unvalidated) · DC-10 (thesis-proposal: no registered artifact ID, no invariant checks — mitigated by planned S02 Pydantic) · DR-11 (`investment-case-lineage-v1` introduced_sprint S07 but absent from S07 deliverables) · AS-05 (R2 "immutable decision" author ambiguous — pin as recomputed gate record) · AS-06 (PR unilaterally relabels `ASXOS_PORTFOLIO_BRIEF_ENABLED` unlock condition "superseded" vs unchanged portfolio-conventions.md — stricter, so hygiene not exposure) · TOOL-01 (new test file trips 14 lint errors under ruff ≥0.15 — RUF043/C420; clean under CI-pinned 0.7.0).

---

## C. North-star contribution map

The ratified charter (`docs/product/north-star.md`) defines the output, the three-layer moat (1 thought-process integration · 2 discipline scaffolding · 3 theme stewardship), and success criteria. The programme defines three of its own metrics in `roadmap.yaml` (NS-CUD, NS-ALERT, NS-EDGE) — currently **unmapped** to the charter (NS-03).

| Sprint | Claimed outcome | Causal mechanism | Strength |
|---|---|---|---|
| S01 guardrails/registry/Model A archive | CUD+EDGE (+ALERT unjustified) | Integrity preconditions; moves no metric itself | Indirect (enabling) |
| S02 thesis materializer | CUD | Governed cited draft = CUD numerator clause | **Strong** |
| S03 immutable broker report | CUD | Evidence-complete report clause; operationalizes the charter's broker-report reframe | **Strong** |
| S04 point-in-time context + Model A decoupling | CUD | Evidence-quality precondition for exact review | **Strong** |
| S05 blind review + eligibility | CUD | Mechanizes moat layer 2 (pre-commitment vs confirmation bias) | **Strong** |
| S06 monitoring + revision proposals | CUD+ALERT | The identify→monitor→change loop; the HUBS-stop failure criterion; latency measured directly | **Strong — most direct charter hit** |
| S07 construction/risk/sizing | CUD+EDGE (+ALERT unjustified) | Deterministic sizing proof clause; frozen lineage for EDGE | **Strong** CUD / enabling EDGE |
| S08–S09 evaluator foundations, fills/ledger | EDGE | Pre-registered protocol validity; unbiased shadow returns | Strong (enabling; pays off ≥252 sessions post-S12) |
| S10 actions/FX/tax/NAV | CUD+EDGE | Reconciled-accounting clause + after-tax leg | **Strong** |
| S11 outcomes/gates | CUD+EDGE | The measurement apparatus of NS-EDGE itself | **Strong** |
| S12 staging + surfaces | CUD (+ALERT/EDGE indirect) | Terminal non-routable package; one CLI/brief truth; starts the runway clock | Strong CUD |

**Weak/unjustified work:** NS-ALERT attributions on GOV-01/PORT-01 (no mechanism — NS-04); `dependency-isolation-evidence-v1` as a permanent contract for a model being decommissioned (NS-07). **Charter coverage gaps:** moat layer 3 (theme stewardship) receives zero sprints; layer 1 (the morning ritual) only S12 rendering; five-plus sprints build EDGE measurement whose first possible payoff is ~a year after S12. Both are defensible prioritisations — the evidence machinery is the encoded Model-A-decay lesson — but they are prioritisation decisions the charter reserves to James, and no decision records them (NS-06).

---

## D. Contract and harness gap matrix

36 contracts ↔ 36 schemas 1:1 (+ `evaluator-common` shared defs + `roadmap.schema` = 38; no orphans — verified). Root `canonical_hash` recomputation is genuine, enforced, and tested; all schemas are closed (`additionalProperties:false`) at every level. The systematic pattern: **the decision side (research→review→proposal→sizing→staging structure) is genuinely recomputed with mutation-based negative tests; the measurement side (fills→NAV→outcomes→statistics→promotion) is largely schema-valid but label-trusted, with null/degenerate fixtures.**

| Contract | Semantic recompute | Negative tests | Material gaps |
|---|---|---|---|
| thesis-proposal | refs-only | none | no registered ID; invariants unchecked (DC-10) |
| broker-report | partial (bytes via candidate hash) | via review tests | figure provenance rules unvalidated |
| review-context | **full** | many | freshness threshold unanchored (RI-02); missing freeze fields (MI-01); catalysts/falsifiers absent (RI-04) |
| reviewer-assessment | **full** (identity=constant table) | yes | content unauthenticated (RI-01) |
| review-eligibility | **full** (decision re-synthesized) | many | — |
| investment-case-lineage | **full** | yes | duplicate-ID handling (DC-05) |
| portfolio-proposal | **full** (waterfall, weights, loss-at-stop) | yes | liquidity caps unenforced (PC-03) |
| sizing-decision | full for structure; **limits producer-attested** | yes | PC-02/04/05/06 |
| staged-order-set | full-ish | yes | policy unbound (PC-01); calendar unbound (PC-07); INVALIDATED/EXPIRED never exercised |
| paper-intent | partial | ref-level | **line binding unenforced + fixture hash wrong (DC-01, P0)** |
| paper-order / paper-fill | refs-only / partial (money recomputed) | thin | causality/participation/limit self-asserted (DC-03) |
| branch-ledger | partial (debits=credits recomputed) | yes | TAX linkage prose-only (DC-07) |
| branch-nav | partial (component identity) | NAV only | Dietz/rollforward/digest-equality absent (DC-03); single-entry fixture |
| episode-outcome | **refs-only despite claimed full recompute** | none | DC-02; MATURED path zero fixtures |
| cohort-statistics | partial (seed, protocol, Holm counts) | protocol drift only | estimates/bounds self-asserted; no golden vector (DC-04) |
| paper-evaluator | partial (counts, gate predicates) | yes | gate inputs cross-copied, not derived |
| promotion-decision | partial (internal consistency + James const) | yes | gate hash placeholder (DC-08); identity unauthenticated (AS-01) |
| benchmark-snapshot / portfolio-snapshot | refs-only despite claimed recomputes | none | DC-03; only fixture = empty portfolio |
| security-classification-snapshot | **full** | yes | no ETF/LIC look-through (PC-09) |
| trading-calendar / tax-profile | refs-only | none | DC-09; day-count CGT (EV-01); no 45-day rule (EV-06) |
| model-a-archive-manifest / restore-evidence | **full** (restore proof recomputed) | yes incl. spoofs | rebuild source unspecified (MI-07); float8 (MI-08); no final post-shutdown append (MI-04) |

Cross-cutting: canonicalization normative-vs-implemented mismatch (full JCS vs ASCII subset, DC-06); duplicate-ID silent disable (DC-05); no fixture anywhere exercises a non-initial lifecycle state; idempotency is a programme-level rule with per-contract keys only where noted.

---

## E. Revised 12-sprint plan

**Framing decision (evidence-based, per the review standard's "do not weaken requirements to make the schedule fit"):** twelve *sprints* are preserved; twelve *calendar weeks* are not, because the dossier's own declared mission windows sum to ~368 attended hours with 52–56h peak weeks (DR-01 — concrete arithmetic, not preference). The revised plan keeps every sprint outcome and every gate, adds a Sprint 0 repair week, decouples sprint from week (a sprint closes on its exit evidence; the calendar is a projection), and publishes two honest calendars:

- **Aggressive:** 13 sprints in ~14–16 weeks — requires James at ~25–30 attended h/wk and same-week PR review turnaround.
- **Realistic:** 13 sprints in ~20–24 weeks at ~15–18 attended h/wk, with S07 and S10–S11 spanning two weeks each.

Two parallel lanes start in week 1 and are owned by James, not by missions: **PROC-01** (licensed XJO-TR + prices/volumes + corporate actions + calendar provider resolution — a purchasing decision; deliverable = provider manifest fixture consumed by S08's entry criteria) and **DEC-SHEET** (the `JAMES_INPUT_REQUIRED` policy-value sheet — issued at S06 close, due before S07-C, so the evaluator lineage is never frozen over placeholder policies (DR-09)). The M-A2/M-A3 Model A shutdown lane is scheduled (conditional on DEC-025 approval) no later than alongside S04, and release gate R1 gets an explicit predicate under BOTH the APPROVED and NOT APPROVED branches (DR-08).

### S00 — Dossier repair & ratification (new; entry: James accepts this review's findings)

**Outcome:** the dossier is internally true — every contract claim about the harness is either enforced or explicitly re-labelled; the four financial-semantics defects are corrected; delivery is re-baselined; acceptance is a recorded James act.
**Missions (dependency order):**
- **S00-A (12h) — capital-path harness enforcement.** Fix DC-01 (line-binding recompute + corrected fixture hash), PC-01 (staging policy resolution: adverse fraction, tick band, Σ notional+fees ≤ SIZED), PC-02 (bind `limit_value` to policy per code; assert `PASS ⇒ observed ≤ limit` with a `comparison` discriminator; fix the shipped LOSS_HEADROOM fixture), PC-03 (ADV/spread/participation recompute), PC-04/05/06 (oversell, cash floor, price age), DC-05 (duplicate-ID hard error). Each fix lands with the mutation test that previously passed now failing.
- **S00-B (12h) — measurement-side honesty + financial semantics.** EV-01/PC-08 (calendar CGT rule replaces day-count in contract+schema+fixture, citing spec §5.1), EV-06 (45-day franking block, reusing TC-21 semantics), EV-02/DC-02/DC-03 (per claimed recompute: implement it, or amend the contract to name the production service with an explicit "not harness-enforced" marker — implementing preferred; all stdlib-Decimal computable), DC-08 (resolve promotion `gate_decision_ref` to the in-dossier evaluator; require gate-boolean equality), DC-04 (one MATURED golden chain: 5 sessions × 5 branches, non-null returns, recomputed; bootstrap reference-vector job specced for CI full-check), DC-07 (TAX fixture event + interval/digest checks), EV-03/EV-04 (pre-registered analysis schedule + real economic hurdle + MDE/power fields in evaluation-policy), EV-10 (policy↔evaluator threshold cross-check).
- **S00-C (8h) — authority, vocabulary, and plan repair.** NS-01 (`ADVICE_READY` → `STAGING_ELIGIBLE` or architecture-table alignment, one change across schema/contract/fixtures/architecture), NS-05/DR-07 (s01:9 → AC-01–05), AS-01/AS-03 (code-owner coverage extended to the programme tree, the roadmap manifest, and all seven authority documents; branch-protection verification recorded; James-decision artifacts defined as "merge of a code-owner-reviewed PR authored via an attended `asx` command with paired `governance_events` row" — 0034 pattern), AS-02 (status lines → "proposed; James's merge of PR #70 constitutes acceptance"; decision-log row + james-inbox clearance drafted for the merge), AS-06 (gate-condition text reconciled "whichever is stricter"), NS-03/NS-04/NS-08 (NS mapping to charter; attribution subsets; README CUD pointer), DR-03 re-splits written into S03–S06 docs, DR-04 brownfield-survey mission added ahead of S07, DR-05 PROC-01 lane row, DR-06 `acceptance-tests.yaml` manifest + validator consumption, DR-08 M-A2/M-A3 roadmap rows + R1 dual-branch predicate, MI-05 (`journal.py` added to the M-A1 inventory; trace roots widened to all product entry points), MI-06 (S03 legacy `monitor_only` strip rule + fixture).
**Exit gate:** validator + 111-test suite + all new mutation tests green; every P0/P1 correction either landed or explicitly deferred by a James decision recorded in decisions.md.
**James decision required:** accept findings; ratify merge-as-acceptance mechanics; choose aggressive vs realistic calendar; PROC-01 kickoff.

### S01 — Guardrails, registry, Model A archive (re-split per DR-02)

**Outcome (unchanged):** proposal registry live; dossier validator in CI; Model A read-only inventory/archive/restore/decision packet.
**Missions:** S01-a (8h) validator CI wiring + `acceptance-tests.yaml` enforcement · S01-b (12h) registry + walker + envelope decoder + tests · S01-c (8h) CLI/command/service adapters + tests · S01-M02 (12h) Model A inventory/archive/restore drill (with MI-07 rebuild-source rule, MI-08 float8 pin, MI-09 "queries AND results" + reproduction drill recomputing the 19,032-row headline numbers).
**Entry:** S00 closed. **Exit:** AC-01–05 via manifest-named tests. **James:** DEC-025 APPROVED / NOT APPROVED on the M02 packet (the decision record is ratified by James's merge, not authored into effect by the LLM lane — AS-01). **Deferred:** M-A2/M-A3 execution (own lane).

### S02 — Thesis proposal materializer

As specified (it was TIGHT, not oversized), plus the NS-02 resolution James chooses: either a second registered producer for James-authored theses through the same validation/review pipeline, or a recorded decision accepting agent-only intake **plus** a scoped re-materialization plan for existing holdings' theses so CUD is non-degenerate. **Exit adds:** projected-CUD report over current real holdings.

### S03 — Immutable broker report (split A/B per DR-03)

S03-A (12h) migration + version service + JCS hash (DC-06 canonicalization decision applied: ASCII-normative or full-JCS with vectors) · S03-B (12h) projection + CLI + evidence + MI-06 legacy `monitor_only` strip rule with audited exclusions. **James:** DC-06 canonicalization choice.

### S04 — Review context + Model A decoupling (split A/B)

S04-A (12h) point-in-time loader + serializer/hash, with MI-01 schema fix (knowledge_cutoff, report sha256, loader version, published/available chronology) and RI-02 ratified freshness-policy artifact (all 8 source types, RI-03) · S04-B (12h) reviewer adapters + RI-04 context binding of catalysts/falsifiers/discipline + RI-05 scenario binding + RI-07 case-ID + MI-02 isolation-evidence enum extension + injection/deny tests. **Parallel lane:** M-A2 (if DEC-025 approved).

### S05 — Blind review + eligibility (split A/B)

S05-A (12h) migration + repositories + evidence PR · S05-B (12h) blind orchestration + RI-01 bundle registry (recomputed identity content hashes — no longer production-deferred; it is the load-bearing authentication of the chain) + deterministic synthesizer + full truth table + CLI + RI-06 blindness documented as process control with sealed-input evidence. **Parallel lane:** M-A3 (if approved; includes MI-04 maturation-grace sequencing + final archive append + MI-10 revival-block trigger, live-fire verified).

### S06 — Monitoring + revision proposals (split A/B)

S06-A (12h) migration + event/impact/latency pure functions · S06-B (12h) scheduled job + delivery + Render/deadman/drift ops evidence (the James-gated apply is its own calendar item, not inside the window). **Exit adds:** DEC-SHEET issued to James.

### S06.5 — Brownfield survey (new, one 8h mission — DR-04)

Existing-code reuse tables with exact paths for S07–S12: legacy allocator disposition (freeze/tombstone/coexist), `holding_lots`/`current_holdings` ownership, tax-engine integration surface (`asxos/domain/tax/*`), brief compose integration (`asxos/brief/compose.py` gates), security-master field audit (issuer/group/board-lot/tick vs PC-09 look-through reality), corporate-action source audit (vs EV-07 coverage). Re-estimate S10/S12 afterwards. **Exit:** every S07–S12 sprint doc has a reuse table with ≥1 resolving repo path (validator-enforced).

### S07 — Construction, risk, sizing (5 missions as declared; 2 weeks realistic)

As specified plus the S00-A capital-path checks now enforced end-to-end (PC-01…06 are entry criteria, not aspirations). **Entry:** DEC-SHEET returned — at least one James-ratified policy bundle with non-rejection golden vectors (DR-09). **James:** all policy values; PC-09 caps documented as issuer-of-record until a look-through source exists.

### S08 — Evaluator foundations (2 weeks realistic)

As specified minus procurement (PROC-01 resolved it; S08-A only pins identities). Adds EV-03 pre-registered analysis schedule, EV-04 economic hurdle + MDE fields, EV-05 dirty-session/gap re-entry semantics, EV-08 `effective_episode_sample_size` gate. **Entry:** PROC-01 manifest resolves; ratified non-rejection policy bundle exists.

### S09 — Paper orders, fills, ledger (2 weeks realistic)

As specified; DC-03 fill causality/participation/limit recomputes are entry criteria. WIP cap active: no start while >2 of S08's product PRs unmerged (DR-10).

### S10 — Actions, FX, tax, NAV (2–3 weeks realistic; the honest worst case)

As specified plus: EV-01 calendar-CGT adapter reusing the existing tax engine; EV-06 45-day franking; EV-07 corporate-action coverage extended to the full "at least" list **before** the zero-defect bar is ratified, with a defect-arrival model against actual holdings and a bounded `RESOLVED_WITHIN_N_SESSIONS` path that does not reset the streak on exact retroactive repair.

### S11 — Outcomes, statistics, gates (2 weeks realistic)

As specified plus DC-04 golden MATURED chain + CI bootstrap reference vector; EV-08 taxonomy fixes; EV-09 conviction-calibration diagnostic block (no gate authority); EV-10 threshold cross-checks.

### S12 — Staging, CLI/brief, release (1–2 weeks)

As specified plus PC-07 calendar binding; MI-05 all-entry-point trace roots; AS-05 R2 decision pinned as recomputed gate record; S12-D James disposition unchanged. **Exit:** R1 checklist passes under whichever DEC-025 branch is live; 30/252-session clocks start only after James authorises hidden observation.

**Explicitly deferred beyond the programme (unchanged from the dossier, endorsed):** external-fill reconciliation, capital-universe expansion, any UNCALIBRATED visibility (R3) or evidence language (R4), broker capability (never).

---

## F. Claude execution recipes

The dossier's own `prompts/eight-hour-mission.md` / `twelve-hour-mission.md` / `sprint-start.md` / `sprint-close.md` are sound harnesses (verified: correct freeze discipline, PR ceilings, NOT-READY escape). Recipes below parameterize them; every mission inherits: **forbidden scope** = no merge, no production migration apply, no deploy, no Model A runtime change, no broker capability, no authority-document edit outside an M-A2 mission, no self-declared James decision; **rollback** = branch-only work, revert = close PR unmerged; **completion** = named acceptance tests green on the mission branch + evidence packet + `acceptance-tests.yaml` rows updated.

### S00-A — capital-path harness enforcement (12h) — full recipe

- **Objective:** the validator rejects every stageability attack reproduced in this review.
- **Ingest:** this packet §B (DC-01, PC-01…06, DC-05); `scripts/validate_investment_program.py` `_validate_portfolio_semantics`/`_validate_staging_semantics`; fixtures `sizing-valid.json`, `sizing-origin-valid.json`, `paper-intent-valid.json`, `staged-order-valid.json`, `staging-policy-valid.json`, `risk-policy-valid.json`; contracts staging/sizing/risk-policy.
- **Changes:** validator only + fixture corrections (line-hash `8eb3140d…`→recomputed `1511834c…`; LOSS_HEADROOM limit corrected to a true headroom semantics with explicit `comparison` field added to schema); no runtime code.
- **Data-contract changes:** sizing-policy/staged-order schemas gain `comparison` discriminator; version-bump per the dossier's own rules.
- **Tests:** one mutation test per attack, asserting `DossierError`; the six attacks from this review are the test cases.
- **Failure injection:** re-run each original perturbed fixture — all must now fail.
- **Evidence:** validator PASS on repaired tree; attack matrix re-run table (6× PREVENTED).
- **Handoff:** list any contract sentence still promising an unimplemented check (must be zero or re-labelled).

### S00-B — measurement honesty + financial semantics (12h) — full recipe

- **Objective:** no contract claims a recompute the harness doesn't perform; the two sign-definite tax biases are structurally inexpressible.
- **Ingest:** §B EV-01/02/03/04/06/10, DC-02/03/04/07/08; `docs/foundation/spec/tax-alpha.md` §5.1, §4.3; `asxos/domain/tax/dividends.py::check_45_day_warnings` (TC-21, reference semantics only — do not modify runtime).
- **Changes:** tax-profile contract+schema+fixture (calendar CGT rule; franking holding block); evaluation-policy (analysis schedule, economic hurdle w/ provenance, MDE field); implement the six claimed recomputes (stdlib Decimal) or re-label with "production-service-enforced" markers — implementing preferred; promotion gate-ref resolution; MATURED golden chain fixture; TAX ledger event + interval/digest checks; threshold cross-check.
- **Tests:** golden CGT boundary vectors (365-day fail / +1-day pass / leap variant); 44-vs-46-clear-day franking; per-recompute mutation tests; promotion-vs-evaluator disagreement test.
- **Failure injection:** perturb `session_return`, NAV rollforward, fill fraction, gate booleans — each must fail.
- **Evidence:** before/after table of "claimed vs enforced" per contract.
- **James decision consumed:** economic-hurdle value (from DEC-SHEET-0).

### S00-C — authority, vocabulary, plan repair (8h) — full recipe

- **Objective:** the dossier stops asserting its own acceptance; James-gated decisions have a mechanical shape; the plan is arithmetically honest.
- **Ingest:** §B NS-01/03/04/05/08, AS-01/02/03/06, DR-03/04/05/06/07/08, MI-05/06; the repo's code-owner file; `docs/product/decision-log.md`.
- **Changes:** docs + code-owner coverage + roadmap.yaml only (re-baselined weeks/mission tables per §E; `week` marked non-normative in `roadmap.schema.json` or re-numbered); drafted decision-log row + james-inbox item for the merge; `acceptance-tests.yaml` skeleton + validator consumption.
- **Tests:** validator cross-checks sprint AC headers vs matrix (fails on the pre-fix bytes — the DR-07 self-test); initiative NS-subset rule; reuse-table ≥1-path rule armed for S07–S12 (activates at S06.5).
- **Evidence:** diff of every "accepted/locked" → "proposed; merge ratifies" line; code-owner coverage table.
- **James decision consumed:** acceptance mechanics; calendar choice; PROC-01 kickoff.

### S01–S12 — recipe parameters (dossier prompt harness + these deltas)

| Mission | One verifiable outcome | Key ingest beyond sprint doc | Injection to prove |
|---|---|---|---|
| S01-a (8h) | CI runs validator + manifest gate; a close claiming an unmanifested AC fails | S00-C manifest | fabricate a close.md claiming AC-27 → typed failure |
| S01-b (12h) | registry resolves every producer; unknown producer denied | `agent_run_service.py`, guards | unregistered producer envelope → deny |
| S01-c (8h) | CLI adapters route through registry; legacy paths unchanged | `cli/agent_run.py` | direct-write bypass attempt → deny |
| S01-M02 (12h) | sealed manifest + attended restore drill reproducing decay headline numbers | MI-07/08/09 rules | corrupted-but-rehashed archive → FAIL not PASS |
| S02 (12h) | one governed draft materialized end-to-end, concurrency-safe | S02 doc; NS-02 decision | mid-write failure → full rollback; double-consume → one result |
| S03-A (12h) | immutable version table + hash service live in integration Postgres | DC-06 decision | non-ASCII payload → per-decision reject/round-trip |
| S03-B (12h) | report built from a real legacy thesis; `monitor_only` figures excluded with audit | MI-06 fixture | re-labelled ML figure → provenance failure |
| S04-A (12h) | context with full freeze fields recomputed from live-shaped data | MI-01 schema | `published_at > knowledge_cutoff` → reject |
| S04-B (12h) | five adapters fed context-only; isolation evidence covers review classes | MI-02 enum | adapter given DB tool → deny test |
| S05-A (12h) | five tables migrated in integration; repositories transactional | DR-03 split | trigger-order live-fire (rolled-back txn — the Phase 2a lesson) |
| S05-B (12h) | full truth table passes; fabricated assessment rejected via bundle registry | RI-01 registry | constant-identity forgery → reject |
| S06-A (12h) | latency engine pure functions with ASX-session arithmetic | s06 doc | synthetic event → correct P95 in trading time |
| S06-B (12h) | one synthetic end-to-end alert delivered; deadman wired | ops doc | job failure → deadman fires, brief omits section |
| S06.5 (8h) | reuse tables for S07–S12 with resolving paths; re-estimates published | DR-04 list | validator fails a pathless sprint doc |
| S07-A…E | per dossier (5 missions) | S00-A checks as entry | the six §B attacks re-run against the *implementation* |
| S08-A…D | per dossier; PROC-01 pinned | EV-03/04/05/08 deltas | gate evaluated off-schedule → non-primary label |
| S09-A…D | per dossier | DC-03 recomputes as entry | fill before eligible event → reject |
| S10-A…E | per dossier + EV-01/06/07 adapters | tax engine surface (S06.5) | CGT/franking golden vectors; demerger postings |
| S11-A…E | per dossier + DC-04 vectors | CI bootstrap job | perturbed reference vector → CI fail |
| S12-A…D | per dossier + PC-07/MI-05/AS-05 | all-entry-point trace | journal.py post-shutdown emits no signal_ref |

---

## G. Decision register

### Already ratified (in-repo record exists; not re-litigated)

- Rule #11 Model A quarantine as **standing** policy; ML engine shelved (CLAUDE.md; `ml-engine-shelf-2026-07-11.md`; decay analysis).
- Single-user posture, NUMERIC(18,6), calendar CGT arithmetic (rule #6), tax-spec authority, hard-fail infra (CLAUDE.md non-negotiables).
- M13 portfolio conventions incl. `ASXOS_PERSONAL_USE` firewall and the contamination-isolation model gate.
- The P0 question answered against Model A (2026-07-11) and Phase 2c reframed model-independent.

### Implied by the dossier but NOT ratified by any repo record (require James's explicit act — normally his merge of the repaired PR, recorded in decision-log)

- **DEC-001–DEC-024 as a block** — plausibly agreed in the 24h planning conversation, but the repo's own governance has no acceptance artifact (AS-02). Material items deserving conscious re-confirmation at merge: DEC-001 (product pivot from decision-support wording to direct tailored output + `ORDER_STAGED`), DEC-017 (long-only XASX/AUD capital universe), DEC-018 (loss-at-risk construction replacing the M13 composite-score approach), DEC-012 (three programme north-star metrics).
- The **"accepted" status of the dossier itself** and its CLAUDE.md/docs-README authority re-pointing.
- **Agent-only thesis authorship** (NS-02) — never explicitly decided anywhere.
- **Theme-stewardship/morning-ritual deferral** for the programme window (NS-06).
- **`ASXOS_PORTFOLIO_BRIEF_ENABLED` unlock-condition supersession** (AS-06).

### Claude (arbi) recommends

- Run **S00 before S01**; land all P0/P1 corrections at the contracts/fixtures/validator layer before any implementation session reads the dossier as authority.
- **Merge-as-acceptance** made explicit and recorded (decision-log row + james-inbox clearance in the same merge).
- **DEC-025 concur**: full runtime decommission with immutable restorable evidence is the right target (it converts a prose quarantine into structural absence and protects cohort validity) — with the MI-04 sequencing fix (disable → maturation grace → final tracker run → final archive append), MI-09 "queries AND results", MI-10 revival-block trigger, and an honest note that the shelf doc's free-monitoring revival lane is being given up.
- **Re-baseline delivery** per §E (12 sprints, honest calendar, two parallel James lanes, WIP cap).
- **Scope sprint-session DB tools to read-only** (`supabase-ro`) and extend code-owner coverage per AS-01/03/04 — the pre-existing `m14_candidate_agent_db_role_scoping` gap becomes load-bearing under this programme.
- Set the **economic hurdle** to a provenance-backed number and add the **pre-registered analysis schedule** before any evaluator lineage freezes.

### Only James can decide

1. Accept/reject this review's findings and the S00 repair plan (the stop-condition decision).
2. DEC-025 — Model A runtime decommission: APPROVED / NOT APPROVED (at S01-M02).
3. DEC-001 reconfirmation — direct tailored output + `ORDER_STAGED` as the product target.
4. Calendar: aggressive (~14–16 wk) vs realistic (~20–24 wk), i.e., his attended hours/week.
5. PROC-01 — pay for / source licensed XJO-TR and market data (a purchasing decision).
6. NS-02 — James-authored thesis intake path vs agent-only drafting.
7. Every `JAMES_INPUT_REQUIRED` policy value (cash, leverage, loss budgets, concentration, liquidity, staging, economic hurdle).
8. DC-06 — canonicalization: ASCII-normative wire rule vs full-JCS with vectors.
9. NS-06 — ratify (or reject) the programme-window deferral of moat layers 1 and 3.
10. Merge, and every future migration apply / deploy / release gate — unchanged.

---

## H. Proposed document patches (no edits made — this is the S00 work order)

### H1. Blocking corrections (gate: before any sprint session treats the dossier as authority)

1. `scripts/validate_investment_program.py` — staging semantics: resolve `staging-policy-v1` by hash; assert order adverse fraction == policy; tick from classification band; Σ staged notional + fees ≤ SIZED (PC-01).
2. Same file — sizing semantics: read `limit_value`, bind to policy per constraint code, assert `PASS ⇒ observed ⊴ limit` with schema `comparison` discriminator (PC-02); enforce `liquidity_limits` (PC-03); derive `current_weight` from snapshot holdings + oversell check (PC-04); `projected_cash ≥ cash_buffer` (PC-05); price-age windows at proposal/sizing/staging (PC-06); duplicate-ID hard error (DC-05).
3. `fixtures/paper-intent-valid.json` — correct `sizing_line_sha256` to the recomputed line digest; add line-binding recompute to validator (DC-01). `fixtures/sizing-valid.json` — correct the LOSS_HEADROOM check to true semantics.
4. `contracts/tax-profile-v1.md` + schema + fixture — replace `minimum_holding_days` with the §5.1 calendar rule; forbid bare day-count (EV-01/PC-08). Add `franking_holding_rule` (45 clear days, §4.3 / TC-21) (EV-06).
5. Six "the semantic validator recomputes…" sentences (episode-outcome, benchmark-snapshot, portfolio-snapshot, paper-fill, paper-order, branch-nav) — implement or re-label; promotion `gate_decision_ref` resolved to the in-dossier evaluator (EV-02/DC-02/DC-03/DC-08).
6. `evaluation-policy-v1` — pre-registered analysis schedule + `gate_evaluation_count`; real economic hurdle with provenance; MDE/power fields (EV-03/EV-04).
7. Schemas `investment-case-lineage-v1` / `staged-order-set-v1` + fixture + architecture — resolve the `ADVICE_READY` vocabulary conflict (NS-01).
8. `sprints/s01…md:9` — "AC-01–05" (NS-05/DR-07); validator cross-check of sprint AC headers vs matrix.
9. Status/authority language: `decisions.md:3-5`, `README.md:3`, `CLAUDE.md:13` → "proposed; James's merge ratifies"; drafted decision-log row (AS-02). Code-owner coverage extended to the programme tree, roadmap manifest, and all seven authority documents; branch-protection verification recorded (AS-01/AS-03).
10. `roadmap.yaml` + sprint docs — re-baselined mission decomposition (S01 four missions; S02–S06 A/B splits; S06.5 brownfield survey; PROC-01 lane; M-A2/M-A3 rows; R1 dual-branch predicate; `week` non-normative) (DR-01…08).
11. `review-context-v1` schema — freeze fields (`knowledge_cutoff`, report sha256, loader version, published/available) (MI-01); ratified freshness-policy artifact covering all 8 source types (RI-02/RI-03); catalysts/falsifiers/discipline binding or an explicit ratified exclusion (RI-04).
12. `dependency-isolation-evidence-v1` — extend `covered_outputs` to review/staging classes (MI-02). Reviewer bundle registry with recomputed content hashes scheduled in S05 as load-bearing, not production-deferred (RI-01).

### H2. Institutional-quality improvements (within the affected sprints)

Scenario binding context↔report (RI-05) · blindness evidence discipline (RI-06) · context case-ID (RI-07) · dirty-session/gap re-entry semantics + excluded-span reconciliation (EV-05) · corporate-action coverage extension + defect-arrival model before ratifying the zero-defect bar (EV-07) · `effective_episode_sample_size` gate + s11 taxonomy fix (EV-08) · conviction-calibration diagnostic (EV-09) · threshold cross-checks + defect-key enforcement (EV-10) · MATURED golden chain + CI bootstrap reference vector (DC-04) · canonicalization decision + vectors (DC-06) · TAX event fixture + interval/digest checks (DC-07) · calendar semantic checks + staged `not_before` binding (DC-09/PC-07) · thesis-proposal ID + invariants (DC-10) · ETF/LIC look-through or documented issuer-of-record limitation (PC-09) · deny-manifest as pinned artifact incl. `model_versions`; perturbation of live tables not just archive (MI-03) · M-A3 maturation-grace + final archive append (MI-04) · `journal.py` + health-check inventory rows; all-entry-point trace roots (MI-05) · `monitor_only` strip rule + archive-claim correction (MI-06) · restore rebuild-source pin (MI-07) · float8 export rule (MI-08) · decay-bundle AND + reproduction drill (MI-09) · `approved_for_allocation` revival-block trigger (MI-10) · sprint-session DB tools scoped read-only (AS-04) · R2 decision pinned as recomputed record (AS-05) · gate-condition reconciliation (AS-06) · NS mapping/attribution/README fixes (NS-03/04/08).

### H3. Delivery refinements

`acceptance-tests.yaml` AC→test manifest consumed by the validator; close-verdict session ≠ build session stated in `sprint-close.md` (DR-06) · WIP cap + James review-throughput budget in `operations-and-rollout.md` (DR-10) · DEC-SHEET as a standalone deliverable with S08 entry criterion (DR-09) · `investment-case-lineage-v1` introduced-sprint placement fix (DR-11) · initiative NS-subset validator rule (NS-04).

### H4. Optional future extensions (record, do not schedule)

Fold `dependency-isolation-evidence-v1` into evaluator-config if DEC-025 approved (NS-07) · `security_kind` enum migration (pre-existing backlog, aligns with classification snapshot) · regex-escape lint fixes for ruff ≥0.15 (TOOL-01) · post-programme external-fill reconciliation contract (already deferred by the dossier — endorsed).

---

---

## I. Automation lanes (governor question, 2026-07-25: "how can we weave automated work in as well")

The dossier is attended-only by design; the repo already has the machinery to automate safely — the arbi permission tiers, the `ARBI_UNATTENDED=1` unattended-guard hook that mechanically blocks irreversible tiers, Routines/cron triggers, PR-activity subscriptions, and CI. The rule that keeps automation compatible with every §B authority finding: **automate verification and preparation, never decisions.** Three lanes:

**GREEN — unattended, start immediately (verification only, no repo mutation beyond ephemeral runs):**
- CI on every PR: dossier validator + the S00 mutation-test suite + `acceptance-tests.yaml` manifest gate (S01-a). This turns this review's attack matrix into a permanent regression net.
- Nightly Routine: run the validator against `main` + every open sprint branch; report drift/DOSSIER_DRIFT into the session or brief. Weekly `/arbi-dream` consolidation as already governed.
- PR steward on sprint PRs (`subscribe_pr_activity`): autofix CI failures on Claude-owned branches, keep drafts green so James's review time goes to financial semantics, not lint. Reversible tier only — never merges.
- Decision-latency nag: a Routine that watches the DEC-SHEET / PROC-01 / james-inbox items and surfaces overdue governor inputs (DR-09's failure mode is James-latency invisibility, and this is its cheap antidote).

**AMBER — unattended execution, attended acceptance (requires James to opt in per DEC-013's own logic):**
- Overnight execution of **frozen** missions only — DEC-013 already defines the tier: "the contract, invariants, acceptance fixtures, and file scope already exist and no financial meaning is being chosen." A frozen 8h mission (e.g., S01-b registry, S00-A validator fixes after this packet is accepted) can run unattended to a draft PR; morning James/attended-session review is the acceptance step. Mechanics: `ARBI_UNATTENDED=1` + the unattended-guard so migrations/deploys/authority paths hard-deny; sprint sessions scoped to `supabase-ro` (AS-04 — this finding becomes the *enabler* of safe automation, not just a defect); PR ceilings and NOT-READY escape unchanged. A mission that discovers it must choose financial meaning stops with NOT_READY instead of guessing — the dossier's own rule, now load-bearing for automation.
- Automated red-team stage: on every product PR, a fresh-context adversarial agent fan-out (the pattern this review used) posts findings before James looks. Closes DR-06's "closer grades own work" gap with automation rather than more process.

**RED — never automated (mechanically blocked, not just prohibited):**
Migration applies · policy ratification and any `ratified_by`/`decided_by` artifact · promotion/tier decisions · Model A shutdown steps (M-A2/M-A3) · authority-document edits · merge/deploy/release · anything that would write to production Supabase. Enforcement is the AS-01/AS-03/AS-04 corrections: code-owner coverage, read-only DB grants for sessions, unattended-guard, and the 0034-pattern trigger pairing for decision artifacts.

**Net effect:** the 12-sprint calendar's binding constraint is James-attended hours (DR-01/DR-10). GREEN + AMBER lanes move the mechanical share of ~368 mission-hours off his clock — realistic compression from ~20–24 weeks back toward the aggressive ~14–16-week calendar — without any path that acquires authority reserved for him. Recommended sequencing: wire GREEN during S00/S01 (CI + steward are a day of work); pilot AMBER on one frozen S00 mission with a morning-review retro; write the lane definitions into `operations-and-rollout.md` as part of S00-C so automation is governed by the same document set as everything else.

---

*End of review packet. Stop condition reached: no edits to the dossier, no implementation, no merge, no migration, no production action. Awaiting James's decision per §G.*
