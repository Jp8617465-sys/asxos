# Thesis register review — what the 13 actually are

**Status:** determination by arbi, 2026-09-16, at James's instruction — *"@arbi should conduct a deep
research and red team with finance agents"* — in reply to his audit question about the paper book,
"the research theses screens", and what is hard-coded.
**Method:** three read-only finance agents fanned out from the main loop
(`thesis-milestone-monitor`, `thesis-coherence-guard`, `deep-research-agent`), every claim re-verified
by arbi against the live database before it was written here. Red-team pass recorded in §7.
**Boundary:** this document is **evidence and a recommendation**. No `theses` row was written by it.
Any change to a thesis is a governed transition requiring James's approval, which the S8 decisions
issue now makes a one-line comment. Rule #11 holds throughout: no `signals` or `model_versions` read.

## 0. Corrections after red-team review (2026-09-16)

Five errors in the first draft of this document, all found by `arbi-red-team` and all re-verified by
me against code and live data before being written here. They are listed first because two of them
change what should be *done*, not merely what was said.

1. **The provenance claim rests on the text string alone.** §1 infers "Model-selected" from the
   eleven rows' own `thesis_text`. The corroborating facts (NULL levels, one timestamp, zero evidence,
   zero governance events) establish **bulk-created and empty** — which is the ground the
   recommendation actually stands on — but they do **not** independently establish Model A
   provenance, and no `rebalance_runs` / `agent_runs` artefact was cited. The retirement case is
   safe; the headline framing was over-claimed.
2. **"Dissolves the question" overstates it.** James asked about *ownership*. Provenance answers "why
   do these rows look wrong". **§6 is the actual answer to his question** and should be read first.
3. **Rec 1 is not executable as written** — see §5.
4. **Rec 6's justification was wrong** — see §5.
5. **Two arithmetic errors**, corrected in place below: the "61 runs / daily for 84 days" line (61
   runs over 84 days is not daily), and "two of them (WTC, OCL) also appear in the valuation sweep"
   — **six** of the eleven do (TPW, ATR, WTC, BLX, OCL, KPG), verified against `valuation_runs` at
   `as_of='2026-09-16'`.

## 1. Where the thirteen came from

I told James yesterday that the 13 theses' entry bands, stops and targets *"were typed by James"*.
**That is wrong, and wrong in the direction that matters.** Verified in `theses` on 2026-09-16:

**Eleven of the thirteen (ids 3–13) carry this `thesis_text`, character-identical on all eleven:**

> *"Auto-seeded from paper build run_id=1 for PM review. **Model-selected** (5d-signal sleeve is
> quarantined, paper-only); entry band = build reference price. **Conviction + thesis rationale
> pending — owner: PM.**"*

They were written by one INSERT at `2026-06-24 10:24:25.925853+00` — eleven rows, one transaction,
one timestamp. They are the **candidate list of a quarantined model's paper build**, parked in the
theses table for a review that never happened. Their own text says the rationale is pending.

| | ids 3–13 (11 rows) | id 1 CBA.AU | id 2 HUBS.NYSE | ids 14–23 (10 rows, today) |
|---|---|---|---|---|
| Author | auto-seeded from paper build | **James** | **James** | S4 discovery (`system_screen`) |
| `thesis_text` | "rationale pending — owner: PM" | *"Rate cycle play — NIM expansion when RBA cuts and deposit repricing lags"* | ESPP into the BofA-driven dip, with the business case | residual-income value under both conventions, cited |
| `stop_price` | **NULL ×11** | 38.00 | 230.00 | computed ✓ |
| `target_price` | **NULL ×11** | 60.00 | 318.00 | computed ✓ |
| `timeline_days` | **NULL ×11** | 540 | 365 | 365 ✓ |
| entry band | **zero-width** (lower = upper) | 42.00–45.00 | 185.00–190.00 | real band ✓ |
| `conviction_level` | NULL | NULL | NULL | NULL |
| `governance_status` | **`approved` — by column default** | `approved` (default) | `approved` (default) | **`pending_review`** ✓ |
| `thesis_evidence` rows | **0** | 0 | 0 | **20** (2 each) ✓ |

**`governance_events` contains zero rows of `object_type='thesis'`.** All 13 reached `approved`
without a transition, a reviewer or an audit row — it is the DEFAULT for human-authored theses
(migration 0033/0034), not a decision. **"Approved" on these 13 means nobody ever said no.**

