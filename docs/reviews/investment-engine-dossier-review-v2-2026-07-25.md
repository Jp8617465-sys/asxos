# Investment-Engine Dossier — Review Packet v2 (delta)

**Supersedes severity and plan sections of:** `investment-engine-dossier-review-2026-07-25.md` (v1)
**Subject:** PR #70 `docs: add investment-engine implementation dossier` (draft)
**Branch/commit reviewed:** `agent/investment-engine-dossier` @ `b9c2f6f82f51dc91ffa0d954b7452cc61d3bb1ce`
**Date:** 2026-07-25
**Status:** delta only. v1's evidence stands except where narrowed below. No dossier edits, no implementation, no merge, no migration, no production action.

**Framing correction accepted:** v1's findings are an evidence packet, not ratified conclusions. Five of James's corrections are accepted in full; two are accepted with a sharpening that the fixture evidence supports; none are rejected. v1's verdict of **AMBER** stands, and the gating effect is unchanged — the dossier must not become implementation authority until the blockers close. What changes is severity vocabulary, three finding statements, the repair vehicle, and the calendar model.

---

## 1. Findings removed or narrowed, and why

### 1.1 Severity vocabulary — all "P0" reclassified to P1 blockers (accepted in full)

v1 used P0 for seven findings. In this repo P0 denotes a production incident. Nothing in the dossier is executable, broker-connected, or capital-touching; the harness defects are pre-merge integrity defects. **DC-01, PC-01, PC-02, PC-03, DR-01, DR-02, DR-04 are reclassified P1-blocker.** The class definition used from here:

> **P1-blocker** — must close before the dossier becomes implementation authority. Not a production incident; no live capital or executable path is affected.

No finding is downgraded in its *gating* effect by this change.

### 1.2 PC-02 — narrowed and re-stated (accepted; fixture evidence sharpens it)

**v1 said:** the validator should assert `PASS ⇒ observed ≤ limit`, and cited `LOSS_HEADROOM observed=15000 / limit=0 / PASS` as a shipped defect.

**That was wrong, and the shipped fixture proves it.** Full enumeration of `sizing-valid.json`'s 18 `NUMERIC_LIMIT` checks shows at least three distinct comparison directions sharing one `check_type`:

| Direction | Checks | Example |
|---|---|---|
| MINIMUM (observed must be ≥ limit) | `AVAILABLE_CASH`, `LOSS_HEADROOM`, `MINIMUM_ORDER`, `BOARD_LOT` | `AVAILABLE_CASH obs=100000.000000 lim=99000.000000 PASS` |
| MAXIMUM (observed must be ≤ limit) | `ISSUER`, `CORPORATE_GROUP`, `SINGLE_NAME`, `SECTOR`, `THEME`, `PORTFOLIO_LOSS_AT_STOP`, `GROSS_EXPOSURE`, `NET_EXPOSURE`, `TURNOVER`, `ADV_PARTICIPATION`, `SPREAD`, `FEES` | `SECTOR obs=0.100000 lim=0.300000 PASS` |
| EXACT / CAP_APPLIED | `TARGET_NOTIONAL`, `RESERVATIONS` | `TARGET_NOTIONAL obs=10000.000000 lim=10000.000000 PASS` |

`LOSS_HEADROOM obs=15000 lim=0 PASS` is therefore **correct** under a MINIMUM reading, and v1's proposed universal rule would have wrongly failed six legitimate checks. v1's own attack constructions remain valid (an `AVAILABLE_CASH` observed of 5.00, or a `MINIMUM_ORDER` limit of 50000 against a 10000 order, must fail) — but they fail under MINIMUM semantics, not under the rule v1 stated.

**Corrected finding PC-02′ (P1-blocker):** the contract defines no comparison discriminator, so `NUMERIC_LIMIT` carries three incompatible meanings under one type and the validator cannot check any of them; and `limit_value` is not derived from a resolved policy/source artifact (validator reads it zero times), so both the direction *and* the bound are producer-supplied.

