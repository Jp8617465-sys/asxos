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

## 1. The finding that dissolves the question

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
- **`check_thesis_invalidations` has run 61 times, most recently 2026-09-15.** It has passed over
  those eleven rows daily for 84 days and **can never fire on them**. Its silence is structural — it
  would look identical if every one of them had collapsed.
- **Revisit-overdue: 13 of 13** (44–81 days). Every thesis gets a flat 30-day revisit regardless of
  its horizon, so CBA (540-day) and an eleven with no horizon at all are treated the same.

## 3. The two real theses

**CBA.AU (id 1) — a scale defect, not a result.** Band 42.00–45.00, stop 38.00, target 60.00,
against a close of **152.50**. CBA's entire 432-row price history (2025-01-02 → 2026-09-15) ranges
142.36–191.40: it has never traded within 100 points of that band. The band can never be entered and
the stop can never be hit. Any "progress to target" reading (+660%, "ABOVE TARGET") is a division
artefact. **Do not read CBA as a win.** The levels were typed against a wrong scale — most likely
per-share figures for a different instrument or a pre-split basis.

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

**Nothing here is executed. Each item is a one-line comment on the decisions issue (S8).**

| # | Recommendation | Why | Reversal |
|---|---|---|---|
| 1 | **Retire the eleven auto-seeded rows** (ids 3–13) — `status='retired'`, reason recorded | They are a quarantined model's candidate list with the rationale explicitly pending; rule #11 forbids acting on Model A output anyway; they carry no capital; and while they sit at `approved` they misrepresent the book's discipline state | one governed transition each; the rows are append-only history, nothing is deleted |
| 2 | **Fix CBA's levels or retire it** | Its band is unreachable by a factor of ~3.4; it is currently unfalsifiable | one revision |
| 3 | **Record HUBS's two open items** — lock-window end date, and the FX confirmation that lives in a repo doc but not the database | The AUD P&L sign depends on the second | one revision |
| 4 | **Wire the writeback** (arbi's, code): when a decision packet completes for a symbol with a thesis, write a `thesis_revisions` row and move `last_revisited_at` | Otherwise the ledger keeps under-reporting, and every future review inherits this defect | one revert |
| 5 | **Make the revisit cadence horizon-scaled**, not a flat 30 days | A 540-day thesis and a 90-day thesis should not share a review clock | one revert |
| 6 | **Require a stop, target and timeline before a row may reach `approved`** | The eleven could not exist in this state if the gate existed; the ten new `system_screen` rows already satisfy it | one revert |

**Do not** conclude from the valuation sweep that James's picks were wrong. Ten of the twelve were
never his, and of the two that were, the model's disagreement with CBA is confounded by a scale
defect in the thesis row itself.

## 6. What is working

The ten rows opened today by S4 discovery (ids 14–23: BWP, PGF, HLI, CWP, KAR, YAL, HVN, CCP, LSF,
HM1) are the correct shape and the contrast is the clearest evidence that the sprint fixed the right
thing: a cited rationale naming the value under **both** conventions, a computed stop, target and
entry band, a 365-day timeline, **two `thesis_evidence` rows each (20 total)**, and
`governance_status='pending_review'` — awaiting James, not defaulted to approved.

That is the machine proposing and the human disposing, which is what "owned by arbi and the financial
agent system" is supposed to mean.

## 7. Red team — the objections and what survives

*Recorded before any recommendation above is acted on.*

- **"You are retiring eleven rows on a text string."** The string is not the only evidence: NULL
  stop/target/timeline on all eleven, a zero-width band equal to the build reference price, one
  shared INSERT timestamp, zero evidence rows, zero governance events. The text corroborates; it
  does not carry the finding alone.
- **"Auto-seeded does not mean worthless — some may be good businesses."** Agreed, and the
  recommendation does not say otherwise. Retiring the *row* destroys no analysis, because no analysis
  exists in it. Any of the eleven can be re-opened as a real thesis with levels and a rationale; two
  of them (WTC, OCL) also appear in the valuation sweep and can be judged there on their merits.
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