**So the model-versus-James framing in yesterday's memo was wrong.** When the valuation model
screened "10 of 12 of James's theses" as expensive, it was disagreeing with **a quarantined model's
unreviewed candidate list**, not with James's judgement. Only two rows are James's written theses,
and the model's verdict on those two is not the interesting fact about either (§3).

This is also the direct answer to *"I am a bit confused about … the research theses screens"*. The
confusion is well founded: **eleven of those rows are not theses.** They have no stop to breach, no
target to progress toward, no horizon to expire and no rationale to test.

## 2. What follows mechanically — the instrumentation gap

Because those eleven carry no levels, nothing in the discipline system can act on them:

- **Stop violations: 0 of 13** — eleven have no stop; CBA's sits 75% below market (§3); HUBS's is
  intact at +5.2% and was reclassified alert-only on 2026-07-04 because the shares are ESPP-locked.
- **Timeline expiries: 0 of 13** — eleven have no timeline, so they cannot expire, ever.
- **Classifiable at all: 2 of 13.**
- **`check_thesis_invalidations` has run 61 times over the 84 days to 2026-09-15** (not daily — 61
  runs, 84 days). Every one of those runs passed over the eleven rows and **none could ever fire on
  them**. The silence is structural: it would look identical if every one of them had collapsed.
- **Revisit-overdue: 13 of 13** (44–81 days). Every thesis gets a flat 30-day revisit regardless of
  its horizon, so CBA (540-day) and an eleven with no horizon at all are treated the same.

## 3. The two real theses

**CBA.AU (id 1) — a scale defect, not a result.** Band 42.00–45.00, stop 38.00, target 60.00,
against a close of **152.50**. CBA's entire 432-row price history (2025-01-02 → 2026-09-15) ranges
142.36–191.40: it has never traded within 100 points of that band. The band can never be entered and
the stop can never be hit. Any "progress to target" reading (+660%, "ABOVE TARGET") is a division
artefact. **Do not read CBA as a win.** The levels were typed against a wrong scale — most likely
per-share figures for a different instrument or a pre-split basis.

*Measured detachment, corrected:* the first draft said "~3.4×". The quantity the `price_detached`
rule actually tests is `detachment_ratio` — distance from the **nearest band edge** over the **band
midpoint** (`rules.py:518-524`) — which is (152.50 − 45) / 43.5 = **2.471264**, against a blocking
threshold of 1.0. Five different "×detached" figures for CBA now circulate in repo docs (3.4, 3.5,
2.62, 2.653333, ~4) and none of them is this one, because they are price÷band ratios. Reconciling
them to the measured quantity is its own small backlog item.

**HUBS.NYSE (id 2) — the stop was above the entry from inception.** `stop_price` 230.00 exceeds
`actual_entry_price` 187.54 and the band upper 190.00: as typed, the thesis was stop-violated the day
it opened. It reads as intact today only because price ran to 241.96. The 2026-07-04 revision
reclassified $230 as an alert level, not an executable trigger, because the shares are locked — a
correct decision that leaves the field reading as a stop to anything that does not parse the prose.
Two items that revision recorded as open 74 days ago are still open: the lock-window end date, and
the acquisition FX (0.6450 vs 0.7171), on which the AUD P&L sign depends. The FX was later confirmed
against the brokerage statement in `.claude/rules/portfolio-conventions.md` — **that confirmation
never reached the database**.

## 4. The structural finding: the ledger and the examination machinery are not connected

`theses.last_revisited_at` says CBA has been untouched since 2026-05-28. **It has not been.** CBA was
independently challenged twice — `dpk-cba-1-2026-09-01` and `dpk-cba-1-2026-09-04`, both
`abstain`, `model_independence=true`, with a full `challenge_results` bear case naming the failing
rules. Neither moved `last_revisited_at` by a second.

**Root cause, in code:** `thesis_versions` / `decision_packets` / `challenge_results` key on
`symbol` + `exchange` with **no `thesis_id` FK** to `theses`; and `decision_engine/builder.py` only
*reads* `last_revisited_at` (`:356`, `:789`) — the sole writers are in `theses/service.py`. A
complete challenge-and-abstain cycle can run without the discipline ledger noticing, and did, twice.

**Consequence for any review, including this one:** *"days since last review" is a floor, not a
measure.* Wherever the ledger says stale, the honest reading is "no review was recorded here".

## 5. Recommendation

