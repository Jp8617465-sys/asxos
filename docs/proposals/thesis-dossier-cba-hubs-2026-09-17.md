# The two real theses — dossier for James's disposition

**Status:** current · evidence and decisions only. **No number here is proposed by arbi.**
**Scope:** `theses` ids 1 (CBA.AU) and 2 (HUBS.NYSE) — after the 2026-09-17 rework these are the
only two rows left at `governance_status='approved'`, and the only two James authored
**Owner:** arbi produced it; every decision in §3 is James's
**Method:** `thesis-milestone-monitor` against `supabase-ro`, read-only. Rule #11 observed — no
`signals` row, no Model A output, not even via a hand-written query. Measured on the 2026-09-16
closes.

**Register state at the time of measuring:** 2 approved (ids 1–2), 11 retired (ids 3–13, tonight),
10 rejected (ids 14–23, yesterday).

**One correction to record first.** `conviction_level` is **NULL on both**. Every "conviction n/5"
anywhere in the docs is *unset*, not low.

---

## 1. CBA.AU (id 1) — the plan never described the security

Recorded: band 42.00–45.00, target 60.00, stop 38.00, timeline 540 days, opened 2026-05-28,
`status='watching'`, `actual_entry_price` NULL, **zero `holding_lots` rows ever**,
`invalidation_conditions` empty.

**The band was never reachable — not on one session of the 433 the repo holds.**

| | |
|---|---|
| price history | 2025-01-02 → 2026-09-16, 433 rows |
| close range | 142.36 – 191.40 |
| lowest low ever | **140.21** (2025-04-07) |
| sessions with low ≤ 45.00 (band ceiling) | **0** |
| sessions with low ≤ 38.00 (stop) | **0** |
| close on the day it was opened | 161.41 — already detached |

The band ceiling sits **3.12× below the lowest print on file**. The 60.00 target is 60.4% *below*
the current 151.54, so "hitting target" would need a two-thirds decline.

**No milestone verdict on this thesis carries information, and that is the important part.**
`actual_entry_price` is NULL and there are no lots, so both anchors `trajectory.py` can use are
absent — `progress_to_target` cannot be called at all. If an anchor were substituted,
`classify_trajectory` short-circuits on `current_price >= target_price` and returns
**ABOVE_TARGET** — a label meaning "thesis played out, realise profit" on a position that was never
opened, in a stock trading 2.5× the plan. That is the division artefact in its purest form, and it
is exactly the false positive an automated monitor would emit.

**The detachment-figure mystery is solved, and it was never bad data.** Three live formulas, all
arithmetically correct:

| formula | value (close 151.54) |
|---|---|
| `close / band_upper` | 3.367556 |
| `close / band_mid` | 3.483678 |
| `(close − band_upper) / band_mid` — the form `challenge_results` actually stores | 2.449195 |

The **2.471264** the register review quoted is that third formula on the **2026-09-15** close of
152.50. So the five conflicting figures across repo docs are one formula difference plus one
session's staleness. Filed as **E-21**: name one canonical definition with its formula beside it.

**Discipline state.** Exactly one `thesis_revisions` row ever — the `opened` one.
`last_revisited_at` is **111 days** old; `revisit_due_at` is **81 days past due**. In that window
the price moved 161.41 → 151.54 with no recorded response.

**And the system did challenge it — three times, with the ledger unmoved.** Three
`challenge_results` and three `decision_packets` (2026-09-01, 09-04, 09-16), **all `abstain`**,
zero dispositions recorded. The latest packet expires **2026-10-15** and its `decision_ask` says in
as many words: record a disposition for each finding. Two of its five findings are **blocking** — no
GICS sector recorded (so the D8 sector cap is uncheckable) and the price plan detached. Four more
rules were unevaluable for want of a measurement. Its scenario summary (+37.9% / 0% / −12.6%) is
computed off the 43.50 band midpoint, so those percentages describe a security trading at 43.50 —
not CBA. This gap is filed as **A-47**, the packet→thesis writeback.

---

## 2. HUBS.NYSE (id 2) — profitable, and its stop has never worked

Recorded: band 185.00–190.00, target 318.00, stop 230.00, timeline 365 days,
`actual_entry_price` 187.54, `status='active'`, one open lot (24 shares, ESPP, acquired 2026-05-31).

**The position is profitable on every defensible basis.** The currency trap that has twice produced
a false loss reading, shown so it cannot recur: `cost_base_normal` 6978.23 is **AUD**;
`prices.close` 236.46 is **native USD**. Dividing 6978.23 by 24 gives 290.76, which compared to a
USD close reads as −18.7% *and* as a violated stop. Both are false — that is an exchange rate
wearing a loss's clothes.

| basis | return |
|---|---|
| USD (both legs native; cost 4500.96 = 24 × 187.54 exactly) | **+26.09%** |
| AUD at the lot's recorded acquisition FX 0.6450 | **+14.80%** |
| AUD at the vendor FX 0.7171 | **+27.63%** |

