# Working memory — 2026-07-11 · run `etf-phase1-build`

**Layer:** untrusted working scratch (ladder 8) — advisory only until a dream + the promotion
gate promote it into `../approved-lessons.md`.

**Run:** ETF/multi-instrument Phase-1 Slice-1 as arbi-led build (James: "you are my lead…
scope the best build"). Migration 0037 (`security_kind`) applied to prod on James's go;
readers kind-scoped to `au_equity`; forced-sell + rebalance-snapshot kind-scoped; two INSERT
writers fixed. Commits a708dd5 → df1edd9. Two independent reviews (portfolio-invariant-guard,
security-engineer) each caught a real forward-looking gap the 1264-passing suite missed.

---

## Candidate lesson L-cand-2 — a NOT NULL column with no default breaks every unpatched writer the instant the migration lands

**Status:** candidate · **Type:** migration/ordering · **Source:** `/pm`-led ETF build 2026-07-11
**Applies-when:** adding a `NOT NULL` column (no default) to a populated table with multiple
INSERT writers.
**Behaviour-change:** update **every INSERT writer** (not just readers) IN THE SAME change that
applies the migration, and **verify each emitted INSERT against the real constraint** (a
rolled-back txn is fine) before considering it done. Readers being behavior-preserving is not
enough — writers fail loudly in prod the moment the constraint is live.

**What happened.** I got the *readers-first* ordering right (ML readers → `au_equity` before
ingesting any ETF, so Model A can't be polluted). But I applied 0037 (`security_kind NOT NULL`,
no default) to prod while two INSERT writers still omitted the column: `refresh_universe`
(weekly cron, breaks on the next new listing) and `_ensure_in_universe` (`asx holdings add` —
the primary trade-entry path — breaks on any new symbol; `ON CONFLICT DO NOTHING` does NOT
suppress a NOT NULL violation). security-engineer caught it; live replay confirmed the old
insert fails `23502` and the fixed inserts succeed. The 1264-passing suite missed it because
mocked connections don't enforce constraints — the **exact** portfolio-conventions verification
lesson, now on the writer side.

**The fix choice was itself load-bearing:** do NOT paper over it with a column DEFAULT — a
default silently classifies any future unclassified write as `au_equity`, the very Model-A
pollution vector `security_kind` exists to close. Keep the column defaultless (fail loud,
non-negotiable #10) and classify explicitly per writer — and by SUFFIX, not a constant, because
`_ensure_in_universe` sets `is_active=TRUE`, so a foreign ESPP symbol hardcoded `au_equity`
would leak a US equity into the ML universe.

**Process correction for next time:** for an additive NOT NULL column, either (a) update
readers AND writers in the branch and apply the migration only after both are verified, or (b)
add the column nullable + backfill, ship writers, THEN a follow-up sets NOT NULL. I applied on
James's "apply it" before the writers were ready → a (loud, non-corrupting) prod exposure that
lasts until PR #24 merges + deploys.

## Candidate lesson L-cand-3 — the fan-out review catches forward-looking gaps a green suite cannot

**Status:** candidate · **Type:** review-process · **Source:** same run
Two reviewers, two real catches the tests passed straight through:
- portfolio-invariant-guard: the forced-sell edit closed only ONE of TWO auto-liquidation
  paths — a held ETF would still hit the `exited_universe` full-sell via the rebalance snapshot.
  Fixed (snapshot now kind-scoped, mirroring the foreign guard).
- security-engineer: the NOT NULL writer breakage (L-cand-2).
Both were "no-op today, breaks on first real ETF" gaps — invisible to a suite with no held ETF
and no real constraint. Reinforces L-cand-1 (reconcile-at-source) generalised to *proactive*
review: on a structural migration, ask each specialist "what breaks on the FIRST real use,"
not just "do current tests pass."

## State at end of run (for the dream to fold)
Slice-1 complete + safe: 0037 live; readers `au_equity`; both fund auto-liquidation paths
closed; writers fixed + live-verified; ~1266 tests pass (16 joblib errors + 1 lightgbm fail are
documented sandbox gaps). **Live exposure until PR #24 merges+deploys:** new-symbol writes fail
loudly (no corruption). Slice-2 (ingest VGS/VAS + passive mandates) is now purely additive.
