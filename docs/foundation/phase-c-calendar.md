# Phase C — Calendar

Anchor date: today is Tuesday 2026-05-19. The calendar covers M1 through M6 from `docs/rebuild/phase-5-milestones.md`. After M6 the system has working model inference with SHAP. Calendar planning stops here; M7-M12 (signals persisted, tax layer, retraining, regulatory, brief, production) gets its own calendar exercise once you reach M6 and have a real velocity measurement to plan from.

## Inputs

Original milestone day estimates from phase-5-milestones.md, restated:

| Milestone | Deliverable | Focused days |
|---|---|---|
| M1 | Repo bootstrap, hard-fail lifecycle, first migration applied | 1–2 |
| M2 | EODHD ingestion for one symbol, end-to-end, idempotency test | 2 |
| M3 | Universe load + bulk price ingestion for all active ASX symbols | 1 |
| M4 | Fundamentals refresh job | 1 |
| M5 | Feature engine ported, 22 features computable from prices + fundamentals | 3 |
| M6 | Model A loaded, predictions + SHAP for one date, CLI `asxos signal BHP.AU` | 2 |
| Total | | 10–11 focused days |

A focused day equals roughly six hours of uninterrupted dev work, the kind you get on a Sunday morning when nothing else is happening.

Pre-M1 work is not counted in the milestone estimates but is required: the BUILD_GUIDE Part 2 cull, the BUILD_GUIDE Part 3 service setup (Render account verification, GitHub repos for asxos and asxos-backups, Resend domain verification, Healthchecks.io account), the Supabase Pro-to-free downgrade. Estimate: one weekend of evening-and-Sunday work, roughly two to three focused days spread across a week.

Australian public holidays in the relevant window: Queen's Birthday Monday 2026-06-08 (NSW, VIC, ACT, SA, TAS — not QLD, WA). This is the only major holiday between now and mid-August 2026. A long weekend is a small productivity boost rather than a drag.

## Calendar A — Optimistic (10–12 hours per week, no slip)

Assumes you find roughly two weeknight evenings (about three hours each) plus most of one weekend day. Roughly twelve hours per week of dev time. No milestone slips. This calendar is achievable only if life cooperates — no work crisis, no weekend interruptions, no tax accountant call eating Saturday, no kids' commitments overrunning Sunday.

| Week | Dates | Work |
|---|---|---|
| 1 | May 19 – May 24 | **Pre-work.** Cull Render Starter crons (8 services), downgrade Supabase Pro → free, cancel Voyage AI, create new GitHub repos (`asxos`, `asxos-backups`), provision Render + Resend + Healthchecks accounts, generate GitHub PAT for backup repo. |
| 2 | May 25 – May 31 | **M1.** Repo bootstrap. `pyproject.toml`, Docker Compose for local Postgres or Supabase preview branch, Makefile, `asxos/config.py` with fail-fast loader, `asxos/db.py` with asyncpg pool, `asxos/api/main.py` with hard-fail lifespan. Apply `0001_initial.sql` via Supabase MCP. Verify `/health` returns 503 when DB is stopped. |
| 3 | Jun 1 – Jun 7 (long weekend Jun 6–8) | **M2.** EODHD ingestion module (`asxos/ingestion/eodhd.py`), `asxos/jobs/sync_prices.py` for one symbol (BHP.AU hardcoded), JobMonitor port to `asxos/jobs/monitor.py`, idempotency test. Queen's Birthday long weekend is the bulk of the work. |
| 4 | Jun 8 – Jun 14 | **M3.** Universe load (`asxos/ingestion/universe.py`), bulk price ingestion via EODHD EOD bulk endpoint, full ASX universe (~2,200 symbols). Verify ~2,000 price rows for today's date. |
| 5 | Jun 15 – Jun 21 | **M4.** Fundamentals job (`asxos/jobs/sync_fundamentals.py`), per-symbol rate-limited ingestion, weekly cadence. Begin M5 prep (read existing feature engine code). |
| 6 | Jun 22 – Jun 28 | **M5 part 1.** Feature engine port begins. Momentum and volatility feature groups. The 3-day milestone starts here. |
| 7 | Jun 29 – Jul 5 | **M5 part 2.** Remaining six feature groups (liquidity, trend, cross_sectional, fundamental, macro, sentiment) plus `_safe_quintile` guard plus training/serving parity test. |
| 8 | Jul 6 – Jul 12 | **M6.** Model A artefact load, in-memory cache, `predict_with_shap()`, CLI `asxos signal BHP.AU` returns "BUY (confidence 12) — driving factors: mom_6 (+0.027), pe_ratio_zscore (-0.018), trend_200 (+0.012)". |