**The stop at 230.00 is not a raised trailing stop.** I said it was earlier tonight and that was
wrong. Judged on entry and price path rather than on the ordering:

- It was authored **above the entry price** — 230.00 against a 187.54 fill, +22.6%. There was no
  prior profit to trail.
- The price fell away from it immediately: max close 262.20 on 2026-06-01, then down to 170.28 on
  2026-06-25.
- **48 of 77 sessions (62.3%) closed at or below the stop**, most recently 2026-09-10 (223.55) and
  2026-09-11 (225.33). The current 236.46 is a recovery back above a stop that has already gone.

A level a position closes below on 62% of its life is not functioning as a stop on any reading. The
most defensible characterisation from the data: it was set against the pre-crash regime the thesis
text describes, so it has behaved as a recovery marker, not a risk limit. **What it should be is
James's alone and no number is proposed here.**

Today it sits **2.73%** below the close (6.46 USD). The 2026-09-16 session alone ranged 10.44, so
the stop is inside one ordinary day's range.

**The constraint that makes all of this moot has no home in the schema.** The 2026-07-04
`assumption_change` revision records that the shares are in a **locked employee-share-scheme
window** and non-disposable, so the stop and the triggered invalidation "operate as ALERT/REVIEW
levels only, not executable sell triggers". It then says to record the window's end date when
known. It never was — and an `information_schema` scan for `%lock%`, `%window%`, `%blackout%`,
`%disposable%`, `%espp%` returns **zero columns across all tables**. A 74-day-old free-text note is
the only record of the fact that neutralises the entire stop mechanism on the only live position,
and nothing will tell James when it lifts. Filed as **A-48**.

**Trajectory here IS computable**, because the anchor is sound and in the same currency as the close:

```
HUBS.NYSE [conviction unset] | 108 of 365 days elapsed
Progress +26.09% of the +69.56% needed -> 37.50% of the journey at 29.59% of the timeline
Verdict ON TRACK (1.27x expected pace)
Required to target: +34.48% in 257 days = ~52% annualised
```

Two things that label does not carry, and both matter more than the label. **ON TRACK is a snapshot
one 2.73% move from STOP VIOLATED**, and the stop was live-breached six sessions ago. And the number
to weigh is the **~52% annualised** the remainder now implies, not the progress. Whether that is
plausible is James's assessment.

`last_revisited_at` is 74 days old, `revisit_due_at` 44 days past due, and the stop was breached on
25 of the 52 sessions since that revision with no further revision recorded.

**Two smaller defects found in passing.** The timeline expires **2027-05-31**, one day *before* CGT
discount eligibility on 2027-06-01 — and the thesis text names the CGT date as the intent, so the
horizon and the budget disagree by exactly the day that carries the discount. And
`invalidation_conditions[0]` cites a close of 192.12 on 2026-07-03; `prices` has no row for that
date and the 192.12 close is 2026-07-02. The value is right, the date is off by one session.

---

## 3. What James must decide

**CBA.AU**

1. Whether this row should exist as an active `watching` thesis at all, given the plan never
   described the security — including on the day it was written.
2. If it continues: whether the rate-cycle *reasoning* is still held, separately from the levels.
   Only the levels are demonstrably stale.
3. Which detachment definition is canonical (**E-21**).
4. A disposition for each of the three abstained challenges — the 2026-09-16 packet asks for
   exactly this and expires 2026-10-15. Specifically the missing GICS sector, the empty
   invalidation conditions, and the absent base rate.
5. Whether the 81-day revisit overdue is answered by a revision or by closing the row.

**HUBS.NYSE**

1. Whether a stop the position has closed below on 62% of its life is a stop he is still running —
   and what a stop means at all while the ESPP lock makes it unexecutable by his own revision.
2. Whether the lock-window end date can be obtained and recorded (**A-48** builds the column).
3. Which acquisition FX stands, 0.6450 or 0.7171. It moves the AUD return between +14.80% and
   +27.63% and sets the CGT cost base. **The database says unresolved;
   `.claude/rules/portfolio-conventions.md` says "confirmed against the brokerage statement". One
   is stale** — and that file is `.claude/`, so correcting it is a PR for James either way.
4. Whether 2027-05-31 (timeline) or 2027-06-01 (CGT discount, and the text's stated intent) is the
   governing horizon.
5. Whether ~52% annualised from here is a pace he believes — and the 44-day revisit, recorded
   either way.

---

**Summary across the two real theses:** STOP VIOLATED 0 (one breached-then-recovered) · STALLED 0 ·
BEHIND 0 · **ON TRACK 1** (HUBS) · ABOVE TARGET 0 · **NOT COMPUTABLE 1** (CBA — no anchor; any
verdict, including the ABOVE TARGET a monitor would emit on a substituted anchor, is an artefact).

Advisory and read-only. No write attempted, no order, no target, stop, band or size proposed.
