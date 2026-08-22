# asxos execution chain — 2026-08-22

**Status:** live mission envelope for this session (not a second queue)
**Authority:** James — exclusive-writer cleared; start executing a chain
**Canonical queue:** `docs/product/roadmap-state.md` (Amendments D/E)
**Red-team:** `/arbi-run` 2026-08-22 — campaign CHALLENGE; hybrid holds with amendments

This file is the envelope for **one** work order. It does not reopen the four-wave
campaign. Later units get their own envelope after `/arbi-close`.

## /pm-review proof (this session)

`/pm-review HUBS.NYSE` ran with post-#149 agent definitions.

Four fan-out agents, **zero** Model A / `signals` figures. Direct
`thesis-coherence-guard` on thesis 2 returned **NEEDS REVIEW** (revisit 19d
overdue) — not EXAMINED, not a crash.

```
HUBS.NYSE — VERDICT: REVIEW

FOR
- ON TRACK: 40% of journey at 23% of timeline; stop $230 intact vs $239.86
  (thesis-milestone-monitor)
AGAINST
- XJO total-return benchmark unavailable; no alpha computed
  (benchmark-performance-analyst)
- 100% of book vs 10% per-name / 30% sector caps; conviction NULL; ESPP locked
  (portfolio-coherence-reviewer)
- 4.1% from stop (alert only while locked) (portfolio-coherence-reviewer)

MARKET: risk-off orderly as of 2026-08-20 — 33.0% of names above 200-day MA
(threshold 40%); AVIX 10.85; ASX 200 9,083.80 (market-context-narrator)

HERE'S WHY: price progress is ahead of linear pace, but the book is a locked
single-name concentration with no conviction, no usable XJO-TR comparison, and
an overdue revisit. REVIEW, not EXIT-CANDIDATE: stop intact; ESPP window locked.
Watch: unrecorded lock-window end date and the $230 stop.
```

`#150` is already on `main` (`d15266f`).

## THE ONE THING (this PR)

**W1-1 — `asxos_pit_db` acquisition path** (P5 integration evidence, not Stage 4).

Widen `AcquisitionPath` to `Literal["hashed_fixture", "asxos_pit_db"]`.
SELECT-only over `rs_security_master`, `rs_financial_statements`,
`rs_fundamentals_pit`, `prices`. Hashed PIT snapshot; JSON/MD render; `abstain`
with named `missing_evidence` for G2/G3/G5. Fixture never-real invariant stands.

**Amendment E:** `renders:` one live PIT-backed review (honest abstain).

## Binding constraints

One work order / branch / draft PR / close. Not Stage 4 complete. No tax import.
No allocator. No screening INSERT. No 0045.
Code path is Python allowlist-only (app role). This VM had no DATABASE_URL;
the live render used the same four-table SELECT list, then adapt_pit_snapshot.
HUBS/CBA are not this unit's symbol.

## Must not touch

`0042`; `signals` / Model A; theses writers; tax math; V2 flag; merge; F4.

## Next (after close)

James names screening seed, 0045, or SB1-02. Do not chain without a close row.


## Amendment E renders (this unit)

`renders:` `docs/proposals/w11-tls-pit-renders-2026-08-22.md`

TLS.AU FY2024 yearly income, cutoff 2025-08-21. `acquisition=asxos_pit_db`
`data_mode=real` `outcome=abstain`. Missing G2 / G3 / G5 named.
presentation_sha256 `1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0`.

Not Stage 4. CLI exists (`asx results-review show`) but was not executed on
this VM (no `DATABASE_URL`).