**Required correction:** add an explicit per-check `comparison` field with values `MINIMUM | MAXIMUM | EXACT | CAP_APPLIED`; annotate all 18 constraint codes normatively in `sizing-policy-v1`; require `limit_value` to resolve from the ratified policy or source artifact identified by `source_ref`; assert direction-correct pass semantics per code.
**Acceptance test:** a check whose action is PASS while violating its declared direction fails; a check whose `limit_value` does not equal the resolved policy value fails; the current shipped fixture passes unchanged once annotated.

### 1.3 EV-06 — reclassified P2, bias claim withdrawn (accepted; evidence supports the withdrawal)

**v1 said:** missing 45-day franking rule produces a systematic ~30bp/event upward bias in after-tax active return.

**Not proven, and two pieces of evidence cut against it.** The fixture's `entity_class` is `INDIVIDUAL_RESIDENT_PAPER_SCENARIO`; the host implementation is `check_45_day_warnings_smsf`, whose docstring states the $5,000 small-shareholder exemption available to individuals does **not** apply to SMSFs — i.e. for an individual below that threshold the credits are legitimately retained and no denial occurs. Separately, `franking_credit_utilization: OFFSET_ESTIMATED_TAX_NO_REFUND_ASSUMED` assumes no refundability, which biases the estimate **downward**. The host rule is also warning-only — credits are never auto-removed (spec §4.3) — so "reuse the repo's implementation" would not have produced a denial either.

**Corrected finding EV-06′ (P2):** the tax profile encodes no explicit franking *eligibility* semantics — no holding-period qualification, no small-shareholder exemption threshold, no entity-conditional switch. The gap is representational, not a demonstrated bias: it becomes material only if the profile is ever SMSF, if credits exceed the individual exemption threshold, or if the capital universe expands. Authoritative warning-only behaviour must be preserved, not converted into automatic denial.

### 1.4 EV-04 — corrected; the epsilon reading was wrong (accepted in full)

**v1 said:** `minimum_stress_cost_active_return: "0.000001"` is an economically meaningless epsilon standing in for the promised hurdle.

**Incorrect.** DEC-024 pins database-bound decimals to exactly six fractional digits; `0.000001` is therefore the *canonical representation of strict positivity*, not a weakened threshold. It faithfully encodes the locked `> 0` gate.

**Corrected finding EV-04′ (P2):** the defect is that the separately promised economic-materiality hurdle, minimum-detectable-effect and power statement (`s08:106`, `s11:107`) exist in no artifact — so James would ratify a `> 0` pass with no statement of what effect size the test could actually detect. **Explicitly not required:** converting that diagnostic into a strategy gate. Raising a ratified gate threshold without a governor decision is itself an authority violation, and v1 came close to recommending one. The correction is a *reported* hurdle/MDE/power block alongside the unchanged `> 0` gate.

### 1.5 EV-03 — retained P1, statistic re-labelled (accepted)

The finding stands: no pre-registered analysis schedule exists, so the gate may be recomputed every session after 252 and reported at the flattering stopping time. The **20–30% figure is re-labelled a plausible single-comparator simulation result, not a proven dual-comparator gate error rate.** The two comparator series (HOLD, XJO-TR) are highly correlated, and no simulation was run against the frozen dependency-aware bootstrap; the direction (nominal 10% is materially understated under repeated looks) is not in doubt, the magnitude is unquantified. Marked UNRESOLVED pending simulation, which S08 should produce as part of pre-registration.

### 1.6 Delivery calendar — assertion withdrawn, replaced by a capacity model (§4)

v1 asserted 20–24 weeks. The ~368 declared mission-hour total is verified and stands, but the calendar inference **conflated agent mission-hours with James-hours** and modelled neither concurrent lanes, overnight frozen missions, nor independent reviewer separation. Withdrawn; see §4. DR-01 is retained as P1-blocker on its true defect — *the dossier contains no capacity model at all* — not on a specific week count.

### 1.7 S00-B scope — withdrawn as unbuildable (accepted)

