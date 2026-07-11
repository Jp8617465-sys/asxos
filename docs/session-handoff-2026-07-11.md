# Session handoff — 2026-07-11

**Status:** current · **Read priority:** read first (newest handoff)
**Supersedes:** `session-handoff-2026-07-04.md` on the Model A P0 (now RESOLVED) and on live state.
**Owner:** arbi writes this at `/arbi-close`; James audits.

---

## STOP — read this first (the old P0 is RESOLVED; the frame has changed)

The 2026-07-04 handoff's P0 — *"Model A's signal reliability is in dispute"* — is **RESOLVED
(2026-07-11), against Model A.** The decay check ran on **19,032 matured `signal_outcomes`**:
`corr(ml_prob, 21d) = −0.03`; STRONG_BUY returned −0.09% at 21d vs HOLD's +5.07% (conviction
inverted at the top) → **no usable edge** over the horizon theses hold for.
(`docs/model-a-decay-analysis-2026-07-11.md`.)

**James's call is made: SHELVE the ML engine** (`docs/product/ml-engine-shelf-2026-07-11.md`).
Model A is demoted to a dormant passive monitor. **Rule #11 is now STANDING policy** — not a
temporary block. Do NOT re-run the decay check or re-open the P0; that is settled. The product
IS the **model-independent moat**: thesis discipline, tax intelligence, theme stewardship, and
multi-instrument (ETF/LIC) support. Rule #11 lifts only when a *new* model version passes a
pre-registered decay bar AND earns `approved_for_allocation` — never on the basis of v1_5.

The s766B personal-advice firewall is unchanged: arbi steers *what gets built*, never *what to
trade*; James executes every trade in his own broker.

---

## What shipped this session

**Merged to `main` (PR #25, `eff3732`, CI green):**
- The **ML-shelf** decision doc + a full reconciliation of the arbi doc set from
  "dispute open / run the decay check next" → "resolved / shelved / rule #11 standing"
  (roadmap-state header+body, north-star, arbi agent/harness/permission/autonomy, evals +
  fixture, docs/README, portfolio-policy, next-session-backlog banner, cleanup-backlog, CLAUDE.md).
  Dated 2026-07-04 docs and the append-only `decision-log.md` rows left frozen as history.
- **ETF Phase-2 Slice 2a** — `asxos/ingestion/universe.py` ingests ETFs/LICs/hybrids tagged by
  `security_kind`, so funds are held/valued/taxed **without** entering Model A's universe (the
  kind-scoped ML readers on `main` filter `security_kind = 'au_equity'`). Now **test-covered**
  (5 new `refresh_universe` tests pin the writer-level pollution firewall; `test_ingestion.py`
  39→44).
- **arbi operating docs:** `james-inbox.md` (decisions reserved to James), `dark-launch-exit-plan.md`
  (ship/delete/keep-dark verdicts + expiries), `.claude/agents/arbi-red-team.md` (adversarial
  gate, wired into `/arbi`); subagent count 20→21.

**Merge-readiness audit** before the merge: `arbi-red-team` (five failure modes all PASS;
MERGE-READY-IF) + `technical-writer` (9 findings). All must-fixes + live should-fixes actioned.

**On the branch, UNMERGED (3 commits `97c2cd5` / `aa28db0` / `b5ca66e`):** the reversible-remit
**permission allow-list** in `.claude/settings.json` (governor-applied via `/fewer-permission-prompts`)
+ its draft doc + governance sync into `arbi-permission-model.md` and `decision-log.md`.

**Launched then PAUSED:** the **Product Reality Sweep** (`wf_23a6e2ea-b23`) — 5 read-only domain
auditors (crons/services, data tables, brief/dark-launch, docs, theses) + synthesis, producing
ship/fix/quarantine/delete across every live surface. Stopped mid-run because its read-only SQL
flooded James with per-query prompts (see the permission caveat below). **Resumable from cache.**

---

## Exact next-session pickups (in order)

