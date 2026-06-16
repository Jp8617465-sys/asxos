# ASXOS Current State, Quant Guide Synthesis, and Next Roadmap

*Created 2026-06-16 · Branch `claude/asxos-current-state-quant-guide-synthesis` (off `main` @ `a719b3c`) · Documentation only — no production change.*

This pack integrates three things: (1) the **proven** scheduled-cron production recovery, (2) the **Quant Platform Benchmarking Guide v2** (sibling branch `claude/quant-platform-benchmarking-guide`), and (3) **new empirical evidence** that resolves the two P0 signal-correctness risks from production data.

## Claim categories (kept separate, per the research standard)
1. **Verified ASXOS production facts** — from SELECT-only `job_runs`/`prices`/`signals` queries this session.
2. **Verified repo/code facts** — `file:line` from this session's audits.
3. **Quant guide claims** — from the v2 guide; `[verify]` caveats preserved.
4. **Public/institutional theory** — publicly documented standards, not private fund internals.
5. **ASXOS recommendations** — opinion, marked.
6. **Speculative** — marked.

## Headline
- **Production loop: GREEN.** Tuesday 2026-06-16 window ran end-to-end; signals advanced 2026-06-10 → **2026-06-15**; recency-gate fresh-path + `latest_complete_trading_day` anchor proven live. 7/8 jobs succeeded (only `ingest_regulatory` failed on the known ATO/Treasury feed).
- **Signal correctness: RED (contained).** Both P0 risks are now **CONFIRMED from data**, not merely suspected — see `04`. The pipeline *runs* correctly; the *labels* are mis-specified. Do not treat labels as portfolio-ready.
- **Data completeness: YELLOW.** Four missing trading days (2026-06-04/05/11/12); no durable `price_coverage` metadata.
- **Classification (unchanged): ML-assisted ranking signal with unverified alpha** — now with confirmed label mis-specification on top of the unverified-alpha status.

## Reading order
| File | Contents |
|---|---|
| `01-production-current-state.md` | Proven cron recovery + fresh query data + GREEN/YELLOW/RED/UNKNOWN |
| `02-quant-guide-synthesis.md` | What the v2 guide says, distilled to next-decision claims |
| `03-asxos-vs-market-leaders.md` | Condensed gap table vs serious-quant standard |
| `04-p0-signal-correctness-plan.md` | **The crown jewel** — both P0 risks CONFIRMED empirically + fix plan |
| `05-price-completeness-plan.md` | The 4-day gap, `price_coverage` design, sequencing |
| `06-priority-roadmap.md` | What to build / defer / not-build-yet |
| `07-parallel-workstream-plan.md` | Safe parallelism for Opus + UltraCode |
| `08-future-prompts.md` | Pasteable next prompts |

## Single recommended immediate next action
> **Revised after independent red-team — see `09-redteam-and-revisions.md` (authoritative; overrides `04`/`06` sequencing).**

**E — ship the brief honesty caveat, standalone.** The P0 verification is **done in this pack (both risks CONFIRMED)**, but the *fix* should not lead: the brief caveat is the only **zero-risk, reversible, no-label-change** step that removes the real user-facing harm now (STRONG_BUY/SELL shown as calibrated 5%-conviction signals the data shows they are not). **Then, in order:** (1) close the artefact-scale UNKNOWN (read-only P0-A); (2) **adj_close adoption + retrain `v1_6`** (the deeper data fix; regenerates `expected_return` on clean prices); (3) **derive label thresholds once** on the clean `v1_6` distribution — avoiding the double re-derivation that a units-fix-first order would cause. Baseline/rank-IC research and the price-gap (`GAP`) + `price_coverage` designs run **in parallel as read-only**. Production status is **GREEN-provisional** (needs ~4 clean weekly cycles).
