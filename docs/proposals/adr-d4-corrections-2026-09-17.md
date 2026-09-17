# Proposed ADR corrections — D4 #3 and D4's scoring basis

**Date:** 2026-09-17 · **Status:** PROPOSAL — awaiting James's ratification
**Governor-owned:** `docs/product/architecture-decision-record.md` is James's (`AGENTS.md` §14).
arbi drafts; James ratifies, amends or rejects. **Nothing in this document changes the ADR.**

Two corrections, found by measurement during the selection/ideation mission. Both concern **D4**, the
eight-criterion bar that gates rule #11's removal — so both affect what it would take to lift a
quarantine, which is why they go to you rather than being filed as backlog rows.

---

## Correction 1 — D4 #3 records a state that measurement contradicts

**Current text** (`architecture-decision-record.md:174`):

> 3. **Survivorship-clean** — delisted securities included. Already supported.

**Measured 2026-09-17 via `mcp__supabase-ro__execute_sql`:**

| `rs_security_master` | rows | Common Stock | with any `prices` row | with any `rs_fundamentals_pit` row |
|---|---|---|---|---|
| `is_active = false` | 2,040 | 1,872 | **57** | **1,515** |
| `is_active = true` | 2,399 | 1,861 | 2,398 | 1,857 |

**Survivorship-clean is true of the fundamentals panel and false of the price panel.** Of 2,040 delisted
names, 1,515 carry point-in-time fundamentals and **57** carry any price history at all.

**Why this is not pedantry.** Every cross-sectional test needs a forward **return**, and returns come
from prices. A test can only include a delisted name if that name has prices spanning its delisting. So
D4 #3 — a criterion recorded as *already met* — **is not satisfied for any test this system can
currently run.**

**This already produced a misleading reassurance.** The sealed value-to-price run (#304) reported that
only **4** names across all four cutoffs dropped for want of a forward price, and that read as evidence
the survivorship correction had worked. It is better explained the other way: the delisted names were
never in the price panel to drop. A near-zero attrition count on a panel that excludes the dead is what
survivorship bias looks like when you measure it with the biased instrument.

**Proposed replacement:**

> 3. **Survivorship-clean** — delisted securities included. **Supported on the fundamentals side only**
>    (`rs_fundamentals_pit` carries 1,515 of 2,040 delisted names). **NOT supported on the price side**
>    (57 of 2,040), so forward returns cannot currently include delisted names and this criterion is
>    **unmet**. Meeting it requires a delisting-inclusive price backfill, driven off
>    `rs_security_master` rather than `universe.is_active`.

**Reversal cost:** none. This is a factual correction to a status annotation; no code depends on it.

---

## Correction 2 — D4's scoring basis names a table that should not be revived

**Current text** (`architecture-decision-record.md:181`):

> Scored on the same `signal_outcomes` basis Model A faced (correlation of predicted vs realised 5-day
> and 21-day return) — which requires Slice 4, since the writer no longer exists (§3.3).

**Two things have changed since this was written (2026-08-23).**

**(a) Slice 4 is partly built.** `asxos/domain/decision_engine/outcomes.py:1-3` states it *"Replaces the
deleted `jobs/track_signal_outcomes.py`"*, backed by migration 0052 and the live
`jobs/observe_decision_outcomes.py`. What does not exist is a writer keyed to a *registered strategy's
forecast* rather than to a `decision_packets` row — so the remaining work is a **generalisation of
`outcomes.py`**, not the rebuild this line anticipates.

**(b) `signal_outcomes` should not be written to again, and the reason is forensic.** Reviving a frozen
rule-#11 table is the thing rule #11 forbids — but there is now a stronger reason than the rule. The
2026-09-17 archaeology established, against the deleted code:

| finding | evidence |
|---|---|
| the job skipped any signal with no entry-date price, and stored `NULL` when a symbol stopped trading before +5d/+21d | `jobs/track_signal_outcomes.py:85-93`, `:101-102` @ `6fa2b21^` |
| returns were **simple, price-only, on raw `close` not `adj_close`** — a split enters as a spurious return | `:70`, `:101-102` |
| `was_direction_correct` was computed **only at 21 days**, though the model's label was a **5-day** horizon | `:104-107` |
| its selection window opened at `as_of − 21 **calendar** days` while `actual_return_21d` needs 21 **trading** days, and a `NOT EXISTS` guard meant those rows were **never re-evaluated** | `:29-30`, `:33-56` |

So `signal_outcomes` is **conditioned on survival to +21 trading days**, unadjusted for corporate
actions, and structurally seeded with permanently-`NULL` 21-day rows. It is a sound evidentiary record
of *what Model A's signals did* — which is all the decay analysis used it for, correctly — and it is
**not a sound scoring basis for a successor**.

**Proposed replacement:**

> Scored on realised forward returns at the horizons a successor claims to predict, written by a
> **model-agnostic forecast-outcome writer** — a generalisation of
> `asxos/domain/decision_engine/outcomes.py` (ADR Slice 4, migration 0052) from `decision_packets` to any
> registered strategy's forecast. **Not** `signal_outcomes`: that table is frozen under rule #11, and is
> in any case survivorship-conditioned, unadjusted for corporate actions, and structurally
> `NULL`-seeded at 21 days (see `docs/research/selection-landscape-2026-09.md`). Returns must be
> adjusted-close and total-return, and must include names that delisted inside the window — which
> depends on #3 above.
>
> `OUTCOME_WINDOWS_TRADING_DAYS` (`decision_engine/types.py:44`) **must not be widened** to serve this:
> it drives decision-packet outcomes, which are investment output (Amber). A successor's horizons belong
> in their own constant.

**Reversal cost:** none as a document change. It does redirect a future build from "rebuild
`track_signal_outcomes.py`" to "generalise `outcomes.py`", which is the cheaper of the two and does not
touch a quarantined table.

---

## What these corrections do *not* do

- **They do not lift or weaken rule #11.** Model A's output stays quarantined.
- **They do not lower D4's bar.** Correction 1 makes D4 *harder* to satisfy by marking a criterion unmet
  that was recorded as met. Correction 2 changes the instrument, not the threshold.
- **They do not authorise an ML build.** ADR §7's *"until D4's bar is met"* is untouched.

---

## Context: why both surfaced now

The mission that found them opened on a premise I asserted and did not verify — that no measured
deterministic baseline existed. It was false; the value×quality composite and its evaluation engine were
both already implemented. Checking that premise properly is what surfaced these two, and the general
lesson is already recorded on `main` as **L53**: *a writer producing a questionable value and a consumer
trusting it are two separate facts — open the readers before ranking by severity.*

Applied here: D4 has been read many times as a checklist. Nobody had run the query behind the words
*"Already supported"*.