1. **Relaunch the Product Reality Sweep in a FRESH session** (where the committed allow-list
   loads at startup, so its `supabase-ro` SQL won't prompt):
   `Workflow({scriptPath: "<session-dir>/workflows/scripts/product-reality-sweep-wf_23a6e2ea-b23.js", resumeFromRunId: "wf_23a6e2ea-b23"})`
   — completed agents return cached results. Read the synthesis, then act on the cron issues (2).
2. **Fix the genuine cron issues** the live `job_runs` probe surfaced (these are NOT the shelved
   ML lane — that's dormant on purpose):
   - `check_model_staleness` — fails permanently post-shelve (retrain intentionally suspended);
     make it shelf-aware so it stops alarming on expected staleness (noise to quiet).
   - `sync_financial_statements` — a zombie `running` row from ~07-04 (JobMonitor's 2h stale-heal
     never fired → likely the Render cron is suspended/broken; investigate via Render REST API).
   - `validate_price_data` — FAIL on ~15 anomalies; characterise (real vs false-positive).
   - `track_signal_outcomes` — absent from `job_runs` entirely; it's the shelf's one active
     ML-monitor task (keeps `signal_outcomes` maturing). Confirm the Render cron is wired.
3. **Merge the 3 permission-allow-list commits** on the branch to `main` (or let them carry into
   the next branch). They're reversible docs+config; no migration.
4. **ETF Slice 2** (VGS/VAS as first-class held/valued/taxed positions) — starts once James
   supplies the holding-lot data (`james-inbox.md`). Backend design already drafted this session.
5. **`/arbi-dream`** — rich fuel accrued in `docs/product/memory/working/`: the L8 discipline
   lesson (finish→split→review→merge before chasing the next thread) + a queued
   `approved-lessons.md` resolution lesson (L6 is stale pre-resolution). Promotion is
   CODEOWNER-gated (`/arbi-promote`); arbi cannot self-approve.

---

## Pending — requires James (the governor)

From `docs/product/james-inbox.md` (these gate real progress and arbi cannot self-serve them):
- **HUBS `conviction_level`** — NULL on the thesis (and all theses, risk R11). HUBS is ~100% of
  capital; the size-vs-conviction check can't run without your 1–5 number.
- **CBA thesis #1** — recorded entry/stop/target (42/45/38/60) is ~4× detached from live ~168;
  fix the levels or retire the row (it's `watching`, not held — no capital moves either way).
- **VGS.AU / VAS.AU holding-lot data** — quantity · cost base · acquisition date (+ FX if not
  AUD) — needed before ETF Slice 2 can record real positions.

Plus:
- **Merge the permission-allow-list branch** (item 3 above) if you want it on `main`.
- **Permission hot-reload caveat (why you kept clicking "allow" this session):** this remote
  (web) session read its permissions once at startup, before the allow-list existed, and does
  **not** hot-reload `.claude/settings.json`. The file is correct and committed; it takes effect
  in a **fresh session**. If a brand-new session *still* prompts for `mcp__supabase-ro__execute_sql`,
  then claude.ai/code isn't honoring repo-file permissions (a repo can't grant itself tool
  access) and the setting must be made in the **web UI's own permission control**.

---

## Load-bearing gotchas (don't re-learn these the hard way)

- **`cost_base_normal` is the AUD tax base, not native currency** (risk R10). Dividing it by
  quantity and comparing to a USD `prices.close` is a currency error — it made two agents report
  HUBS as −29% when it was ≈ flat (+9.8% USD). Convert both legs to one currency first.
- **Sandbox can't run the full suite:** the sandbox Python is 3.11 (project requires 3.12) and
  lacks ML deps (joblib/lightgbm) + httpx/pydantic/etc. Tests pass in Render CI. Don't chase the
  16 known collection-errors (`CLAUDE.md` §Known test environment gaps).
- **Render is REST-API only** (`api.render.com/v1`, `$RENDER_API_KEY`) — there is NO Render MCP.
- **Governance transitions:** any `governance_status` change must emit `governance_events`
  INSERT **before** the UPDATE, live-verified against the real trigger (mocked tests don't catch
  the order). See `.claude/rules/portfolio-conventions.md`.

---

## Files to commit to `main` (per `docs/README.md` — handoffs live on `main`)

This handoff + the `roadmap-state.md` refresh are on the branch. Commit them (and, if desired,
the 3 permission-allow-list commits) to `main` so the next session reads current truth.
`/arbi-close` does not push/merge — that's a deliberate `/ship` step.