**Nothing here is executed. Each item is a one-line comment on the decisions issue (S8)** — except
where marked, because two of the six turned out not to be one-line items at all.

**Sequencing, and it is binding on Rec 1.** The first scheduled `daily-brief` run is tonight,
2026-09-16 20:30 UTC, and `build_decision_packets` builds one packet **per approved thesis**.
Retiring eleven (plus CBA) before it fires leaves **one** approved thesis — the ESPP-locked,
alert-only HUBS — and the mission's own DoD (iv)/(v), which closes C-23/C-25/C-26 on observed
`job_runs.rows_written`, cannot be read in the shape the handoff specifies. **Order: run fires →
counts observed → C-25/C-26 closed → then retire.**

| # | Recommendation | Why | Reversal |
|---|---|---|---|
| 1 | **Retire the eleven auto-seeded rows** (ids 3–13) — **after tonight's run** | They are a bulk-created, empty candidate list with the rationale explicitly pending; they carry no capital; while they sit at `approved` they misrepresent the book's discipline state | **NOT one transition each — this is a code build.** `status` has no `'retired'` value (`0012:68-70` CHECK: research/watching/active/exited/expired). `governance_status='retired'` is valid (`0033:38`) but **no code path reaches it**: `service.py` exposes only `approve_object`/`reject_object`, and `reject_object` hard-fails on a row already `approved` (`:1017-1019`), which all eleven are. `cli/thesis.py` has no retire verb. A raw `status` UPDATE would write **no** `governance_events` row, because the 0034 trigger guards `governance_status` only |
| 2 | **Fix CBA's levels or retire it** — **already owned: backlog D-3, and ruled by James 2026-07-16** | Detached 2.471264 against a 1.0 blocking threshold; currently unfalsifiable | one revision. Not a new finding — cite D-3 |
| 3 | **Record HUBS's two open items** — lock-window end date, and the FX confirmation that lives in a repo doc but not the database | The AUD P&L sign depends on the second | one revision |
| 4 | **Wire the writeback** (arbi's, code): when a decision packet completes for a symbol with a thesis, write a `thesis_revisions` row and move `last_revisited_at` | Otherwise the ledger keeps under-reporting, and every future review inherits this defect. **This is the only recommendation here that changes the product** rather than tidying state — it is the discipline moat, `north-star.md` layer 2 | one revert |
| 5 | **Make the revisit cadence horizon-scaled**, not a flat 30 days | A 540-day thesis and a 90-day thesis should not share a review clock. This is also the cadence mechanism that unblocks the deferred `m14_candidate_governance_aware_revisit_cadence` | one revert |
| 6 | **Close the `governance_status` DEFAULT, then add the level gate** | My first draft said *"the eleven could not exist in this state if the gate existed"*. **Wrong** — this document's own §1 says they reached `approved` by **column default** (`0033:37`), never passing through `approve_object`, so a gate inside the approval path would have been bypassed by exactly the route they took. If the stated cause is the default, the fix is the default. The level gate is still worth having (the ten new rows already satisfy it), but it is the second half, not the first. Note when it lands: `apply_github_decisions` routes an `APPROVE` comment straight into `approve_object`, so a new hard-fail becomes a refusal comment on James's phone | one revert |

**Do not** conclude from the valuation sweep that James's picks were wrong. Ten of the twelve were
never his, and of the two that were, the model's disagreement with CBA is confounded by a scale
defect in the thesis row itself.

## 6. The direct answer to James's question — and it is not the clean one I first wrote

This is the section that answers *"all this should be owned by arbi and the financial agent system.
What is hard coded right now?"*, and it should be read before §1.

**What I first wrote:** the ten rows opened by S4 discovery (ids 14–23: BWP, PGF, HLI, CWP, KAR, YAL,
HVN, CCP, LSF, HM1) are "the correct shape" — cited rationale, computed stop, target and entry band,
365-day timeline, two `thesis_evidence` rows each, `governance_status='pending_review'` awaiting
James. *"That is the machine proposing and the human disposing."*

**The shape is right. The contents are not, and `portfolio-coherence-reviewer` found why.** Verified
by me against `theses` and `prices` on 2026-09-16:

| Finding | Evidence |
|---|---|
| **The "computed" levels are three constants.** On all ten rows, to six decimal places: `stop = 0.640000 × target`, `entry_band_lower = 0.650000 × target`, `entry_band_upper = 0.800000 × target` | `SELECT stop_price/target_price, entry_band_lower/target_price, entry_band_upper/target_price FROM theses WHERE thesis_id BETWEEN 14 AND 23` → identical on every row |
| **So the stop sits 1.54% below the bottom of its own entry band**, on every name, with **no reference to the security's volatility**. Fill at the band's lower edge and the stop is inside one day's noise; fill at the upper edge and it is 20% away. The same thesis carries a 13-fold different risk profile depending where in its own band it fills | arithmetic on the ratios above |
| **`LSF.AU` (id 22) was proposed already below its own stop** — close 4.82 against stop 4.957965. The screen emitted a thesis that was stopped out at birth | `prices` 2026-09-15 |
| **Six of the ten are above `entry_band_upper`** and not actionable (HLI, CWP, KAR, YAL, HVN, CCP); three are in band (BWP, PGF, HM1) | same query |
| **Four of the ten are outside the valuation model's domain.** PGF, LSF and HM1 are listed investment companies and BWP is an A-REIT: for an LIC "ROE" is the portfolio's return and "book" is NAV; for a REIT under IAS 40 property revaluations run through profit, so ROE *contains the mark* and the model capitalises a one-off revaluation as a recurring excess return. Three of the four are GICS-tagged "Financial Services", so the 30% sector cap reads them as financials diversification when the economic exposure is broad equity beta | `universe`; `theses.thesis_text` ids 14–23 |

So: the entry band, stop and timeline I called "policy that should live in a governed row" in the
sprint plan were not merely un-governed — **they are three multipliers on a model fair value, applied
uniformly to a REIT, two coal-and-oil names and three closed-end funds.** That is the same defect
class as the A$25,000 paper-capital literal James caught me on, one layer further in, and it is a
better answer to his question than anything in §1.

**What genuinely is working**, and it is not nothing: the rows carry a cited rationale naming the
value under both conventions, two `thesis_evidence` rows each (20 total, against **0** on the
original thirteen), and `governance_status='pending_review'` — awaiting James rather than defaulted
to approved. The governance skeleton does what it was built to do. **It is the numbers flowing
through it that are unowned.**

## 7. Red team — the objections and what survives

*Recorded before any recommendation above is acted on.*

- **"You are retiring eleven rows on a text string."** The string is not the only evidence: NULL
  stop/target/timeline on all eleven, a zero-width band equal to the build reference price, one
  shared INSERT timestamp, zero evidence rows, zero governance events. The text corroborates; it
  does not carry the finding alone.
- **"Auto-seeded does not mean worthless — some may be good businesses."** Agreed, and the
  recommendation does not say otherwise. Retiring the *row* destroys no analysis, because no analysis
  exists in it. Any of the eleven can be re-opened as a real thesis with levels and a rationale;
  **six** of them (TPW, ATR, WTC, BLX, OCL, KPG — corrected from "two") appear in the 2026-09-16
  valuation sweep and can be judged there on their merits.
- **"The model screened them expensive, so retiring them is the model governing James's picks."**
  This is the objection the fan-out was commissioned to test, and it fails on the facts: they are not
  his picks, and the recommendation rests on their *emptiness*, not on their valuation. Retirement
  would be correct even if the model had screened all eleven cheap.
- **"Rule #11 says do not act on Model A output — is retiring them acting on it?"** No. Retiring a
  row *because* it is unreviewed Model A output is the quarantine being enforced, not circumvented.
  The alternative — leaving them at `approved` — is the state rule #11 warns against.
- **"Days-since-review is unreliable (§4), so the fatigue evidence is unsafe."** Correct, and it is
  why fatigue is not the ground for any recommendation here. The grounds are missing levels, missing
  evidence and missing governance — all directly observed, none inferred from the revision clock.

## 8. Verification

- Provenance: `SELECT count(*) FROM theses WHERE thesis_text ILIKE '%Auto-seeded from paper build%'`
  → **11**; the same 11 return NULL for `stop_price`, `target_price`, `timeline_days`.
- Governance: `SELECT count(*) FROM governance_events WHERE object_type='thesis'` → **0**.
- Evidence: `thesis_evidence` → **0** rows on ids 1–13, **20** rows on ids 14–23.
- CBA scale: `MIN(close), MAX(close)` for CBA.AU over `prices` → 142.36 / 191.40 against a band of
  42.00–45.00.
- After any accepted recommendation: the transition appears in `governance_events` with a reason,
  and `thesis_revisions` gains the matching row — the two artefacts whose absence is the finding.