**Optimistic M6 done: Sunday 2026-07-12.** Eight weeks from today.

## Calendar B — Realistic (5–7 hours per week, one milestone slips)

Assumes you find one weekend day at most, plus the occasional weeknight evening. Roughly six hours per week of dev time. One milestone slips — almost certainly M5, the feature engine, which is the only milestone with real complexity. This calendar treats slip and life drag as the expected case rather than the exception.

| Week | Dates | Work |
|---|---|---|
| 1 | May 19 – May 24 | **Pre-work part 1.** Cancel Voyage AI, downgrade Supabase to free, create new `asxos` GitHub repo, generate Render account verification. |
| 2 | May 25 – May 31 | **Pre-work part 2.** Cull Render Starter crons (one or two per evening), create `asxos-backups` repo, generate GitHub PAT, set up Resend domain verification, create Healthchecks check URLs. |
| 3 | Jun 1 – Jun 7 | **M1 part 1.** Repo bootstrap files (`pyproject.toml`, Makefile, `.env.example`, Docker Compose). |
| 4 | Jun 8 – Jun 14 (Queen's Birthday Jun 8) | **M1 part 2.** Hard-fail lifespan handler, first migration applied via Supabase MCP, `/health` 503-on-stopped-DB verified. Long weekend helps. |
| 5 | Jun 15 – Jun 21 | **M2 part 1.** EODHD client and rate limiter. |
| 6 | Jun 22 – Jun 28 | **M2 part 2.** JobMonitor port, idempotency test. M2 finished. |
| 7 | Jun 29 – Jul 5 | **M3.** Universe + bulk prices for ASX 200 (smaller universe initially). |
| 8 | Jul 6 – Jul 12 | **M4.** Fundamentals job. |
| 9 | Jul 13 – Jul 19 | **M5 part 1.** Feature engine port begins. Momentum + volatility groups. |
| 10 | Jul 20 – Jul 26 | **M5 part 2.** Liquidity + trend + fundamental groups. |
| 11 | Jul 27 – Aug 2 | **M5 part 3.** Cross-sectional + macro + sentiment groups, parity test. |
| 12 | Aug 3 – Aug 9 | **M5 slip week.** Most likely scenario: the training/serving parity test fails at small magnitudes, you debug the rounding/dtype difference, and it takes the full week to find the cause. |
| 13 | Aug 10 – Aug 16 | **M6 part 1.** Model A artefact load and cache. |
| 14 | Aug 17 – Aug 23 | **M6 part 2.** `predict_with_shap`, CLI command. |

**Realistic M6 done: Sunday 2026-08-23.** Fourteen weeks from today.

## Per-milestone slip risk and reassessment trigger

For each milestone: the single most likely cause of slip, and the calendar-week trigger at which you stop pushing the date back and re-scope the milestone instead.

**M1 — Repo bootstrap.** Most likely slip: the local dev environment fights back. Postgres in Docker vs Supabase preview branch ergonomics, getting `/health` to actually 503 when the DB is stopped, lifespan handler ordering. Reassess trigger: **if M1 takes more than 4 calendar weeks**, the local dev environment is wrong. Drop docker-compose entirely. Use only a Supabase preview branch via `mcp__supabase__create_branch` for development. The complexity vanishes.

**M2 — EODHD ingestion.** Most likely slip: the JobMonitor port has unexpected dependencies on the old codebase's `app/core/events`, alert webhook config, or SMTP fallback that take days to untangle. Reassess trigger: **if M2 takes more than 4 calendar weeks**, the JobMonitor port is over-scoped. Inline it as a simple `try/except` plus an INSERT into `job_runs` plus a Healthchecks ping. The webhook alerts and SMTP fallback wait.

**M3 — Universe + bulk prices.** Most likely slip: universe normalisation surprises. `.AU` vs `.AX` ticker suffixes, delisted handling, missing tickers from EODHD bulk endpoint, currency mismatches on the small number of foreign-listed ASX entities. Reassess trigger: **if M3 takes more than 3 calendar weeks**, ship a smaller universe — the ASX 200 only, loaded from a static CSV. Defer the full universe load to a later milestone. The system can produce signals on 200 stocks before it produces them on 2,200.

**M4 — Fundamentals.** Most likely slip: EODHD's fundamentals endpoint is per-symbol and much slower than the bulk EOD endpoint. Rate limiting on per-symbol calls plus the larger response payloads adds up to hours of wall time. Reassess trigger: **if M4 takes more than 3 calendar weeks**, ship without fundamentals for v1. The feature engine produces only the 16 technical features (momentum, volatility, liquidity, trend) rather than all 22. Fundamentals features wait for M4a.

**M5 — Feature engine.** This is the highest-risk milestone and the most likely candidate for the realistic-calendar slip. Most likely slip: the training/serving parity test fails. Computing features for the same date twice produces almost-equal results but not byte-equal results. The cause is usually a subtle dtype difference (float32 vs float64 in pandas), a different NaN-handling path (`_safe_quintile` edge case on a small group), or a date boundary mismatch (using `as_of` inclusively in training and exclusively in serving). Each cause takes a day or two to track down. Reassess trigger: **if M5 takes more than 5 calendar weeks**, scope down to just momentum and volatility feature groups (10 of 22 features). The other six groups become a separate milestone M5a. The system can run with a reduced feature set; better that than blocking on a parity test that won't converge.

**M6 — Model A load + SHAP.** Most likely slip: the existing `model_a_v1_5_classifier.txt` artefact from the old repo refuses to load in the new environment. Dependency version skew on LightGBM, joblib, or numpy is the most common cause. Reassess trigger: **if M6 takes more than 4 calendar weeks**, retrain Model A on the new feature outputs rather than porting the existing artefact. This is itself a multi-day exercise but it is well-scoped and the M5 deliverable produces clean inputs for it. Becomes milestone M6a.

## Which calendar to start with

**Start with the realistic calendar. Treat any earlier delivery as a happy surprise.**

The optimistic schedule implies near-monastic discipline plus zero life intrusions for eight weeks. Solo founders building on evenings and weekends almost always converge on five to seven hours per week of effective time, not ten to twelve. A 10-12-hour week is what you get when there's no tax accountant follow-up, no work crisis, no family commitment overruns, and no weekend where you're just too tired to sit at a screen. Plan for the steady state, not the best case.

The realistic schedule also bakes in one full milestone slip on M5, which is the only milestone with real complexity. If M5 doesn't slip you ship M6 by 2026-08-16, a week early. If you genuinely hit 10-12 hours per week you ship M6 by 2026-07-12, five weeks early. Both happy outcomes; both invisible to anyone other than you.

The cost of committing to the optimistic schedule and missing it is psychological more than practical. Missing a calendar you committed to feels like a setback. Missing a calendar you padded by 50% feels like a setback only if M5 takes seven weeks instead of three. The realistic schedule gives you slack you can use silently rather than slack you have to explain.

**Realistic finish date: 2026-08-23. Plan against this. Anything earlier is bonus.**

## What this calendar does not cover

After M6 the system has model inference. It does not yet have: persisted signals (M7), tax alpha layer (M8 — uses the new spec at `docs/spec/tax-alpha.md`), retraining pipeline (M9), regulatory ingestion (M10), morning brief (M11), production deployment to Render (M12). Those are six more milestones, roughly eight to ten more weeks at the realistic cadence.

Total system-complete from today: 2026-08-23 (M6) plus 8–10 weeks = late October to early November 2026. The full timeline is roughly five months at the realistic cadence. M1-M6 is the foundation; the real personal-OS-is-useful moment is M11 (morning brief), and that's in late October at the earliest.

Once you reach M6 and have a real velocity measurement (actual hours spent per milestone vs estimated), redo this calendar exercise for M7-M12 with calibrated inputs.