v1's S00-B combined roughly five to six independent outcomes into one 12-hour window — the exact defect v1 charged against S02–S06 (DR-03). Withdrawn and replaced by the R0 work order in §3, which also adopts the correct principle for measurement kernels: **fix the dishonest wording now, implement the derivations in their owning sprints (S09–S11).** R0 does not duplicate runtime.

### 1.8 Retained without change

DC-01 · PC-01 · PC-03 · EV-01 (day-count CGT) · RI-01 · RI-02 · RI-04 · EV-02 / DC-02 / DC-03 (as wording defects now, implementation requirements in S09–S11) · DC-08 · AS-01 · AS-02 · AS-03 · NS-01 (`ADVICE_READY`) · NS-02 · NS-05/DR-07 · DR-04 · DR-05 · DR-06 · DR-08 · MI-01 · MI-02 · MI-04 · MI-05 · MI-06 · all P2/P3 rows from v1 §B not amended above.

---

## 2. Corrected severity register

**P1-blockers — must close in R0, before PR #70 merges as implementation authority (16)**

| ID | Finding | Vehicle |
|---|---|---|
| DC-01 | Paper-intent→sized-line hash binding unenforced; shipped fixture hash resolves to nothing | R0-A2 |
| PC-01 | Staging trusts its own adverse-price input; no policy resolution, no tick-band binding | R0-A2 |
| PC-01b | Worst-case staged notional + fees may exceed the sizing budget | R0-A2 |
| PC-02′ | No `MINIMUM/MAXIMUM/EXACT/CAP_APPLIED` comparison semantics; `limit_value` not policy-resolved | R0-A1 |
| PC-03 | Liquidity, ADV, spread, price-age rules never recomputed | R0-A1 |
| PC-04/05/06 | Oversell reconciliation, cash-solvency floor, stale price basis unenforced | R0-A1 |
| DC-05 | Duplicate artifact IDs silently disable reference checking | R0-A2 |
| EV-01 | Day-count CGT (`minimum_holding_days: "365"`) violates rule #6 / spec §5.1 | R0-B1 |
| RI-02 | Review freshness thresholds producer-supplied, bound to no immutable policy | R0-B1 |
| DC-08 | Promotion evidence can contradict the evaluator gate and still pass | R0-B1 |
| RI-04 | Reviewer packet omits catalysts/falsifiers/discipline that AC-15 promises to bind | R0-B2 |
| EV-02/DC-02/DC-03 | Six contracts claim harness recomputation that does not exist | R0-B2 (wording) → S09–S11 (implementation) |
| RI-01 | Reviewer identity is constant-equality; assessment content unauthenticated | R0-B2 (schedule as load-bearing) → S05 |
| MI-01 | Review-context schema omits its own mandated freeze fields | R0-B2 → S04 |
| AS-01/AS-02/AS-03 | Acceptance self-ratified; James-decision artifacts unauthenticated; code-owner gaps | R0-B3 |
| NS-01 | `ADVICE_READY` in canonical schemas ahead of the authority gate | R0-B3 |
| NS-05/DR-07 | `s01:9` claims AC-26–27 the matrix locks at S06/S07 — shipped DOSSIER_DRIFT | R0-B3 |
| DR-01/DR-04 | No capacity model; S07–S12 name zero existing modules | R0-C1/C2 |
| DR-05/DR-08 | Data procurement and Model A M-A2/M-A3 lane unscheduled on the critical path | R0-C2 |

**P2 (24)** — as v1 §B, with EV-04′ and EV-06′ replacing their v1 statements, and EV-03's magnitude claim re-labelled. **P3 (13)** — unchanged.

---

## 3. R0 Dossier Repair Gate — exact work order

**Vehicle:** a pre-merge repair gate on PR #70. **Not** a thirteenth sprint; the sprint count stays twelve and the roadmap gains no new sprint row. R0 lands as additional commits on `agent/investment-engine-dossier` (or a stacked branch merged into it) before James merges PR #70.

