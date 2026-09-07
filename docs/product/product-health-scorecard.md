# ASXOS Product Health Scorecard

**Generated:** 2026-09-06 12:21 UTC (hand-assembled from live read-only queries this wake, via
the read-only Supabase MCP role (`supabase-ro`) — the queries mirror `_freshness` /
`_cron_reality` / `_investment_readiness`, `scripts/product_health.py:53-138`, exactly; the
Actions-substrate rows come from `gh run list`. Every figure below is **measured** unless marked
*inferred*. Previous edition: 2026-07-14 — seven weeks stale, backlog E-16.)
**Top line:** 🔴 **1 FAIL · 🟡 3 WARN · plus 1 live red outside `job_runs`** — the data pipeline
is fresh and complete; the one FAIL (`retrain_model_a`) is dormant by policy (rule #11); the
monitoring lane is **red on complete data** because of a false positive introduced on 09-02
(fix drafted this wake); the two investment-readiness WARNs are the same two thesis rows James
has a retire ruling waiting on; and the daily `issue-snapshot` workflow has failed since this
morning because the `main` ruleset now rejects its push.

> Answers *is ASXOS actually working?* — not *did tests pass?*.

---

## 🔴 What's actually broken today

1. **`check_cron_health` — FAILED 09-03, 09-04, 09-05 on a false positive.** Each failure is
   `DEGRADED: sync_prices as_of=… NO_EQUITY_DATA — ASX=0`, yet `prices` holds **2,299** AU rows
   for 2026-09-02 and **2,288** for 2026-09-03, and the two flagged runs wrote 2,383 / 2,373
   rows. *Inferred from code:* PR #171 (merged 09-02) made `clock.today()` the Sydney date, so
   the 06:30 AEST run's self-heal window now ends on a day that has not closed;
   `jobs/sync_prices.py:353` classified that empty day. The 09-06 run passed only because the
   weekend rule (#187) expects no `sync_prices` row. At the Actions level the `pipeline-health`
   scheduled runs were **red 09-02T23:54Z, 09-03T23:51Z, 09-04T23:48Z** (a latest-run-only view
   shows only the Sunday green — that is how this went unrecorded). **Fix drafted: #212**
   (backlog **A-25**) — the verdict now targets
   the freshest *closed* session. Until it merges the deadman lane is red every weekday for
   nothing, which is the failure mode that trains the reader to ignore it.
2. **`issue-snapshot` — scheduled run 34030294978 (09-06 11:27 UTC) FAILED**, and will fail daily
   at 07:00 UTC: the workflow pushes `docs/ops/github-issues-snapshot.json` straight to `main`
   and the ruleset (#205: PR-required, `full-check` required, no bypass actors) rejects it
   (`GH013`). Green 09-01→09-05. `.github/**` is James-only — patch, options and verify steps in
   `docs/proposals/claude-config-patches-2026-09-06/issue-snapshot.md`; backlog **A-24**.
3. **`retrain_model_a` — 0/2, last attempt 2026-06-06.** Dormant by standing policy (rule #11,
   resolved against Model A 2026-07-11); the training chain was deleted in #144. Not a live-ops
   item — listed because the row still exists.

## 🟢 Recovered / observed since the 2026-07-14 edition

- **`backup.yml` — GREEN 2026-09-05 16:09 UTC** (run 33976969363), the first green since 08-22,
  after #186's dump-before-verify fix merged 09-05. **Now observed, too:** two more scheduled greens on 09-06 — run 34045223384 (16:22 UTC, dump only,
  drill skipped) and run 34048829799 (17:30 UTC, **`restore_drill` job success** — the first drill
  since #186). `HEALTHCHECK_URL_BACKUP_IRREPLACEABLE` is still absent from the nine repo secrets, so
  the deadman cannot page — backlog **B-3 / C-1** (C-1 now needs only the secret + pasted run ids).
- **`track_signal_outcomes`** — the 07-14 FAIL cleared (3/4, last success 2026-08-02); the writer
  chain is now retired with Model A, so the row is historical.
- **`derive_fundamentals_pit`** — ran 2026-09-06 and populated `rs_fundamentals_pit.knowledge_tier`
  on **54,459 of 54,466** rows; the 09-03 close recorded it as NULL. Backlog **C-2** observed.
- **`weekly-research` chain** — scheduled green on three consecutive Saturdays (08-22, 08-29 run
  33270549838, 09-05 run 33982730538). Backlog **C-11** observed.
- **`sync_financial_statements`** 9/13, **`sync_fundamentals`** 77/77, **`sync_universe`**
  16/16 — all success on the 09-06 weekly fire.
- **`regulatory_events` / `ingest_regulatory`** — 56/90 all-time, 9/9 success in the last 14 days
  (the 07-14 edition flagged it flaky; the last fortnight is clean).

---

## 🟡 Still worth watching

- **`revisit overdue` = 2 and `conviction_level NULL` = 2** — both active/watching theses. One of
  them is CBA thesis #1, 3.5× price-detached, revisit 67+ days overdue (backlog **D-3**, one-word
  ruling); the other is the single active thesis. R11 (backlog **E-12**) is the standing cause.
- **Daily brief tonight is the first scheduled send after #178** bumped `resend` 2.4.0 → 2.39.0 on
  the live send path (every test mocks it) — cron `30 20 * * 0-4`, next fire 2026-09-06 20:30
  UTC. Backlog **D-14**.
- **The three standing lanes** (`backlog-roll`, `nightly-triage`, `weekly-toolwatch`) are on
  `main`, `workflow_dispatch`-only with an `acknowledge_write_token_risk` gate, **0 runs each** —
  correct while gate 7 (backlog **A-22**) is open; `backlog-roll` also fails at step 0 without
  `HC_BACKLOG_URL` (**A-20**).
- **Dark surfaces #1 and #4 expired 2026-08-31** and are still unruled (**D-1 / D-2**; drafts in
  #190); #3 expires 2026-09-30 (**D-15**).

---

## Data freshness (as of 2026-09-06 12:21 UTC)

| metric | value | grade | note |
|---|---|---|---|
| `prices` | 2026-09-03 (783,234 rows) | 🟢 PASS | 3d old (warn at 4d). Friday 09-04's close lands with the Monday 06:30 AEST run by design (cron Sun–Thu 20:30 UTC). 09-01/02/03 carry 2,319 / 2,299 / 2,288 AU rows |
| `market_context` | 2026-09-04 (47 rows) | 🟢 PASS | 2d old |
| `portfolio_daily_snapshots` | 2026-09-03 (66 rows) | 🟢 PASS | 3d old |
| `fundamentals` | 2026-09-06 (143,715 rows) | 🟢 PASS | 0d old — weekly fire 09-06 |
| `signal_outcomes` | 60,072 rows | 🟢 PASS | frozen decay evidence intact (was 24,454 on 07-14; the tracker ran until 08-02) |
| `signals` | frozen: 64,189 rows, `as_of` 2026-08-05 | ⚪ excluded | no writer since #144; never evidence for capital (rule #11) |
| `rs_fundamentals_pit.knowledge_tier` | 54,459 / 54,466 populated | 🟢 PASS | 0049 backfill observed 09-06 |
| `universe` | 2,459 total / 2,396 active | ⚪ INFO | +18 / +12 since the 08-20 snapshot |

## Cron reality (`job_runs`, all-time · last 14 days, as of 2026-09-06)

| grade | jobs |
|---|---|
| 🔴 FAIL | `retrain_model_a` (0/2, last 06-06 — dormant, rule #11) |
| 🟡 WARN | `check_cron_health` (25/61 all-time; **5 of 12 failed in 14d**: 08-28 mid-session `ASX=0`, 08-31 weekend MISSING false positive fixed by #187, **09-03/04/05 the Sydney-date false positive above**; last run 09-06 success) |
| 🟢 PASS (last run succeeded; clean 14d) | `check_au_positions` 43/43 · `check_thesis_invalidations` 53/53 · `check_us_positions` 44/44 · `compose_brief` 63/63 · `derive_fundamentals_pit` 8/12 · `ingest_market_context` 46/46 · `ingest_news` 63/65 · `ingest_regulatory` 56/90 · `ingest_sentiment` 58/66 · `ingest_underlyings` 46/46 · `materialise_brief_sections` 8/8 · `score_macro_theses` 19/19 · `snapshot_portfolio` 66/73 · `sync_corporate_actions` 12/12 · `sync_financial_statements` 9/13 · `sync_fundamentals` 77/77 · `sync_prices` 76/76 (two runs carry the false degraded note) · `sync_security_master` 12/12 · `sync_universe` 16/16 · `validate_price_data` 41/45 |
| ⚪ retired / unscheduled (last row is historical, expected) | `build_portfolio` (last `blocked` 08-01 — DROPPED, Amendment F) · `detect_theme_stages` (last 08-05 — KEEP ruled, unscheduled, **D-11**) · `generate_signals` (last 08-05 — deleted with Model A, #144) · `track_signal_outcomes` (last 08-02) · `check_model_staleness` (last 08-05) · `compute_factor_scores` (08-11) · `compute_opportunity_cost` (08-01) |

## Investment readiness

| metric | value | grade |
|---|---|---|
| active theses | 1 | 🟢 PASS |
| watching theses | 1 (CBA #1 — **D-3** retire ruling pending) | ⚪ INFO |
| open holdings | 1 | ⚪ INFO |
| holdings without active thesis | 0 | 🟢 PASS |
| theses missing stop/target | 0 | 🟢 PASS |
| revisit overdue | 2 | 🟡 WARN |
| conviction_level NULL | 2 of 2 | 🟡 WARN (R11, **E-12**) |
| governed themes / members | 1 (`big-4-banks`) / 1 (CBA.AU — the Stage 4 *negative* control; a positive control needs a second member, **C-5**) | ⚪ INFO |
| approved macro theses | 3 | ⚪ INFO |
| decision packets / outcomes / receipts / dispositions | 1 (`dpk-cba-1-2026-09-01`, abstain) / 0 / 0 / 0 | ⚪ INFO — every Stage 4/5 `renders:` is honestly empty until James's live CLI runs (**C-3 … C-8**) |

## Product surfaces

| surface | state |
|---|---|
| daily brief | 🟢 renders (`compose_brief` 63/63, last 09-04); next scheduled send tonight is the first after the `resend` bump (**D-14**) |
| news/sentiment brief | 🟢 SHIP (verdict 2026-08-21) |
| portfolio brief | 🔴 dark, **EXPIRED 2026-08-31**, unruled (**D-1**) |
| paper-trade evaluator | 🔴 dark, **EXPIRED 2026-08-31**, unruled (**D-2**) |
| V2 brief tree | ⚪ KEEP-DARK to 2026-09-30 (**D-15**) |
| decision engine, Stages 1→5 machinery (`asx replay / research / candidates / decision`) | 🟡 on `main` since 09-05 (#192–#198, #201); personal-use gated; live halves are James's; no Stage cell flipped |
| irreplaceable backup | 🟡 green 09-05; dump + **restore drill green 09-06** (run 34048829799) · deadman secret absent (**B-3 / C-1**) |
| GitHub issues snapshot (D10 mitigation) | 🔴 red since 09-06 (**A-24**) |
| standing agentic lanes | ⚪ armed, never fired; automatic triggers barred until **A-22** |

---

## The ranked next actions this scorecard surfaces

1. **Land the `sync_prices` completeness-target fix** (AW-01 PR, drafted 09-06) — the health lane
   is red on complete data every weekday until it merges.
2. **A-24 — apply the `issue-snapshot.yml` patch** (James; `.github/**`) — one red scheduled run
   per day until then.
3. **B-3 + C-1 — deadman secret, then dispatch `backup.yml` and `restore_drill=true`** (James) —
   turns "green" into "observed".
4. **D-3 — retire CBA thesis #1** (one word) — clears half of both WARNs; **E-12** (R11) clears
   the rest.
5. **D-14 — read tonight's `daily-brief` run** after it fires at 20:30 UTC.
