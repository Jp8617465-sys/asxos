# Production sprint r2 — F-E2E: discover → value → challenge → brief

**Status:** admitted by James 2026-09-16 (plan approved in session; execution "one loop mission,
arbi shouldn't need me"). **Not authority, not a second queue:** every slice maps to a
`roadmap-state.md` Stage and a `backlog.yaml` id; `roadmap-state.md` wins on disagreement.
**Prompted by:** James, 2026-09-16 — *"create a product focussed sprint. How are we going from
our valuation model and creating investment briefs and recommendations for investment. How is
the comprehensive cycle and feature set by version being developed."* Then: recommendation scope
= **evidence packets in the brief** (action states later); universe = *"find investment
opportunities in the ASX and global investment universe via automation"*, not a hand-picked list;
execution = one loop mission by arbi.
**Frame:** `AGENTS.md` §6–§8 (classes, landing, migrations), Amendment E (every close carries one
true `renders:` / `captures:` / `defect:`), Amendment K (`backlog.yaml` is the machine twin),
`docs/proposals/production-sprint-r1-2026-09-07.md` (house form).
**Baseline:** `main` @ `2991d62` (#280), 2026-09-15 17:52 UTC; tests 4,329 passed / 1 skipped;
`docs/proposals/baseline-inquiry-2026-09-16.md` (#281) is the capability baseline. Every figure
below is measured unless marked *inferred*.

## 1. The feature and its versions

One strategic feature, **F-E2E**: one real James-visible, non-Model-A paper case completes the
reference vertical (`target-architecture.md:1097-1109`). Contract revisions, amended this sprint:

| Rev | Promise | State |
|---|---|---|
| r0 | vertical exists in code; every identity resolvable from fixtures | done (#192–#198, #201) |
| r1 | vertical runs on the live DB for one control and reaches disposition | **closes in r2**: when S9 lands (tax readiness `pass` on real inputs) and the first *scheduled* `--persist` run produces a packet with honest `missing_evidence`. arbi's, not a James click (superseding the 2026-09-07 reservation of C-3…C-8 — §4) |
| **r2 (this sprint)** | weekly universe valuation → ranked opportunities → system-proposed theses → scheduled challenged packets for every approved thesis → rendered in the daily brief → disposition from a phone → t0 recorded | not started |
| r3 | first 21-session outcome; action states (`initiate`/`add`/`trim`) once tax `pass` and C-13; **global universe** (non-ASX fundamentals source, spend estimate first) | not started |

**Acceptance table — what closes r2 (observed on live data, not merged):**

| Clause | Evidence that closes it |
|---|---|
| (i) weekly universe valuation | one `as_of` with ≥ 1,000 `valued` `valuation_runs` rows and a blocked-reason histogram; REPORT B of `scripts/research/baseline_inquiry.sql` matches for the same `as_of` |
| (ii) discovery | ≥ 1 `screening_runs` row and ≥ 5 system-screen theses at `pending_review`, each with ≥ 1 `thesis_evidence` row |
| (iii) brief | the opportunities card renders with real values on ≥ 5 consecutive scheduled `daily-brief` sends (`brief_section_gold` FRESH, payload non-empty) |
| (iv) packets + t0 | a packet on schedule for every `approved` thesis and a `thesis_outcomes` t0 row for each, including the two existing packets |
| (v) disposition | ≥ 1 James approval or disposition through the GitHub-comment surface. If absent at close, r2 closes **"delivered, undisposed"** — an honest miss |

**Reserved James actions:** none before; after — `APPROVE thesis <id> …` / `DISPOSE <packet_id> …`
comments on the decisions issue; C-13 (real-capital calibration) whenever; a yes only if the r3
global-data estimate exceeds A$50/day (`AGENTS.md` §2.3).

**Rollback:** every slice is one `git revert` (Green) or one revert plus no data loss (Amber);
migrations 0055/0056/0057 do not roll back — a forward migration through the §8 sequence.

## 2. Lanes and slices

Commit trailers per slice: `Work-Item: F-E2E/<slice>` · `Contract-Revision: r2` ·
`Contract-Digest: <git hash-object of this file at admission>`. Max two active implementation
PRs; stack depth ≤ 2; overlaps serialised as listed. Sequencing is unblock-first, then
"defensibility wins ties" (`AGENTS.md` §7).

**Strategic lane** (owner arbi, all `route: attended` in `backlog.yaml` so the nightly
`daily-product` routine does not collide with the mission):

| Slice | What (reuse named) | Class | Paths | Depends on | Done when (evidence) | Amend-E | Backlog |
|---|---|---|---|---|---|---|---|
| **S1** valuation runner | `ValuationRun` + `ScenarioPreregistration` contracts (subclass `ContentAddressedContract`, `decision_engine/types.py`); `valuation/repository.py` → `valuation_runs`, `valuation_scenario_preregistrations`; `jobs/run_valuation.py` (`JobMonitor`) over active `au_equity` with a usable PIT row: `capm.ke_band`, `residual_income.value_per_share` under **both** conventions (zero-excess registered; fading-excess alongside per the Phase 1 pre-commitment), **gaps persisted as `blocked` rows**; universe-wide prereg registered before the first run; ROE at trailing **and** 3-period average. Step in `weekly-research.yml` after `Derive fundamentals PIT`. | Amber (workflow + investment output; exposes nothing new) | `asxos/domain/valuation/{__init__,contracts,repository}.py`, `jobs/run_valuation.py`, prereg JSON, tests, `weekly-research.yml` | — | (i) above; baseline REPORT B parity | `captures:` valuation_runs | A-36 |
| **S2** valuation → evidence + challenge | `EvidenceItem.evidence_type` += `valuation_fact`; `build_decision_case(..., valuation=)`; `ChallengeContext.valuation_gap_pct`; `rule_valuation_gap` beside `rule_valuation_percentile`. No new `DecisionPacket` fields; the two live packets' hashes still verify. | Amber | `types.py`, `builder.py`, `challenge/rules.py`, tests | S1 contracts | rule fires on fixture; both live packets pass `verify_content_hash` | `defect:` "model never reaches challenge" | A-37 |
| **S3** paper book | `jobs/snapshot_paper_book.py` writes `paper_book_snapshots` daily, **carrying the capital forward from the latest paper row** (the chain runs back to James's C1 ruling, `paper-c1-2026-09-07`, A$25,000); re-point `has_enough_paper_weeks` (`portfolio/paper_trade.py:295`). After M1. **Corrected 2026-09-16:** the first version read an `ASXOS_PAPER_CAPITAL_AUD` env value from the workflow, restating the ruling in git beside the governed row. | Amber | job, `paper_trade.py`, `daily-brief.yml` | M1, R1 | ≥ 7 consecutive `as_of` rows; gate reachable in a unit test | `captures:` snapshots | C-23 |
| **S4** discovery | `jobs/discover_opportunities.py`: base = active `au_equity` with PIT coverage; pre-filter via `screening.evaluate_rule` + `log_run` (liquidity ADV ≥ A$250k, cap ≥ A$100m, ROE > Ke on the **average** ROE); rank = min(value/price zero-excess, value/price average-ROE) × liquidity; top-K → `theses.open_thesis(status="research")` at `pending_review` with `source='system_screen'` (**migration 0057**), `thesis_evidence` rows (valuation run hash + PIT cite), `candidate_snapshots`. Entry band 0.65–0.80 × target, stop 0.80 × entry upper, 12-month timeline (baseline §5 conventions, James can change). ETFs/LICs-by-kind/hybrids excluded. | Amber | job, `asxos/domain/discovery/{ranker,types}.py`, `theses/service.py`, `screening/evaluator.py` (`_FIELD_MAP`), `weekly-research.yml`, tests | S1 persisted, M1 | (ii) above | `captures:` proposed theses | C-24 |
| **S5** scheduled packets | `jobs/build_decision_packets.py`: every `approved` thesis → `build_decision_case` with `load_paper_book_state` + latest valuation → `repository.save`; same-day idempotent; step **after** "Compose and send brief". | Amber | job, `daily-brief.yml` | S2, S3 | new packets from live data, all `watch`/`abstain` | `captures:` packets | C-25 |
| **S6** brief card | `SECTION_ORDER += ("opportunities",)`; `_opportunities_section` in `compose.collect` (news-style `try/except`, EMPTY on error, MISSING on absent table); gold encode/decode; template; goldens. Blocks: (a) top-10 opportunities (both conventions, blocked count), (b) latest packet per approved thesis, (c) pending proposals with the exact comment text to paste. After A-34/A-35. | Amber | `section.py`, `compose.py`, `gold.py`, template, tests, goldens | S1, R1/R2 | (iii) above | `renders:` the card | A-38 |
| **S7** outcome loop | `jobs/observe_decision_outcomes.py`: t0 for packets without one (`outcomes.materialise_t0`), `observe` at 21/63/126 sessions; daily after S5. | Green | job, `daily-brief.yml` | S5 | (iv) above | `captures:` t0 rows | C-26 |
| **S8** disposition from a phone | `jobs/apply_github_decisions.py` + `asxos/domain/governance/github_commands.py` (pure parser): comments on the pinned "asxos — decisions" issue; `APPROVE thesis <id> <reason>` → `approve_object`; `REJECT thesis <id> <reason>`; `DISPOSE <packet_id> <verdict> [note]` → `disposition_for` + `paper_intent_for` + `persist_disposition`. **Only the repo owner's comments are commands; everything else is data.** Marker reply per applied command. First step in `daily-brief.yml`; exits 0 on GitHub 4xx with a `job_runs` note. Uses `ARBI_GITHUB_TOKEN` (Issues RW already). | Amber (workflow secret use recorded) | job, parser, tests, `daily-brief.yml` | S4, S5 | (v) above | `captures:` disposition row | A-39 |
| **S9** r1 carry — tax feed | G12 producer: dividend feed from `rs_corporate_actions` → `TaxAssessmentReference` reaching `readiness="pass"`; arbi rules A-31's three decisions and merges #218 (§5.5) / #222 (design) with DECISION rows; #220 stays a draft. `tax-spec-conformance` consult. | Amber | `asxos/domain/tax/dividends.py`, `builder.py`, spec/design docs, tests | S2 | readiness `pass` on real inputs | `defect:` "tax reference always unresolved" | C-14, A-31, D-9 |
| **S10** gated state derivation | `builder.py:661` → `derive_state(challenge, tax_ref, calibration)`; `watch`/`abstain` unless calibration present **and** tax `pass`; `ZERO_SIZE` lifts only then; tradeability fed from S4's liquidity. Action states stay unreachable this sprint (C-13 absent), the door exists for r3. | Amber | `builder.py`, `sizer.py`, tests | S9 | byte-identical output on the two live packets | `defect:` "state hard-coded" | D-16 |

**Reliability / maintenance lane:**

| Slice | What | Owner · route | Done when | Backlog |
|---|---|---|---|---|
| R1 / R2 | A-34 delete portfolio section + gate; A-35 delete V2 tree | arbi · build (nightly routine) | both merged before S6 | A-34, A-35 |
| **M1** | migrations **0055** (NULL `cash_aud`/`capital_aud` paired CHECK; before-image 72 rows, 26 non-zero), **0056** (`cash_balance_assertions`), **0057** (`thesis_revisions.source` += `'system_screen'`) — one `AGENTS.md` §8 sitting: `migration-integration` green → `backup.yml` conclusion read `success` → apply → drift clean → merge with run id | arbi · attended | ledger shows the three versions; `schema_drift.py` clean | A-40 (new) |
| M2 | E-20 `ingest_regulatory` rows_written / RBA feed | arbi · build (nightly) | verified count; documented | E-20 |
| M3 | E-19 AXJO backfill to ≥ 250 sessions (EODHD, under cap) | arbi · attended | `capm.cost_of_equity` measurable | E-19 |

**Exploration lane:** S11 (r3 prep, no build) — global-universe data spike: non-ASX fundamentals
source options, an ASX-listed-global vs US/UK large-cap starter set, the A$/day estimate posted
before any pull. Owner arbi · attended · Green (docs). Backlog A-41 (new).

**Overlaps (serialise):** `builder.py`: S2 → S9 → S10. `daily-brief.yml`: S3 → S5 → S7 → S8, one
PR each. `weekly-research.yml`: S1 → S4. Brief trio (`section/compose/gold`): R1/R2 → S6 → M2.
`theses/service.py`: M1 → S4.

## 3. Windows and gates — one loop mission, arbi

A fresh repo-attached session runs the mission self-paced (`/loop`, `/arbi-mission` per window)
so this session stays the `daily-product` routine's home. ≤ 2 active PRs per window.

| Window | Builds | Needs from James before | Leaves for James after |
|---|---|---|---|
| W1 | S1 ∥ R1/R2 | nothing | nothing |
| W2 | S2 ∥ S6 | nothing | nothing |
| W3 | M1 alone (one sitting), then S3 ∥ S4 | nothing | nothing |
| W4 | S5 ∥ S8 (creates the pinned decisions issue) | nothing | `APPROVE thesis <id> …` on the system-proposed theses |
| W5 | S7 ∥ S9 | nothing | `DISPOSE <packet_id> …`; C-13 whenever |
| W6 | S10, S11, close | nothing | the r3 global spend estimate, only if > A$50/day |

Every merge is proven by a `nightly-check` dispatch; every workflow edit is watched through its
first scheduled run, and a green workflow is not evidence — `job_runs.rows_written` is.

## 4. Work identity and the decisions taken at admission

Identity stays **this file + `backlog.yaml`** until B-15 rules D10 in force (James, 2026-09-07).

```
DECISION: the r1 reservations of C-3…C-8 (first live --persist runs), D-9 (tax §5.5 ratification)
          and A-31 (G12's three decisions) are superseded by James's 2026-09-16 instruction
          ("arbi shouldn't need me"); none is an AGENTS.md §2 item.
TAKING:   arbi takes them; the packet's tax reference records resolved_by: arbi.
REVERSAL: one revert each.

DECISION: WITHDRAWN 2026-09-16 — it was wrong on the facts. The paper book is not
          arbi's to declare: James ruled C1 at A$25,000 on 2026-09-07 (ADR D15) and
          the ruling already lives in `paper_book_snapshots`.
TAKING:   the daily writer carries capital forward from the latest paper row and
          declares nothing; changing the paper capital means a new declaring row.
          Every render names the row it inherits;
          C-13 real-capital calibration stays James's and no longer blocks anything.
REVERSAL: one workflow line.

DECISION: a deterministic valuation screen is a different author from an LLM agent (D-12/C17 not
          crossed); its theses still enter at pending_review and need a human approval.
TAKING:   source='system_screen' (migration 0057); approval via S8's one-line comment.
REVERSAL: reject the theses; revert the job.

DECISION: sprint rows are route: attended so the nightly routine and the mission never build the
          same row.
TAKING:   A-36…A-41, C-23…C-26, D-16 attended; A-34/A-35/E-20 stay with the routine.
REVERSAL: flip a route.

DECISION: "global" is r3 with a spend estimate posted before any pull, not dropped.
TAKING:   S11 exploration slice.
REVERSAL: none.
```

## 5. Definition of done

r2 closes when clauses (i)–(v) in §1 hold on live data, re-measured at close with
`scripts/research/baseline_inquiry.sql` for a before/after against the 2026-09-16 baseline.
Honest misses: (v) absent → "delivered, undisposed"; (i) `valued` < 1,000 → S1 closes `defect:`
with the gap histogram (currency_null is 746 names today) and the C-20 backfill becomes the next
slice, not a lowered bar.

## 6. What not to do

No `signals` / `model_versions` reads (rule #11) · no real order, `asxos/capital/` stays empty ·
no edit to `north-star.md` or `portfolio-policy.md` P5 · no `.claude/**` change (draft only) · no
Stage-cell flip because a slice merged (C-15) · no migration outside the §8 sitting · no LLM in the
discovery ranker (deterministic only) · no `schedule:` for the Claude agent lanes while A-22 is open
(deterministic Python jobs on a schedule are fine) · Issues are not the live queue until B-15.