Three independent lanes; A/B/C touch mostly disjoint file sets and can run concurrently.

### Lane A — capital-path integrity (validator + fixtures; 24h, 2 missions)

**R0-A1 (12h) — constraint comparison semantics and policy-resolved limits.**
Outcome: *every numeric sizing check declares its comparison direction and resolves its bound from a ratified artifact; a direction-violating PASS fails.*
Scope: add `comparison` (`MINIMUM|MAXIMUM|EXACT|CAP_APPLIED`) to the sizing-decision schema; annotate all 18 constraint codes normatively in `sizing-policy-v1`; validator resolves `limit_value` from the artifact named by `source_ref` and asserts direction-correct semantics; fold in PC-03 (ADV/spread/price-age from `risk_policy.liquidity_limits`), PC-04 (`current_weight` derived from snapshot holdings + sellable-quantity check), PC-05 (`projected_cash ≥ cash_buffer`).
Forbidden: changing any threshold value; altering the shipped fixture's PASS outcomes (correctly-annotated fixtures must still pass).
Tests: direction-violation per class; unresolved-limit; the v1 attack set (AVAILABLE_CASH=5.00, MINIMUM_ORDER limit 50000, oversell against empty holdings, negative projected cash) each fail.

**R0-A2 (12h) — lineage and staging binding.**
Outcome: *the reproduced staging attacks fail and every in-dossier reference resolves.*
Scope: DC-01 (line-level `sizing_line_sha256` recompute; correct the fixture digest); PC-01 (resolve `staging-policy-v1` by hash — adverse fraction equals policy, tick from the classification band, Σ staged notional + fees ≤ SIZED); DC-05 (duplicate `(contract, artifact_id)` → hard error); PC-07 calendar binding of `not_before` if it fits the window, else defer to S12.
Tests: the 10%-adverse / over-notional attack fails; a one-nibble line-hash mutation fails; a duplicate ID with changed bytes fails.

### Lane B — authority and contract integrity (contracts/schemas/docs; 28h, 3 missions)

**R0-B1 (12h) — financial-semantics contracts.**
Outcome: *tax, freshness and promotion contracts express the correct rule and are harness-checked.*
Scope: EV-01 (replace `minimum_holding_days`/`ACQUISITION_TO_DISPOSAL_DATE` with the §5.1 calendar rule; schema forbids a bare day-count field); EV-06′ (explicit franking eligibility block — holding-period qualification, small-shareholder exemption threshold, entity-conditional switch — preserving warning-only, never auto-denial); RI-02 (immutable ratified freshness-policy artifact; thresholds resolve from it; RI-03 source-type coverage); DC-08 (promotion `gate_decision_ref` resolves to the in-dossier evaluator; gate booleans must equal the recomputed gate).
Tests: CGT boundary vectors (365-day → no discount; +1 day → discount; leap variant); inflated freshness threshold → reject; promotion disagreeing with the evaluator → reject.

**R0-B2 (8h) — honesty pass and reviewer-packet completeness.**
Outcome: *no contract sentence claims harness behaviour that does not exist.*
Scope: for each of the six claimed recomputes (episode-outcome, benchmark `session_return`, portfolio-snapshot totals, paper-fill rules, paper-order chronology, branch-NAV Dietz/rollforward/digest), either implement a bounded check where it is genuinely small, or **relabel the sentence as a named S09–S11 implementation acceptance requirement with an AC id** — full kernel work stays in its owning sprint; RI-04 (bind catalysts/falsifiers/discipline into the reviewer packet, or record a ratified exclusion); schedule RI-01 (bundle registry with recomputed identity hashes) and MI-01 (context freeze fields) into S05/S04 as load-bearing, not production-deferred.
Forbidden: implementing benchmark/fill/NAV/outcome/statistical kernels here.

