# Finance red-team 2026-08-08 — evidence input to D0-04

**Status: HISTORICAL RECORD — dispositioned 2026-08-09, merged to `main` 2026-08-17.** This
document is retained as the evidence base and the durable record of the D1–D9 governor
rulings (§6.1). It is **not** a live work queue: read §6.1 for what James actually ruled,
and check the current roadmap for what has since been built. The register, verdict and
R1–R9 candidate work orders below are as-of-2026-08-08 and were not re-verified at merge.

**Why it merged after the fact.** The §6.1 rulings existed only as a GitHub PR comment on
draft PR #78 for eight days. `docs/README.md` requires that a doc a future session must read
be committed to `main` — branch-only artifacts are candidate evidence, not authority — so
the rulings were unreachable to every later session. Merging fixes that. D1/D2 are the
approvals that authorise the parked rules-integrity work (PR #80, migration `0042`); before
this merge, that build's authorisation record lived nowhere durable.

**Original status when written: PROPOSAL — bounded, read-only evidence input to work order
D0-04** (the "Product and financial-semantics correction sheet" in the outcome-programme
convergence-sprint proposal). This document carried **no implementation authority and created
no roadmap**: it delivers a defect register, a verdict, and candidate work orders. Every
build, migration, governed-doc change, parameter, and grandfathering decision below was
**James-gated** — see §6.1 for how each was gated.
Firewall: nothing in this document or its appendices is a direction regarding any live
position; all HUBS ESS/CGT dates and computations are **UNKNOWN / NOT RELIABLE** pending
verified Division 83A facts and accountant review.

Companion file: `finance-red-team-2026-08-08-appendices.md` — the complete verbatim
evidence record (frozen packet, rule manifest, six panel outputs, both plan-level
critiques, dissent pass). Nothing in the appendices was edited or summarized.

---

## 1. Mission provenance

**The charge (James, 2026-08-08):** the system "is giving bad advice", "the agents are not
really guiding toward the north star", and "some of the rules written seem to be arbitrary
and not actually making a good decision — these need to be addressed." Scope set by James:
all finance-bearing rules; deliverable: challenge + ranked fix proposals, approval before
any code.

**Plan lineage.** Rev 1 was itself red-teamed before execution (arbi-red-team:
PROCEED-WITH-CHANGES with six amendments; a completeness critic: twelve gaps — both
verbatim in Appendices I/J). James then issued a 12-point correction packet producing
**rev 4**, which governs this mission: bounded D0-04 input; a frozen finance-rule
manifest before any judgment; a content-addressed evidence packet; the corrected HUBS
frame; hard agent constraints (no return computation by the benchmark or milestone
agents; tax agent gap-identification only); an underwriting-gate rubric; functional-
influence legal classification instead of a wording firewall; behavioural-fixture
acceptance; a fresh synthesizer distinct from the mock's author; and an isolated
worktree with a two-file allowlist.

**Process actually run:**

| Step | Artifact | Where |
|---|---|---|
| −1. Denominator freeze | Finance-rule manifest, ~200 rules / 15 surfaces, **NOT fully reconciled** (unswept surfaces listed in its header — no "all rules" claim is made anywhere) | Appendix B |
| 0. Governor interrogation | 3 answers, pasted into every envelope | §2 below |
| 1. Evidence packet | 10 content-addressed entries (SHA-256), repo pinned at origin/main `1b471b60`, 7 explicitly UNAVAILABLE facts | Appendix A |
| 2. Panel | 6 seats: finance adversary (general-purpose; no in-fleet role exists — itself a finding), thesis-milestone-monitor (flags only), portfolio-coherence-reviewer (+self-inventory), benchmark analyst (no return calc), macro-economist (regime design), tax-spec-conformance (gaps only) | Appendices C–H |
| 3. Synthesis | Fresh synthesizer (not the mock/envelope author) — root-cause table, 31-row register, verdict, work orders | §3 below, verbatim |
| 4. Dissent | arbi-red-team pass over the draft before this PR | §4 below, verbatim verdict |

**Conflict-of-interest guards used:** the orchestrator that built the challenged brief mock
did not rank, judge, or filter — panels attach verbatim; the synthesizer and dissent
reviewer are independent; imperfectly-cited adverse findings are flagged, never dropped.

## 2. Governor interrogation (Step 0) and corrected frame

| Question | James's answer (2026-08-08) |
|---|---|
| Was the HUBS $230 stop deliberate at authoring? | **Placeholder / experiment** — not firmed up |
| What is the CBA $42–45 band? | **Error** — wrong numbers from the start |
| What should a triggered invalidation condition DO? | **Immediate exit prompt** — push an exit decision that day |

**Corrected HUBS frame (verbatim, rev 4):** "Confirmed semantic/actionability defect;
born-breached if intended as an immediate hard-exit trigger. Lock-at-authoring and
intended trigger semantics remain unproven." The thesis row's own `tax_notes` documents
the stop as ALERT/REVIEW-only while the ESS trading window is locked (end date unknown),
and flags the acquisition FX as estimated and disputed — "the AUD P&L sign depends on it."

The combination the interrogation exposed is the mission's sharpest single fact: **a
placeholder rule entered a pipeline wired to hard-exit expectations.** The system cannot
represent the difference, and when its trigger fired it produced one unverifiable email,
no decision loop, and a permanently stale state.

## 3. Synthesis (fresh synthesizer, verbatim)

The following is the independent synthesizer's report, unedited. The orchestrator records
no disagreement with it (see §5).

---

# Finance red-team synthesis — fresh-synthesizer report, 2026-08-08

**Role:** independent synthesizer for work order D0-04. Inputs: frozen packet `finance-red-team-evidence-2026-08-08` (entries cited `id@hash`), frozen rule manifest (2026-08-08, denominator NOT reconciled — all coverage claims below are scoped to swept surfaces), six panel outputs (panels 1, 3, 4, 5, 6, 7), repo at origin/main `1b471b60` for spot verification. Firewall honoured: nothing below is functionally-directive about any live position; all HUBS ESS/CGT dates and computations are UNKNOWN / NOT RELIABLE pending Div 83A facts and accountant review (packet meta, corrected_hubs_frame).

---

## 1. Root-cause hypothesis table

| Hyp. | Evidence FOR | Evidence AGAINST | Ruling |
|---|---|---|---|
| **(a) Authoring is unvalidated** (rules born malformed) | 13/13 theses malformed at authoring; zero earn WELL-FORMED (panel-3 Task 1). HUBS stop 230 above entry 187.54 and the whole 185–190 band on a long thesis; born-breached on latest-close-at-authoring (E01@21ff37f2, E05@22e3234378, D01@28d5d505). CBA band 42–45 vs market 178.01 — governor: "Error — wrong numbers from the start" (meta.governor_answers). All 11 research theses have degenerate point bands (E02@16d71743, "systematic authoring artifact"). No ordering/coherence lint anywhere on swept surfaces; `enter_thesis` checks existence, not coherence (panel-1 §2; portfolio-conventions.md:70-83). | The one well-authored artifact — the five falsifier metrics in `earnings_notes` (E01) — shows authoring competence exists; the failure includes downstream consumption (panel-1 §3 item 6: "authored well, orphaned at evaluation"). The sanity-multiple concept exists in code, just at read time only (`disc.data_sanity_multiple`, manifest §1). | **SUPPORTED** |
| **(b) Maintenance/revision failure** (rules rot; no re-validation clock) | Frozen "50d MA ($243.61)" text decaying since authoring (E01; panel-1 §2 "revision rot"). Trigger note frozen at 2026-07-03 through a 7-close recapture (E05; panel-3 §1.0). CBA revisit 42d overdue, HUBS 5d overdue spanning the earnings event (D01; panel-4 A5/A6). Profile `capital_aud` stale vs snapshot (E03@77859aad vs E06@028a9870; panel-4 A11). Doc-vs-profile cap agreement "only by coincidence" (panel-4 item 4; manifest `pol.sector_cap_30` stale-risk). | A revisit clock exists and fires RED (`sev.revisit_overdue_red`, manifest §2) — dates are clocked; it is rule *content* (stops, bands, embedded values, trigger state) that has no freshness mechanism. Several rot instances reduce to (d)'s missing state machine rather than an independent cause. | **SUPPORTED** (secondary) |
| **(c) Decision-support gap** (decisions demanded with no re-underwriting basis) | Target 318 has no recorded derivation; no valuation-basis field exists (panel-1 §3 item 4) — the mock's "re-underwrite" path had nothing to re-underwrite from. Falsifiers evaluated by no surface; the Q2 print passed unchecked; a "guidance cut" headline scored 0.997 *positive* (panel-3 F7; E09@5870e314). Tax consequence vanishes exactly where decisions are framed (panel-7 Task 1 headline). | Much of the basis exists but is misrouted, not absent — the §9 tax apparatus is "rich but misrouted" (panel-1 §3 item 5); this hypothesis is substantially the surface expression of (a)+(d)+(e). | **SUPPORTED** (secondary) |
| **(d) Wrong primitive** (single static stop for a 12-month tax-driven hold; write-once trigger state) | Write-once trigger cannot represent re-arm, episodes, partial satisfaction, or resolution (panel-3 F3; `check_thesis_invalidations.py:151-152`, verified). It asserted a breach through 8 above-level closes and produced the mock's false "day 36" headline (E05; D01 item 3). Compound masking: fixing the scheduler alone evaluates nothing on 08-06 (panel-3 F6, CRITICAL). Horizon contradiction: 365d CGT economics + daily-close "immediate exit prompt" intent, with the system emitting HOLD (`pm.weekly_watchlist_text`) and exit-review (`inval.alert_wording`) about the same shares in the same period (panel-1 §3 item 3). No schema field for trigger semantics (panel-3 F10). | The static-stop primitive serves the AU daily-alert design adequately (manifest §6); the governor's intended semantics ("immediate exit prompt") *can* be expressed by a stop — the missing pieces are state, semantics, and instrument constraints, not the concept of a stop. | **SUPPORTED** |
| **(e) Serious-vs-sandbox indistinguishability** (placeholders enter the same pipeline as underwritten rules) | Governor: the 230 stop was "Placeholder / experiment (not firmed up)" (meta.governor_answers) — and it drove a production alert naming an exit command on 2026-07-03 (panel-1 §4.1; `check_thesis_invalidations.py:179-185`, verified). The confidence-manufacturing pipeline strips a hedge at every stage (panel-1 §4.1). All 13 theses born `governance_status='approved'` by default (E01/E02). Placeholder intent and the ALERT-only demotion both live only in free-text `tax_notes`, read by exactly one manual CLI surface (panel-7 F5; `cli/thesis.py:926`). | Governance machinery that *could* distinguish (draft/pending_review) exists — but defaults human-authored rows straight to approved, so the distinction is never exercised (portfolio-conventions.md governance section). This is mitigation-exists-unused, not counter-evidence. | **SUPPORTED** |

**Primary vs secondary.** PRIMARY: **(a), (d), (e)** — (a) and (e) are the root pair (rules born malformed AND indistinguishable from underwritten ones, attested directly by the governor's own answers on both live ladders), and (d) is the amplifier that converted a placeholder into five weeks of standing false state and structurally absorbed the one event the intended semantics existed for. SECONDARY: **(b)** (real, with independent instances, but most of its mass is retired by fixing (d) plus a freshness clock) and **(c)** (largely the surface expression of the primaries plus misrouting).

---

## 2. Ranked defect register

Status: CONFIRMED = replayed against packet/code by a panel or by me; PLAUSIBLE = asserted, not replayed. "Feeds" = D0-04 item; NONE is itself information.

| # | Defect | Evidence | Sev. | Status | Feeds D0-04 |
|---|---|---|---|---|---|
| 1 | Write-once invalidation trigger state (no re-arm/episodes/resolution) produced a false "day 36 below stop" decision headline through a 7-close recapture, and — compound masking — even with the scheduler fixed would evaluate nothing on the 08-06 re-breach (cond #1 non-active, #2–4 unparseable) | `check_thesis_invalidations.py:151-156` (verified); E01@21ff37f2; E05@22e3234378; D01@28d5d505; panel-3 F3/F6; panel-1 §1.1 | CRITICAL | CONFIRMED | invalidation-condition shape |
| 2 | Authoring pipeline validates nothing: 13/13 theses malformed (stop above band on a long; governor-ERROR band; 11 degenerate point bands), all born `governance_status='approved'` | E01, E02@16d71743, meta.governor_answers; panel-3 Task 1; panel-1 §2 | CRITICAL | CONFIRMED | **NONE** — no D0-04 item covers authoring validation |
| 3 | Personal-advice firewall is per-pipeline; the mock — the most directive surface the system has produced (ranked paths, named exit command, "ACTION REQUESTED") — was minted in an ad-hoc lane no gate touches, un-learning the repo's own wording firewall | panel-1 §1.2/§6; manifest `disc.timeline_wording_firewall` (discipline.py:220-229) | CRITICAL | CONFIRMED (mechanism); class per panel-1 assessment, which I adopt | ADVICE_READY conflict |
| 4 | Placeholder/serious indistinguishable in schema: placeholder stop fired a production exit-command email; intended semantics and the ALERT-only demotion live only in free-text `tax_notes`, unreachable by every automated surface | meta.governor_answers; E01 tax_notes; `cli/thesis.py:926`; panel-3 F10; panel-7 F5 | HIGH | CONFIRMED | invalidation-condition shape |
| 5 | 3 of 4 HUBS conditions machine-inert and silently skipped, indistinguishable in the stored field from watched ones; "on volume" qualifier silently dropped with no record of the narrowing | `check_thesis_invalidations.py:42-47,154-156` (verified); panel-3 F1/F2 | HIGH | CONFIRMED | invalidation-condition shape |
| 6 | Discipline machinery dark through the crash: no `check_thesis_invalidations` run for as_of 08-06/07/08; the −19.1% USD day never machine-evaluated; cause not in packet | E08@ac39a924 (note); panel-3 F5 | HIGH | CONFIRMED (cause un-evidenced — see §6) | NONE |
| 7 | The five written falsifiers are evaluated by no surface — `active_theses.py:43` fetches `earnings_notes` and drops it; a headline touching falsifier #5 scored 0.997 positive polarity | panel-3 F7; E09@5870e314; E01 | HIGH | CONFIRMED | invalidation-condition shape |
| 8 | Concentration invisible: `per_name_cap_pct` has no scheduled reader (allocator dead behind the model gate, E04@417d7cfe); the generic concentration RED is mechanically unreachable on the V2 daily brief (`JOIN prices … p.dt = $1` exact-date join, prices end yesterday); 100% single-name book vs the 10% cap flagged by nothing for the life of the position | `wealth_state.py` join (verified); E03@77859aad, E06@028a9870, D01; panel-1 §3 item 2 / C1; panel-4 A1 | HIGH | CONFIRMED | sizing policy defaults |
| 9 | FOUR conflicting concentration thresholds for one investor: 10% per-name (profile), 30% sector (profile + governed doc), 10/20% per holding (severity.py), 40% sector (agent prompt, unsourced) | E03; manifest §2 `sev.concentration_10_20pct`, §13 `agt.pcr.sector_gt_40pct`, §15 `pol.sector_cap_30`; panel-4 Part B | HIGH | CONFIRMED | sizing policy defaults |
| 10 | Employer concentration (ESPP: income + equity on one company) is unrepresentable — no field, rule, or prompt anywhere swept | panel-1 §3 item 2 (schema/manifest sweep) | HIGH | CONFIRMED (as absence, swept surfaces only) | NONE |
| 11 | Cross-currency break-even: monitor feeds AUD per-share cost (`cost_base_normal/quantity`) against a USD close — §5.4's same-currency precondition violated; the hint is structurally suppressed (`current_price <= cost` → None) and the header P&L renders ≈ −27.6% — the documented R10 error class, now in the flagship tax-decision surface | `position_monitor/display.py:35` and `tax/cgt.py:146-147` (both verified); panel-7 F3; `.claude/rules/portfolio-conventions.md` R10 section | HIGH | CONFIRMED | NONE (nearest: accounting/tax alignment — D0-04 carries no currency-consistency item) |
| 12 | Div 775 forex gain implemented + tested, consumed by no product surface; spec §8.3's claim that `positions.py` flags `forex_gain_aud` is contradicted by code (zero matches) — the one consequence class that can flip the AUD P&L sign is wired to nothing | grep of `positions.py` (verified: no fx_gain/forex/775); panel-7 F1; spec:338 | HIGH | CONFIRMED | NONE |
| 13 | ESS/Div 83A unrepresented: spec §9's `acquisition_type` accommodation exists nowhere in code/schema; no ESS test case; every tax surface treats the ESPP lot as an ordinary purchase; the derived 2027-06-01 CGT date renders as fact with no provisional marker while all HUBS ESS/CGT dates are UNKNOWN | panel-7 F2/Task 2; E06 column list; meta.corrected_hubs_frame; spec:355-359 | HIGH | CONFIRMED | calendar CGT holding-period representation |
| 14 | Benchmark: every stored `benchmark_tr_level` is the 4% proxy (level identity reproduced); no real accumulation series seeded; licence UNVERIFIED; the only prescribed alpha method (`capital_aud` endpoints) is the construct the V1 brief deleted after a false −75.7% — `agt.bpa.periods_and_alpha` graded INVALID-METHOD | `snapshot_portfolio.py:81-97,278-284`; `wealth_state.py:101-108`; E06; panel-5 Tasks 1/2/4 | HIGH | CONFIRMED (licence half UNAVAILABLE, abstained) | benchmark identity/licence |
| 15 | No cash-flow ledger; flows enter `capital_aud` as performance; unlike the retro-correctable proxy, ledger history is lost every day it does not exist | panel-5 Task 2 #2/#5, material item 2; `snapshot_portfolio.py:29-31` | HIGH | CONFIRMED | benchmark identity/licence |
| 16 | Regime gate is a stateless single-print OR that zeroes the entire discovery surface; the spec's 5-rung posture ladder is flattened to on/off with the milder rung getting the maximal penalty; live on the 2026-08-08 brief | `classifier.py:69-83`; `new_ideas.py:23,44-50` (verified); E08@ac39a924; panel-6 F1/F2; spec:347-348 | HIGH | CONFIRMED | NONE |
| 17 | Suppression fails OPEN: missing `market_context_current` row → `effective_regime=None` → section renders normally; NULL breadth soft-degrades in the permissive direction — both invert the fail-loud/conservative-on-missing doctrine | `new_ideas.py:37-50` (verified); `classifier.py:77-81`; panel-6 material items (self-ranked SEV-2) | HIGH | CONFIRMED | NONE |
| 18 | Static "HOLD — CGT clock ticking. Macro confirming." box emitted whenever a CGT date exists, regardless of regime — contradicted by the live classifier the same day; three numeric vocabularies (and two different vol indices) for the same risk | `display.py:266-278` (verified); E08 (`risk_off_orderly`); panel-6 F4; panel-7 optional items | HIGH | CONFIRMED | NONE |
| 19 | An approved macro thesis without `machine_conditions` scores `open` forever — the early return skips the horizon-expiry check, no surface reads `evaluation_detail`, no alert fires; id 11 will exhibit this on the scorer's first run (outcomes count 0) | `score_macro_theses.py:148-157,167-173`; E07@e7a394d1; panel-6 F3 | MEDIUM-HIGH | CONFIRMED (code-replayed; outcome not yet observed) | invalidation-condition shape (sibling class) |
| 20 | The invalidation email is the only alert naming an exit command — for shares documented non-disposable — in tension with the repo's own s766B verb firewall; and delivery is best-effort: `_send_alert` swallows everything including missing env vars while the job reports success | `check_thesis_invalidations.py:104-122,179-185` (verified); panel-3 F8/F9; panel-1 §4.3 | MEDIUM | CONFIRMED | ADVICE_READY conflict |
| 21 | Trigger writes are bare UPDATEs — no `thesis_revisions` row, no governance event — and the note stamps the run date, not the price date (192.12 is the 07-02 close; no 07-03 row exists) | code:161-178,:165 (verified); E05; panel-3 F4/F8; manifest `inval.trigger_writes_status` | MEDIUM | CONFIRMED | invalidation-condition shape |
| 22 | CBA sits in a total machinery blind spot: every job/collector filters `status='active'`, and the coherence agent's anchor LATERAL does too — the one thesis with a governor-confirmed ERROR band, empty conditions, and a 42-day-overdue revisit is watched by nothing | code:82; charter :42 (verified); panel-3 material item; panel-1 C4(a); panel-4 A5 | MEDIUM | CONFIRMED | NONE |
| 23 | Charter defects in portfolio-coherence-reviewer: anchor query pulls `model_a` signal labels into every review (quarantine leak); the "state that non-AUD names are excluded" escape hatch excludes 100% of the current book; output template names no currency | charter :45-46, :52-53 (verified), :109; panel-1 C4; panel-4 self-note | MEDIUM | CONFIRMED | Model A exclusions |
| 24 | Dead CGT arm: the earnings-within-14d-of-CGT RED can never fire — sole caller hardcodes `cgt_date=None` | `severity.py:96-104`; `active_theses.py:169-175`; panel-7 F7 | MEDIUM | CONFIRMED | calendar CGT holding-period representation |
| 25 | Four-way acquisition-FX contradiction: DB 0.6450 flagged "estimated" · vendor 0.7171 · `scripts/hubs_espp_scenarios.py:35` 0.7162 · governed docs assert 0.6450 "confirmed" — AUD P&L sign unresolved | E06; D01; panel-7 F6/Task 2 row 4; portfolio-conventions.md | MEDIUM | CONFIRMED (resolution UNAVAILABLE) | NONE |
| 26 | `unrealised_fx_pnl_aud` is total unrealised P&L mislabeled as the FX leg (MV − cost, exactly matching the 2026-08-07 row), on the disputed FX cost leg | `snapshot_portfolio.py:294-296`; E06 arithmetic; panel-5 material item 1 | MEDIUM | CONFIRMED | NONE |
| 27 | Counted suppression line absent (spec :359 — code returns before the SELECT, nothing counted) and no regime override mechanism exists at all (spec :350) | `new_ideas.py:44-50` (verified); panel-6 F5/F6; manifest `spec.new_ideas_suppression_msg`/`spec.user_override` | MEDIUM | CONFIRMED | NONE |
| 28 | Conviction framework has no input data: `conviction_level` NULL on every thesis including the 100% position; size-vs-conviction discipline undefined over the whole book | E01; panel-4 A3; manifest `disc.conviction_unset_yellow` | MEDIUM | CONFIRMED | sizing policy defaults |
| 29 | Structural protections hollow: `cash_floor_pct=0` / `leverage_cap=1` satisfied trivially; the governed policy carries both as "[governor to set]" holes | E03; manifest `pol.cash_floor_hole`/`pol.leverage_cap_hole`; panel-4 A10 | LOW | CONFIRMED | sizing policy defaults |
| 30 | Two divergent capital figures: profile A$6,666.98 (stale since 07-04) vs snapshot A$7,147.02 — profile-based weight math exceeds 100% | E03; E06; panel-4 A11 | LOW | CONFIRMED | NONE |
| 31 | Snapshot `as_of` pairs an ASX close with a same-calendar-date NYSE close — session offset on every joint observation | `snapshot_portfolio.py:169-175,220-227`; panel-5 Task 2 #7 (ASSESSMENT) | LOW | PLAUSIBLE | benchmark identity/licence |

**Register-level observations.** (i) The two largest defect masses feed **invalidation-condition shape** (7 rows) and **sizing policy defaults** (5 rows). (ii) Eleven rows map to **NONE** — D0-04 as listed has no item for authoring validation, currency-consistency, tax-rule wiring, regime-gate integrity, or alert delivery; that absence is a work-order finding in its own right. (iii) Three D0-04 items received **zero confirmed defects from any panel**: source-run provenance, nested citation resolution, agent_evidence→thesis_evidence ID namespaces (and paper-vs-actual outcome labels received only an inventory grading, panel-5 Task 4 `agt.bpa.paper_vs_live` NOT-RUNNABLE-NOW) — those items were not exercised by this red-team, not cleared by it.

---

## 3. Verdict on the brief mock: **REBUILD**

Panel-1 §1 classified the card functionally-directive and specified the rule-integrity-first ordering. I adopt the classification and rule **REBUILD** — not REFRAME, because the defect is in the premise and the state pipeline feeding the card, not its layout.

**Three strongest reasons:**

1. **The headline factual claim was false, and the pipeline cannot currently produce a true one.** "DAY 36 BELOW STOP" was sourced solely from a write-once flag set 2026-07-03; the tape shows 8 of those 36 days closed above the level, and the flag's own note misdates the trigger close (panel-1 §1.1; panel-3 §1.0 re-derivation; E05@22e3234378; `check_thesis_invalidations.py:151-152`, verified). Rewording a card fed by state with no re-arm semantics reframes a falsehood; only R2 makes a true headline producible.
2. **All three offered options inherit a shared premise — "a live, seriously-authored, currently-breached, enforceable stop" — that fails on at least two of three components** (placeholder per governor; ALERT-only while locked per `tax_notes`; recaptured then re-breached per E05). The legitimate response — repair the rule, then decide — was structurally absent (panel-1 §1.3). A decision architecture premised on unproven rule integrity cannot be reframed into validity; it must be rebuilt on the ordering.
3. **It was functionally-directive in a lane no firewall gate touches** — ranked options, a named CLI disposal command, an "ACTION REQUESTED" eyebrow — while the codebase's own discipline module deliberately strips action verbs from far milder surfaces (`disc.timeline_wording_firewall`; panel-1 §1.4/§6). It also rendered an unverified tax representation (a CGT discount date presented as fact while all HUBS ESS/CGT dates are UNKNOWN — meta.corrected_hubs_frame) and an R10-class FX omission (panel-1 §1.4).

**What any successor surface must satisfy** (adopting panel-1's ordering verbatim, with one addition): (1) **rule integrity first** — a rule that is placeholder, born-breached, stale-triggered, or semantics-ambiguous yields a *rule-repair card*, never an action card; (2) **enforceability second** — instrument constraints (lock windows) demote triggers to ALERT/REVIEW on the face of the card; (3) **facts third** — tape vs flag, falsifiers vs actuals, tax consequence per path, FX basis; unavailable facts are printed, not papered over; (4) **options last**, unranked or status-quo-first, each carrying its own prerequisites and tax consequence, with "insufficient evidence — no decision solicited today" as a valid output. Plus: **functional-influence classification attaches to the output, not the lane** — any generated surface that renders a live position and names or ranks an action is functionally-directive by definition and must pass the ordering or be demoted (panel-1 §6 Q5).

**Disagreement with panel-1:** none material. One refinement: REBUILD is a verdict on this card and its feeding pipeline, not a ban on the card *class* — a decision card on a live position is a legitimate product surface once R1/R2/R9 exist; sequenced behind them, the correct first successor artifact for the current state is the rule-repair card itself.

---

## 4. Remediation work orders (R1–R9, as D0-04 inputs)

Fixture key — the seven behavioural fixtures: **BB** born-breached tradeable stop · **LK** locked review trigger · **TR** valid trailing stop · **SP** stale price · **CC** cash contribution · **ES** ESS-tax unknown · **WA** weak-evidence-requiring-abstention. New fixtures the panels' findings demand: **RB** re-breach-after-recapture (the E05 three-episode/two-recapture series replayed end-to-end — panel-3 F3/F6) · **FO** fail-open regime row (missing `market_context_current` row must suppress, not render — panel-6 material item) · **XC** cross-currency break-even (foreign lot must produce an FX-translated hint or a named refusal, never silent None — panel-7 F3) · **PB** degenerate point band (band_lo==band_hi refused or explicitly attested — E02) · **CN** single-name-100% book fires a scheduled concentration finding (register #8).

| R | Scope (reshaped per mandate) | Defect class / severity | Depends on | Owner | Authority class | Acceptance |
|---|---|---|---|---|---|---|
| **R2** | Invalidation machinery: per-condition state machine (active / triggered / re-armed / resolved, episode list with **price-date** provenance), authoring-time parse baseline stored on the row, **loud** unparseable surfacing (an inert condition is a visible finding on every consumer, never a skip — register #5), `thesis_revisions` audit row on every transition, semantics enum `hard_exit\|alert_review` per rung, instrument-constraints field (lock windows) consumed by every alert surface | CRITICAL (register #1, #4, #5, #7, #19, #21) | R1 (shared parser contract); R9 (semantics attestation) | buildable-after-approval | code + **schema migration (James-gated)** | RB, LK, BB, TR, SP |
| **R1** | Authoring/revision integrity, defense-in-depth: **DB CHECK** (long ⇒ stop < band_lo ≤ band_hi < target; band non-degeneracy) + **service lint** in enter/open paths + **parse-echo round-trip** (run the production parser at write time; echo "what I will enforce" — panel-1's binding half) + **periodic sweep** (R8 is the recurring arm). Authoring wizard = optional UX; underwriter-agent-in-loop = advisory-only, never the gate (panel-1 §2: lint launders placeholders — R9's attestation is the counterpart) | CRITICAL (register #2; #5 at write time) | R9 (attestation is lint's escape hatch); R2 (semantics enum is a lint input) | buildable-after-approval | code + **schema migration (James-gated)** | BB, TR, PB |
| **R3** | Governed conviction/cap framework + concentration-threshold unification: ONE canonical table in the governed policy doc; reconcile the FOUR thresholds (register #9) to it; conviction required-at-activation (register #28); fix the `wealth_state` exact-date join so the concentration surface is reachable (register #8); employer-concentration representation (register #10) as a governor design decision | HIGH (register #8, #9, #10, #28, #29) | **Governor decisions** (canonical numbers; conviction policy; employer-risk field) | james-decision → buildable | **governed-doc (James-gated)** + code + **schema migration (James-gated)** | CN, CC (flows must not masquerade as cap breach/cure) |
| **R7** | Successor decision surface per §3: output-attached functional-influence classification; the four-step ordering; rule-repair card as the product response to failed integrity; unavailable facts printed per option; tax consequence per option or named-unavailable (panel-7 Task 1 asymmetry); "no decision solicited today" valid | CRITICAL class (register #3, #20) | R1, R2, R9 (the ordering needs integrity/semantics/attestation to evaluate); **governor decision** (firewall policy attaches to outputs) | james-decision (policy) + buildable | **governed-doc (James-gated)** + code | BB → rule-repair card; LK → ALERT/REVIEW on the face; ES → unavailable-fact printed on the option; WA → abstention output |
| **R4** | Regime gate: hysteresis + asymmetric confirmation windows (reuse `score_macro_theses` window machinery, panel-6 F1 design; `CLASSIFIER_VERSION` bump + CI-pin updates); **dislocation mode is NEW DESIGN requiring explicit approval** (panel-6 F2 flagged it as invention; its data foundation is weak until R1 fixes the degenerate bands); counted suppression line preserving panel-6 F5's five properties; **fail-CLOSED** on missing context row; staleness gate on classifier inputs; vocabulary unification on the classifier's version-stamped constants; "Macro confirming" made conditional or removed | HIGH (register #16, #17, #18, #27) | R1 (dislocation mode consumes entry bands); **governor decisions** (parameters; dislocation approval) | mixed: fail-closed + counted line buildable; hysteresis/dislocation james-decision | code (+ spec/governed-doc for the posture ladder, James-gated) | FO, SP (classifier-input staleness) |
| **R9** | Thesis provenance: attestation field (`placeholder\|underwritten` + basis text) on ladders/conditions; capital-eligibility distinct from the born-approved governance default — an unattested rule never reaches an action-framed surface or names an action in an alert; grandfathering of the 13 existing rows is the governor's call | HIGH (hypothesis (e) primary; register #2's born-approved facet, #4) | **Governor decisions** (attestation policy; grandfathering) | james-decision + buildable | **schema migration (James-gated)** + governed-doc | BB (unattested placeholder blocked from action surfaces), LK |
| **R8** | Periodic rule-integrity sweep: scheduled re-run of R1 lint + R2 state re-validation over all live rules; rule-freshness clock (embedded market values like "50d MA ($243.61)" re-derived at revisit; triggered states re-checked against the tape); doc-vs-profile drift reconciliation (panel-4 item 4) | HIGH (recurring arm of register #1's stale-state class; frozen-text rot; #25-adjacent doc drift) | R1, R2 | buildable-after-approval | code (job) | RB (sweep flags stale triggered state), SP |
| **R5** | Fleet behaviour audit KEEP/ADAPT/RETIRE: run every `agt.*` rule against the held-out fixture set (the seven + RB/FO/XC/PB/CN); adjudicate panel-4 Part B's inventory (5 LIVE / 1 DEAD / 1 CONFLICTING / 1 UNSOURCED / 4 NOT-RUNNABLE-NOW) and panel-5 Task 4 (INVALID-METHOD rows); strip `model_a` from the coherence anchor and kill the non-AUD escape hatch (register #23); source or retire the magic numbers (40%, 5%, 20%, 12mo/10pos). **Preserve Model A diagnostic references; prohibit only capital-evidence use** (rule #11, `pol.model_a_quarantine`) | HIGH (register #23; panels 4/5 inventories) | R1, R2, R3 (fixtures + canonical thresholds must exist) | buildable-after-approval | agent-charter change (+ governed-doc where thresholds get sourced, James-gated) | WA (charters must abstain rather than force); full held-out set |
| **R6** | Scorecard representation test: evaluate whether the **existing** measures (evidence_grounding, risk_reduction) would have penalized this mission's confirmed failures; any new measure runs **shadow-only** until proven | MEDIUM (meta-gap: no register row — the mock's failure would have moved no score) | R7 (the classification being measured); **governor decision** | james-decision | **governed-doc (James-gated)** | shadow replay against this mission's record; no fixture |

**Leverage ranking (largest confirmed-defect mass retired soonest):** **R2 → R1 → R3 → R7 → R4 → R9 → R8 → R5 → R6.** R2 alone retires the CRITICAL compound class and five further register rows; R1 closes the intake that produced 13/13 malformed rules; R3's cheapest component (the exact-date join fix plus one canonical-threshold decision) restores the only scheduled surface that could have told the governor about a 10x cap breach; R7 retires the firewall-bypass class but cannot land before R1/R2/R9; R4 restores discovery-surface integrity and closes the fail-open inversion; R9 is a small build with outsized gating effect; R8 is R1/R2's recurring arm; R5 and R6 consume the others' outputs.

**SEQUENCED BEHIND governor decisions:** R3 (canonical thresholds; conviction policy; employer-risk representation), R4 (hysteresis parameters; dislocation-mode approval), R6 (scorecard), R7 (output-attached firewall policy), R9 (attestation + grandfathering). R1, R2, R8 are buildable after approval, with their schema migrations James-gated. Separately, the XC fixture belongs to whichever work order carries the tax-wiring repairs (register #11, #12, #13, #24) — those four rows map to no R item as reshaped, and D0-04 should either widen an R item or add one; I flag the gap rather than invent a mandate.

---

## 5. Coverage statement

**Swept.** (i) The manifest's surfaces: discipline evaluator, severity ladder, trajectory classifier, brief collectors, V1 compose, position-check jobs, screening, portfolio domain, tax warnings, regime/signal classifiers, theme/underlying/position-monitor classifiers, lifecycle/governance constants, seven agent prompts, pm-review, governed docs (manifest §1–§15) — with the manifest's own header caveat that the denominator is NOT reconciled. (ii) The packet: E01–E09 + D01 (hashes per meta.entry_hashes). (iii) Six panel lenses: adversary (mock/authoring/behaviour/firewall), milestone-monitor (ladders/invalidation machinery), portfolio-coherence (book vs framework + self-inventory), benchmark (identity/licence/method), macro-economist (regime gating), tax-spec-conformance (consequence surfacing). (iv) My spot verifications: `wealth_state.py`, `check_thesis_invalidations.py` (skip/write/note/email/`_send_alert`), `new_ideas.py`, `tax/positions.py` grep, `position_monitor/display.py`, `tax/cgt.py`, `portfolio-coherence-reviewer.md`.

**Explicitly NOT swept** (manifest "Possibly missed surfaces," verbatim scope): `migrations/*.sql` CHECK constraints (named highest-value gap), API routes, most CLI display bands, ingestion modules, feature engine, model internals, research alpha-eval constants, journal/regulatory/agent-run guards, ~120 test files, scripts/hooks/skills, arbi governance docs beyond the policy grep, ~20 proposals, the full tax-spec TC matrix, CLAUDE.md end-to-end, render.yaml cron anchoring. Additionally not exercised by any panel: the D0-04 items source-run provenance, nested citation resolution, agent_evidence→thesis_evidence ID namespaces (see §2 note (iii)). **Wave-2 items:** my inputs comprise panels numbered 1 and 3–7; no panel-2 file was provided and my inputs do not state whether one existed — I report the numbering gap as a fact about my inputs, nothing more. No "all rules" claim is made anywhere in this document.

---

## 6. Disagreements and flagged-but-uncited adverse findings

**Disagreements, ruled:**

1. **Panel-4 A7 vs panel-1 C3** (leading with "8.5% below the 230 stop" while the stop is governor-classified placeholder). Ruled for panel-1: distance-to-an-unauthored-number is a state of the database, not of the book, and must not headline any successor surface. A7's substance (three mutually inconsistent stop semantics + stale state + unevaluated re-breach) survives intact and is register #4/#1.
2. **Four-way acquisition-FX** (panel-7 F6): governed docs say "confirmed," the DB row says "estimated," a script uses a third value, the vendor a fourth. Ruled: UNRESOLVED; the packet meta (rev 4, governor-corrected, listing the brokerage rate as unavailable) governs this mission, so the governed docs' "confirmed" assertion is treated as suspect pending the statement — a James-gated doc correction, flagged for R8's drift sweep. Note the frozen manifest itself repeats the "confirmed" claim (`rul.r10_currency`), so the manifest inherits this contradiction.
3. **Panel-4's −16.0% AUD drawdown vs panel-1 C5** (method uses the flow-affected `capital_aud` series the system's own history disqualifies). Ruled: the figure is admitted with the flow-clean-this-once caveat panel-1 supplied; the finding it supports — a RED-by-its-own-ladder drawdown while the discipline machinery was dark — stands independent of the exact number.
4. **Panel-6's fail-open finding** was self-ranked SEV-2 but placed outside its numbered findings. Ruled: elevated into the register at HIGH (row #17), verified by me.
5. **Panel-1 computed returns; panel-3's envelope barred them.** An envelope difference, not a factual conflict; panel-1's figures re-check against E01/E05.

**Flagged-but-uncited adverse findings (kept, with what's missing):**

- The identities of the three `wealth_state` items on the 2026-08-08 brief (panel-1 §3 item 2, ASSESSMENT) — missing: item-level `brief_runs` payload.
- Whether `ASXOS_PERSONAL_USE=1` is set for the production `compose_brief` service — i.e., whether the V1 §5.1 lines actually reach the sent email (panel-7 abstention) — missing: render.yaml/env evidence.
- The cause of the missed invalidation runs for 08-06/07/08 (panel-3 F5) — missing: scheduler/Render evidence; the gap itself is CONFIRMED from E08.
- Delivery of the single 2026-07-03 [INVALIDATION] alert (panel-1 §4.3) — unverifiable **by design**: `_send_alert` swallows all failures (verified); the missing evidence cannot exist under current code.
- Realized whipsaw frequency of the 22/450 regime boundaries (panel-6) — missing: `market_context` history, outside the frozen packet.
- Whether HUBS Q2 actuals fired the written falsifiers — UNAVAILABLE per meta; the E09 "guidance cut" headline keeps this flagged, not confirmed.

---

## 7. Out-of-scope observations (mine, unranked, non-binding)

- `_send_alert` interpolates author-controlled condition text into an unescaped `<pre>{body}</pre>` HTML email (`check_thesis_invalidations.py:118-119`) — a minor HTML-injection/rendering surface noticed during verification; no panel raised it.
- A `.claude/worktrees/finance-red-team/` tree duplicating repo files is present on disk (surfaced by my `fx_capital_gain` grep); the packet meta's working-tree statement names only one untracked file — likely gitignored worktree tooling, unverified, noted for packet-hygiene only.
- E01 shows `source_run_id` NULL on both live theses; a future evidence packet that freezes `agent_runs`/`thesis_evidence`/`governance_events` would give the three unexercised D0-04 items (source-run provenance, nested citation resolution, ID namespaces) a denominator this mission lacked.

---

*Abstentions honoured throughout: ESS lock end date, Div 83A facts, brokerage FX, Q2 actuals, TWR/MWR series, licence terms, and macro id 11's conditions are UNAVAILABLE (packet meta); no ruling above depends on their resolution, and nothing in this document is a direction regarding any live position.*

---

*(End of fresh-synthesizer report.)*

## 4. Dissent pass (arbi-red-team)

**Verdict: CONCUR-WITH-NOTES.** The full pass is verbatim below; per the mission's conflict-of-interest rules its notes are RECORDED here, not silently applied to the synthesis. The orchestrator highlights three for the reader: (i) the R2→R1 leverage ordering leans on two stretched row-mappings (register #7, #19) — and the governor's own three interrogation answers are authoring/attestation failures, which argues R1/R9-first is equally defensible (decision D1/D2 are independent approvals precisely so the ordering stays James's call); (ii) REBUILD reason 2 carries a qualification — the mock's path 2 was repair-shaped, and the claim survives on the framing distinction (a co-equal same-day option under an ‘invalidated’ verdict, not a demotion to a rule-repair card); (iii) R5's charter edits should be James-gated exactly like governed docs — adopted: treat D7's R5 as James-gated text changes. The dissent's enrichment (the monitor's input key is literally named `cost_usd` while populated with AUD-derived cost — the R10 trap in schema form) attaches to decision D8.

---

# DISSENT PASS — verdict on `synthesis-fresh-synthesizer.md`

**VERDICT: CONCUR-WITH-NOTES.** I replayed the load-bearing citations against the repo working tree (stated identical to origin/main 1b471b60) and the frozen packet. Every code citation I checked holds exactly as cited. The notes below are recordable refinements, none rises to DISSENT.

## Spot-verification record (what I independently confirmed)

- `/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py` — write-once skip (:151-152), unparseable skip (:154-156), regexes (:42-47), run-date note (:165), bare UPDATE (:173-178), exit-command email (:179-185), `_send_alert` total swallow incl. missing env vars (:104-122). Register #1/#4/#5/#20/#21 anchored.
- Tape math from E05: 8 of the 36 days (07-03→08-08) closed above 230 (07-20, 07-28..08-05); 192.12 is the 07-02 close, no 07-03 row; −19.1% on 08-06. "DAY 36 BELOW STOP" (`brief-mock.html:297`) is false as stated. REBUILD reason 1 is evidence-forced.
- `/Users/jpcino/Desktop/asxos/asxos/domain/brief/collectors/wealth_state.py:57-59` exact-date join (register #8), :101-108 removed −75.7% return line (register #14/#15).
- Cross-currency chain (register #11): `position_monitor/service.py:216-222` sums `cost_base_normal` (AUD) → :286 per-share → :247 returned under the key **`cost_usd`** → `display.py:82-90` header P&L; `display.py:35` `cost_base_normal / quantity`; `tax/cgt.py:146-147` returns `None`. Math checks: 6,978.23÷24 = 290.76 vs 210.45 → −27.6%.
- `positions.py` grep: zero `fx_gain|forex|775` matches; spec `tax-alpha.md:338` contradicted (register #12). Spec :355-359 `acquisition_type` accommodation, absent from the E06 column list (register #13). `scripts/hubs_espp_scenarios.py:35` FX_ACQ 0.7162 — the third FX value (register #25).
- `classifier.py:69-83` single-print OR + permissive breadth skip (:77-81); `new_ideas.py:37-50` fail-open and return-before-count (registers #16/#17/#27); V2 spec :347-350, :359 as cited.
- `snapshot_portfolio.py:81-97/:274-284` proxy + flag semantics; `:294-296` `unrealised_fx_pnl` = MV − cost (registers #14/#26). `score_macro_theses.py:151-157` early return skips the :167-173 horizon check (register #19).
- `active_theses.py:43` `earnings_notes` fetched once, never referenced again (grep: single hit); :172 `cgt_date=None` (registers #7/#24). `severity.py:64-67` "do not sell"; :96-104 dead arm.
- Charter `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md` :41-43 `status='active'` LATERAL, :45-46 `model_a` pull, :52-53 non-AUD escape hatch, :109 currency-less template (registers #22/#23). `cli/thesis.py:926` sole `tax_notes` reader (register #4). `discipline.py:220-229` wording firewall — REBUILD reason 3 anchored.

## The six challenges

**1. Native failure modes — PASS, one note.** No recency overfit (the HUBS incident *is* the mandate), no cleanup-dressed-as-product (rule-integrity work is the charged mission, bounded to D0-04 inputs), and no memory-over-repo: the synthesis cites zero consolidated-memory content, and its FX ruling (§6 disagreement 2) correctly puts the governor's live answer above a stale governed doc *while surfacing the contradiction for a James-gated correction* rather than silently overriding — the right ladder handling. **Note (leverage-ranking):** the claim "R2 alone retires the CRITICAL compound class and five further register rows" (synthesis :99) leans on two stretched mappings — register **#7** (falsifiers live in `earnings_notes`, a column R2's scope text never touches; R2 governs `invalidation_conditions`) and **#19** (`score_macro_theses`, a sibling pipeline R2's scope doesn't name). Discount those two and R2's mass edge over R1 narrows; the R2→R1 order may still be right, but the stated justification overstates it.

**2. Overclaiming — PASS.** Every CONFIRMED row I replayed is confirmed; #31 is correctly PLAUSIBLE; #6 correctly carries "cause un-evidenced"; #3's class is honestly labeled adopted-assessment; #10 carries the swept-surfaces caveat. §5 restates the denominator caveat, and §2 note (iii) correctly treats zero-defect D0-04 items as unexercised, not cleared. The E08 latest-9 window is deep enough (spans back to 08-02) that the missed-runs inference is sound.

**3. Firewall — PASS.** No sentence in the synthesis or its quoted panel content is functionally-directive about HUBS/CBA; all HUBS ESS/CGT facts are held UNKNOWN; the closing abstentions line is honoured in the body. The closest approach — "the correct first successor artifact is the rule-repair card itself" (:79) — is product-process, not position direction.

**4. REBUILD verdict — SURVIVES; one wording note.** Reason 1 alone forces REBUILD: no layout change fixes a headline sourced solely from write-once state (verified in code). Reason 3 is anchored by `discipline.py:220-229` vs `brief-mock.html:297,344`. **Note (reason 2):** "the legitimate response — repair the rule, then decide — was structurally absent" is attackable as written: the mock's path 2 ("Re-underwrite… `asx thesis revise 2`", `brief-mock.html:345`) *is* a repair-shaped option. The claim survives only on the framing distinction (path 2 is offered as a co-equal same-day decision under an "invalidated" verdict and "Action requested" eyebrow, requiring UNAVAILABLE Q2 actuals — not a demotion to a repair card), and the proposal should carry that qualification explicitly.

**5. Bounded authority — PASS, one note.** Schema migrations (R1/R2/R3/R9), governed docs (R3/R4/R6/R7/R9), and parameters (R3 thresholds, R4 hysteresis/dislocation, R9 attestation/grandfathering) are all correctly James-gated; :101 explicitly declines to invent a mandate for the unmapped tax rows. **Note:** R5's authority class, "agent-charter change" (:96), is the only governed-text edit *not* marked James-gated. In a mission whose charge is "written rules are arbitrary," charter edits (e.g. stripping `model_a` from `portfolio-coherence-reviewer.md:45-46`) should carry the same gate flag as governed docs.

**6. Most likely rejection trigger.** The **R2 → R1 leverage ordering** (:99). All three of James's own interrogation answers — placeholder stop, error band, misunderstood trigger semantics — are *authoring/attestation* failures, i.e. R1/R9 territory; ranking the machinery fix first can read as the system again prioritising plumbing over the intake that produced 13/13 malformed rules, and the stated justification for R2-first partly rests on the two stretched row-mappings in note 1. Runner-up: the four tax-wiring rows (#11, #12, #13, #24) mapping to **no** R item, flagged-not-assigned (:101) — defensible under the Div 83A hold, but it leaves the money question James actually has visibly unowned.

**One enrichment, free to take:** the mechanism behind register #11 is sharper than either panel-7 or the synthesis states — the monitor's input key is literally named `cost_usd` while `service.py:247` populates it with the AUD-derived `cost_base_normal/quantity`. The misnamed field *is* the R10 trap in schema form and belongs in whichever work order carries the currency-consistency item.

Key files: `/Users/jpcino/.claude/jobs/cb048518/tmp/synthesis-fresh-synthesizer.md`, `/Users/jpcino/.claude/jobs/cb048518/tmp/evidence-packet-2026-08-08.json`, `/Users/jpcino/.claude/jobs/cb048518/tmp/brief-mock.html`, `/Users/jpcino/Desktop/asxos/jobs/check_thesis_invalidations.py`, `/Users/jpcino/Desktop/asxos/asxos/domain/position_monitor/service.py`, `/Users/jpcino/Desktop/asxos/asxos/domain/tax/cgt.py`, `/Users/jpcino/Desktop/asxos/docs/foundation/spec/tax-alpha.md`, `/Users/jpcino/Desktop/asxos/.claude/agents/portfolio-coherence-reviewer.md`, `/Users/jpcino/Desktop/asxos/asxos/domain/theses/discipline.py`.

---

## 5. Compiler's note (orchestrator)

I built the brief mock this mission condemns and authored the panel envelopes; under the
rev-4 conflict-of-interest guards I did not rank, judge, or filter. I verified the
synthesizer's citations spot-check clean against the packet and repo. **I record no
disagreement with the synthesis, including the REBUILD verdict on my own artifact.** Two
mission-process notes for the record: (i) the synthesizer's §5 "panel-2 numbering gap" is
an artifact of seat numbering in the rev-4 plan (seats were numbered 1 and 3–7; no seat 2
was ever defined or dispatched); (ii) its §7 worktree observation is this deliverable's own
isolated worktree, created after the packet was frozen — packet meta remains accurate for
packet-build time.

## 6. Decisions requested (inbox-shaped; approve / reject / defer each)

Nothing below executes without your approval. Default recommendations stated; a deferral
leaves current behaviour unchanged.

| # | Decision | Default recommendation |
|---|---|---|
| D1 | **Build R2** (invalidation state machine + semantics enum + instrument constraints; schema migration) | Approve — retires the CRITICAL compound class (register #1) and five further rows |
| D2 | **Build R1** (authoring/revision integrity: DB CHECK + service lint + parse-echo; schema migration) | Approve — closes the intake that produced 13/13 malformed ladders |
| D3 | **R3 governor inputs**: one canonical concentration-threshold table; conviction required-at-activation; employer-concentration representation; set the `[governor to set]` cash-floor/leverage holes | Decide values — the build is small once the numbers exist; the `wealth_state` join fix (register #8) is buildable immediately on approval |
| D4 | **R9 attestation policy**: placeholder-vs-underwritten field; grandfathering of the 13 existing rows | Approve the field; grandfather all 13 as `placeholder` pending your re-attestation |
| D5 | **R7 firewall policy**: functional-influence classification attaches to outputs, not lanes; the four-step ordering (rule integrity → enforceability → facts → options) becomes the governed standard for any decision-framing surface | Approve as governed-doc amendment |
| D6 | **R4 regime-gate**: approve fail-CLOSED + counted line (conformance, buildable now); decide hysteresis parameters and whether to approve the NEW-DESIGN dislocation mode | Approve conformance half now; defer dislocation mode until R1 fixes the band data it consumes |
| D7 | **R8 sweep + R5 fleet audit + R6 scorecard shadow test** | Approve R8 with R1/R2; defer R5/R6 until the fixture set exists |
| D8 | **Tax-wiring work order** (register #11 cross-currency break-even, #12 Div 775 orphan + spec §8.3 contradiction, #13 ESS `acquisition_type`, #24 dead CGT arm): the synthesizer flagged these as mapping to no R item — D0-04 should widen an item or add one | Approve as a new D0-04 sub-item ("tax-consequence wiring & currency consistency") |
| D9 | **Acquisition-FX resolution** (register #25): obtain the brokerage statement rate; correct whichever of the DB flag / conventions-doc "confirmed" claim is wrong | Your action (document outside agent contexts); until resolved every AUD P&L figure stays caveated |

### 6.1 Governor rulings (James, 2026-08-09, recorded by arbi)

**This subsection is the authoritative disposition of §6.** Transcribed verbatim from the
governor's ruling comment on PR #78 (2026-08-09T06:19:14Z), which was the only copy until
this document merged on 2026-08-17.

| # | Decision | Ruling |
|---|---|---|
| D1 | Invalidation-machinery rebuild (R2) | **APPROVED** |
| D2 | Authoring-integrity gate (R1) | **APPROVED** |
| D3 | Canonical conviction/cap framework | **APPROVED IN PRINCIPLE — values via finance agents**: James directs that the framework values be proposed by the finance agents, grounded in best investment practices + the prior north-star work — not ratified from today's defaults. Constraint carried from the register: the agents' own unsourced magic numbers (register #9, #23) may not be the source; proposals must cite external practice or governed prior work. The `wealth_state` exact-date join fix (register #8) proceeds with the D1/D2 build batch as a value-free bug fix unless James objects. |
| D4 | Placeholder/underwritten attestation | **APPROVED + grandfather all 13 existing theses as `placeholder`** pending re-attestation |
| D5 | Output-attached firewall policy (four-step ordering) | **APPROVED** as governed-doc amendment |
| D6 | Regime gate | **BOTH HALVES APPROVED** — conformance (fail-closed + counted suppression line) AND design (hysteresis + dislocation mode). Governor overrides the synthesizer's defer-recommendation on the design half. Panel-6's proposed parameters (enter 22/450/0.40, exit 20/420/0.45; disorderly 30/600 in, 26/550 out; majority-2-of-3 entry, 3-consecutive exit; dislocation_discount_pct 0.10, max 3 items) are the build's starting defaults, confirmed at PR review; the degenerate-band data caveat stands until R1 lands. |
| D7 | R8 sweep / R5 fleet / R6 scorecard | **R8 APPROVED** (builds with D1/D2); **R5/R6 DEFERRED** until the fixture set exists |
| D8 | Tax-wiring work order (cost_usd currency fix, Div 775 wiring/spec amendment, ESS acquisition_type, dead CGT arm) | **APPROVED** as a named D0-04 sub-item; ESS/Div 775 outputs stay caveated pending Div 83A facts/accountant review |
| D9 | Acquisition-FX resolution | **James's action** — brokerage statement resolves 0.6450 vs 0.7171 vs 0.7162; whichever of the DB "estimated" flag / conventions-doc "confirmed" claim is wrong gets corrected |

**Build authority as ruled:** approved items proceed as reversible draft PRs through the
normal review flow; schema migrations remain James-gated at apply time (Supabase MCP). D3's
value-setting task dispatches the finance agents in advisory mode; James sets the final
numbers.

**Implementation status as at merge (2026-08-17) — informational, not part of the ruling.**
D1/D2/D4 plus R8 were built on `claude/rules-integrity-build` and are **parked in draft PR
#80**, review loop incomplete; its migration `0042` is unapplied and absent from `main`
(`asxos/api/main.py:14` reserves the number by name). `docs/product/target-architecture.md`
§14 sets out the reconciliation each parked item needs before merge, and requires the
migration be redesigned as expand → backfill → dual-read/verify → contract. D3's
conviction/cap framework doc is not on `main`. D9 was subsequently resolved at 0.6450 and is
recorded in `.claude/rules/portfolio-conventions.md`. Treat every other line as open until
the roadmap says otherwise.

## 7. Mechanical verification of this deliverable

- Branch `claude/finance-red-team` from exact `origin/main 1b471b60cdaa176692cc5f987e8399acfdab03d9`, isolated worktree.
- Allowlist: `docs/proposals/finance-red-team-2026-08-08.md` + `docs/proposals/finance-red-team-2026-08-08-appendices.md`. `git diff --name-only origin/main` equals exactly these two paths; zero `.py`.
- The untracked convergence-sprint proposal (D0 programme) exists only in the main checkout and is untouched.
- Docs-only draft PR; James merges or closes.
