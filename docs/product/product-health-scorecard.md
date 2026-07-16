# ASXOS Product Health Scorecard

**Generated:** 2026-07-14 (hand-assembled from live read-only queries this run, via the
read-only Supabase MCP role — `scripts/product_health.py --write` cannot reach the DB directly
from this sandbox, its own `asyncpg`/`DATABASE_URL` connection times out on this network; the
queries below mirror `_freshness`/`_cron_reality`/`_investment_readiness`,
`scripts/product_health.py:53-138`, exactly).
**Top line:** 🔴 **2 FAIL · 🟡 3 WARN** — the data pipeline is fresh and the monitoring lane
that was degraded on 2026-07-11 has **substantially recovered** (see below). `track_signal_outcomes`
still shows FAIL, but that's stale pre-fix data awaiting revalidation, not a new break (corrected
below — an earlier draft of this doc mis-framed it as new); `retrain_model_a` is still broken
(mitigated by rule #11, not a live-ops emergency).

> Answers *is ASXOS actually working?* — not *did tests pass?*.

---

## 🔴 What's actually broken today

1. **`track_signal_outcomes` — 0/1, but this is stale pre-fix data, not a new failure.**
   Its only recorded run was 2026-07-12 and failed; the cast fix (PR #30, commit `db5a3ff`)
   landed 2026-07-13 11:13:44 UTC — *after* that failure, and the job hasn't run again since.
   This is exactly the "next Sun 03:00 UTC `track_signal_outcomes` cron" residual watch-item
   `roadmap-state.md` already tracks as a pending *validation*, not an unfixed bug. Nothing to
   diagnose here yet — the row will only mean something once it runs again post-fix.
2. **`retrain_model_a` — still 0/2, last attempt 2026-06-06 (now 5+ weeks stale).** Mitigated
   by the rule #11 quarantine (Model A is dormant by standing policy since 2026-07-11, not by
   broken-job accident) — this is a stale job, not a live-ops emergency.

## 🟢 Recovered since 2026-07-11 (reconciling the last scorecard's three FAILs)

- **`check_cron_health`** — was 0/7 FAIL ("the deadman is blind"); **now last-run SUCCESS**
  (2026-07-13), though the all-time track record is still thin (1/10) — the monitor just came
  back online, watch it for a few more days before calling it stable.
- **`check_model_staleness`** — was 0/7 FAIL; **now last-run SUCCESS** (2026-07-13, 2/10
  all-time) — same "just recovered, thin track record" caveat.
- **`sync_financial_statements`** — was stuck in a `running` state since 07-04 (an
  `oomKilled` orphan); **fixed by PR #32**'s `executemany` batching — last run SUCCESS
  (2026-07-13, 1/4 all-time).
- **`signal_outcomes` (24,454 rows, unchanged from 07-11)** — the 2026-07-10 decay analysis
  question this raised is **answered, not still open**: the P0 Model A decay check ran
  against these 19,032 matured rows and concluded **RESOLVED, against Model A** (`corr(ml_prob,
  21d) = −0.03`; see `docs/model-a-decay-analysis-2026-07-11.md`). ML is shelved (rule #11);
  this table's presence no longer represents an unblock question to chase.

---

## 🟡 Still worth watching

- **`ingest_regulatory` / `regulatory_events`** — the job itself succeeds (last SUCCESS
  2026-07-13, 12/46 all-time) but the table it feeds is still near-empty: **2 rows, latest
  2026-07-08** (6 days stale) — unchanged from the 07-11 scorecard. The RSS ingest is flaky
  enough that job-level success doesn't mean fresh regulatory content is landing.
- **`revisit overdue`** (Investment readiness): 1 of 2 active/watching theses (CBA) is past
  its revisit-due date — same CBA thesis flagged in `james-inbox.md` as fix-or-retire.
- **`conviction_level NULL`** (Investment readiness, R11): both of the 2 live active/watching
  theses have no `conviction_level` set — the size-vs-conviction coherence check, and the new
  PR2 discipline digest's conviction-unset summary line, can't run until this is set.

---

## Data freshness (as of 2026-07-14)

| metric | value | grade | note |
|---|---|---|---|
| `prices` | 2026-07-13 (697,034 rows) | 🟢 PASS | 1d old |
| `signals` | 2026-07-13 (37,301 rows) | 🟢 PASS | 1d old |
| `market_context` | 2026-07-13 (8 rows) | 🟢 PASS | 1d old — RC3 (RBA/iron/VIX null) already resolved 2026-07-12; row count up from 6 |
| `portfolio_daily_snapshots` | 2026-07-13 (31 rows) | 🟢 PASS | 1d old |
| `fundamentals` | 2026-07-14 (94,963 rows) | 🟢 PASS | 0d old |
| `signal_outcomes` | 24,454 rows | 🟢 PASS | populated — decay check already run (P0 resolved 2026-07-11) |
| `regulatory_events` | 2 rows, latest 2026-07-08 | 🟡 WARN | RSS ingest flaky; card near-empty (unchanged since 07-11) |

## Cron reality (job_runs, all-time, as of 2026-07-14)

| grade | jobs |
|---|---|
| 🔴 FAIL | `track_signal_outcomes` (0/1, last failure 07-12 — predates the 07-13 cast fix `db5a3ff`, hasn't re-run since; not a new break); `retrain_model_a` (0/2, last failure 06-06, dormant/expected) |
| 🟢 PASS (last run succeeded) | `build_portfolio` (6/8), `check_au_positions` (7/7), `check_cron_health` (1/10, just recovered), `check_model_staleness` (2/10, just recovered), `check_thesis_invalidations` (11/11), `check_us_positions` (8/8), `compose_brief` (26/26), `compute_factor_scores` (2/2), `compute_opportunity_cost` (2/2), `derive_fundamentals_pit` (3/3), `detect_theme_stages` (7/7), `generate_signals` (22/32), `ingest_market_context` (8/8), `ingest_news` (26/28), `ingest_regulatory` (12/46, flaky but last run ok), `ingest_sentiment` (21/29), `ingest_underlyings` (8/8), `snapshot_portfolio` (31/38), `sync_corporate_actions` (3/3), `sync_financial_statements` (1/4, just recovered), `sync_fundamentals` (51/51), `sync_prices` (38/38), `sync_security_master` (3/3), `sync_universe` (7/7), `validate_price_data` (3/7) |

## Investment readiness

| metric | value | grade |
|---|---|---|
| active theses | 1 (HUBS) | 🟢 PASS |
| watching theses | 1 (CBA — data-broken ladder + revisit overdue) | ⚪ INFO |
| open holdings | 1 (HUBS.NYSE) | ⚪ INFO |
| holdings without active thesis | 0 | 🟢 PASS |
| theses missing stop/target | 0 | 🟢 PASS |
| revisit overdue | 1 (CBA) | 🟡 WARN |
| conviction_level NULL | 2 of 2 | 🟡 WARN (R11) |

## Product surfaces

| surface | state |
|---|---|
| daily brief | 🟢 renders (`compose_brief` 26/26) |
| portfolio discipline digest | 🟡 **new this session** — PR2a (loader, #40) + PR2b (render, #41) landed as draft PRs; not yet merged/live |
| thesis cards w/o Model A | 🟢 yes (R9 shipped — best-effort model gate) |
| portfolio brief | ⚪ dark (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`) |
| news/sentiment brief | 🟢 shipped (`ASXOS_NEWS_BRIEF_ENABLED=1`, per PR #38) |
| ETF/multi-instrument | 🟡 Slice 1 built + `security_kind` live in prod; Slice 2 blocked on James's VGS/VAS holding-lot data |

---

## The ranked next actions this scorecard surfaces

1. **Watch for `track_signal_outcomes`'s next run (Sun 03:00 UTC)** — its only recorded run
   predates the 07-13 fix, so there's nothing to diagnose yet; confirm it goes green post-fix
   rather than re-investigating pre-fix data.
2. **Keep watching `check_cron_health`/`check_model_staleness`** for a few more days before
   trusting the "recovered" verdict — both have only 1-2 successful runs so far.
3. **`retrain_model_a`** stays broken but is correctly dormant under rule #11 — no action
   needed unless/until a new model version is proposed for the promotion gate.
4. **`ingest_regulatory`/`regulatory_events`** — still flaky at the data layer even though the
   job reports success; the RSS-feed-level investigation from 07-11 was never completed.
5. **CBA thesis (revisit overdue, data-broken ladder)** — `james-inbox.md`'s existing
   fix-or-retire item; James-owned, not independently actionable.