**R0-B3 (8h) — authority mechanics and vocabulary.**
Outcome: *the dossier no longer asserts its own acceptance and James-gated decisions have a mechanical shape.*
Scope: AS-02 (status lines → "proposed; James's merge of PR #70 ratifies"; drafted decision-log row + james-inbox item); AS-01/AS-03 (code-owner coverage over the programme tree, roadmap manifest and all seven authority documents; branch-protection verification recorded; decision artifacts defined as code-owner-reviewed merge + attended command + paired `governance_events` row, 0034 pattern); NS-01 (`ADVICE_READY` resolved across schema/contract/fixture/architecture); NS-05 (`s01:9` → AC-01–05) plus the validator cross-check that fails on the pre-fix bytes; AS-06 gate-condition reconciliation; NS-03/04/08 north-star mapping, attribution subsets, README pointer.

### Lane C — delivery grounding (planning docs; 20h, 2 missions)

**R0-C1 (12h) — brownfield path survey.**
Outcome: *every S07–S12 sprint doc carries a reuse table with resolving repository paths, and the affected sprints are re-estimated.*
Scope: legacy allocator disposition (freeze / tombstone / coexist); `holding_lots`/`current_holdings` ownership; tax-engine integration surface; brief-compose integration point and its gates; security-master field audit for issuer/group/board-lot/tick (feeds the PC-09 look-through reality check); corporate-action source audit against EV-07 coverage.
Test: validator fails any sprint whose reuse table resolves zero repository paths.

**R0-C2 (8h) — lanes, capacity and automation.**
Outcome: *every release-gate criterion traces to a scheduled unit under both DEC-025 branches, and the capacity model is written down.*
Scope: M-A2/M-A3 roadmap rows + R1 dual-branch predicate (APPROVED and NOT APPROVED); PROC-01 procurement lane owned by James with S08 entry criterion; concurrency/WIP model and PR budget into `operations-and-rollout.md`; the §5 automation lanes recorded as governed policy; DEC-SHEET as a standalone deliverable due before S07-C.

**R0 totals:** 7 missions, 72 agent-hours, three concurrent lanes → **critical path ≈ 24 agent-hours ≈ 3–5 calendar days** including review turnaround. James input required: accept findings (opens R0), review 7–9 draft PRs (~4h), decide the four items in §6 that R0 consumes.

---

## 4. Revised twelve-sprint capacity model

v1's calendar claim is withdrawn and replaced with an explicit model. **Stated assumptions, all falsifiable:**

| Input | Value | Basis |
|---|---|---|
| Declared mission-hours, S01–S12 | ~368 | summed from the sprints' own windows (verified) |
| R0 | 72 | §3 |
| Concurrent agent lanes | 2–3 | limited by intra-sprint file conflicts and review context-switching, not compute |
| Overnight frozen missions | permitted for DEC-013 "frozen" tier only | DEC-013's own definition |
| Independent reviewer | separate session, not James | DR-06 correction; costs agent time, not governor time |
| PR review, financial-dense | ~40 min | S07/S09/S10/S11 diffs |
| PR review, structural/docs/evidence | ~15 min | S01–S06, evidence PRs |
| PR WIP cap | ≤2 unmerged product PRs per sprint boundary | DR-10 |

**James-hours (the actual scarce resource):** ~25h PR review (≈25 dense × 40 min + ≈30 light × 15 min) + ~20h decisions (R0 acceptance 2h; DEC-025 M02 packet 2h; DEC-SHEET policy values ~5h; DC-06 1h; NS-02 1h; twelve migration-apply gates ~4h; R1 authorisation 2h; residual gates ~3h) ≈ **45h ± 15h across the whole programme.** At 6 h/week that is ~7.5 weeks of governor time spread over the programme — **James-hours are not the binding constraint.**

**The binding constraint is dependency-chain latency.** Critical-path agent hours per stage after the R0 re-splits (mission hours ÷ achievable concurrency): S01 ≈16 · S02 12 · S03–S06 ≈14 each · S06.5 8 · S07 ≈28 · S08 ≈24 · S09 ≈24 · S10 ≈32 · S11 ≈32 · S12 ≈20 → **≈252 critical-path agent-hours.** At 10–14 effective agent-hours/day (day lane + overnight frozen lane) that is ~18–25 working days ≈ 4–5 weeks of pure execution. Add per-stage gate latency (review + James-gated migration apply) at ~1.5 days × 13 stages ≈ 4 weeks, and ~25% slack for NOT_READY returns and rework ≈ 2 weeks.

