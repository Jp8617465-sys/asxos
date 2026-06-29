# Shared Supabase project audit + migration-process hardening (2026-06-28)

Triggered by migration 0029: the live pre-apply catalog check found a dependent view
(`stock_universe`) that no file-based review could have seen, because **asxos's schema
is a 43-table tenant inside a ~165-table Supabase project** (`asx-portfolio-os`,
`gxjqezqndltaelmyctnl`) that also holds another application's schema and dead leftovers
from the previous asxos repo.

This doc (1) inventories what's in the project, (2) recommends process hardening so the
next migration can't be surprised, and (3) proposes a **staged, backup-first wipe** of
the non-asxos schema for James's decision. **No destructive action has been taken** —
the wipe is a proposal pending explicit go.

---

## 1. Inventory (live, read-only)

- **165 tables** in `public`; asxos `migrations/` define **43**. **122 tables are not
  asxos's** (foreign app + previous-repo leftovers).
- **5 views**: `current_holdings`, `market_context_current`, `stock_universe` are
  asxos-tracked (the last now via 0029). `v_pending_retraining_jobs`,
  `v_recent_deployments` are **not** in migrations (dead-ML themed).
- Functions/triggers: mostly the **pgvector** extension (`vector_*`, `halfvec_*`, …) +
  another app's `updated_at` triggers (`update_user_accounts_updated_at`,
  `update_budget_goals_updated_at`, …) and helpers (`sync_portfolio_prices`,
  `get_stock_intelligence`, `auto_expire_notifications`).

### Classification (by data + code-reference, the only criteria that matter)

| Bucket | Count | Data | asxos code refs |
|---|---|---|---|
| **KEEP — current asxos** | 43 migration tables + `signal_outcomes` | the real data (prices 674k, signals 17k, fundamentals 63k, rs_corporate_actions 41k, …) | yes |
| **DEAD — asxos legacy (prev repo)** | ~50 tables | almost all 0 rows; carries ~450 MB of empty bloat | **none** |
| **FOREIGN — another app** | ~70 tables | nearly all 0 rows | **none** |

**`signal_outcomes` (24,454 rows) is the one surprise:** not in `migrations/` but
referenced by 3 current asxos files — live asxos data with no migration home. **Capture
it into a migration** (do NOT wipe).

**The other ~120 non-migration tables are not referenced by any asxos `.py`.** Only four
hold any rows at all: `user_preferences` (22), `semantic_memories` (14),
`state_property_tax_rates` (6), `user_portfolios` (2) — 44 rows total, all in the
FOREIGN bucket.

**Storage bloat (0 rows, but allocated):** `fundamentals_history` 198 MB,
`model_a_features_extended` 128 MB, `model_shap_values` 116 MB, `screen_matches` 15 MB,
`ensemble_signals`/`model_d_signals` ~9 MB each — all DEAD/legacy ML from the previous
repo. Dropping these reclaims the bulk of the wasted space.

### What the FOREIGN app is
Table names describe a **personal-finance / wealth-advisor app**: `user_accounts`,
`user_holdings`, `budget_goals`, `financial_profiles`, `investment_plans`,
`loan_accounts`, `property_assets`, `goal_*`, `advisor_*`, `assistant_*`,
`notifications`, `subscriptions`, `push_subscriptions`. It is **effectively empty**
(44 rows across 4 tables) — a template/seed or abandoned prototype, not a live
populated app. The org has other Supabase projects (`realflow-staging`, `Gym-OS`,
plus a default project) that more plausibly host live apps.

---

## 2. Process hardening (do regardless of the wipe decision)

1. **Standing pre-apply catalog check.** Add to `api-conventions.md` (Migrations §) a
   required step before any `ALTER`/`DROP COLUMN`: run the `pg_depend` dependent-object
   query (views/rules/constraints/indexes on the target column) — the exact query that
   caught `stock_universe`. This is the systemic fix; it's ~15 lines of runbook.
2. **Capture `signal_outcomes`** into a migration (`CREATE TABLE IF NOT EXISTS` matching
   its live shape) so the one live out-of-band asxos table is reproducible.
3. **Classify the 2 unknown views** (`v_pending_retraining_jobs`, `v_recent_deployments`)
   — confirm dead, then drop them in the wipe (below) or document if kept.

---

## 3. Wipe — APPLIED 2026-06-28 (migration 0030)

**DONE.** James chose "backup-then-drop-all non-asxos". Migration `0030` archived the
14 data-bearing tables (10 prev-repo legacy + 4 foreign) into schema
`archive_dropped_20260628` via CTAS, then dropped all **122** non-asxos tables (CASCADE)
+ the 2 dead views (`v_pending_retraining_jobs`, `v_recent_deployments`). Result:
**public 165→43 tables** (42 asxos + `schema_migrations`) + 3 asxos views; asxos data
intact (`prices` 675k); archive holds the 14 tables (e.g. `signal_evidence_chains` 4,107
rows); `schema_migrations` 83→84; `REQUIRED_MIGRATIONS`=84. Verified `asxos_fk_into_drop=0`
pre-drop. The ~12 orphaned foreign trigger/helper functions were left (inert; dropping
`update_model_versions_timestamp`/`update_updated_at_column` could affect kept asxos
triggers — optional follow-up). The `archive_dropped_20260628` schema can be dropped later
to reclaim space once you're confident nothing's needed from it.

The original staged proposal is retained below as the record.

## 3a. Original staged wipe proposal (superseded by §3)

**Safety preconditions (non-negotiable):**
- **Full backup first** — `backup_irreplaceable.sh` does NOT cover these tables; take a
  Supabase point-in-time/branch snapshot or `pg_dump` of the whole project before any
  DROP.
- Do the drops as a **numbered, reversible-by-restore migration** (0030), reviewed via
  the gate, not ad-hoc `execute_sql`.
- Drop in FK-safe order or `DROP TABLE … CASCADE` after confirming no asxos table has an
  FK into a dropped table (none expected — asxos tables are self-contained).

**Stage A — dead asxos-legacy (lowest risk).** Drop the ~50 previous-repo tables (all
0-or-trivial rows, none code-referenced) incl. the 450 MB bloat (`fundamentals_history`,
`model_a_features_extended`, `model_shap_values`, the `model_{a,b,c,d}_*`, `screen_*`,
`ensemble_signals`, `signal_evidence_chains`, `universe_history*`, …) + the 2 dead views.
Reclaims the storage; zero impact on current asxos.

**Stage B — foreign app (needs one confirmation).** Drop the ~70 `user_*` / finance /
advisor / notification tables + their triggers/functions. Confirm first that the 4
populated tables (`user_preferences`, `semantic_memories`, `state_property_tax_rates`,
`user_portfolios`) aren't another of your apps you want to keep. If unsure, skip these
4 and drop the rest.

**Out of scope:** the pgvector extension functions (leave — they're an installed
extension, not user schema) and anything in the KEEP bucket.

---

## 4. The strategic question for James
Is `asx-portfolio-os` meant to be **asxos-only** going forward? If yes, Stages A+B are
straightforward cleanup. If the foreign app might be revived here, keep Stage B. Either
way, asxos's single-user / no-RLS assumption (CLAUDE.md #4) is safer once the project is
single-tenant. Recommended: **harden now (§2); wipe Stage A after a backup; decide Stage
B once the 4 populated tables are identified.**
