# Research-store build — session handoff (canonical state)

**Updated:** 2026-06-25 · **Supabase project:** asx-portfolio-os (`gxjqezqndltaelmyctnl`)
· **Branch:** `claude/kind-mendel-cvpxh7`

> **Provenance note.** The handoff doc referenced at the start of the 2026-06-25
> session (`docs/research/session-handoff.md`) was **never actually committed** — it
> existed in no commit, stash, or branch. This file re-creates it from the committed
> research docs **plus the live DB** (the real ground truth). Keep it committed.

---

## 1. Ground-truth DB state (queried live 2026-06-25)

The "5-name slice" is a **hand-trimmed fixture, not a real ingestion run**:

| Table | Rows | Reality |
|---|---|---|
| `rs_security_master` | **5** | full `sync_security_master` (ingests ~2,382 active + ~1,986 delisted, no scoping) has **NEVER run**; the 5 rows were hand-seeded. `gics_sector` is **NULL** for all. |
| `rs_corporate_actions` | 13 | 5 names, dividends only |
| `rs_financial_statements` | 8 | only **FY2025**, 2 statement-types/name; WTC has **0** statement rows |
| `rs_fundamentals_pit` | 5 | one row/name (incl. a WTC row with no backing statement — slice artifact) |
| `rs_factor_scores` | **0** | table exists (migration 0027); now populated by `compute_factor_scores` |
| `rs_index_membership`, `rs_estimates` | 0 | not built (index history is the open survivorship gap) |
| `job_runs` (research jobs) | **0** | the JobMonitor + cron path is **completely unexercised** — Sunday/manual is its first real run |

Supporting facts: `prices` = 1,885 symbols, **~18 months** (2025-01-02 → 2026-06-24,
~373 td/symbol). Production `universe.sector` is fully populated (EODHD `General.Sector`
— same source we now use for the research store). `fundamentals` (production) is 1 month
deep — why the research store exists.

**Binding constraint:** with ~18mo of prices, factor-IC at 252d has ~1–2 independent
windows, 63d ~5–6 → the value×quality test is **indicative, not decision-grade** (same
power ceiling the 5d ML signal hit). The candidate stays a candidate; the ML signal
stays quarantined/paper-only.

## 2. Decisions taken this session (with the user)

1. **Populate timing:** the user triggers the Render chain **now** (the sandbox cannot
   run it — no EODHD key, empty DATABASE_URL, no Render MCP).
2. **Sector source:** enrich `rs_security_master.gics_sector` from EODHD `General.Sector`,
   folded into `sync_financial_statements`' existing `/fundamentals` call (zero extra
   API cost). Morningstar-style sector (not true GICS) — labeled as such.
3. **Universe scope:** **active-only** (~2,382) for the `/fundamentals` fan-out — the
   security master still holds delisted names; survivorship backtesting is a labeled
   out-of-v1 gap.

## 3. Built this session (commit `888bbd3` on the branch)

- `asxos/domain/research/factor_scores.py` — leak-safe sector-neutral z-scores
  (knowledge_date≤as_of, dt≤as_of). Categories value/quality/momentum/low-vol/yield;
  composite = value×quality. Idempotent UPSERT on (symbol, as_of, factor_set_version).
- `jobs/compute_factor_scores.py` — weekly DB-to-DB job; hard-fail on 0 rows.
- `asxos/domain/research/alpha_loader.py` `load_factor_panel` + `jobs/eval_alpha_factors.py`
  — factor panel → `alpha_eval` at 21/63/126/252d (the value×quality TEST vehicle).
- `asxos/ingestion/financial_statements.py` — gics_sector/industry enrichment pass.
- `render.yaml` — `--active-only` on corp-actions + financial-statements; new
  `asxos-compute-factor-scores` cron (Sun 03:30 AEST).
- `tests/test_factor_scores.py` — pure-math + leak-safe orchestrator (stdlib-only).

Validated via stdlib smoke test (sandbox lacks pytest/asyncpg/ruff/mypy — full
`make check` runs in CI). No new migration (rs_factor_scores already in 0027).

## 4. Run plan (to populate + test) — REQUIRES the branch deployed to `main`

Render crons deploy from `branch: main`. `sync_security_master` is correct on **current**
main; the rest need commit `888bbd3` on main first (--active-only + sector enrichment +
factor job).

| # | Trigger | Needs deploy? | Verify |
|---|---|---|---|
| 0 | `asxos-sync-security-master` | no (current main) | `rs_security_master` ≈ 4,368 rows |
| — | **deploy `888bbd3` → main** | — | Render redeploys the cron services |
| 1 | `asxos-sync-corporate-actions` (--active-only) | yes | `rs_corporate_actions` populated for active names |
| 2 | `asxos-sync-financial-statements` (--active-only) | yes | statements full-depth; `gics_sector` back-filled (`sectors_enriched`>0) |
| 3 | `asxos-derive-fundamentals-pit` | yes | `rs_fundamentals_pit` multi-year per name |
| 4 | `asxos-compute-factor-scores` | yes | `rs_factor_scores` populated (sector-neutral) |
| 5 | `python jobs/eval_alpha_factors.py` (manual, read-only) | yes | prints IC/decile report (expect underpower warnings) |

## 5. Open items / risks

- **HEALTHCHECK_URL_* still empty** → no deadman alert. `job_runs` records success/failure
  regardless; verify there Monday. (Setting the URLs is a Render env action — needs the user.)
- **Index-membership history** (ASX200/300) still unavailable → v1 is a labeled cap-rank
  / broad-tradable **proxy**, never "historical ASX 200". The one remaining hard gap.
- **First full-scale ingestion is unvalidated** — the slice never exercised a real
  decades-deep `/fundamentals` payload. Watch the first `sync_financial_statements` for
  data-shape surprises (NUMERIC overflow already forced migration 0028).
- **`ingest_regulatory` failed two mornings** (ATO + Treasury below 50% threshold) —
  NOTED, not investigated (the user will ask if they want it chased).