**Result — 12 weeks is supportable as the aggressive case, contra v1.** Bands:

| Case | Duration | Requires |
|---|---|---|
| **Aggressive** | **12–13 weeks** | 3 lanes, overnight frozen missions running, ≤24h review turnaround, ~10 James h/wk, migration applies same-day, ≤1 NOT_READY per sprint |
| **Nominal** | 16–18 weeks | 2 lanes, 48–72h review turnaround, ~6 James h/wk |
| **Degraded** | 22–26 weeks | 1 lane, weekly review batching, or procurement/decommission stalls on the critical path |

The two stalls that convert aggressive into degraded are both external to engineering and both currently unscheduled: **PROC-01** (licensed XJO-TR — a vendor timeline no lane can compress) and **M-A2/M-A3** (Model A shutdown, including a *naturally elapsed* no-write observation window that is calendar time, not work time). R0-C2 schedules both. DR-01 stands as a P1-blocker on the absence of any such model in the dossier — not on a week count.

---

## 5. Automation lanes (retained from v1 §I, unchanged in substance)

Principle: **automate verification and preparation, never decisions.** GREEN (unattended now): CI running the validator + the R0 attack-regression suite on every PR; nightly drift validation of main and open sprint branches; PR steward autofixing CI on Claude-owned branches; a decision-latency monitor surfacing overdue DEC-SHEET/PROC-01/inbox items. AMBER (unattended execution, attended acceptance): overnight runs of DEC-013-*frozen* missions only, under `ARBI_UNATTENDED=1` with the unattended-guard blocking irreversible tiers and sessions scoped to read-only DB grants, ending at a draft PR; plus an automated fresh-context adversarial pass on every product PR, which is what closes DR-06's self-grading gap. RED (mechanically blocked, never automated): migration applies, policy ratification, any `ratified_by`/`decided_by` artifact, promotion/tier decisions, M-A2/M-A3 steps, authority-document edits, merge/deploy/release. The AMBER lane is what makes the aggressive 12-week case reachable; AS-04 (read-only DB scoping) is its enabler, not merely a defect.

---

## 6. Remaining James decisions

