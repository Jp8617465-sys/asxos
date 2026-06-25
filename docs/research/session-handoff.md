# Session handoff — research-store pipeline

_Last updated: 2026-06-25 (AEST). Read this first to resume; it is the canonical
"where we are / what's next" for the research-data-store build._

---

## TL;DR

The full **research-store ingestion + PIT-derivation pipeline is shipped and merged**
(PR #6 → `main`, merge `b99529a`). All four weekly Render crons are **provisioned and
waiting for their first run**. The `rs_*` tables currently hold only a **5-name
validation slice** — full survivorship-free population happens at the first Saturday
cron run (or a manual trigger). Next build step is `rs_factor_scores`.

---

## What is shipped (merged to `main`)

| Component | File(s) | State |
|---|---|---|
| Security master ingestion | `asxos/ingestion/security_master.py`, `jobs/sync_security_master.py` | merged, dry-run verified |
| Corporate actions (divs/splits) | `asxos/ingestion/corporate_actions.py`, `jobs/sync_corporate_actions.py` | merged, dry-run verified |
| Financial statements + PIT leak guard | `asxos/ingestion/financial_statements.py`, `jobs/sync_financial_statements.py` | merged |
| `rs_fundamentals_pit` derivation | `compute_pit_factors(...)`, `jobs/derive_fundamentals_pit.py` | merged, validated on real data |
| Schema widen (migration **0028**) | `migrations/0028_*.sql` | applied — `NUMERIC(18,6)→(24,6)` on $ columns (CBA total-assets overflow caught during validation) |
| EODHD client additions | `exchange_symbols_delisted`, dividends, splits | merged |

**Validation evidence:** chain proven end-to-end on CBA/BHP/WTC/CSL/GMG — sane factor
profiles, **43–58-day disclosure lags, zero future-date leakage**. The PIT anchor guard
(`docs/research/evidence-log.md` "gating finding") is the load-bearing correctness
property — do not weaken it.

---

## Live infrastructure

- **Git:** branch `claude/sweet-mccarthy-awiiip`, fully merged into `origin/main`. Working tree clean.
- **Supabase:** project `asx-portfolio-os` = `gxjqezqndltaelmyctnl` (ap-southeast-2, ACTIVE_HEALTHY).
- **Render:** owner `tea-d5i85bili9vc73as37eg`, repo `Jp8617465-sys/asxos`, branch `main`, region `oregon`. 45 services total.

### The four new crons (provisioned via Render API, 2026-06-25)

| Service | ID | Schedule (UTC) | First run (AEST) | Needs EODHD |
|---|---|---|---|---|
| `asxos-sync-security-master` | `crn-d8u6msflk1mc73fe1bgg` | `10 16 * * 6` | Sun 2026-06-28 ~02:10 | yes |
| `asxos-sync-corporate-actions` | `crn-d8u6n78k1i2s73eis830` | `30 16 * * 6` | Sun 2026-06-28 ~02:30 | yes |
| `asxos-sync-financial-statements` | `crn-d8u6n7ugvqtc739fbi30` | `50 16 * * 6` | Sun 2026-06-28 ~02:50 | yes |
| `asxos-derive-fundamentals-pit` | `crn-d8u6n8flk1mc73fe1pj0` | `10 17 * * 6` | Sun 2026-06-28 ~03:10 | no (DB only) |

- All `not_suspended`, `lastSuccessfulRunAt=None` (never run yet).
- Env vars are **literal values** (`DATABASE_URL`, `EODHD_API_KEY`, `PYTHON_VERSION=3.12.13`) — mirroring the existing 12 crons, which also store them literally (there is no Render blueprint). So `render.yaml` and the live services match → `make check-drift` is clean.
- **`HEALTHCHECK_URL_*` is empty on all four** — jobs run fine, but there is **no Healthchecks.io deadman ping** until a UUID is pasted into each (kept out of git via `sync:false`).

---

## Cron report — morning of 2026-06-25 AEST (as_of 2026-06-24)

The **daily** pipeline ran. The four new research crons did **not** run (they are weekly;
first run is Sunday 06-28). From `job_runs`:

| Job | Time (AEST) | Status | Rows | Note |
|---|---|---|---|---|
| `sync_fundamentals` | 04:00 | ✅ | 1870 | |
| `sync_prices` | 06:30 | ✅ | 1864 | |
| `snapshot_portfolio` | 06:40 | ✅ | 1 | as_of 06-23 |
| `generate_signals` | 06:50 | ✅ | 1707 | 265s |
| `ingest_regulatory` | 06:55 | ❌ **FAILURE** | 0 | `only 1/3 succeeded (33.3% < 50% threshold) — first failing: ['ATO','Treasury']` |
| `ingest_news` | 06:57 | ✅ | 0 | |
| `compose_brief` | 07:00 | ✅ | 10 | brief still composed |
| `ingest_sentiment` | 07:02 | ✅ | 0 | |

**`ingest_regulatory` is a RECURRING failure** (identical on 06-24): the ATO and Treasury
sources are failing, leaving only 1/3 below the 50% threshold. Pre-existing, **not** related
to the research-store work. Needs its own investigation — likely the ATO/Treasury source
endpoints changed. The brief degrades gracefully (its regulatory section is omitted).

---

## Data state — IMPORTANT

`rs_fundamentals_pit` and the other `rs_*` tables hold **only the 5-name validation slice**
(CBA/BHP/WTC/CSL/GMG), not the full universe. Full survivorship-free population happens at
**first Saturday cron** (Sun 06-28 AEST) **or** via a one-off manual trigger of the chain in
dependency order: `security-master → corporate-actions → financial-statements → derive`.

---

## Open decisions for the next session

1. **Populate now or wait for Sunday?** Trigger an immediate manual run of the 4-cron chain
   to populate `rs_*` from the 5-name slice to full universe, or let the first scheduled run
   (Sun 06-28 ~02:10–03:10 AEST) do it.
2. **Build `rs_factor_scores` next** — sector-neutral z-scores over the PIT inputs (the actual
   Layer-1 alpha signal), then wire `alpha_eval` to **test** the value×quality candidate on
   real ASX data. Until that evidence exists, the candidate stays a *candidate* and the 5-day
   ML signal stays **quarantined / paper-only**.
3. **Healthcheck URLs** — paste a Healthchecks.io UUID into each new cron's `HEALTHCHECK_URL_*`
   if deadman monitoring is wanted.
4. **`ingest_regulatory` ATO/Treasury failure** — investigate separately (source endpoints).
5. **Index-history still open** (evidence-log promotion checklist) — obtain a true historical
   ASX-membership source, or **label** the v1 universe a cap-rank/broad-tradable **proxy**,
   never "historical ASX 200".

---

## Invariants to keep in mind (see CLAUDE.md + `.claude/rules/`)

- Hard-fail startup / no graceful warnings in infra code.
- `NUMERIC` for all $ — and note 0028 widened the deep-history columns to `(24,6)`.
- Calendar arithmetic for the CGT 12-month rule (`relativedelta(years=1)+timedelta(days=1)`).
- Tax math cites `docs/foundation/spec/tax-alpha.md` section numbers.
- All Render/Supabase changes go through `render.yaml` + git + `make check-drift` / MCP —
  the one documented exception this session was creating the 4 crons via the Render API
  (user-authorized), which is consistent with how the existing crons are stored.
- Never print `EODHD_API_KEY` / `DATABASE_URL` values.
