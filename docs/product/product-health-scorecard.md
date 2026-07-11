# ASXOS Product Health Scorecard

**Generated:** 2026-07-11 (hand-assembled from live read-only queries this run;
`scripts/product_health.py --write` regenerates it against `docs/product/data-contracts.md`).
**Top line:** 🔴 **3 FAIL · 🟡 ~6 WARN** — the data pipeline is fresh and the brief renders
(the discipline/tax/valuation product *works*), but the **monitoring + model-maintenance layer
is degraded**, and `signal_outcomes` is unexpectedly **populated** (possible P0 unblock).

> Answers *is ASXOS actually working?* — not *did tests pass?*.

---

## 🔴 The three things that are actually broken

1. **`check_cron_health` — 0/7 success, failing every run.** The monitor that's supposed to
   detect cron failures is itself down — so the deadman is blind. Fix this first; it's the
   instrument everything else is watched by.
2. **`check_model_staleness` — 0/7, failing every run.** No model-staleness signal.
3. **`retrain_model_a` — 0/2, last attempt 2026-06-06 (35 days ago).** Model A has not
   retrained in over a month. (Mitigated by rule #11 quarantine — but the job is broken.)

## 🟢 The big positive finding — reconcile this

**`signal_outcomes` has 24,454 rows.** The 2026-07-10 decay analysis recorded it as *empty* and
had to compute forward returns from `prices` by hand. It is now populated. **This likely means
the Model A decay check (the P0) is directly runnable from `signal_outcomes`** instead of
reconstructed — a real potential unblock of `the_one_thing`. Verify what populated it (a
`track_signal_outcomes` run?) and whether the columns support the 5d/21d horizon decay directly.

---

## Data freshness (as of 2026-07-11)

| metric | value | grade |
|---|---|---|
| `prices` | 2026-07-09 · 692,416 rows | 🟢 PASS (2d) |
| `signals` | 2026-07-09 · 33,932 | 🟢 PASS (2d) |
| `fundamentals` | 2026-07-10 · 87,475 | 🟢 PASS (1d) |
| `portfolio_daily_snapshots` | 2026-07-08 · 30 | 🟢 PASS (3d) |
| `market_context` | 2026-07-09 · **6 rows total** | 🟡 WARN — fresh but sparse; `rba_cash_rate`/iron/vix NULL (RC3) |
| `signal_outcomes` | **24,454** | 🟢 PASS — populated (was reported empty 2026-07-10) |
| `regulatory_events` | **2 rows** | 🟡 WARN — RSS ingest flaky (9/43); card near-empty |

## Cron reality (job_runs, all-time)

| grade | jobs |
|---|---|
| 🔴 FAIL (never succeeded) | `check_cron_health` (0/7), `check_model_staleness` (0/7), `retrain_model_a` (0/2, last 06-06) |
| 🟡 WARN | `validate_price_data` (1/5, last fail), `sync_financial_statements` (**stuck `running`** since 07-04), `ingest_regulatory` (9/43), `generate_signals` (20/30), `ingest_sentiment` (19/27) |
| 🟢 PASS | `compose_brief` (24/24), `sync_prices` (36/36), `sync_fundamentals` (47/47), `snapshot_portfolio` (30/36), `check_au_positions` (5/5), `check_us_positions` (6/6), `check_thesis_invalidations` (8/8), `ingest_market_context` (6/6), `sync_universe` (6/6), `ingest_news` (24/26), `detect_theme_stages`, `ingest_underlyings`, + 6 one-offs |

## Product surfaces

| surface | state |
|---|---|
| daily brief | 🟢 renders (`compose_brief` 24/24) |
| thesis cards w/o Model A | 🟢 yes (R9 shipped — best-effort model gate) |
| portfolio brief | ⚪ dark (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`) |
| news/sentiment brief | ⚪ dark (`ASXOS_NEWS_BRIEF_ENABLED=0`) |
| ETF/multi-instrument | 🟡 Slice 1 built + `security_kind` live in prod; readers deploy on PR #24 merge; not yet holdable (Slice 2) |

## Investment readiness

| metric | value | grade |
|---|---|---|
| active theses | 1 (HUBS) | 🟡 thin |
| watching theses | 1 (CBA — **DATA-BROKEN** ladder + revisit 14d overdue) | 🔴 |
| open holdings | 1 (HUBS.NYSE) | ⚪ |
| holdings without active thesis | 0 | 🟢 |
| theses missing stop/target | 0 | 🟢 |
| revisit overdue | 1 (CBA) | 🟡 |
| conviction_level NULL | 2 of 2 live | 🟡 (R11) |

## Autonomy health

| metric | value |
|---|---|
| guard tests | 🟢 59/59 (`unattended-guard.sh`) |
| open P0/P1 risks | R1 (Model A P0), R2 (agent DB role), R5 (prompt-only enforce), R8, R10 (cost-base ccy), R11 (conviction NULL) |
| memory | second brain live (`memory/`); working notes for this session's runs; `/arbi-dream` cadence pending |

---

## The ranked next actions this scorecard surfaces

1. **Verify `signal_outcomes` (24k) → run the Model A decay check directly** — this may unblock the P0.
2. **Fix `check_cron_health`** — the blind watcher; everything else's early-warning depends on it.
3. **Fix `check_model_staleness` + `retrain_model_a`** (broken every run) and the stuck `sync_financial_statements`.
4. **Reduce `ingest_regulatory`/`validate_price_data`/`generate_signals` failure rates.**
5. **Fix CBA data-broken thesis** (RC2) + the market_context feed NULLs (RC3, RBA/iron/vix).