**Consumed by R0 (needed to start or close it):**
1. Accept this corrected register and open R0. *(the stop-condition decision)*
2. DC-06 — canonicalization: ASCII-normative wire rule vs full JCS with test vectors.
3. NS-02 — James-authored thesis intake path vs agent-only drafting (and, if agent-only, whether existing holdings' theses get re-materialised so Capital-Under-Discipline is non-degenerate).
4. Capacity target — aggressive / nominal, i.e. your available hours per week and review turnaround commitment.
5. PROC-01 kickoff — sourcing and paying for licensed XJO-TR and market data.

**Consumed later, unchanged:**
6. DEC-025 — Model A runtime decommission: APPROVED / NOT APPROVED (at S01-M02).
7. DEC-001 reconfirmation — direct tailored output and `ORDER_STAGED` as the product target.
8. Every `JAMES_INPUT_REQUIRED` policy value via DEC-SHEET, due before S07-C.
9. NS-06 — ratify or reject the programme-window deferral of moat layers 1 and 3.
10. The economic-materiality hurdle value (reported, not gated — EV-04′).
11. Merge, every migration apply, deploy, R1 authorisation, and all release gates.

---

## 7. Exact proposed patches to PR #70

No edits made. Grouped by R0 mission; each is a concrete file target.

**R0-A1** — `schemas/sizing-decision-v1.schema.json` (+`comparison` enum, required on `NUMERIC_LIMIT`) · `contracts/sizing-policy-v1.md` (normative direction table for all 18 codes) · `contracts/risk-policy-v1.md` (liquidity limits declared resolvable) · `scripts/validate_investment_program.py::_validate_portfolio_semantics` (direction assertion, policy-resolved `limit_value`, liquidity/ADV/spread/price-age recompute, snapshot-derived `current_weight` + sellable check, cash floor) · `fixtures/sizing-valid.json`, `sizing-origin-valid.json` (annotate `comparison`; values unchanged) · `tests/test_investment_program_dossier.py` (+8 mutation tests).

**R0-A2** — `validate_investment_program.py::_validate_staging_semantics` (resolve `staging-policy-v1`; adverse fraction equality; tick from classification band; Σ notional + fees ≤ SIZED) · line-binding recompute in the intent/lineage path · duplicate-ID hard error in the reference index · `fixtures/paper-intent-valid.json` (`sizing_line_sha256` → recomputed digest) · `fixtures/staged-order-valid.json` (unchanged if compliant) · tests (+5).

**R0-B1** — `contracts/tax-profile-v1.md` + `schemas/tax-profile-v1.schema.json` + `fixtures/tax-profile-valid.json` (calendar CGT rule replacing `minimum_holding_days`; franking eligibility/exemption block, entity-conditional, warning-only preserved) · new `contracts/review-freshness-policy-v1.md` + schema + fixture; `review-context-v1` freshness resolves to it · `contracts/promotion-decision-v1.md` + `fixtures/promotion-decision-valid.json` (`gate_decision_ref` → in-dossier evaluator digest) · validator + tests (+6 incl. CGT boundary and leap vectors).

**R0-B2** — `contracts/{episode-outcome,benchmark-snapshot,portfolio-snapshot,paper-fill,paper-order,branch-nav}-v1.md` (six sentences: implement-or-relabel with an AC id) · `contracts/review-context-v1.md` + schema (catalysts/falsifiers/discipline binding or ratified exclusion) · `sprints/s04`, `s05` (MI-01 freeze fields, RI-01 bundle registry marked load-bearing) · `acceptance-matrix.md` (new AC ids for relabelled requirements).

**R0-B3** — `decisions.md:3-5`, `README.md:3`, `CLAUDE.md:13` (status → proposed/merge-ratifies) · repo code-owner file (programme tree, roadmap manifest, seven authority docs) · `schemas/investment-case-lineage-v1.schema.json:321-327`, `schemas/staged-order-set-v1.schema.json:59-63`, `fixtures/staged-order-valid.json`, `architecture.md:246` (`ADVICE_READY` resolution) · `sprints/s01…md:9` (→ AC-01–05) · validator sprint-AC cross-check · `docs/product/decision-log.md` + `james-inbox.md` (drafted acceptance rows) · `docs/product/roadmap-state.md` / `.claude/rules/portfolio-conventions.md` (AS-06 reconciliation).

**R0-C1** — `sprints/s07`–`s12` (existing-code reuse tables with resolving paths) · validator rule enforcing ≥1 resolving path · re-estimates in `roadmap.yaml`.

**R0-C2** — `docs/product/roadmap.yaml` (M-A2/M-A3 rows; PROC-01 lane; `week` non-normative or re-based; DEC-SHEET deliverable) · `operations-and-rollout.md` (R1 dual-branch predicate; WIP/PR budget; capacity model from §4; automation lanes from §5) · `acceptance-matrix.md` (R1 criteria traceability).

---

## 8. Branch and merge handling

Confirmed: commit `5775628` on `claude/investment-engine-dossier-review-ozg1ny` adds **only** `docs/reviews/investment-engine-dossier-review-2026-07-25.md` on top of `main`. There are no dossier deletions in it; any deletions seen came from diffing the two branch tips rather than the merge base. v2 adds only this second report. Cleanest handling, as you suggested: **cherry-pick the two review commits onto `agent/investment-engine-dossier`** so the review travels with PR #70, rather than merging the review branch. I have not done this — say the word and I will.

---

*End of Review Packet v2. Stop condition reached: no implementation, no merge, no migration, no production action. Awaiting the §6 decisions.*
