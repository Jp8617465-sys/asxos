# asxos build guide

**Status:** current **as a build record**; **NOT current as an executable instruction set** —
see the banner below
**Scope:** executable manual (M1–M12)
**Last verified:** 2026-07-04
**Docs-truth correction:** 2026-08-13 (`SB0-01` sweep)
**Read priority:** read first — **with the banner below**
**Superseded by:** N/A as a whole; its **Model A sections and its architecture pointer are
superseded** (below)

> ### ⛔ DO NOT EXECUTE THE MODEL A SECTIONS — annotated 2026-08-13 (SB0-01 doc-truth sweep)
>
> This guide is ~2,900 lines and contains **zero** mentions of "rule #11", "quarantine", or
> "shelved". It was written before the decisions that govern the system today, and `docs/README.md`
> routes new sessions here as "the executable manual". Followed literally, it would **re-arm the
> exact machinery the project deliberately switched off.** Two corrections:
>
> **1. Model A is shelved and being retired. Its sections here are history, not instructions.**
> On 2026-07-11 the decay analysis found **no usable edge** on 19,032 matured signals
> (`corr(ml_prob, 21d) = −0.03`; STRONG_BUY 21d −0.09% vs HOLD +5.07% — conviction inverted at
> the top), James **shelved the ML engine**, and CLAUDE.md rule **#11** became standing policy.
> A retirement programme (`P1-01`…`P1-05`) is in progress; the classified reference manifest is
> `docs/product/model-a-reference-manifest.md`. Specifically **do not execute**:
>
> | Here | What it would do | Why not |
> |---|---|---|
> | §M6 (`:1400`) | Load Model A, serve predictions + SHAP at API startup | Re-introduces a runtime dependency `P1-02` exists to remove |
> | `:1435` | Seed `model_versions` with `('model_a','v1_5', …, TRUE)` | Re-activates the model row; `approved_for_allocation` was **revoked** 2026-07-11 (R8) and that revocation is rule #11's mechanical enforcement point |
> | `:459`, `:1975` | `make retrain`; "`asx model activate v1_6` flips active" | Omits the two gates a *new* model must clear before it may influence capital: a **pre-registered decay bar** (positive, monotonic conviction→21d return) **and** a separate explicit `approved_for_allocation` grant. Activation alone is not approval |
> | `:180`, `:2197`, `:2205`, `:2258`, `:2334`, `:2864` | Weekly `asxos-retrain-model-a` schedule | Job is RETIRE-dispositioned; and see (2) — the platform is gone |
>
> **2. The deployment architecture described here is superseded, twice over.** `:17` names
> "six systemd-timer-driven jobs, ten Postgres tables" and calls
> `phase-4-architecture-system-architect.md` "authoritative on every technical choice." That
> document describes an **abandoned VPS/systemd/local-Postgres design** and carries its own
> supersede banner (`docs/README.md:85`). The system then ran on **Render cron + Supabase
> Postgres** — and as of **2026-08-12 Render itself was deleted** (governor ruling,
> `docs/product/roadmap-state.md:116`), leaving **GitHub Actions** (`.github/workflows/`) as the
> executing scheduler. Table count is ~40, not ten. For deployment truth read `docs/README.md`
> §"Authoritative source by area" and the newest `session-handoff-*.md`, never this section.
>
> **What this guide is still good for:** the M1–M12 build narrative, the schema/tax/CLI/brief
> sections, and the rationale for why the rebuild is shaped as it is. Those are unaffected.

A working manual for the rebuild from "nothing" to a working personal investment OS. Read in order. Each section is meant to be executable end-to-end with Claude Code, with the design rationale already settled in `phase-4-architecture-system-architect.md` and `phase-5-milestones.md`. Cross-references to those documents are deliberate — this guide does not re-litigate decisions.

---

## Part 1 — Executive overview

The old `asx-portfolio-os` was a multi-tenant SaaS that died of infrastructure drift: `render.yaml` diverged from what Render was actually running, the FastAPI lifespan handler swallowed dependency-init failures as warnings, and the test suite ballooned past 5,000 tests while jobs silently succeeded on broken upstreams. The diagnosis is complete in `phase-1-audit.md`. The new system, `asxos`, is the opposite of that shape.

The new system is a single-user personal investment OS for one person — James. There is no authentication, no frontend, no multi-tenancy, no event bus, no Redis, no Pydantic at the data layer, no Sentry on day one. It is a FastAPI process bound to `127.0.0.1`, six systemd-timer-driven jobs, ten Postgres tables, a CLI built with Typer, and a daily 7am HTML email rendered by Resend. The chosen architecture is `phase-4-architecture-system-architect.md` and that document is authoritative on every technical choice referenced here.

The headline cost change is concrete. Today the system spends roughly USD 35–55 per month on Render (Starter API, Starter cron plans, mixed free crons), USD 0–25 on Vercel hobby/pro, USD 25 on Supabase Pro, plus EODHD, Anthropic, Voyage AI, Resend, and FRED API subscriptions. The new system reuses a single Render Starter web service at USD 7/month, Render free-tier crons, and a downgraded Supabase free-tier project at USD 0/month (with a DIY daily backup of the irreplaceable tables to a private GitHub repo), plus the same EODHD and Resend subscriptions. Net infrastructure spend drops from approximately USD 130/month to USD 27/month — a saving of roughly USD 103/month. James has explicitly opted to lose 7-day point-in-time recovery in exchange for the USD 25/month saving; the DIY backup covers the irreplaceable subset (holding_lots, decisions, screening_rules, model_versions). Supabase free tier's 500MB storage cap will likely force a Pro upgrade in 6–12 months as historical prices accumulate; budget for that re-evaluation around M12+3 months. (See Part 7 for the line-by-line.)

The headline timeline is eight to ten calendar weeks for the twelve milestones from M1 (repo bootstrap) through M12 (production deploy with crons running). The system becomes genuinely useful at M11 — the first morning brief in James's inbox. M12 puts it on infrastructure that doesn't need babysitting.

The new system shape, in one paragraph: a Render Starter web service runs a Python package `asxos` against a Supabase Postgres 16 database. The API binds to `0.0.0.0` inside the Render container but is reachable only by Render's own cron services and James's own browser via a single token. Eight Render cron services fire jobs that read from EODHD, write to Supabase, run LightGBM inference, at 07:00 Sydney each weekday compose and email a brief, and at 23:00 dump the irreplaceable tables to a private GitHub backup repo. Holdings live in a `holding_lots` table; `current_holdings` is a view. SHAP values live inline as JSONB on the `signals` row. Model versions flip via a single boolean column in `model_versions`. Deployment is `git push origin main` — Render auto-deploys from `render.yaml`. A `make check-drift` target uses the Render MCP to diff actual deployed services against `render.yaml` after every deploy, which is the structural fix for the drift bug that killed the old system: drift is now detectable and Claude Code reports it. Observability is Render logs (queried by Claude Code via the Render MCP), the `job_runs` table (queried by Claude Code via the Supabase MCP), and Healthchecks.io pings. The test suite caps at ~400 load-bearing tests.

This guide assumes Claude Code is the primary IDE and the primary operator of every running service. Per-milestone prompts are provided. The `.claude/commands/` and `.claude/rules/` from the old repo carry forward verbatim — they are the accumulated working agreement and they survive the rebuild. Part 8 covers MCP setup and the day-to-day Claude-Code-driven operations playbook in detail; read it before starting M1 because the choice to use Render plus Supabase rather than a self-managed VPS is driven entirely by MCP coverage for non-technical operation.

---

## Part 2 — The cull list (revised: MCP audit)

Every piece of existing infrastructure has a verdict: cancel, replace-in-place, or keep through cutover. The order matters because some things are still needed for backfill until the new system has its own data.

### MCP-driven audit of the original Hetzner plan

The earlier draft of this guide picked a Hetzner CX22 VPS plus Backblaze B2 plus Tailscale plus a vanilla Postgres-in-Docker stack. That stack is technically clean, cheaper on paper, and operationally hostile to a non-technical operator. The constraint James added — "I need MCP or native connector to Claude as I'm not technical" — flips most of those picks. The new verdicts are below; each is justified in one line and the rationale assumes that the operator drives every routine action through Claude Code rather than SSH or a vendor dashboard.

| Service | Original pick | MCP status | New pick | Why |
|---------|----------------|-------------|-----------|-----|
| Hosting | Hetzner CX22 VPS | No MCP James has | **Render Starter** | Render MCP is one of the most mature; full ops (logs, deploys, env vars, crons) driveable from Claude Code. The drift bug is solved structurally by `make check-drift` (see Part 8.4), not by switching off Render. |
| Database | Postgres 16 in Docker on the VPS | No MCP | **Supabase free tier** | James has the Supabase MCP and uses it daily. Free tier is enough for the first 6–12 months of data; upgrade to Pro when storage approaches 500MB. |
| Job scheduling | systemd timers | No MCP (`journalctl` only via SSH) | **Render cron services** | Flows from the hosting flip. Cron status, logs, manual triggers are MCP-driveable. |
| Object storage / backups | Backblaze B2 + rclone | No MCP | **DIY GitHub-repo backup of irreplaceable tables** | Free-tier Supabase has no automated backups; a daily Render cron runs `pg_dump` on the four irreplaceable tables (holding_lots, decisions, screening_rules, model_versions) and commits the gzipped result to a private `asxos-backups` GitHub repo via `gh` CLI. Prices, fundamentals, signals, and features are re-derivable from EODHD and the model artefacts, so they do not need backup. |
| Email transport | Resend | No MCP, simple REST | **Resend** | One curl call. Documented in Part 8.3. |
| Job monitoring | Healthchecks.io | No MCP, simple REST | **Healthchecks.io** | One curl call per ping. Documented in Part 8.3. |
| Network gating | Tailscale | Community MCP, not installed | **Drop** | No VPS to gate. API auth is a single bearer token on the Render service. |
| Frontend hosting | Vercel | Vercel MCP exists in James's config | **Cancel** | The new system has no frontend. The MCP is unused after cancellation. |

The cost delta vs. the Hetzner plan is roughly +USD 2/month (Render Starter at USD 7 + Supabase free at USD 0 − Hetzner at ~USD 5). The operational delta is much larger in the opposite direction: every "check why X happened" loop that would have required SSH plus `journalctl` plus `psql` plus rclone becomes a single Claude Code prompt against the relevant MCP. At the point Supabase free tier storage fills (estimated 6–12 months in), the delta becomes +USD 27/month, which remains a fair operability premium.

### Cancellation and replacement order

| Item | Verdict | When | Approx. monthly cost | Notes |
|------|---------|------|-----------------------|-------|
| Vercel project (frontend) | Cancel | Immediately at M1 | USD 0–20 | New system has no frontend. Cancel the project, free the custom domain. Remove the Vercel MCP from `~/.claude/settings.json`. |
| Render web service `asx-portfolio-api` | Replace in place | At M1 (rename/replace, do not cancel) | ~USD 7 (Starter) | Re-used by the new system. Rename to `asxos-api`, repoint to the new GitHub repo. Continues to be MCP-driveable end-to-end. |
| Render cron: `daily-prices` | Replace in place | At M3 | USD 0 (free cron) | Becomes `asxos-sync-prices`, new command, same Render service slot. |
| Render cron: `daily-signals` | Replace in place | At M7 | USD 0 (free cron) | Becomes `asxos-generate-signals`. |
| Render cron: `asx-daily-announcements` | Replace in place | At M10 | USD 0 (free) | Becomes `asxos-ingest-regulatory`. |
| Render cron: `asx-aggregate-logs` | Cancel | Immediately at M1 | USD 0 (free) | No Sentry, no Vercel, no aggregation. Render logs queried via MCP replace this. |
| Render cron: `asx-weekly-universe` | Replace in place | At M3 | USD 0 (free) | Becomes `asxos-sync-universe`, weekly cadence. |
| Render cron: `asx-weekly-fundamentals` | Replace in place | At M4 | USD 0 (free) | Becomes `asxos-sync-fundamentals`. |
| Render cron: `asx-weekly-features` | Cancel | At M5 | USD 0 (free) | Not in new system — features computed in-process during `generate-signals`. |
| Render cron: `asx-weekly-drift` | Cancel | At M9 | USD 0 (free) | Retraining job handles drift implicitly. |
| Render cron: `asx-check-price-alerts` | Cancel | Immediately at M1 | USD 0 (free) | No alerts surface. Brief subsumes the use case. |
| Render cron: `asx-send-digests` | Replace in place | At M11 | USD 0 (free) | Becomes `asxos-compose-brief`. |
| Render cron: `asx-weekly-etf-holdings` | Cancel | Immediately at M1 | USD 0 (free) | ETF holdings not in M1–M12 scope. |
| Render cron: `asx-detect-etf-changes` | Cancel | Immediately at M1 | USD 0 (free) | Same. |
| Render cron: `macro-data` | Cancel | At M5 | USD 0 (free) | Macro features computed in-process. |
| Render cron: `news-ingestion` | Cancel | Immediately at M1 | USD 0 (free) | News not in M1–M12. Regulatory feed replaces it. |
| Render cron: `earnings-sync` | Cancel | At M4 | USD 0 (free) | Folded into fundamentals. |
| Render cron: `evaluate-signal-outcomes` | Cancel | Immediately at M1 | USD 0 (free) | Outcome tracking deferred to journal in M10. |
| Render cron: `data-retention` | Cancel | Immediately at M1 | USD 0 (free) | No conversations, no whatif sessions, no guests to clean up. |
| Render cron: `semantic-maintenance` | Cancel | Immediately at M1 | USD 0 (free) | No semantic memory in new system. |
| Render cron: `asx-retrain-model-a` | Replace in place | At M9 | USD 0 (free) | Becomes `asxos-retrain-model-a`, Sunday cadence. |
| Render cron: `asx-retrain-model-b` | Cancel | Immediately at M1 | USD 0 (free) | Model B not in scope. |
| Render cron: `validate-feature-freshness` | Cancel | Immediately at M1 | USD 0 (free) | `/health` 503 on stale signals replaces it. |
| Render cron: `validate-signal-quality` | Cancel | Immediately at M1 | USD 0 (free) | Brief leads with failures. |
| Render cron: `monitor-model-performance` | Cancel | Immediately at M1 | USD 0 (free) | Retraining gates carry this load. |
| Render cron: `validate-data-consistency` | Cancel | Immediately at M1 | USD 0 (free) | One Postgres, no consistency to validate across services. |
| Render cron: `monitor-api-quotas` | Cancel | Immediately at M1 | USD 0 (free) | Token bucket in the EODHD client replaces it. |
| Render cron: `sector-macro-correlations` | Cancel | Immediately at M1 | USD 0 (free) | Out of scope. |
| Render cron: `confidence-decay` | Cancel | Immediately at M1 | USD 0 (free) | Out of scope. |
| Render cron: `analyst-ratings-freshness` | Cancel | Immediately at M1 | USD 0 (free) | Out of scope. |
| Supabase project | **Keep through M12 and beyond, downgrade to free tier** | At M1 (downgrade) | USD 0 (free tier) | Becomes the single source of truth. Same project; new schema added alongside legacy tables, legacy tables dropped in M3+ as data migrates. Downgrade from Pro to free tier at M1 — James has opted out of PITR/automated backups in favour of the DIY GitHub-repo backup of irreplaceable tables. Plan to re-upgrade to Pro when storage approaches 500MB (estimated 6–12 months in). |
| EODHD API subscription | Keep | Through M12 and beyond | ~USD 20 | Sole price + fundamentals + earnings source. Required. |
| FRED API key | Keep | Through M12 | USD 0 | Free tier, used by macro feature group. |
| Voyage AI subscription | Cancel | Immediately at M1 | Variable | No semantic memory in new system. |
| Anthropic API key | Keep | Beyond M12 (Claude Code use) | Variable | Used by Claude Code, not by the application. |
| Resend account | Keep | Through M11 and beyond | USD 0 (free tier) | Morning brief vendor. |
| Hetzner CX22 | **Do not provision** | n/a | n/a | Original plan abandoned. No SSH, no `journalctl` to operate by hand. |
| Backblaze B2 | **Do not provision** | n/a | n/a | Supabase Pro backups replace it. |
| Tailscale | **Do not configure** | n/a | n/a | No VPS to gate. |
| Domain `asx-portfolio.com` (or equivalent) | Optional repoint | At M1 | ~USD 1.50 (amortised) | Detach from Vercel. The new API is served from Render's `*.onrender.com` subdomain plus a custom domain if James wants one later. |
| SSL/TLS certs | Render-managed | n/a | n/a | Automatic on Render. |

### Total monthly savings

Conservative tally of recurring charges that go away (counting only items being cancelled, not items being reused in place):

- Render Starter crons that were on the paid plan unnecessarily (collapsed into free cron services on the new project): USD ~28
- Vercel hobby/pro: USD 0–20
- Voyage AI: variable, assume USD 5

That is roughly **USD 35–55 per month** in clean cancellations.

New monthly cost:

- Render Starter web service (reused, renamed `asxos-api`): USD 7
- Render free-tier cron services (7 jobs): USD 0
- Supabase free tier (downgraded from Pro at M1): USD 0
- Healthchecks.io: USD 0 (free tier)
- Resend: USD 0 (free tier covers one user's morning brief)
- EODHD: unchanged (~USD 20)
- FRED: USD 0

Net infrastructure spend drops from roughly **USD 110/month → USD 32/month** (plus EODHD). The EODHD bill is unchanged and is the price of having signals at all. Total monthly recurring saving, focused only on what is changing: approximately **USD 75–80 per month**. The Hetzner plan would have saved another USD 27/month on top of that and required James to learn `journalctl`. He is buying back operability with that USD 27.

### Order-of-operations dependencies

1. At M1: cancel Vercel, cancel all out-of-scope crons (alerts, ETF, news, retention, semantic, monitoring crons, Model B retraining, evaluate outcomes, validate-* crons). These have no migration path because their use case is dropped. Rename the existing Render web service to `asxos-api` and point it at the new GitHub repo. Verify the Render MCP, Supabase MCP, and GitHub CLI are all working in Claude Code (see Part 8.6 for verification).
2. At M3: replace `daily-prices` cron in place with `asxos-sync-prices`, replace `asx-weekly-universe` with `asxos-sync-universe`, cancel `macro-data`.
3. At M4: replace `asx-weekly-fundamentals` with `asxos-sync-fundamentals`; cancel `earnings-sync`.
4. At M5: cancel `asx-weekly-features`.
5. At M7: replace `daily-signals` with `asxos-generate-signals`.
6. At M9: cancel `asx-weekly-drift`; replace `asx-retrain-model-a` with `asxos-retrain-model-a`.
7. At M10: replace `asx-daily-announcements` with `asxos-ingest-regulatory`.
8. At M11: replace `asx-send-digests` with `asxos-compose-brief`.
9. After M11 verified for one week of clean brief delivery: monitor Supabase storage usage monthly via `mcp__supabase__execute_sql` (`SELECT pg_database_size('postgres')`). Re-upgrade to Pro the month before storage crosses 500MB; expect this around 6–12 months in as historical prices accumulate.

The legacy Supabase tables are not deleted until the new schema has fully replaced their function and a full week of clean operation has passed. They live alongside the new tables in the same Supabase project, distinguishable by name.

---

## Part 3 — New infrastructure setup (revised: MCP audit)

This is the one-time setup. Every step is driveable from Claude Code via an MCP, except where a vendor requires James to authenticate in a browser to create an account. Where a browser step is unavoidable, the step is marked **browser-only**; everything else has a Claude Code prompt provided so James never has to translate the step into a tool call himself.

The flip from the previous draft: there is no VPS, no SSH, no Docker, no `journalctl`, no Tailscale, no rclone, no Backblaze. The runtime is Render (web service + cron services) and Supabase (Postgres + daily backups). Both have MCPs James already has installed.

### 3.1 GitHub repo (one-time, browser-only)

1. Sign in to https://github.com.
2. Create a new private repo named `asxos`. Empty — do not initialise with a README; the local repo bootstrap in Part 4 will push the first commit.
3. From the local workstation, verify `gh auth status` is green. If not, run `gh auth login`. Claude Code drives GitHub via the `gh` CLI, which is preinstalled on James's machine.

### 3.2 Supabase project (one-time, browser-only for project creation)

Supabase has an MCP, but project creation itself requires a browser session because billing is involved.

1. Sign in to https://supabase.com.
2. Create a new project: name `asxos`, region Sydney (`ap-southeast-2`), Postgres 16. Generate and record the database password — it is the only one Supabase will not show you again.
3. Downgrade the existing project to the free tier from the dashboard (Project Settings → Billing → Change Plan). James has explicitly opted to lose 7-day point-in-time recovery in exchange for the USD 25/month saving; the DIY GitHub-repo backup (see Part 3.6) covers the irreplaceable subset. Plan to re-upgrade when DB size approaches 500MB.
4. Once the project is provisioned, record:
   - **Project ref** (the slug in the URL, e.g. `abcd1234efgh`)
   - **`DATABASE_URL`** from Project Settings → Database → Connection string → URI (use the session-pooler form on port `5432`)
   - **`SUPABASE_URL`** and **`SUPABASE_ANON_KEY`** from Project Settings → API
5. After project creation, the Supabase MCP can do everything else. Verify by asking Claude Code:

   > "Use the Supabase MCP to list the tables in the asxos project (ref: `<your-ref>`). I expect an empty list."

   The MCP tool invoked is `mcp__supabase__list_tables`. The expected result is an empty list (or the Supabase auth/storage system tables only).

### 3.3 Render account and project (one-time, browser-only for account)

1. Sign in to https://render.com if not already; James has an existing Render account from the old project.
2. Create a new Render workspace (or reuse the existing one) and verify the connected GitHub account has access to the `asxos` repo.
3. **Do not provision services manually.** They will be defined in `render.yaml` (Part 4) and Claude Code will create them via the Render MCP on the first deploy. This is the structural fix for the drift problem: every service starts life from `render.yaml`, not from a dashboard click.
4. Verify the Render MCP is connected by asking Claude Code:

   > "Use the Render MCP to list workspaces, then select the workspace that has the asxos GitHub integration."

   The MCP tools are `mcp__render__list_workspaces` and `mcp__render__select_workspace`.

### 3.4 Healthchecks.io (one-time, browser-only)

Healthchecks.io has no MCP, so this is a one-time browser setup. Daily operation is one curl call per ping, run by Render crons; Claude Code can drive ad-hoc tests against the same API.

1. Sign up at https://healthchecks.io/.
2. Create a project `asxos`.
3. Create six checks, one per job: `sync-prices`, `sync-fundamentals`, `generate-signals`, `ingest-regulatory`, `compose-brief`, `retrain-model-a`.
4. For each, copy the ping URL (looks like `https://hc-ping.com/<uuid>`).
5. Configure email notification on the project to `jamespcino@gmail.com`.
6. Set grace period: 60 minutes for daily jobs, 4 hours for weekly retrain.

These six URLs become `HEALTHCHECK_URL_<JOB>` env vars on the Render service.

### 3.5 Resend (one-time, browser-only)

Resend has no MCP but the send API is one curl call.

1. Sign up at https://resend.com/.
2. Verify a sending domain (or use the test domain initially, knowing it only delivers to the verified inbox `jamespcino@gmail.com`).
3. Generate an API key with `emails:send` scope only.
4. Record `RESEND_API_KEY` and the verified sender as `BRIEF_FROM_EMAIL`.

### 3.6 DIY backup repo for irreplaceable tables (one-time)

Because Supabase is on the free tier, automated backups and 7-day PITR are off. The DIY substitute is a private GitHub repo, populated by a daily Render cron that dumps the four irreplaceable tables and commits the gzipped result. The replaceable tables (prices, fundamentals, signals, features, regulatory_events, job_runs) are not backed up — they are re-derivable from EODHD and the model artefacts.

Irreplaceable tables, in dependency order:

- `holding_lots` — James's actual position lots, the only data only he has
- `decisions` — the strategy evolution journal, append-only and irreversible
- `screening_rules` — curated rule definitions, hand-tuned over time
- `model_versions` — record of which model artefact was active when

Setup steps:

1. From the GitHub UI, create a private repo named `asxos-backups` under James's account. No README, no `.gitignore`, no licence. Empty.
2. From the local machine, clone it: `gh repo clone <github-username>/asxos-backups /tmp/asxos-backups-init && cd /tmp/asxos-backups-init && git commit --allow-empty -m "init" && git push`.
3. Generate a fine-grained GitHub PAT with `Contents: Read and write` scope on `asxos-backups` only. Save the value as `BACKUP_GITHUB_TOKEN` for Part 3.6 env var upload.
4. The backup script (`scripts/backup_irreplaceable.sh`) ships in M12; it is invoked by a `asxos-backup-irreplaceable` Render cron service running daily 23:00 AET. The script:
   - Runs `pg_dump` against Supabase with `--table=holding_lots --table=decisions --table=screening_rules --table=model_versions --data-only --no-owner --no-acl`
   - Pipes through `gzip` to a file named `backup-$(date +%Y-%m-%d).sql.gz`
   - Clones the backup repo via the PAT, commits the new file, pushes, prunes files older than 90 days from the repo (via `git rm` of dated files; full history preserved)
5. Verify by asking Claude Code after M12: "Show me the last 5 files in the `asxos-backups` repo and confirm the most recent dump is from today." Claude Code uses `gh api` via Bash to list the contents.

Restore procedure (one-pager for emergencies, lives in `docs/operations/RESTORE.md` in the asxos repo): clone `asxos-backups`, `gunzip` the most recent dump, `psql $DATABASE_URL < backup-YYYY-MM-DD.sql`. Estimated restore time for the four tables: under 30 seconds.

The total size of these four tables stays small. Estimate: 100 lots × 200 bytes = 20KB, 1,000 decisions × 500 bytes = 500KB, 100 screening rules × 1KB = 100KB, 50 model versions × 200 bytes = 10KB. Each gzipped dump under 200KB. 90 days of history under 20MB in the backup repo. GitHub free tier handles this without any concern.

### 3.7 Environment variables (one-time, MCP-driven)

After Parts 3.1–3.6 are done, collect all secrets into a single local `.env.production` file. This file is **not** committed; it is the source for one bulk upload to Render via MCP.

```bash
# .env.production (locally, .gitignored)
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=...
EODHD_API_KEY=...
FRED_API_KEY=...
RESEND_API_KEY=...
BRIEF_FROM_EMAIL=brief@asxos.<your-verified-domain>
BRIEF_TO_EMAIL=jamespcino@gmail.com
HEALTHCHECK_URL_SYNC_PRICES=https://hc-ping.com/...
HEALTHCHECK_URL_SYNC_FUNDAMENTALS=https://hc-ping.com/...
HEALTHCHECK_URL_GENERATE_SIGNALS=https://hc-ping.com/...
HEALTHCHECK_URL_INGEST_REGULATORY=https://hc-ping.com/...
HEALTHCHECK_URL_COMPOSE_BRIEF=https://hc-ping.com/...
HEALTHCHECK_URL_RETRAIN_MODEL_A=https://hc-ping.com/...
HEALTHCHECK_URL_BACKUP_IRREPLACEABLE=https://hc-ping.com/...
BACKUP_GITHUB_TOKEN=ghp_...  # fine-grained PAT scoped to asxos-backups repo only
BACKUP_REPO=<github-username>/asxos-backups
ASXOS_TZ=Australia/Sydney
ASXOS_API_HOST=0.0.0.0
ASXOS_API_PORT=10000
ASXOS_API_TOKEN=$(openssl rand -hex 32)
```

Note `ASXOS_API_HOST=0.0.0.0` and port `10000`: Render injects `PORT=10000` and requires the service to bind to the public interface. The API is protected by a bearer token (`ASXOS_API_TOKEN`) rather than network gating, which removes the need for Tailscale.

Once the Render service exists (auto-created from `render.yaml` on the first deploy in M1), upload the env vars in one shot:

> "Use the Render MCP to set every variable in `.env.production` on the `asxos-api` service. Use `mcp__render__update_environment_variables`. Report the resulting variable list when done so I can verify against the file."

This is the only acceptable way to set Render env vars in the new system. The dashboard is read-only as far as routine operation is concerned; any deviation is caught by `make check-drift` (Part 8.4).

### 3.8 Local dev workflow

Local dev does not require any of the above. The repo bootstrap in Part 4 sets up:

- A Supabase preview branch via `mcp__supabase__create_branch` — isolated copy of the production schema, separate DB connection, throwaway. Claude Code creates, applies migrations to, and discards these via MCP. This is the canonical local-dev pattern.
- A local FastAPI on `127.0.0.1:8788` pointed at the preview branch's `DATABASE_URL`.
- The Make targets from Part 4.6 unchanged.

There is no migration runner script in this repo. Migrations are plain `.sql` files in `migrations/`, applied exclusively via `mcp__supabase__apply_migration`. Local-only docker-compose Postgres is kept available for offline development but is not the default path; if used, migrations are applied with `psql -f` against the local DB and the lifespan drift check is bypassed with `SKIP_MIGRATION_DRIFT_CHECK=1`.

Infrastructure is now ready. Move to Part 4 to bootstrap the repo. The deployment specifics — `render.yaml`, the cron schedule, the production env upload — are handled at M12 with Claude Code driving every step via MCP, and Part 8 is the complete reference for that workflow.

---

## Part 4 — Repository bootstrap

The new repo is `asxos`. Create it as a fresh GitHub repo (private). Clone locally and follow this sequence. Every file in this section is provided verbatim — paste into the new repo and it should work.

### 4.1 Initial structure

```bash
mkdir asxos && cd asxos
git init -b main
mkdir -p src/asxos/{api/routes,domain/{signals,tax,models},ml,ingest,jobs,cli}
mkdir -p tests/{unit,integration,jobs}
mkdir -p migrations models deploy/timers scripts
touch src/asxos/__init__.py
touch src/asxos/{api,domain,ml,ingest,jobs,cli}/__init__.py
touch src/asxos/api/routes/__init__.py
touch src/asxos/domain/{signals,tax,models}/__init__.py
```

### 4.2 `.python-version`

```
3.12
```

### 4.3 `pyproject.toml`

```toml
[project]
name = "asxos"
version = "0.1.0"
description = "Personal ASX investment intelligence OS"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "asyncpg==0.29.0",
    "psycopg[binary]==3.2.3",
    "psycopg2-binary==2.9.10",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "lightgbm==4.5.0",
    "shap==0.46.0",
    "numpy==1.26.4",
    "pandas==2.2.3",
    "scikit-learn==1.5.2",
    "joblib==1.4.2",
    "httpx==0.27.2",
    "tenacity==9.0.0",
    "typer==0.12.5",
    "rich==13.9.2",
    "jinja2==3.1.4",
    "resend==2.4.0",
    "python-dotenv==1.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "pytest-cov==5.0.0",
    "ruff==0.7.0",
    "mypy==1.13.0",
    "types-requests",
]

[project.scripts]
asx = "asxos.cli.main:app"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers"
```

### 4.4 `.env.example`

```bash
# Database
DATABASE_URL=postgresql://asxos:CHANGE_ME@localhost:5432/asxos

# EODHD (sole price + fundamentals source)
EODHD_API_KEY=

# FRED (macro feature group)
FRED_API_KEY=

# Resend (morning brief)
RESEND_API_KEY=
BRIEF_FROM_EMAIL=brief@asxos.local
BRIEF_TO_EMAIL=jamespcino@gmail.com

# Healthchecks.io (one ping URL per job)
HEALTHCHECK_URL_SYNC_PRICES=
HEALTHCHECK_URL_SYNC_FUNDAMENTALS=
HEALTHCHECK_URL_GENERATE_SIGNALS=
HEALTHCHECK_URL_INGEST_REGULATORY=
HEALTHCHECK_URL_COMPOSE_BRIEF=
HEALTHCHECK_URL_RETRAIN_MODEL_A=

# Paths (override only on the VPS)
ASXOS_MODELS_DIR=./models
ASXOS_DATA_DIR=./data

# Timezone for cron-like behaviour
ASXOS_TZ=Australia/Sydney

# API binding (always loopback in production)
ASXOS_API_HOST=127.0.0.1
ASXOS_API_PORT=8788
```

### 4.5 `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file:
      - /etc/asxos/postgres.env
    volumes:
      - asxos-pg-data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U asxos -d asxos"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  asxos-pg-data:
```

For local development the env file path becomes a relative path; the Makefile handles both.

### 4.6 `Makefile`

```make
.PHONY: help dev migrate test sync-universe sync-prices sync-fundamentals signals brief retrain shell deploy logs format lint typecheck

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-22s %s\n", $$1, $$2}'

$(VENV)/bin/activate:
	python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

dev: $(VENV)/bin/activate ## Start the API on 127.0.0.1:8788
	$(PY) -m uvicorn asxos.api.main:app --host 127.0.0.1 --port 8788 --reload

migrate: ## Reminder: migrations are applied via Supabase MCP, not this target
	@echo "Migrations are applied via Claude Code using mcp__supabase__apply_migration."
	@echo "Ask Claude Code: 'apply migration 00NN to the asxos Supabase project'."
	@echo "For offline docker-compose dev: psql \$$DATABASE_URL -f migrations/00NN_*.sql"

test: $(VENV)/bin/activate ## Run pytest
	$(VENV)/bin/pytest

sync-universe: $(VENV)/bin/activate ## Pull active ASX universe from EODHD
	$(PY) -m asxos.jobs.sync_universe

sync-prices: $(VENV)/bin/activate ## Pull today's prices for all active symbols
	$(PY) -m asxos.jobs.sync_prices

sync-fundamentals: $(VENV)/bin/activate ## Pull fundamentals (weekly cadence)
	$(PY) -m asxos.jobs.sync_fundamentals

signals: $(VENV)/bin/activate ## Compute features and persist signals for today
	$(PY) -m asxos.jobs.generate_signals

brief: $(VENV)/bin/activate ## Compose and send the morning brief
	$(PY) -m asxos.jobs.compose_brief

retrain: $(VENV)/bin/activate ## Run the Model A retraining pipeline
	$(PY) -m asxos.jobs.retrain_model_a

shell: $(VENV)/bin/activate ## Open a psql shell against the local DB
	psql $$DATABASE_URL

deploy: ## Rsync code and unit files to the VPS, daemon-reload, restart
	bash scripts/deploy.sh

logs: ## Tail journalctl for all asxos units on the VPS
	ssh asxos@asxos-prod 'journalctl -u "asxos-*" -f'

format: $(VENV)/bin/activate ## Apply ruff formatting
	$(VENV)/bin/ruff format src tests

lint: $(VENV)/bin/activate ## Lint with ruff
	$(VENV)/bin/ruff check src tests

typecheck: $(VENV)/bin/activate ## Run mypy on domain and ml only
	$(VENV)/bin/mypy src/asxos/domain src/asxos/ml
```

### 4.7 `README.md`

```markdown
# asxos

Personal ASX investment intelligence OS for one user.

## Quickstart

```bash
git clone <repo>
cd asxos
cp .env.example .env  # fill in EODHD_API_KEY, RESEND_API_KEY, healthchecks URLs
docker compose up -d  # starts Postgres
make migrate
make dev  # starts API on 127.0.0.1:8788
```

## Daily verbs

- `make sync-prices` — pull today's OHLCV
- `make signals` — compute features and persist signals
- `make brief` — compose and send the 7am email
- `asx ask BHP.AU` — print today's signal with SHAP factors
- `asx tax-view` — print the tax-adjusted view of current holdings
- `asx journal add BHP.AU buy 100 'thesis...'` — record a decision

## Architecture

See `docs/rebuild/phase-4-architecture-system-architect.md` and the build guide at `docs/rebuild/BUILD_GUIDE.md`.
```

### 4.8 `.gitignore`

```
.venv/
__pycache__/
*.pyc
.env
.env.local
*.joblib
*.pkl
data/
.coverage
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
.DS_Store
```

### 4.9 `ruff.toml`

```toml
line-length = 100
target-version = "py312"

[lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "C90"]
ignore = ["E501"]

[lint.mccabe]
max-complexity = 12

[format]
quote-style = "double"
```

### 4.10 `mypy.ini`

```ini
[mypy]
python_version = 3.12
strict_optional = True
warn_unused_ignores = True
disallow_untyped_defs = True
warn_redundant_casts = True
no_implicit_optional = True

[mypy-lightgbm.*]
ignore_missing_imports = True

[mypy-shap.*]
ignore_missing_imports = True
```

### 4.11 Migrations — MCP-driven, no runner script

There is no migration runner in this repo. Migrations are plain numbered `.sql` files in `migrations/` (e.g., `0001_initial.sql`, `0002_signals.sql`). Applying them happens exclusively through the Supabase MCP — Claude Code reads the file and calls `mcp__supabase__apply_migration` with the SQL contents. Supabase records each applied migration in its canonical `supabase_migrations.schema_migrations` table.

The workflow:

1. Write the migration as `migrations/00NN_short_name.sql`. Idempotent SQL (use `IF NOT EXISTS` patterns), with a corresponding rollback comment block at the top.
2. For production: ask Claude Code "apply migration 00NN to the asxos Supabase project." Claude reads the file, calls `mcp__supabase__apply_migration`, reports success or the Postgres error.
3. For local dev on a preview branch: ask "create a Supabase preview branch from main and apply migration 00NN to it." Claude calls `mcp__supabase__create_branch` then `mcp__supabase__apply_migration` against the branch URL.
4. For offline docker-compose dev (rare): `psql $DATABASE_URL -f migrations/00NN_short_name.sql` and set `SKIP_MIGRATION_DRIFT_CHECK=1` so the lifespan handler does not complain about the missing `schema_migrations` row.

The lifespan handler reads `supabase_migrations.schema_migrations` and compares the applied count against the count of `.sql` files in `migrations/`. Drift fails startup. This catches the situation where someone writes a migration file but forgets to apply it before deploy — the API refuses to start with the new code against the old schema.

The `make migrate` target prints a reminder rather than executing anything; the actual apply step is a Claude Code prompt, not a shell command.

### 4.12 `src/asxos/config.py`

Fail-fast settings loader. No silent defaults for required keys.

```python
"""Application configuration. Fails on missing required vars."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required
    database_url: str = Field(..., alias="DATABASE_URL")
    eodhd_api_key: str = Field(..., alias="EODHD_API_KEY")
    resend_api_key: str = Field(..., alias="RESEND_API_KEY")
    brief_from_email: str = Field(..., alias="BRIEF_FROM_EMAIL")
    brief_to_email: str = Field(..., alias="BRIEF_TO_EMAIL")

    # Optional with sane defaults
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")
    models_dir: Path = Field(default=Path("./models"), alias="ASXOS_MODELS_DIR")
    data_dir: Path = Field(default=Path("./data"), alias="ASXOS_DATA_DIR")
    tz: str = Field(default="Australia/Sydney", alias="ASXOS_TZ")
    api_host: str = Field(default="127.0.0.1", alias="ASXOS_API_HOST")
    api_port: int = Field(default=8788, alias="ASXOS_API_PORT")

    # Healthchecks ping URLs
    hc_sync_prices: str = Field(default="", alias="HEALTHCHECK_URL_SYNC_PRICES")
    hc_sync_fundamentals: str = Field(default="", alias="HEALTHCHECK_URL_SYNC_FUNDAMENTALS")
    hc_generate_signals: str = Field(default="", alias="HEALTHCHECK_URL_GENERATE_SIGNALS")
    hc_ingest_regulatory: str = Field(default="", alias="HEALTHCHECK_URL_INGEST_REGULATORY")
    hc_compose_brief: str = Field(default="", alias="HEALTHCHECK_URL_COMPOSE_BRIEF")
    hc_retrain_model_a: str = Field(default="", alias="HEALTHCHECK_URL_RETRAIN_MODEL_A")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

### 4.13 `src/asxos/db.py`

asyncpg pool + numpy adapters registered at import time.

```python
"""Database connectivity. Registers numpy adapters at import."""
from __future__ import annotations

import numpy as np
import psycopg2.extensions
import asyncpg
from typing import Optional

from asxos.config import get_settings


# Register numpy adapters once at module load so every psycopg2 caller is safe.
for _np_type, _py_type in [
    (np.int64, int),
    (np.int32, int),
    (np.float64, float),
    (np.float32, float),
    (np.bool_, bool),
]:
    psycopg2.extensions.register_adapter(
        _np_type,
        lambda x, _cast=_py_type: psycopg2.extensions.AsIs(_cast(x)),
    )


_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=get_settings().database_url,
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("asyncpg pool not initialised; call init_pool() first")
    return _pool
```

### 4.14 `src/asxos/api/main.py`

The lifespan handler hard-fails on missing dependencies. This is the structural fix for the old `logger.warning(...) and continue` bug.

```python
"""FastAPI application with hard-fail lifespan."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException

from asxos.config import get_settings
from asxos.db import close_pool, init_pool, pool

logger = logging.getLogger("asxos.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1) Postgres reachable and migrations current
    p = await init_pool()
    async with p.acquire() as conn:
        if os.getenv("SKIP_MIGRATION_DRIFT_CHECK") != "1":
            applied = await conn.fetchval(
                "SELECT COUNT(*) FROM supabase_migrations.schema_migrations"
            )
            on_disk = sum(1 for _ in Path("migrations").glob("*.sql"))
            if applied != on_disk:
                raise RuntimeError(
                    f"Migration drift: {applied} applied, {on_disk} on disk. "
                    f"Ask Claude Code to apply pending migrations via Supabase MCP."
                )

    # 2) EODHD key present (deeper check happens in /health to keep startup fast)
    if not settings.eodhd_api_key:
        raise RuntimeError("EODHD_API_KEY is required")

    # 3) Active model loads (only if any rows exist in model_versions)
    async with p.acquire() as conn:
        active = await conn.fetchrow(
            "SELECT version, artifact_path FROM model_versions WHERE is_active = true LIMIT 1"
        )
    if active is not None:
        artefact = Path(active["artifact_path"])
        if not artefact.exists():
            raise RuntimeError(f"Active model artefact missing: {artefact}")

    # 4) Writable dirs
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    logger.info("asxos API ready")
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    async with pool().acquire() as conn:
        max_price_dt = await conn.fetchval("SELECT MAX(dt) FROM prices")
        max_signal_dt = await conn.fetchval("SELECT MAX(as_of) FROM signals")

    healthy = True
    detail: dict = {
        "max_price_dt": max_price_dt.isoformat() if max_price_dt else None,
        "max_signal_dt": max_signal_dt.isoformat() if max_signal_dt else None,
    }
    if max_price_dt and max_signal_dt:
        if (max_price_dt - max_signal_dt).days > 1:
            healthy = False
            detail["reason"] = "signals more than 1 trading day behind prices"

    if not healthy:
        raise HTTPException(status_code=503, detail=detail)
    return {"status": "ok", **detail}
```

This file is enough to get M1 working. Routes for signals, holdings, tax, journal, and brief are added across M6, M7, M8, M10, M11.

### 4.15 `.claude/` directory

Copy `.claude/commands/` and `.claude/rules/` from the old repo verbatim:

```bash
cp -R /Users/jamespcino/Projects/asx-portfolio-os/.claude/commands ./.claude/
cp -R /Users/jamespcino/Projects/asx-portfolio-os/.claude/rules ./.claude/
```

A new short `CLAUDE.md` lives at the repo root — covered in Part 6.

### 4.16 First commit

```bash
git add .
git commit -m "chore: bootstrap asxos repo"
git remote add origin git@github.com:jamespcino/asxos.git
git push -u origin main
```

The repo is now ready for M1. Move to Part 5.

---

## Part 5 — Milestones in detail

Each milestone has the same shape: recap, pre-flight, files, migration, code shapes, Claude Code prompts, verification, commit. Reference `phase-5-milestones.md` for the higher-level "why" of each milestone.

### M1 — Repo bootstrap and hard-fail lifecycle

**Recap.** The repo exists, the API boots locally with a lifespan handler that opens the asyncpg pool, checks migration count parity, and refuses to start if either fails. `/health` returns 200 with DB state. Killing Postgres makes `/health` 503. This is the foundation for everything else — every subsequent milestone trusts that a healthy `/health` reflects reality.

**Pre-flight.**
- Part 4 complete: pyproject.toml, .env.example, docker-compose.yml in place
- Local Docker + Docker Compose installed
- `.env` exists with `DATABASE_URL=postgresql://asxos:dev@localhost:5432/asxos` (dev only)
- `EODHD_API_KEY` and `RESEND_API_KEY` in `.env`

**Files to create.**
- `migrations/0001_initial.sql` — minimal table to give the lifespan check something to verify
- `src/asxos/api/main.py` — covered in Part 4
- `src/asxos/api/routes/health.py` — split out if growing (skip for M1; keep inline)
- `tests/integration/test_health.py`

**Migration `migrations/0001_initial.sql`.**

```sql
-- depends:

CREATE TABLE IF NOT EXISTS securities (
    symbol TEXT PRIMARY KEY,
    exchange TEXT NOT NULL DEFAULT 'AU',
    name TEXT,
    sector TEXT,
    currency TEXT NOT NULL DEFAULT 'AUD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    delisted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_securities_active ON securities(is_active) WHERE is_active = TRUE;
```

**Code shape — `tests/integration/test_health.py`.**

```python
import httpx
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok_when_db_reachable():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8788") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
```

**Claude Code prompts.**

1. Scaffold: "Create `migrations/0001_initial.sql` per BUILD_GUIDE.md M1. Then apply it to the asxos Supabase project via `mcp__supabase__apply_migration`. Confirm via `mcp__supabase__list_tables` that the expected tables exist."
2. Implement: "Fill in `src/asxos/api/main.py` per BUILD_GUIDE.md section 4.14. Use the lifespan signature shown. Do not add `/health` to a separate router yet — keep it inline."
3. Test: "Write `tests/integration/test_health.py` that starts the API in-process via httpx + TestClient and asserts `/health` returns 200. Then kill Postgres locally (`docker compose stop postgres`) and assert it returns 503. Restore Postgres after."

**Verification.**
```bash
docker compose up -d
make migrate           # → "Applying 1 migrations: - 0001_initial; Done."
make dev &             # API on :8788
curl -s http://127.0.0.1:8788/health | jq
# → {"status":"ok","max_price_dt":null,"max_signal_dt":null}
docker compose stop postgres
curl -i http://127.0.0.1:8788/health | head -1
# → HTTP/1.1 503 Service Unavailable
docker compose start postgres
make test
# → 1 passed in N.NNs
```

**Commit.** `feat(M1): repo bootstrap with hard-fail lifespan and /health`

### M2 — EODHD price ingestion, one symbol end-to-end

**Recap.** `asxos.ingest.eodhd` has a single rate-limited async client. `asxos.jobs.sync_prices` pulls today's prices for `BHP.AU` and upserts. `JobMonitor` is in place to track runs in `job_runs`. Re-runs are idempotent.

**Pre-flight.**
- M1 complete; `/health` 200
- `EODHD_API_KEY` in `.env`

**Files to create.**
- `migrations/0002_prices.sql`
- `migrations/0003_job_runs.sql`
- `src/asxos/ingest/eodhd.py`
- `src/asxos/ingest/prices.py`
- `src/asxos/jobs/sync_prices.py`
- `src/asxos/jobs/_runner.py` — JobMonitor port
- `tests/test_eodhd_ingestion.py`

**Migration `0002_prices.sql`.**

```sql
-- depends: 0001_initial

CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT NOT NULL REFERENCES securities(symbol),
    dt DATE NOT NULL,
    open NUMERIC(18,6),
    high NUMERIC(18,6),
    low NUMERIC(18,6),
    close NUMERIC(18,6) NOT NULL,
    adj_close NUMERIC(18,6),
    volume BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, dt)
);

CREATE INDEX IF NOT EXISTS idx_prices_symbol_dt_desc ON prices(symbol, dt DESC);
```

**Migration `0003_job_runs.sql`.**

```sql
-- depends: 0002_prices

CREATE TABLE IF NOT EXISTS job_runs (
    run_id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    rows_written INTEGER,
    error TEXT,
    dependencies_ok BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_job_runs_name_started ON job_runs(job_name, started_at DESC);
```

**Code shape — `src/asxos/ingest/eodhd.py`.**

```python
"""EODHD client. One per process, rate-limited."""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from asxos.config import get_settings


class EODHDClient:
    BASE = "https://eodhd.com/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._sem = asyncio.Semaphore(10)  # peak concurrency cap
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    async def _get(self, path: str, **params: Any) -> Any:
        async with self._sem:
            params["api_token"] = self.api_key
            params["fmt"] = "json"
            r = await self._client.get(f"{self.BASE}{path}", params=params)
            r.raise_for_status()
            return r.json()

    async def daily_prices(self, symbol: str, *, from_date: str | None = None) -> list[dict]:
        params: dict[str, Any] = {}
        if from_date:
            params["from"] = from_date
        return await self._get(f"/eod/{symbol}", **params)

    async def fundamentals(self, symbol: str) -> dict:
        return await self._get(f"/fundamentals/{symbol}")

    async def exchange_symbols(self, exchange: str = "AU") -> list[dict]:
        return await self._get(f"/exchange-symbol-list/{exchange}")


@lru_cache(maxsize=1)
def get_client() -> EODHDClient:
    return EODHDClient(api_key=get_settings().eodhd_api_key)
```

**Code shape — `src/asxos/jobs/_runner.py`.**

```python
"""JobMonitor port: opens a job_runs row, captures status, pings healthcheck."""
from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from asxos.db import init_pool, pool


logger = logging.getLogger("asxos.jobs")


@asynccontextmanager
async def run_job(name: str, healthcheck_url: str | None = None) -> AsyncIterator[dict]:
    """Wrap a job in a job_runs row. Caller mutates the yielded dict with rows_written, etc."""
    await init_pool()
    state: dict = {"rows_written": 0, "dependencies_ok": True}
    async with pool().acquire() as conn:
        run_id = await conn.fetchval(
            "INSERT INTO job_runs (job_name, status) VALUES ($1, 'running') RETURNING run_id",
            name,
        )
    try:
        yield state
        async with pool().acquire() as conn:
            await conn.execute(
                "UPDATE job_runs SET status='ok', finished_at=NOW(), rows_written=$2, dependencies_ok=$3 WHERE run_id=$1",
                run_id, state["rows_written"], state["dependencies_ok"],
            )
        if healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.get(healthcheck_url)
            except Exception:
                logger.warning("healthcheck ping failed for %s", name)
    except Exception:
        err = traceback.format_exc()
        async with pool().acquire() as conn:
            await conn.execute(
                "UPDATE job_runs SET status='error', finished_at=NOW(), error=$2 WHERE run_id=$1",
                run_id, err,
            )
        if healthcheck_url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.get(f"{healthcheck_url}/fail")
            except Exception:
                pass
        logger.error("job %s failed:\n%s", name, err)
        sys.exit(1)
```

**Code shape — `src/asxos/jobs/sync_prices.py`.**

```python
"""Sync today's prices for all active securities. M2: hardcoded BHP.AU. M3: full universe."""
from __future__ import annotations

import asyncio

from asxos.config import get_settings
from asxos.db import pool
from asxos.ingest.eodhd import get_client
from asxos.jobs._runner import run_job


async def upsert_prices(symbol: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    async with pool().acquire() as conn:
        await conn.execute("INSERT INTO securities(symbol) VALUES ($1) ON CONFLICT DO NOTHING", symbol)
        await conn.executemany(
            """INSERT INTO prices (symbol, dt, open, high, low, close, adj_close, volume)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               ON CONFLICT (symbol, dt) DO UPDATE SET
                   open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                   close=EXCLUDED.close, adj_close=EXCLUDED.adj_close, volume=EXCLUDED.volume""",
            [
                (symbol, r["date"], r.get("open"), r.get("high"), r.get("low"),
                 r["close"], r.get("adjusted_close"), r.get("volume"))
                for r in rows
            ],
        )
    return len(rows)


async def main() -> None:
    settings = get_settings()
    async with run_job("sync_prices", healthcheck_url=settings.hc_sync_prices) as state:
        client = get_client()
        # M2: hardcoded BHP.AU. M3 replaces this with a universe loop.
        rows = await client.daily_prices("BHP.AU")
        state["rows_written"] = await upsert_prices("BHP.AU", rows)
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Claude Code prompts.**

1. Scaffold: "Create migrations 0002 and 0003 per BUILD_GUIDE.md M2. Apply them. Confirm `\\d prices` and `\\d job_runs` look right via `make shell`."
2. Implement: "Implement `src/asxos/ingest/eodhd.py`, `src/asxos/jobs/_runner.py`, and `src/asxos/jobs/sync_prices.py` per the code shapes in BUILD_GUIDE.md M2. Do not yet handle universe — keep BHP.AU hardcoded."
3. Test: "Write `tests/test_eodhd_ingestion.py` using respx to mock the EODHD /eod endpoint. Test: (a) a successful pull writes N rows; (b) re-running with the same response writes zero new rows. Use a real (test) Postgres."

**Verification.**
```bash
make sync-prices
psql $DATABASE_URL -c "SELECT COUNT(*) FROM prices WHERE symbol='BHP.AU';"
# → some count > 0
make sync-prices  # second run
psql $DATABASE_URL -c "SELECT COUNT(*) FROM prices WHERE symbol='BHP.AU';"
# → same count (idempotent)
psql $DATABASE_URL -c "SELECT job_name, status, rows_written FROM job_runs ORDER BY run_id DESC LIMIT 2;"
make test
```

**Commit.** `feat(M2): EODHD client, job runner, sync_prices for BHP.AU`

**Cancellation step.** None yet (Render `daily-prices` stays until M3).

### M3 — Universe loaded, prices for all symbols

**Recap.** Universe ingestion lands; `sync_prices` becomes a per-universe loop using EODHD's bulk EOD endpoint where possible. Delistings detected.

**Pre-flight.**
- M2 complete; prices write for one symbol

**Files.**
- `src/asxos/ingest/universe.py`
- `src/asxos/jobs/sync_universe.py`
- Modify `src/asxos/jobs/sync_prices.py` to loop active universe

**Code shape — `src/asxos/ingest/universe.py`.**

```python
"""Pull active ASX universe from EODHD exchange listing endpoint."""
from __future__ import annotations

from datetime import datetime, timezone

from asxos.db import pool
from asxos.ingest.eodhd import get_client


async def refresh_universe() -> tuple[int, int]:
    """Return (added, delisted) counts."""
    client = get_client()
    rows = await client.exchange_symbols("AU")
    incoming = {r["Code"] + ".AU": r for r in rows if r.get("Type") == "Common Stock"}
    async with pool().acquire() as conn:
        existing = {r["symbol"]: r for r in await conn.fetch("SELECT symbol, is_active FROM securities")}
        added = 0
        delisted = 0
        for sym, r in incoming.items():
            if sym not in existing:
                await conn.execute(
                    "INSERT INTO securities (symbol, name, currency, is_active) VALUES ($1, $2, 'AUD', TRUE)",
                    sym, r.get("Name"),
                )
                added += 1
            elif not existing[sym]["is_active"]:
                await conn.execute(
                    "UPDATE securities SET is_active=TRUE, delisted_at=NULL WHERE symbol=$1",
                    sym,
                )
        for sym in existing:
            if sym not in incoming and existing[sym]["is_active"]:
                await conn.execute(
                    "UPDATE securities SET is_active=FALSE, delisted_at=$2 WHERE symbol=$1",
                    sym, datetime.now(timezone.utc),
                )
                delisted += 1
    return added, delisted
```

**Modified `sync_prices.py` (key change).** Replace the hardcoded `BHP.AU` block with:

```python
async with pool().acquire() as conn:
    symbols = [r["symbol"] for r in await conn.fetch(
        "SELECT symbol FROM securities WHERE is_active = TRUE ORDER BY symbol"
    )]
total = 0
for symbol in symbols:
    rows = await client.daily_prices(symbol, from_date=(date.today() - timedelta(days=7)).isoformat())
    total += await upsert_prices(symbol, rows)
state["rows_written"] = total
```

EODHD also offers a bulk endpoint `/eod-bulk-last-day/AU`; prefer that for the daily run and fall back to per-symbol on backfill. For the implementation, ask Claude Code to add a `daily_prices_bulk(exchange="AU")` method to `EODHDClient` and use it when `from_date is None`.

**Claude Code prompts.**

1. "Implement `src/asxos/ingest/universe.py` and `src/asxos/jobs/sync_universe.py` per M3. Add the `is_active` column logic to `securities` if not present."
2. "Modify `src/asxos/jobs/sync_prices.py` to iterate over active universe. Add a `daily_prices_bulk` method on `EODHDClient` and use it when fetching the most recent trading day."
3. "Backfill: write `scripts/backfill_from_supabase.py` that pulls historical prices from the old Supabase project (using the existing `DATABASE_URL` style connection) and writes into the new local DB. This is one-shot — do not register it as a job."

**Verification.**
```bash
make sync-universe
psql $DATABASE_URL -c "SELECT COUNT(*) FROM securities WHERE is_active = TRUE;"
# → ~2000+
time make sync-prices
# → completes in under 5 minutes
psql $DATABASE_URL -c "SELECT COUNT(DISTINCT symbol) FROM prices WHERE dt = CURRENT_DATE;"
# → matches universe count
```

**Commit.** `feat(M3): universe load and full-universe price sync`

**Cancellation step.** After backfill completes and the new DB has historical prices: cancel Render `daily-prices`, `asx-weekly-universe`, `macro-data`. Verify in Render dashboard.

### M4 — Fundamentals refresh

**Recap.** Weekly fundamentals job pulls per-symbol from EODHD and UPSERTs into `fundamentals`. Failure on one symbol does not abort the rest.

**Files.**
- `migrations/0004_fundamentals.sql`
- `src/asxos/ingest/fundamentals.py`
- `src/asxos/jobs/sync_fundamentals.py`

**Migration.**

```sql
-- depends: 0003_job_runs

CREATE TABLE IF NOT EXISTS fundamentals (
    symbol TEXT NOT NULL REFERENCES securities(symbol),
    as_of DATE NOT NULL,
    pe_ratio NUMERIC(18,6),
    pb_ratio NUMERIC(18,6),
    eps NUMERIC(18,6),
    market_cap NUMERIC(20,2),
    shares_outstanding BIGINT,
    dividend_yield NUMERIC(8,6),
    payout_ratio NUMERIC(8,6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, as_of)
);

CREATE INDEX IF NOT EXISTS idx_fundamentals_asof ON fundamentals(as_of DESC);
```

**Claude Code prompts.**

1. "Create migration 0004_fundamentals.sql per BUILD_GUIDE.md M4."
2. "Implement `src/asxos/ingest/fundamentals.py` with a function that takes a symbol, calls `EODHDClient.fundamentals`, and returns a flattened dict for upsert. Then `src/asxos/jobs/sync_fundamentals.py` iterates active universe, wraps each symbol in try/except, increments `rows_written` on success, logs failures."
3. "Write `tests/test_fundamentals_ingestion.py` covering (a) single-symbol parse, (b) malformed payload (missing PE) returns NULLs without raising, (c) symbol failure does not abort the run."

**Verification.**
```bash
make sync-fundamentals
psql $DATABASE_URL -c "SELECT COUNT(*) FROM fundamentals WHERE as_of >= CURRENT_DATE - 30;"
# → ~2000
```

**Commit.** `feat(M4): weekly fundamentals sync`

**Cancellation.** Cancel Render `asx-weekly-fundamentals` and `earnings-sync` once a full run is verified.

### M5 — Feature engine ported, features computable for one date

**Recap.** The single longest milestone. Port `app/features/ml/feature_engine.py` from the old repo into `src/asxos/domain/signals/feature_engine.py`, including all 8 feature groups and the `_safe_quintile` guard. Output the 22 features in `models/model_a_v1_5_features.json` exactly.

**The 22 features (canonical).** From `models/model_a_v1_5_features.json`:

```
ret_1d, mom_1, mom_3, mom_6, mom_12_1,
vol_30, vol_60, vol_90, vol_ratio_30_90,
adv_20_median, adv_zscore,
trend_200, sma200_slope, sma200_slope_pos,
atr_pct, volume_skew_60,
pe_ratio, pb_ratio, eps, market_cap,
pe_ratio_zscore, pb_ratio_zscore
```

**Files.**
- `src/asxos/domain/signals/feature_engine.py` — orchestrator
- `src/asxos/domain/signals/feature_groups/momentum.py`
- `src/asxos/domain/signals/feature_groups/volatility.py`
- `src/asxos/domain/signals/feature_groups/liquidity.py`
- `src/asxos/domain/signals/feature_groups/trend.py`
- `src/asxos/domain/signals/feature_groups/cross_sectional.py`
- `src/asxos/domain/signals/feature_groups/fundamental.py`
- `src/asxos/domain/signals/feature_groups/macro.py`
- `src/asxos/domain/signals/feature_groups/sentiment.py`
- `tests/test_feature_engine.py` — parity test

**Feature engine shape.**

```python
"""FeatureEngine — orchestrates the 8 feature groups. Same instance for train + infer."""
from __future__ import annotations

from datetime import date
from dataclasses import dataclass

import numpy as np
import pandas as pd


def _safe_quintile(s: pd.Series) -> pd.Series:
    """Quintile rank that returns NaN for an all-NaN group instead of raising."""
    valid = s.dropna()
    if len(valid) == 0:
        return pd.Series(np.nan, index=s.index)
    try:
        return pd.qcut(s, 5, labels=False, duplicates="drop").astype("float")
    except ValueError:
        return pd.Series(np.nan, index=s.index)


@dataclass(frozen=True)
class FeatureMatrix:
    as_of: date
    df: pd.DataFrame  # index: symbol, columns: 22 feature names

    def to_records(self) -> list[dict]:
        return [{"symbol": idx, **row} for idx, row in self.df.iterrows()]


class FeatureEngine:
    """Single source of truth for the 22-feature set."""

    def __init__(self) -> None:
        pass  # stateless; pure function over prices+fundamentals

    def compute(self, prices: pd.DataFrame, fundamentals: pd.DataFrame, as_of: date) -> FeatureMatrix:
        # prices: MultiIndex (symbol, dt), columns include close, volume, adj_close
        # fundamentals: indexed by symbol, latest as_of row per symbol
        from .feature_groups import momentum, volatility, liquidity, trend, cross_sectional, fundamental, macro, sentiment
        parts: list[pd.DataFrame] = []
        parts.append(momentum.compute(prices, as_of))
        parts.append(volatility.compute(prices, as_of))
        parts.append(liquidity.compute(prices, as_of))
        parts.append(trend.compute(prices, as_of))
        parts.append(cross_sectional.compute(prices, fundamentals, as_of))
        parts.append(fundamental.compute(fundamentals, as_of))
        parts.append(macro.compute(prices, as_of))
        parts.append(sentiment.compute(prices, as_of))
        df = pd.concat(parts, axis=1)
        # Enforce ordering and presence of the 22 canonical columns:
        from asxos.domain.signals.feature_spec import CANONICAL_FEATURES
        df = df.reindex(columns=CANONICAL_FEATURES)
        return FeatureMatrix(as_of=as_of, df=df)
```

**`src/asxos/domain/signals/feature_spec.py`.**

```python
"""Canonical 22-feature list. Locked at model release."""
from __future__ import annotations

CANONICAL_FEATURES: list[str] = [
    "ret_1d", "mom_1", "mom_3", "mom_6", "mom_12_1",
    "vol_30", "vol_60", "vol_90", "vol_ratio_30_90",
    "adv_20_median", "adv_zscore",
    "trend_200", "sma200_slope", "sma200_slope_pos",
    "atr_pct", "volume_skew_60",
    "pe_ratio", "pb_ratio", "eps", "market_cap",
    "pe_ratio_zscore", "pb_ratio_zscore",
]
```

**Parity test.**

```python
def test_feature_engine_byte_equal_on_repeated_compute(seeded_db, sample_date):
    from asxos.domain.signals.feature_engine import FeatureEngine
    prices = load_prices_through(sample_date)
    fundamentals = load_fundamentals_as_of(sample_date)
    fe = FeatureEngine()
    m1 = fe.compute(prices, fundamentals, sample_date)
    m2 = fe.compute(prices, fundamentals, sample_date)
    pd.testing.assert_frame_equal(m1.df, m2.df)
```

**Claude Code prompts.**

1. "Port `app/features/ml/feature_engine.py` from `/Users/jamespcino/Projects/asx-portfolio-os/.claude/worktrees/peaceful-rhodes-d221ec/app/features/ml/feature_engine.py` to `src/asxos/domain/signals/feature_engine.py` and `feature_groups/`. Preserve the 8 feature groups exactly. Preserve `_safe_quintile`. Use the canonical list in `feature_spec.py`. Do not change any formulae."
2. "Implement a CLI command `asx features <date>` that pulls prices and fundamentals from the local DB, computes the feature matrix, and prints `df.describe()` plus a head."
3. "Write `tests/test_feature_engine.py` with the parity test from BUILD_GUIDE.md M5. Add a second test asserting all 22 column names match `CANONICAL_FEATURES` and there are no NaN-only columns when given a fully-populated input."

**Verification.**
```bash
asx features 2026-05-15
# → DataFrame summary, ~2000 rows, 22 cols
pytest tests/test_feature_engine.py
# → all green
```

**Commit.** `feat(M5): port FeatureEngine with training/serving parity test`

**Cancellation.** Cancel Render `asx-weekly-features`.

### M6 — Model A loaded, predictions and SHAP for one date

**Recap.** Copy `model_a_v1_5_classifier.pkl`, `model_a_v1_5_regressor.pkl`, `model_a_v1_5_features.json` from the old repo's `models/` into the new repo's `models/`. Add migration `0005_model_versions.sql`. `asx predict <date>` runs end-to-end.

**Files.**
- `migrations/0005_model_versions.sql`
- `src/asxos/domain/models/cache.py`
- `src/asxos/domain/models/model_a.py`
- `src/asxos/cli/main.py` — add `predict` command

**Migration.**

```sql
-- depends: 0004_fundamentals

CREATE TABLE IF NOT EXISTS model_versions (
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    train_window_start DATE,
    train_window_end DATE,
    metrics JSONB,
    artifact_path TEXT NOT NULL,
    classifier_path TEXT,
    regressor_path TEXT,
    features_json_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (model_name, version)
);

CREATE UNIQUE INDEX uq_model_versions_one_active
    ON model_versions(model_name) WHERE is_active = TRUE;

-- Seed Model A v1.5 record (artefacts will be copied in by hand at M6)
INSERT INTO model_versions (model_name, version, artifact_path, classifier_path, regressor_path, features_json_path, is_active)
VALUES ('model_a', 'v1_5', 'models', 'models/model_a_v1_5_classifier.pkl', 'models/model_a_v1_5_regressor.pkl', 'models/model_a_v1_5_features.json', TRUE)
ON CONFLICT (model_name, version) DO NOTHING;
```

**Code shape — `src/asxos/domain/models/cache.py`.**

```python
"""Process-local model cache with 60s TTL re-read of is_active."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib

from asxos.db import pool


@dataclass
class LoadedModel:
    name: str
    version: str
    classifier: object
    regressor: object
    features: list[str]


class ModelCache:
    def __init__(self, ttl: int = 60) -> None:
        self.ttl = ttl
        self._loaded: dict[str, LoadedModel] = {}
        self._last_check: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, model_name: str) -> LoadedModel:
        now = time.time()
        async with self._lock:
            if model_name in self._loaded and now - self._last_check.get(model_name, 0) < self.ttl:
                return self._loaded[model_name]
            async with pool().acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT version, classifier_path, regressor_path, features_json_path "
                    "FROM model_versions WHERE model_name=$1 AND is_active=TRUE",
                    model_name,
                )
            if row is None:
                raise RuntimeError(f"no active version for {model_name}")
            current = self._loaded.get(model_name)
            if current and current.version == row["version"]:
                self._last_check[model_name] = now
                return current
            classifier = joblib.load(row["classifier_path"])
            regressor = joblib.load(row["regressor_path"])
            features = json.loads(Path(row["features_json_path"]).read_text())["features"]
            loaded = LoadedModel(model_name, row["version"], classifier, regressor, features)
            self._loaded[model_name] = loaded
            self._last_check[model_name] = now
            return loaded


_cache = ModelCache()


def get_cache() -> ModelCache:
    return _cache
```

**Code shape — `src/asxos/domain/models/model_a.py`.**

```python
"""Model A: predict + SHAP."""
from __future__ import annotations

import numpy as np
import pandas as pd

from asxos.domain.models.cache import get_cache


async def predict_with_shap(features_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (predictions_df, shap_df).
    predictions_df: symbol-indexed with prob_up, expected_return, rank.
    shap_df: symbol-indexed, columns = feature names + 'bias'.
    """
    model = await get_cache().get("model_a")
    X = features_df[model.features].astype(float).values
    prob_up = model.classifier.predict_proba(X)[:, 1]
    expected_return = model.regressor.predict(X)
    shap_contribs = model.classifier.predict(X, pred_contrib=True)  # n_rows x (n_features + 1)
    shap_df = pd.DataFrame(
        shap_contribs,
        index=features_df.index,
        columns=model.features + ["bias"],
    )
    preds = pd.DataFrame(
        {"prob_up": prob_up, "expected_return": expected_return},
        index=features_df.index,
    )
    preds["rank"] = preds["prob_up"].rank(ascending=False, method="min").astype(int)
    return preds.sort_values("rank"), shap_df
```

**Claude Code prompts.**

1. "Copy `models/model_a_v1_5_classifier.pkl`, `model_a_v1_5_regressor.pkl`, `model_a_v1_5_features.json` from the old repo into the new `models/`. Apply migration 0005. Verify with `psql -c \"SELECT * FROM model_versions;\"`."
2. "Implement `src/asxos/domain/models/cache.py` and `model_a.py` per BUILD_GUIDE.md M6. Update `src/asxos/api/main.py` lifespan to call `await get_cache().get('model_a')` on startup and raise on failure."
3. "Add `asx predict <date>` to the CLI: compute features, run `predict_with_shap`, print the top 10 by rank with their top 3 SHAP factors using rich.Table."

**Verification.**
```bash
asx predict 2026-05-15
# → top-10 table with prob_up, expected_return, and top 3 SHAP factors per row
# Rename the model file and restart
mv models/model_a_v1_5_classifier.pkl models/_disabled.pkl
make dev
# → process exits with "active model artefact missing"
mv models/_disabled.pkl models/model_a_v1_5_classifier.pkl
```

**Commit.** `feat(M6): Model A loader, predict + SHAP, model_versions table`

### M7 — Signals persisted with SHAP, daily pipeline assembled

**Recap.** Migration `0006_signals.sql` adds the signals table. `generate_signals.py` runs end-to-end: features → predict → SHAP → classify → write. Thresholds and regime detection land. `asx signal BHP.AU` works.

**Files.**
- `migrations/0006_signals.sql`
- `src/asxos/domain/signals/thresholds.py`
- `src/asxos/domain/signals/regime.py`
- `src/asxos/jobs/generate_signals.py`
- `src/asxos/cli/main.py` — add `signal` command
- `tests/test_thresholds.py`
- `tests/test_shap_jsonb.py`

**Migration.**

```sql
-- depends: 0005_model_versions

CREATE TABLE IF NOT EXISTS signals (
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    symbol TEXT NOT NULL REFERENCES securities(symbol),
    as_of DATE NOT NULL,
    prob_up NUMERIC(8,6),
    expected_return NUMERIC(8,6),
    signal_label TEXT NOT NULL,
    confidence NUMERIC(8,6),
    rank INTEGER,
    regime TEXT,
    shap JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (model_name, model_version, symbol, as_of),
    FOREIGN KEY (model_name, model_version) REFERENCES model_versions(model_name, version)
);

CREATE INDEX idx_signals_asof_label ON signals(as_of DESC, signal_label);
CREATE INDEX idx_signals_symbol_asof ON signals(symbol, as_of DESC);
CREATE INDEX idx_signals_shap_gin ON signals USING GIN (shap);
```

**Code shape — `src/asxos/domain/signals/thresholds.py`.**

```python
"""Signal label thresholds. Phase-2 canonical values."""
from __future__ import annotations


def classify(prob_up: float, expected_return: float) -> str:
    if prob_up >= 0.65 and expected_return > 0.05:
        return "STRONG_BUY"
    if prob_up >= 0.55 and expected_return > 0:
        return "BUY"
    if prob_up <= 0.35 and expected_return < -0.05:
        return "STRONG_SELL"
    if prob_up <= 0.45 and expected_return < 0:
        return "SELL"
    return "HOLD"


def apply_regime_thresholds(prob_up: float, expected_return: float, regime: str) -> str:
    """Regime-conditioned thresholds: stricter buys in bear, stricter sells in bull."""
    if regime == "bear":
        if prob_up >= 0.70 and expected_return > 0.06:
            return "STRONG_BUY"
        if prob_up >= 0.60 and expected_return > 0:
            return "BUY"
    if regime == "bull":
        if prob_up <= 0.30 and expected_return < -0.06:
            return "STRONG_SELL"
        if prob_up <= 0.40 and expected_return < 0:
            return "SELL"
    return classify(prob_up, expected_return)
```

**Code shape — `src/asxos/jobs/generate_signals.py`.**

```python
"""End-to-end daily signal generation."""
from __future__ import annotations

import asyncio
import json
from datetime import date

import numpy as np
import pandas as pd
import psycopg2.extensions

from asxos.config import get_settings
from asxos.db import pool
from asxos.domain.models.model_a import predict_with_shap
from asxos.domain.signals.feature_engine import FeatureEngine
from asxos.domain.signals.regime import classify_regime
from asxos.domain.signals.thresholds import apply_regime_thresholds
from asxos.jobs._runner import run_job


# numpy adapters already registered in asxos.db at module import.


async def load_inputs(as_of: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    async with pool().acquire() as conn:
        price_rows = await conn.fetch(
            "SELECT symbol, dt, close, adj_close, volume FROM prices WHERE dt <= $1 AND dt > $1 - INTERVAL '760 days'",
            as_of,
        )
        fund_rows = await conn.fetch(
            "SELECT DISTINCT ON (symbol) symbol, as_of, pe_ratio, pb_ratio, eps, market_cap "
            "FROM fundamentals WHERE as_of <= $1 ORDER BY symbol, as_of DESC",
            as_of,
        )
    prices = pd.DataFrame(price_rows).set_index(["symbol", "dt"])
    fundamentals = pd.DataFrame(fund_rows).set_index("symbol")
    return prices, fundamentals


async def upstream_ok_for(as_of: date) -> bool:
    async with pool().acquire() as conn:
        ok = await conn.fetchval(
            "SELECT COUNT(*) FROM job_runs WHERE job_name='sync_prices' "
            "AND status='ok' AND DATE(started_at AT TIME ZONE 'UTC') = $1",
            as_of,
        )
    return ok > 0


async def persist(model_name: str, model_version: str, as_of: date, preds: pd.DataFrame, shap_df: pd.DataFrame, regime: str) -> int:
    rows = []
    for symbol, p in preds.iterrows():
        shap_row = shap_df.loc[symbol].to_dict()
        label = apply_regime_thresholds(float(p["prob_up"]), float(p["expected_return"]), regime)
        rows.append((
            model_name, model_version, symbol, as_of,
            float(p["prob_up"]), float(p["expected_return"]),
            label, abs(float(p["prob_up"]) - 0.5) * 2,
            int(p["rank"]), regime, json.dumps(shap_row),
        ))
    async with pool().acquire() as conn:
        await conn.executemany(
            """INSERT INTO signals
                  (model_name, model_version, symbol, as_of, prob_up, expected_return,
                   signal_label, confidence, rank, regime, shap)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
               ON CONFLICT (model_name, model_version, symbol, as_of) DO UPDATE SET
                   prob_up=EXCLUDED.prob_up, expected_return=EXCLUDED.expected_return,
                   signal_label=EXCLUDED.signal_label, confidence=EXCLUDED.confidence,
                   rank=EXCLUDED.rank, regime=EXCLUDED.regime, shap=EXCLUDED.shap""",
            rows,
        )
    return len(rows)


async def main(as_of: date | None = None) -> None:
    settings = get_settings()
    as_of = as_of or date.today()
    async with run_job("generate_signals", healthcheck_url=settings.hc_generate_signals) as state:
        if not await upstream_ok_for(as_of):
            state["dependencies_ok"] = False
            raise RuntimeError(f"sync_prices has not completed for {as_of}")
        prices, fundamentals = await load_inputs(as_of)
        regime = classify_regime(prices)
        fe = FeatureEngine()
        fm = fe.compute(prices, fundamentals, as_of)
        preds, shap_df = await predict_with_shap(fm.df)
        state["rows_written"] = await persist("model_a", "v1_5", as_of, preds, shap_df, regime)


if __name__ == "__main__":
    asyncio.run(main())
```

**Tests — `tests/test_thresholds.py`.**

```python
import pytest
from asxos.domain.signals.thresholds import classify, apply_regime_thresholds

@pytest.mark.parametrize("prob, exp, label", [
    (0.65, 0.05001, "STRONG_BUY"),
    (0.6499, 0.06, "BUY"),
    (0.55, 0.0001, "BUY"),
    (0.5499, 0.01, "HOLD"),
    (0.45, -0.0001, "SELL"),
    (0.4501, -0.01, "HOLD"),
    (0.35, -0.05001, "STRONG_SELL"),
    (0.3501, -0.06, "SELL"),
])
def test_classify_boundary(prob, exp, label):
    assert classify(prob, exp) == label
```

**Claude Code prompts.**

1. "Apply migration 0006_signals.sql. Implement `thresholds.py` and `regime.py` per BUILD_GUIDE.md M7. `regime.py` classifies based on 200-day moving average of XJO / ASX200 proxy — use the most-traded ASX200 stock or a synthetic mean of top 10."
2. "Implement `src/asxos/jobs/generate_signals.py` per the code shape. Verify the numpy adapter block is loaded by `asxos.db` (not re-registered here)."
3. "Write `tests/test_thresholds.py` with boundary cases at 0.65, 0.55, 0.45, 0.35. Write `tests/test_shap_jsonb.py` asserting we can query `SELECT shap->>'mom_6' FROM signals` and get back a numeric string."
4. "Add `asx signal <symbol>` to the CLI: queries the latest signal for symbol, prints label + top 3 SHAP factors sorted by absolute magnitude."

**Verification.**
```bash
make sync-prices && make signals
asx signal BHP.AU
# → BHP.AU: BUY (prob 0.58, exp_ret +0.024)
#   driving factors: mom_6 (+0.027), pe_ratio_zscore (-0.018), trend_200 (+0.012)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM signals WHERE as_of = CURRENT_DATE;"
# → ~2000
make test
```

**Commit.** `feat(M7): signals persistence with SHAP JSONB, thresholds, regime`

**Cancellation.** Cancel Render `daily-signals`.

### M8 — Holdings and tax alpha layer

**Recap.** Lot-level `holding_lots` table with `current_holdings` view. CSV import. Pure-function tax module: CGT, franking, Div 296, Div 83A. CLI: `asx tax-view`, `asx tax-action`.

**Files.**
- `migrations/0007_holding_lots.sql`
- `migrations/0008_views.sql`
- `src/asxos/domain/tax/{cgt,franking,div_296,div_83a,positions}.py`
- `src/asxos/domain/lots.py`
- `src/asxos/cli/main.py` — `import-holdings`, `tax-view`, `tax-action`
- `tests/test_tax_{cgt,div_296,franking}.py`

**Migration `0007_holding_lots.sql`.**

```sql
-- depends: 0006_signals

CREATE TABLE IF NOT EXISTS holding_lots (
    lot_id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL REFERENCES securities(symbol),
    acquired_at DATE NOT NULL,
    currency TEXT NOT NULL DEFAULT 'AUD',
    qty NUMERIC(18,6) NOT NULL,
    cost_per_unit_local NUMERIC(18,6) NOT NULL,
    cost_per_unit_aud NUMERIC(18,6) NOT NULL,
    fx_rate_at_acquisition NUMERIC(12,6),
    source TEXT,
    account_type TEXT NOT NULL DEFAULT 'personal',  -- personal | super | smsf
    disposed_at DATE,
    disposed_proceeds_aud NUMERIC(18,6),
    espp_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_holding_lots_symbol_disposed ON holding_lots(symbol, disposed_at);
CREATE INDEX idx_holding_lots_active ON holding_lots(symbol) WHERE disposed_at IS NULL;
```

**Migration `0008_views.sql`.**

```sql
-- depends: 0007_holding_lots

CREATE OR REPLACE VIEW current_holdings AS
SELECT
    symbol,
    SUM(qty) AS qty,
    SUM(qty * cost_per_unit_aud) AS cost_basis_aud,
    SUM(qty * cost_per_unit_aud) / NULLIF(SUM(qty), 0) AS avg_cost_aud,
    MIN(acquired_at) AS earliest_acquired_at,
    account_type
FROM holding_lots
WHERE disposed_at IS NULL
GROUP BY symbol, account_type;
```

**Tax module shapes.**

```python
# src/asxos/domain/tax/cgt.py
"""CGT calculations. Pure functions."""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal


def cgt_discount_for(account_type: str, holding_period_days: int) -> Decimal:
    """Returns 0.5 (50% personal), 0.3333 (33% super), or 0 (insufficient hold)."""
    if holding_period_days < 365:
        return Decimal("0")
    if account_type == "super":
        return Decimal("0.3333")
    return Decimal("0.5")


def days_to_eligibility(acquired_at: date, today: date | None = None) -> int:
    today = today or date.today()
    return max(0, (acquired_at + timedelta(days=365) - today).days)


# src/asxos/domain/tax/franking.py
def franking_gross_up(cash_dividend: Decimal, franking_pct: Decimal, corporate_tax_rate: Decimal = Decimal("0.30")) -> Decimal:
    """Returns the imputation credit (franking credit) amount."""
    franked_portion = cash_dividend * franking_pct
    return franked_portion * (corporate_tax_rate / (Decimal("1") - corporate_tax_rate))


# src/asxos/domain/tax/div_296.py
SOFT_THRESHOLD = Decimal("3000000")
HARD_THRESHOLD = Decimal("10000000")
DIV_296_TAX_RATE = Decimal("0.15")


def div_296_liability(super_balance: Decimal, tcb_change: Decimal) -> Decimal:
    """Phase-1 Div 296: 15% on growth above $3M proportional. Returns AUD."""
    if super_balance <= SOFT_THRESHOLD:
        return Decimal("0")
    if tcb_change <= 0:
        return Decimal("0")
    proportional_excess = (super_balance - SOFT_THRESHOLD) / super_balance
    return tcb_change * proportional_excess * DIV_296_TAX_RATE


# src/asxos/domain/tax/div_83a.py
from dataclasses import dataclass


@dataclass
class Div83AOutcome:
    upfront_assessable_income: Decimal
    deferred_taxing_point_at: date | None
    cgt_cost_base: Decimal


def div_83a_treatment(grant_price: Decimal, market_value_at_vest: Decimal, vest_date: date) -> Div83AOutcome:
    """ESPP / ESS upfront taxing point treatment. Simplified: deemed upfront for now."""
    discount = market_value_at_vest - grant_price
    return Div83AOutcome(
        upfront_assessable_income=max(Decimal("0"), discount),
        deferred_taxing_point_at=None,
        cgt_cost_base=market_value_at_vest,
    )
```

**Lots — `src/asxos/domain/lots.py`.**

```python
"""Lot selection: FIFO, LIFO, min-CGT."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class HoldingLot:
    lot_id: int
    symbol: str
    acquired_at: date
    qty: Decimal
    cost_per_unit_aud: Decimal
    account_type: str


@dataclass
class LotSelection:
    lot_id: int
    qty_sold: Decimal
    realised_gain_aud: Decimal
    holding_period_days: int


def select_fifo(lots: list[HoldingLot], qty_to_sell: Decimal, current_price_aud: Decimal, sale_date: date) -> list[LotSelection]:
    selections: list[LotSelection] = []
    remaining = qty_to_sell
    for lot in sorted(lots, key=lambda x: x.acquired_at):
        if remaining <= 0:
            break
        take = min(remaining, lot.qty)
        gain = (current_price_aud - lot.cost_per_unit_aud) * take
        selections.append(LotSelection(
            lot_id=lot.lot_id, qty_sold=take, realised_gain_aud=gain,
            holding_period_days=(sale_date - lot.acquired_at).days,
        ))
        remaining -= take
    return selections


def select_lifo(lots: list[HoldingLot], qty_to_sell: Decimal, current_price_aud: Decimal, sale_date: date) -> list[LotSelection]:
    # same shape, sort reversed
    ...


def select_min_cgt(lots: list[HoldingLot], qty_to_sell: Decimal, current_price_aud: Decimal, sale_date: date, account_type: str) -> list[LotSelection]:
    """Pick the lot combination that minimises post-discount CGT. Brute force at small scale."""
    ...
```

**Claude Code prompts.**

1. "Apply migrations 0007 and 0008. Verify `current_holdings` view returns rows after inserting a test lot."
2. "Implement the tax module per BUILD_GUIDE.md M8. Every function takes Decimal in, returns Decimal out. No I/O, no `await`. Add `positions.tax_adjusted_view(holdings, lots, account_type, super_balance, fy_realised_gains)` that bundles the four scenarios into a single dataclass for the CLI."
3. "Implement `asx import-holdings <csv>` with a documented CSV format (symbol, acquired_at, qty, cost_per_unit_local, currency, fx_rate_at_acquisition, account_type, source). Reject malformed rows with a clear error; do not partial-import."
4. "Write boundary tests: `test_tax_cgt.py` for day 364, 365, 366 in personal and super. `test_tax_div_296.py` for $2,999,999, $3,000,000, $3,000,001, $10,000,000, $10,000,001. `test_tax_franking.py` for 30% and 25% corporate rates."

**Verification.**
```bash
asx import-holdings positions.csv
# → "Loaded 12 lots across 8 symbols"
asx tax-view
# → table with per-position post-discount CGT, days to eligibility, franking-adjusted yield
asx tax-action
# → "Lots crossing 12-month boundary in next 30 days: ..."
make test
# → tax tests pass at every boundary
```

**Commit.** `feat(M8): holding_lots, current_holdings view, pure-function tax module`

### M9 — Retraining pipeline, model version flip

**Recap.** `retrain_model_a.py` ports the old job. Walk-forward validation, three gates. On pass writes new artefact and an `is_active=false` row. `asx model activate v1_6` flips active. Restart loads the new version.

**Files.**
- `src/asxos/jobs/retrain_model_a.py`
- `src/asxos/domain/models/validation.py`
- `src/asxos/ml/train_model_a.py`
- `src/asxos/cli/main.py` — `model activate`
- `tests/test_walk_forward.py`

**Code shape — `src/asxos/domain/models/validation.py`.**

```python
"""Walk-forward validation and gate checks."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ValidationResult:
    auc: float
    samples: int
    degradation_pct: float | None  # vs current active
    passed: bool
    reasons: list[str]


def evaluate_gates(auc: float, samples: int, baseline_auc: float | None, min_auc: float = 0.65, max_degradation: float = 0.05, min_samples: int = 1000) -> ValidationResult:
    reasons: list[str] = []
    if auc < min_auc:
        reasons.append(f"AUC {auc:.4f} below {min_auc}")
    if samples < min_samples:
        reasons.append(f"samples {samples} below {min_samples}")
    deg = None
    if baseline_auc is not None:
        deg = (baseline_auc - auc) / baseline_auc
        if deg > max_degradation:
            reasons.append(f"degradation {deg:.2%} exceeds {max_degradation:.2%}")
    return ValidationResult(auc=auc, samples=samples, degradation_pct=deg, passed=not reasons, reasons=reasons)
```

**Claude Code prompts.**

1. "Port `jobs/retrain_model_a.py` from the old repo into `src/asxos/ml/train_model_a.py` (training logic) and `src/asxos/jobs/retrain_model_a.py` (orchestration). Use the same FeatureEngine from M5. TimeSeriesSplit, 12 folds, 36 months lookback."
2. "Implement `src/asxos/domain/models/validation.py` per shape. Gate values are env-overridable but default to AUC 0.65 / 5% degradation / 1000 samples."
3. "Add `asx model activate <version>` to CLI: BEGIN; UPDATE model_versions SET is_active=FALSE WHERE model_name=$1; UPDATE model_versions SET is_active=TRUE WHERE model_name=$1 AND version=$2; COMMIT. Print before/after rows."
4. "Write `tests/test_walk_forward.py` with synthetic data validating TimeSeriesSplit boundaries do not leak future into train."

**Verification.**
```bash
make retrain
# → "Trained v1_6: AUC=0.7102, samples=84120, degradation vs v1_5=+0.012 (improved). PASS. Wrote models/model_a_v1_6_classifier.pkl."
psql $DATABASE_URL -c "SELECT version, is_active FROM model_versions WHERE model_name='model_a';"
# → v1_5 t, v1_6 f
asx model activate v1_6
# → "Activated model_a v1_6 (was v1_5)"
make dev  # restart API
journalctl -u asxos-api  # local mock — see "Loaded model_a v1_6"
```

**Commit.** `feat(M9): retraining pipeline, walk-forward validation, manual activate`

**Cancellation.** Cancel Render `asx-weekly-drift`, `asx-retrain-model-a`.

### M10 — Regulatory ingestion, decisions journal

**Recap.** `regulatory_events` table. Three sources scraped daily. Decisions journal lands.

**Files.**
- `migrations/0009_regulatory_events.sql`
- `migrations/0010_decisions.sql`
- `src/asxos/ingest/regulatory.py`
- `src/asxos/jobs/ingest_regulatory.py`
- `src/asxos/cli/main.py` — `journal add`, `journal list`, `journal review`

**Migration `0009`.**

```sql
-- depends: 0008_views

CREATE TABLE IF NOT EXISTS regulatory_events (
    event_id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    title TEXT NOT NULL,
    body TEXT,
    symbols TEXT[] NOT NULL DEFAULT '{}',
    parsed_kind TEXT NOT NULL DEFAULT 'other',
    UNIQUE (source, url)
);

CREATE INDEX idx_reg_published ON regulatory_events(published_at DESC);
CREATE INDEX idx_reg_symbols ON regulatory_events USING GIN(symbols);
```

**Migration `0010`.**

```sql
-- depends: 0009_regulatory_events

CREATE TABLE IF NOT EXISTS decisions (
    decision_id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    kind TEXT NOT NULL,  -- buy | sell | hold | watch
    symbol TEXT NOT NULL REFERENCES securities(symbol),
    qty NUMERIC(18,6),
    rationale TEXT NOT NULL,
    snapshot JSONB NOT NULL,  -- signal, regime, top SHAP at decision time
    outcome JSONB
);

CREATE INDEX idx_decisions_symbol ON decisions(symbol, created_at DESC);
```

**Claude Code prompts.**

1. "Apply migrations 0009 and 0010. Implement `src/asxos/ingest/regulatory.py` with three sources: ASX Markets Announcements JSON, ATO RSS, Treasury RSS. UPSERT on (source, url). Symbol regex from title+body."
2. "Implement `src/asxos/jobs/ingest_regulatory.py` wrapping the three sources. Parser classifies kind via 20-line keyword heuristic."
3. "Add `asx journal add <symbol> <kind> <qty> '<rationale>'` to the CLI: pulls today's signal for the symbol, captures the JSONB snapshot, inserts. `asx journal list` shows the last 30 days. `asx journal review` flags decisions older than 60 days with NULL outcome."

**Verification.**
```bash
make ingest-regulatory
psql $DATABASE_URL -c "SELECT COUNT(*) FROM regulatory_events WHERE fetched_at > NOW() - INTERVAL '1 day';"
asx journal add BHP.AU buy 100 'thesis: signal BUY, regime bull, CGT-eligible'
asx journal list
asx journal review
```

**Commit.** `feat(M10): regulatory ingestion + decisions journal`

**Cancellation.** Cancel Render `asx-daily-announcements`.

### M11 — Morning brief, end-to-end usable workflow

**Recap.** Brief composer assembles signals-changed, regime, tax actions, regulatory hits-on-holdings into ~200-word HTML, sent via Resend at 07:00 Sydney each weekday.

**Files.**
- `src/asxos/brief/compose.py`
- `src/asxos/brief/email.py`
- `src/asxos/brief/templates/brief.html.j2`
- `src/asxos/jobs/compose_brief.py`
- `tests/test_brief_compose.py`

**Code shape — `src/asxos/brief/compose.py`.**

```python
"""Compose the morning brief."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import jinja2

from asxos.db import pool


@dataclass
class BriefData:
    as_of: date
    regime: str
    signal_changes: list[dict]    # symbol, old_label, new_label, top_shap
    tax_actions: list[dict]       # symbol, action_kind, threshold_date, detail
    regulatory_hits: list[dict]   # event for each holding
    job_failures: list[dict]      # job_name, error excerpt

    @property
    def has_failures(self) -> bool:
        return bool(self.job_failures)


async def collect(as_of: date) -> BriefData:
    async with pool().acquire() as conn:
        regime = await conn.fetchval(
            "SELECT regime FROM signals WHERE as_of = $1 LIMIT 1", as_of
        ) or "neutral"
        signal_changes = await conn.fetch("""
            WITH today AS (SELECT symbol, signal_label, shap FROM signals s
                JOIN current_holdings h USING (symbol) WHERE s.as_of = $1),
            yesterday AS (SELECT symbol, signal_label FROM signals
                WHERE as_of = $1 - INTERVAL '1 day')
            SELECT t.symbol, y.signal_label AS old_label, t.signal_label AS new_label, t.shap
            FROM today t LEFT JOIN yesterday y USING (symbol)
            WHERE COALESCE(y.signal_label, '') <> t.signal_label
        """, as_of)
        # tax_actions, regulatory_hits, job_failures queries elided for brevity — fill in
        ...
    return BriefData(...)


def render_html(data: BriefData) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
    )
    return env.get_template("brief.html.j2").render(d=data)
```

**Claude Code prompts.**

1. "Implement `src/asxos/brief/compose.py`, `email.py`, and a minimal Jinja template `brief.html.j2`. Template sections in order: (1) failures banner if `d.has_failures`, (2) regime, (3) signal changes on holdings (table), (4) tax actions within 30 days, (5) regulatory events on holdings in last 24h. Keep total HTML under 200 words of prose."
2. "Implement `src/asxos/brief/email.py` using `resend` SDK. From: BRIEF_FROM_EMAIL. To: BRIEF_TO_EMAIL. Subject: 'asxos brief — YYYY-MM-DD'."
3. "Implement `src/asxos/jobs/compose_brief.py` that calls `collect()`, renders, sends, and also prints to stdout. Wrap in `run_job`."
4. "Write `tests/test_brief_compose.py` that uses a seeded test DB and asserts: (a) brief contains symbols from current_holdings; (b) regime is included; (c) failures banner present when a job_runs row has status='error' for today."

**Verification.**
```bash
make brief
# → email arrives in jamespcino@gmail.com
# → stdout shows the same HTML
```

**Commit.** `feat(M11): morning brief composer and Resend dispatch`

**Cancellation.** Cancel Render `asx-send-digests`. Cancel Render `asx-portfolio-api` (after one week of confirmed brief delivery).

### M12 — Production deploy, scheduled crons running (revised: MCP audit)

**Recap.** Deploy to Render and Supabase as set up in Part 3. Eight cron services (seven jobs plus the daily irreplaceable-tables backup) + one web service are defined in `render.yaml` and auto-deployed from `main` via Render's GitHub integration. The DIY backup (Part 3.6) replaces the previous nightly B2 dump and Supabase Pro PITR. Healthchecks.io pings on every cron — emitted from inside each Python job via curl.

**Note on the original Hetzner/systemd plan.** The unit-file approach, `scripts/deploy.sh` (rsync + systemctl), `scripts/backup.sh` (rclone to B2), and the Tailscale-gated VPS plan documented below are obsolete after the MCP audit in Parts 2 and 3. They are retained in the document as a record of the alternative architecture but should not be implemented. The Render-and-Supabase path is described in Part 8.4 (drift discipline) and Part 8.5 (deploy loop). For M12, the deliverables are: a `render.yaml` with one web service `asxos-api` and eight cron services (sync-prices, sync-fundamentals, generate-signals, ingest-regulatory, compose-brief, retrain-model-a, sync-universe, backup-irreplaceable), the production env vars uploaded via `mcp__render__update_environment_variables` (including `BACKUP_GITHUB_TOKEN`), and `/check-drift` passing post-deploy. The backup cron runs `scripts/backup_irreplaceable.sh` daily at 23:00 AET — see Part 3.6 for the script behaviour and Appendix C for the cron entry. The Healthchecks pings are issued from inside each job's Python entry point with `httpx.get(settings.hc_<job>)` at the success and failure points respectively. No systemd, no SSH, no rclone, no B2.

**Files.**
- `deploy/timers/asxos-sync-prices.{service,timer}`
- `deploy/timers/asxos-sync-fundamentals.{service,timer}`
- `deploy/timers/asxos-generate-signals.{service,timer}`
- `deploy/timers/asxos-ingest-regulatory.{service,timer}`
- `deploy/timers/asxos-compose-brief.{service,timer}`
- `deploy/timers/asxos-retrain-model-a.{service,timer}`
- `deploy/timers/asxos-backup.{service,timer}`
- `deploy/asxos-api.service`
- `scripts/deploy.sh`
- `scripts/backup.sh`

**Unit file template — `deploy/timers/asxos-sync-prices.service`.**

```ini
[Unit]
Description=asxos sync-prices job
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=asxos
Group=asxos
WorkingDirectory=/opt/asxos
EnvironmentFile=/etc/asxos/env
ExecStart=/opt/asxos/.venv/bin/python -m asxos.jobs.sync_prices
StandardOutput=journal
StandardError=journal
OnFailure=asxos-failure-alert@%n.service

[Install]
WantedBy=multi-user.target
```

**`deploy/timers/asxos-sync-prices.timer`.**

```ini
[Unit]
Description=Run asxos sync-prices at 06:30 AET weekdays

[Timer]
OnCalendar=Mon..Fri *-*-* 06:30:00 Australia/Sydney
RandomizedDelaySec=60
Persistent=true
Unit=asxos-sync-prices.service

[Install]
WantedBy=timers.target
```

**`deploy/timers/asxos-sync-fundamentals.service` / `.timer`** — same pattern, runs daily at 04:00 AET, command `python -m asxos.jobs.sync_fundamentals`. (Daily-cadence for the EODHD fundamentals call; UPSERT means only changed rows are written.)

**`deploy/timers/asxos-generate-signals.service` / `.timer`** — runs 06:50 AET weekdays, command `python -m asxos.jobs.generate_signals`.

**`deploy/timers/asxos-ingest-regulatory.service` / `.timer`** — runs 06:55 AET daily, command `python -m asxos.jobs.ingest_regulatory`.

**`deploy/timers/asxos-compose-brief.service` / `.timer`** — runs 07:00 AET weekdays, command `python -m asxos.jobs.compose_brief`.

**`deploy/timers/asxos-retrain-model-a.service` / `.timer`** — runs Sundays 02:00 AET, command `python -m asxos.jobs.retrain_model_a`.

**`deploy/timers/asxos-backup.service` / `.timer`** — runs daily 23:30 AET, command `/opt/asxos/scripts/backup.sh`.

**API unit — `deploy/asxos-api.service`.**

```ini
[Unit]
Description=asxos FastAPI service
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=simple
User=asxos
Group=asxos
WorkingDirectory=/opt/asxos
EnvironmentFile=/etc/asxos/env
ExecStart=/opt/asxos/.venv/bin/uvicorn asxos.api.main:app --host 127.0.0.1 --port 8788
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**`scripts/backup.sh`.**

```bash
#!/usr/bin/env bash
set -euo pipefail

DATE=$(date +%Y-%m-%d)
DUMP=/var/backups/asxos/asxos-${DATE}.sql.gz
docker exec -t $(docker compose -f /opt/asxos/docker-compose.yml ps -q postgres) \
    pg_dump -U asxos asxos | gzip > "$DUMP"
rclone copy "$DUMP" b2:asxos-backups/ --quiet
# Retain locally: 7 days
find /var/backups/asxos -name "asxos-*.sql.gz" -mtime +7 -delete
curl -fsS "${HEALTHCHECK_URL_BACKUP:-https://hc-ping.com/00000000-0000-0000-0000-000000000000}" >/dev/null || true
```

**`scripts/deploy.sh`.**

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST="${ASXOS_HOST:-asxos@asxos-prod}"
APP_DIR="/opt/asxos"
SYSTEMD_DIR="/etc/systemd/system"

# 1. Sync code
rsync -azP --delete \
    --exclude '.venv' --exclude 'data' --exclude '.env' --exclude '.git' \
    ./ "$HOST:$APP_DIR/"

# 2. Sync env file if local has one explicitly for deploy
if [ -f deploy/env.production ]; then
    rsync deploy/env.production "$HOST:/etc/asxos/env"
    ssh "$HOST" "sudo chmod 640 /etc/asxos/env && sudo chown root:asxos /etc/asxos/env"
fi

# 3. Build venv on remote
ssh "$HOST" "cd $APP_DIR && python3.12 -m venv .venv && .venv/bin/pip install -e ."

# 4. Apply migrations
ssh "$HOST" "cd $APP_DIR && .venv/bin/python scripts/migrate.py"

# 5. Sync unit files
ssh "$HOST" "sudo cp $APP_DIR/deploy/asxos-api.service $SYSTEMD_DIR/"
ssh "$HOST" "sudo cp $APP_DIR/deploy/timers/*.service $APP_DIR/deploy/timers/*.timer $SYSTEMD_DIR/"

# 6. Reload + enable
ssh "$HOST" "sudo systemctl daemon-reload"
ssh "$HOST" "sudo systemctl enable --now asxos-api.service"
ssh "$HOST" "sudo systemctl enable --now asxos-sync-prices.timer asxos-sync-fundamentals.timer asxos-generate-signals.timer asxos-ingest-regulatory.timer asxos-compose-brief.timer asxos-retrain-model-a.timer asxos-backup.timer"

# 7. Status
ssh "$HOST" "systemctl list-timers 'asxos-*' --no-pager"
echo "Deploy complete."
```

**Claude Code prompts.**

1. "Create the seven service+timer pairs in `deploy/timers/` per BUILD_GUIDE.md M12. Use the sync-prices files as template; vary OnCalendar and command per job."
2. "Implement `scripts/deploy.sh` and `scripts/backup.sh` per BUILD_GUIDE.md M12. Make both executable."
3. "Update the README quickstart to include the production deploy section: prerequisites (Part 3 done), then `make deploy`."

**Verification.**
```bash
make deploy
# → "Deploy complete." + timer list showing seven timers
ssh asxos@asxos-prod 'systemctl list-timers asxos-*'
ssh asxos@asxos-prod 'systemctl status asxos-api'
# Wait until next 07:00 AET — verify email arrives
# Day after — verify rclone has the dump:
ssh asxos@asxos-prod 'rclone ls b2:asxos-backups/ | tail -3'
```

**Commit.** `feat(M12): production VPS deploy, systemd timers, B2 backups`

After M12 is verified for one week of clean brief delivery, cancel the remaining Render services and the Supabase project.

---

## Part 6 — Claude Code workflow

This is how to drive the build with Claude Code as the primary IDE.

### 6.1 Bring forward `.claude/`

The `.claude/commands/` (20 markdown files) and `.claude/rules/` (5 auto-activating rule files) from the old repo are accumulated working agreement. They migrate verbatim. Step is in Part 4.15. After copying, audit each one and delete those that reference dropped features (multi-user, subscriptions, semantic memory, etc.). Concrete deletions to consider:

- Anything mentioning `user_id`, `user_holdings`, `user_portfolios` — these patterns are gone
- Anything mentioning Vercel, Supabase RLS, Render multi-cron orchestration
- Anything mentioning Sentry, alerts, notifications
- Keep: `/signal-pipeline`, `/tax-optimise`, `/regime-detection`, `/error-triage`, `/model-experiment`, `/quality-check`, `/discover`, `/sprint-plan`. These map cleanly onto the new world.

### 6.2 New `CLAUDE.md` at the repo root

The old CLAUDE.md was ~400 lines of multi-tenant SaaS conventions. The new one is much shorter and reflects the no's from `phase-4-architecture-system-architect.md`.

```markdown
# asxos — Claude Code

> Single-user personal investment intelligence OS. Render + Supabase, MCP-driven ops, no frontend.
> Architecture: docs/rebuild/phase-4-architecture-system-architect.md
> Build guide: docs/rebuild/BUILD_GUIDE.md (Part 8 for MCP ops playbook)

## Stack

| Layer | Tech | Where |
|-------|------|-------|
| API | FastAPI on Render Starter (`asxos-api`) | `src/asxos/api/` |
| Jobs | Render cron services, `python -m asxos.jobs.X` | `src/asxos/jobs/` |
| DB | Supabase Postgres 16 (Pro) | `mcp__supabase__*` |
| ML | LightGBM .pkl + in-process cache | `src/asxos/domain/models/` |
| CLI | Typer (`asx ...`) | `src/asxos/cli/` |
| Brief | Resend HTML email at 07:00 AET | `src/asxos/brief/` |
| Ops control plane | Claude Code + Render MCP + Supabase MCP | Part 8 of BUILD_GUIDE.md |

## Conventions

- **Hard-fail startup.** `lifespan` must verify Postgres, migrations current, EODHD key, active model loads, writable dirs. Any failure raises and exits 1. No `logger.warning() and continue`.
- **Numpy adapters.** Registered once in `src/asxos/db.py` at module import. Never re-register in jobs.
- **Money.** `NUMERIC(18,6)` for prices. `NUMERIC(18,4)` for AUD amounts. `NUMERIC(8,6)` for ratios and probabilities. Use `Decimal` in Python, never `float`, for tax math.
- **Auth.** Single bearer token (`ASXOS_API_TOKEN`) on every non-`/health` route. No JWT, no users table.
- **No frontend.** Email + CLI only.
- **No event bus.** Two callers share `domain/` directly.
- **No ORM.** asyncpg directly. `$1, $2, ...` parameter syntax.
- **Pydantic.** API request/response only. Domain functions take primitives.
- **Soft deletes.** None. `disposed_at` on `holding_lots` is journal, not soft delete.
- **Migrations.** Plain `.sql` in `migrations/`. Always applied via `mcp__supabase__apply_migration` (in both production and Supabase preview branches). No migration runner script. Never modify an applied migration. Add a new one.
- **Infrastructure changes.** Render services and crons are defined in `render.yaml`. Env vars are set via `mcp__render__update_environment_variables`. Never edit anything in the Render dashboard. `make check-drift` enforces this.
- **Tests.** Cap ~400. Skip the 80% coverage rule. Each test must catch a real bug or boundary; performative tests get deleted.
- **Commits.** `feat(M5): ...`, `fix(M7): ...`, etc. Reference the milestone in parens.

## Things that are not here on purpose

Redis, Celery, ORM, Sentry, semantic memory, event bus, reverse proxy, frontend, multi-user auth, second user, model B/C/D, archetype clustering, notification routing, multi-environment config, RLS, subscriptions, alerts, VPS, SSH, systemd, Tailscale, Docker on a host, rclone, B2.

See "After M12" in `phase-5-milestones.md` for the full list.
```

### 6.3 `.claude/settings.json` permissions

Auto-allow safe commands so Claude Code does not interrupt with permission prompts mid-flight. Place this at `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(make *)",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(mypy *)",
      "Bash(psql *)",
      "Bash(docker compose *)",
      "Bash(git status)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git show*)",
      "Bash(git branch*)",
      "Bash(git checkout -b *)",
      "Bash(git add *)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(grep *)",
      "Bash(find * -type f)",
      "Bash(curl -s http://127.0.0.1:8788/*)",
      "Bash(python -m asxos.jobs.*)",
      "Bash(asx *)",
      "Bash(jq *)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(sudo *)"
    ]
  }
}
```

### 6.4 Agent routing per milestone

| Milestone | Primary agent | Why |
|-----------|---------------|-----|
| M1 | `backend-architect` | API lifespan + fail-fast pattern |
| M2 | `backend-architect` | EODHD client shape, JobMonitor port |
| M3 | `backend-architect` | universe loop, bulk endpoint integration |
| M4 | `backend-architect` | fundamentals pattern, partial-failure tolerance |
| M5 | `ml-engineer` | feature engine port, parity test |
| M6 | `ml-engineer` | model loading, SHAP integration |
| M7 | `ml-engineer` + `backend-architect` | ML inference + persistence layer split |
| M8 | `backend-architect` | pure-function tax design, lot selection |
| M9 | `ml-engineer` | retraining, walk-forward |
| M10 | `backend-architect` | regulatory scraping, journal |
| M11 | `backend-architect` | brief composition, email |
| M12 | `system-architect` | systemd, deploy, backups |

Use `Explore` for "where in the old repo is X" questions before starting any milestone that ports old code (M2 JobMonitor, M5 feature engine, M9 retraining). The old code is the reference; the new code is the clean port.

### 6.5 TDD discipline

Write the test in the same Claude Code session as the implementation. The pattern per milestone:

1. Open a session, restate the milestone goal (one sentence).
2. Sketch the test first — what shape of input + expected output captures the milestone's definition of done.
3. Implement. Run the test. Iterate until green.
4. Add boundary tests for the canonical failure modes (M5: byte-equal recompute; M7: threshold boundaries; M8: day-365 CGT; M9: TimeSeriesSplit).
5. Commit.

### 6.6 Commit cadence and branches

One commit per milestone minimum. More if there's a natural seam (e.g. M5 ports each feature group as a separate commit, then one commit for the FeatureEngine orchestrator). Branch naming:

```
milestone/M1-bootstrap
milestone/M2-eodhd-prices
...
milestone/M12-vps-deploy
```

After each milestone: merge to `main`, tag `milestone-MN`. The tag is the rollback point.

### 6.7 Slash command mapping

- `/signal-pipeline` — for any work touching M5, M6, M7, M9
- `/tax-optimise` — for M8
- `/regime-detection` — for the regime classifier in M7
- `/model-experiment` — for M9 retraining
- `/error-triage` — for any L2 production issue post-M12
- `/quality-check` — before every commit
- `/discover` — only if a milestone's definition of done is unclear; otherwise skip, the build guide is the spec

### 6.8 Handling blockers

- **L1 (lint, format, type error).** `/quality-check --fix`. Commit. Move on.
- **L2 (logic bug, failing test).** `/error-triage`. Implement fix. Re-test. Commit.
- **L3 (data corruption, can't reproduce, infra outage).** Pause. Surface in a Claude Code session with full context. Do not apply a fix without understanding the root cause.

For L3 specifically, the new system's structural defences (hard-fail lifespan, dependency check at job entry, `/health` 503 on stale signals) mean an L3 should be rare. If one appears, treat the structural defence as load-bearing — fix the cause, not the symptom.

---

## Part 7 — Cost summary and timeline (revised: MCP audit)

### Cost comparison

| Item | Current monthly | New monthly | Delta |
|------|------------------|-------------|-------|
| Render web API (Starter) | USD 7 | USD 7 (reused, renamed `asxos-api`) | 0 |
| Render Starter crons (8 services) | USD 56 | USD 0 (all free-tier crons) | -USD 56 |
| Render free crons (22 services) | USD 0 | USD 0 (8 reused, 22+ cancelled) | 0 |
| Vercel | USD 0–20 | — | -USD 10 (midpoint) |
| Supabase Pro | USD 25 | USD 0 (downgraded to free tier at M1) | -USD 25 |
| Voyage AI | ~USD 5 | — | -USD 5 |
| Healthchecks.io | — | USD 0 (free tier) | 0 |
| Resend | USD 0 | USD 0 (free tier) | 0 |
| EODHD (unchanged) | USD 20 | USD 20 | 0 |
| FRED (unchanged, free) | USD 0 | USD 0 | 0 |
| Anthropic (Claude Code) | variable | variable | 0 |
| **Total** | **~USD 130** | **~USD 27** | **-USD 103** |

The headline number: about USD 103/month saved on infrastructure, leaving Render Starter + EODHD as the two non-trivial recurring application costs (Supabase free tier at USD 0 + the DIY GitHub-repo backup of irreplaceable tables). The earlier Hetzner plan would have saved roughly USD 2 more, but at the cost of operability — every "check what happened" loop would have required SSH plus `journalctl` plus rclone plus `psql`, none of which James can comfortably drive without Claude Code holding his hand. The MCP-driven stack is the right shape for a non-technical operator running a personal system. Re-evaluate Supabase Pro upgrade when DB size approaches 500MB, estimated 6–12 months in.

### Calendar timeline

- **Weeks 1–2.** Part 3 VPS setup in parallel with M1 (repo bootstrap).
- **Weeks 2–3.** M2, M3, M4 (ingestion).
- **Weeks 3–5.** M5 (feature engine — longest milestone).
- **Weeks 5–6.** M6, M7 (model + signals).
- **Weeks 6–7.** M8 (holdings + tax).
- **Weeks 7–8.** M9 (retraining), M10 (regulatory + journal).
- **Week 8.** M11 (brief).
- **Weeks 9–10.** M12 (production VPS) + observation week.

Total: 8–10 weeks calendar. First useful morning brief by week 8. Stable production by week 10.

### Temptations to resist (verbatim from phase-5-milestones.md "After M12")

- No frontend until M12 has been operational for at least a month.
- No second user.
- No additional models in the ensemble.
- No semantic memory, no Voyage embeddings, no Anthropic SDK integration in the app.
- No archetype clustering, no surrogate trees.
- No alternative data sources beyond EODHD + FRED + the three regulatory feeds.
- No backtest UI.
- No model B/C/D feature work.
- No property module.
- No multi-portfolio support.
- No web auth experiment.
- No CI investment beyond the three-job workflow (ruff, mypy, pytest).
- No premature schema additions.
- No "let's port the coach" or "let's bring back the assistant."

These are not preferences. They are the difference between a system that runs and a system that does not.

---

## Part 8 — MCP and Claude Code service control (added: MCP audit)

This is the operations manual. Read it before M1 and again before M12. The architectural flips in Parts 1–3 (Render instead of Hetzner, Supabase instead of vanilla Docker Postgres) are only worth the extra USD 27/month if the day-to-day operating loop is actually MCP-driven; this section is how that loop runs.

### 8.1 The operating philosophy

Every routine operation on the asxos system is driven by Claude Code, either through an MCP server or through Bash with a documented API call. James does not click in vendor dashboards as a routine operation. The dashboard is reserved for two things: the initial account setup steps documented in Part 3, and emergency intervention when an MCP itself is broken or unavailable. Everything in between — checking on overnight cron runs, querying the database, restarting a service, rotating an env var, looking at logs, triggering a manual deploy, sending a test email — is a single Claude Code prompt.

This changes how the system is operated, not what it does. The morning brief still arrives at 7am Sydney time. The signal pipeline still runs on the same schedule. The retraining job still flips the active model version when its validation gates pass. The difference is what happens when something goes wrong. In the old system the failure-recovery loop was: notice the brief did not arrive, log in to Render dashboard, find the cron service, scroll its logs, copy-paste an error into a Claude Code session, ask for a diagnosis, hand-edit env vars in the dashboard, manually trigger a redeploy. In the new system the loop is: notice the brief did not arrive, open Claude Code, type "the brief did not arrive — find out why and fix it if you can," and watch Claude Code call `mcp__render__list_logs`, then `mcp__supabase__execute_sql` against `job_runs`, then `mcp__render__update_environment_variables` if it identifies a missing variable, then `mcp__render__list_deploys` to confirm a new deploy was queued.

The discipline is: when in doubt, look up the MCP. When the MCP does not exist, look up the API call. Only fall back to the dashboard when the API itself is down.

### 8.2 MCP-per-service inventory

This is the minimum viable set of MCPs for the new system. Each subsection covers installation, the env vars the MCP needs, the most useful tool names, and one canonical Claude Code prompt that demonstrates its use.

#### Render MCP

> **SUPERSEDED (2026-07-11): there is no Render MCP in this project.** Render is managed via
> its **REST API** (`https://api.render.com/v1`, bearer `$RENDER_API_KEY`) from Bash/curl. The
> `mcp__render__*` tool names below and throughout this section do not exist — read every
> `mcp__render__X` as the equivalent REST call (`list_services`→`GET /v1/services`,
> `list_logs`→`GET /v1/logs`, `list_deploys`→`GET /v1/services/{id}/deploys`,
> `update_environment_variables`→`PUT /v1/services/{id}/env-vars`). CLAUDE.md #2 and
> `.claude/commands/*` carry the corrected form. This section is retained as historical context.

**Installation.** The Render MCP is added to Claude Code via the MCP registry. From a terminal:

```bash
claude mcp add render --transport http https://mcp.render.com/mcp \
  --header "Authorization: Bearer ${RENDER_API_KEY}"
```

Generate the Render API key at https://dashboard.render.com → Account Settings → API Keys. Record it as `RENDER_API_KEY` in the shell environment Claude Code inherits.

**Verification.** `claude mcp list` shows the render MCP as `connected`. In a session: `/mcp` lists active MCPs.

**Most-useful tools for daily ops.**

| Tool | Purpose |
|------|---------|
| `mcp__render__list_services` | What services exist under the workspace |
| `mcp__render__get_service` | Full configuration of one service including env vars (redacted) |
| `mcp__render__list_logs` | Time-bounded log query with regex filtering — primary debugging surface |
| `mcp__render__list_deploys` | Deploy history; identify when a regression was introduced |
| `mcp__render__get_deploy` | Status of a specific deploy (in_progress / live / failed) |
| `mcp__render__update_environment_variables` | The only sanctioned way to change env vars in the new system |
| `mcp__render__update_cron_job` | Change a cron schedule or command without touching the dashboard |
| `mcp__render__query_render_postgres` | Direct read-only SQL against the Postgres if a Render Postgres is used (not used here; Supabase is the DB) |

**Canonical prompt.**

> "Use the Render MCP to fetch the last 24 hours of logs for the `asxos-generate-signals` cron service. Filter to entries matching `ERROR|Exception|Traceback`. Summarise any failures and propose a fix; do not change anything yet."

#### Supabase MCP

**Installation.** Already installed in James's Claude Code config from prior work. If reinstalling:

```bash
claude mcp add supabase --transport stdio \
  -- npx -y @supabase/mcp-server-supabase@latest \
  --access-token "${SUPABASE_ACCESS_TOKEN}"
```

Generate the access token at https://supabase.com/dashboard/account/tokens. Record as `SUPABASE_ACCESS_TOKEN`.

**Most-useful tools for daily ops.**

| Tool | Purpose |
|------|---------|
| `mcp__supabase__list_projects` | List Supabase projects (sanity check on which env you are pointing at) |
| `mcp__supabase__list_tables` | What tables exist in the asxos schema |
| `mcp__supabase__execute_sql` | Read-only SQL against the project; the primary inspection tool |
| `mcp__supabase__apply_migration` | Apply a versioned migration. The only migration path — there is no runner script. |
| `mcp__supabase__create_branch` | Create a Supabase preview branch from main; used for local dev testing of migrations before applying to production |
| `mcp__supabase__list_migrations` | History of applied migrations |
| `mcp__supabase__get_logs` | Database logs (slow query, connection errors, etc.) |
| `mcp__supabase__get_advisors` | Schema/security advisors — surfaces missing indexes and RLS issues |
| `mcp__supabase__create_branch` | Spin up a temporary preview branch for testing schema changes |

**Canonical prompt.**

> "Use the Supabase MCP to run this SQL against the asxos project: `SELECT job_name, MAX(started_at), status FROM job_runs WHERE started_at > NOW() - INTERVAL '36 hours' GROUP BY job_name, status ORDER BY job_name`. Format the result as a table; flag any job_name where the most recent status is not 'success'."

#### GitHub via `gh` CLI

**Installation.** Preinstalled on James's workstation. Verify with `gh auth status`. No MCP needed — Claude Code calls `gh` directly through Bash.

**Most-useful invocations for daily ops.**

| Command | Purpose |
|---------|---------|
| `gh pr create` | Open a pull request |
| `gh pr checks` | CI status for the current PR |
| `gh run list --workflow=ci.yml` | Recent CI runs |
| `gh run view <id> --log` | Read a CI log when something failed |
| `gh issue create` | File a follow-up |

**Canonical prompt.**

> "Run `gh run list --workflow=ci.yml --limit 5` and tell me whether the latest run on `main` is green. If it is red, fetch the log for the failed job and propose a fix."

#### Vercel MCP — remove at M1

James has the Vercel MCP installed from the old project. The new system has no frontend. Remove it at M1 so it does not clutter `/mcp`:

```bash
claude mcp remove vercel
```

### 8.3 Services without MCPs

Three services in the new stack have no MCP: Healthchecks.io, Resend, and EODHD. All three have simple REST APIs that Claude Code can call via Bash + curl. The canonical invocations are documented here so James never has to write them himself.

#### Healthchecks.io

The entire product is a single ping URL per check. A successful ping is `curl -fsS https://hc-ping.com/<uuid>`. A failure ping appends `/fail`. The cron jobs ping these URLs at the end of every run — that is configured in the job Python code, not on Healthchecks.io.

To test pings from Claude Code:

> "Send a success ping to my Healthchecks.io `compose-brief` URL: `curl -fsS \"${HEALTHCHECK_URL_COMPOSE_BRIEF}\"`. Then read the most recent ping status from `https://healthchecks.io/api/v3/checks/` using the API key in `HEALTHCHECKS_API_KEY` and report the last-seen timestamp."

The Healthchecks.io API key lives in `~/.config/asxos/secrets.env`, sourced before launching Claude Code (`source ~/.config/asxos/secrets.env`). Same for `RESEND_API_KEY` and `EODHD_API_KEY`.

#### Resend

To send a test email:

> "Use curl to send a test brief via Resend. POST to `https://api.resend.com/emails` with header `Authorization: Bearer ${RESEND_API_KEY}` and JSON body `{\"from\": \"brief@asxos.<domain>\", \"to\": \"jamespcino@gmail.com\", \"subject\": \"test from claude code\", \"html\": \"<p>If you got this, Resend is working.</p>\"}`. Report the response status and any error message."

The brief job in M11 wraps this same call in the `resend` Python SDK; the curl form is for diagnosis when the brief did not arrive and Claude Code needs to determine whether the failure is in the job code or in Resend itself.

#### EODHD

EODHD is read-only from the system's perspective: the ingest job pulls from it. Claude Code rarely needs to hit it directly. When it does — usually to check that a new symbol exists, or to compare what EODHD returns against what landed in `prices` — the canonical curl is:

> "Run `curl -fsS \"https://eodhd.com/api/eod/BHP.AU?api_token=${EODHD_API_KEY}&fmt=json&from=2026-05-01&period=d\" | jq '.[-3:]'` and compare those three rows to what the Supabase MCP returns for the same symbol/date range from the `prices` table."

### 8.4 The drift-prevention discipline

The old system died of drift between `render.yaml` and Render's actual deployed state. The structural fix is `make check-drift` — a target that uses the Render MCP to fetch the live service list, cron list, and env-var keys, diffs them against `render.yaml` and `.env.example`, and reports any divergence. The rule is: any change to Render configuration is made via `render.yaml` + `git push` (which triggers Render auto-deploy), never via the Render dashboard. Drift becomes detectable, and detection happens automatically after every deploy.

The drift check itself is a Claude Code slash command. Save the following at `.claude/commands/check-drift.md`:

```markdown
# /check-drift

Compare actual deployed state to `render.yaml` and `.env.example`.

## Steps

1. Use `mcp__render__list_services` filtered to the asxos workspace.
2. For each service, call `mcp__render__get_service` and extract: name, type (web/cron), env, plan, autoDeployTrigger.
3. For each cron service, extract the schedule and command.
4. For each service, list env-var keys (values redacted).
5. Read `render.yaml` from the repo root and parse the same fields.
6. Read `.env.example` and extract the list of expected env var keys.
7. Diff:
   - Services in Render but not in render.yaml → "DRIFT: extra service".
   - Services in render.yaml but not in Render → "DRIFT: missing service".
   - Schedule mismatch on any cron → "DRIFT: schedule".
   - Command mismatch on any cron → "DRIFT: command".
   - Env-var keys in Render but not in .env.example → "DRIFT: extra var".
   - Env-var keys in .env.example marked required but missing in Render → "DRIFT: missing var".
8. Report PASS or list every drift found.
```

Run `/check-drift` after every deploy. Include it in the M12 verification step.

### 8.5 Daily and weekly ops playbook

These are the recurring loops James will actually run on the system. Each is one Claude Code prompt.

**Every morning (~7:30am AET, after the brief arrives).** "How did last night's pipeline go?" Claude Code will use `mcp__render__list_deploys` to confirm no rogue deploys overnight, `mcp__supabase__execute_sql` against `job_runs` to confirm all six jobs ran and finished green, and report any anomalies.

**When the brief does not arrive.** "The brief did not arrive this morning. What broke?" Claude Code will: (1) check Healthchecks.io for the last successful ping of `compose-brief`; (2) `mcp__render__list_logs` on `asxos-compose-brief` for the last run; (3) `mcp__supabase__execute_sql` on `job_runs WHERE job_name='compose-brief' ORDER BY started_at DESC LIMIT 5`. Output is a one-line diagnosis and a proposed fix. If the fix is a Render env var change, Claude Code asks first before applying it; if the fix is in code, it opens a branch and a PR via `gh`.

**Weekly Sunday review.** "Anything I should rebalance this week?" Claude Code queries `current_holdings` joined to the latest `signals` row per symbol, runs the tax-action CLI (`asx tax-view`), and summarises in the form: which holdings have signal-flipped this week, which lots cross the 12-month CGT boundary in the next 30 days, and any unusually-large SHAP factor movements.

**Monthly retraining check.** "Time to look at retraining." Claude Code triggers the retrain via `mcp__render__update_cron_job` to set the schedule to "in 1 minute," waits for completion via `mcp__render__list_logs`, restores the original Sunday schedule, and reports the validation gate results from the `model_versions` table. If the gate passed and the new version is active, the brief will use it the next morning automatically.

**When deploying a new feature.** "Deploy the current branch." Claude Code: confirms the branch is merged to `main`, watches `mcp__render__list_deploys` for the auto-deploy to fire, monitors until `status=live`, runs `/check-drift`, then runs an end-to-end sanity check (`asx ask BHP.AU` or equivalent) against the live API.

**When something looks wrong but you cannot articulate it.** "Something feels off — give me a system health summary." Claude Code runs the equivalent of the 5-point smoke test from the old workflow: Render service status, Supabase reachability, max(`prices.dt`), max(`signals.as_of`), last successful Healthchecks ping for each of the six jobs. Output is a paragraph plus a status table.

### 8.6 Bootstrapping the MCPs

The MCPs are configured in `~/.claude/settings.json` on James's workstation. The relevant section after Part 3 is complete:

```jsonc
{
  "mcpServers": {
    "render": {
      "type": "http",
      "url": "https://mcp.render.com/mcp",
      "headers": { "Authorization": "Bearer ${RENDER_API_KEY}" }
    },
    "supabase": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--access-token",
        "${SUPABASE_ACCESS_TOKEN}"
      ]
    }
  }
}
```

The env vars `RENDER_API_KEY` and `SUPABASE_ACCESS_TOKEN` come from `~/.config/asxos/secrets.env` which James `source`s before launching Claude Code. The Vercel MCP entry from the old project is removed at M1 (`claude mcp remove vercel`). Verify with `/mcp` inside any Claude Code session — both render and supabase should show as `connected`. If either fails to connect: check the env var is present (`echo $RENDER_API_KEY | head -c 5`), check the API key has not been rotated, and as a last resort run `claude mcp remove <name>` followed by `claude mcp add ...` again.

### 8.7 Driving Claude Code from off-machine

James asked how to use `/remote-control`. There is no built-in `/remote-control` command in Claude Code. The closest matches, in order of usefulness for asxos, are:

**Scheduled tasks (`mcp__scheduled-tasks`).** This MCP is in James's config and lets him schedule a Claude Code agent to run on cron. Example: "Every weekday at 6:30am AET, run the prompt 'Check overnight job_runs in Supabase. If any job has status=error, send a one-line summary to my Gmail inbox via the Gmail MCP.'" The scheduled task fires server-side; James does not need his laptop open. Set up via `mcp__scheduled-tasks__create_scheduled_task` from a normal Claude Code session.

**claude.ai/code web interface.** Claude Code runs in browser at https://claude.ai/code, with the same MCPs configured. Useful for checking on the system from a phone or another machine. The `~/.claude/settings.json` config syncs automatically.

**Headless `claude -p "..."`.** For one-shot prompts that could be wired into a Render cron themselves: `claude -p "Use the Supabase MCP to check today's signal count and email me if it's below 1000"`. This is what you would use if you wanted Claude Code itself to act as a monitoring agent. For asxos, the scheduled-tasks MCP is the cleaner choice; reserve headless `claude -p` for ad-hoc shell scripts or one-time experiments.

In summary: there is no `/remote-control`, but the practical effect is achievable through `mcp__scheduled-tasks` for cron-style triggers and the claude.ai/code web UI for interactive ops from anywhere.

---

## Part 9 — Appendices

### Appendix A — Environment variable reference

| Variable | Required | Used by | Example | Notes |
|----------|----------|---------|---------|-------|
| DATABASE_URL | yes | API, all jobs | postgresql://asxos:xxx@127.0.0.1:5432/asxos | Local docker compose on dev; VPS-local on prod |
| EODHD_API_KEY | yes | ingest module | OEAH....EHX | Sole price source |
| RESEND_API_KEY | yes | brief module | re_xxx | Free tier sufficient |
| BRIEF_FROM_EMAIL | yes | brief module | brief@asxos.local | Must match verified Resend sender |
| BRIEF_TO_EMAIL | yes | brief module | jamespcino@gmail.com | The one recipient |
| FRED_API_KEY | no | macro feature group | xxx | Free; without it, macro features are NaN |
| ASXOS_MODELS_DIR | no | model cache | /opt/asxos/models | Defaults to ./models |
| ASXOS_DATA_DIR | no | ingest, brief | /opt/asxos/data | Defaults to ./data |
| ASXOS_TZ | no | timers, brief subject | Australia/Sydney | Default Australia/Sydney |
| ASXOS_API_HOST | no | api | 127.0.0.1 | Never 0.0.0.0 in production |
| ASXOS_API_PORT | no | api | 8788 | |
| HEALTHCHECK_URL_SYNC_PRICES | no | sync_prices job | https://hc-ping.com/uuid | Per-job |
| HEALTHCHECK_URL_SYNC_FUNDAMENTALS | no | sync_fundamentals | … | |
| HEALTHCHECK_URL_GENERATE_SIGNALS | no | generate_signals | … | |
| HEALTHCHECK_URL_INGEST_REGULATORY | no | ingest_regulatory | … | |
| HEALTHCHECK_URL_COMPOSE_BRIEF | no | compose_brief | … | |
| HEALTHCHECK_URL_RETRAIN_MODEL_A | no | retrain_model_a | … | |
| HEALTHCHECK_URL_BACKUP_IRREPLACEABLE | no | backup_irreplaceable job | … | Daily 23:00 AET cron |
| BACKUP_GITHUB_TOKEN | yes | backup_irreplaceable job | ghp_xxx | Fine-grained PAT, `Contents: RW` on asxos-backups repo only |
| BACKUP_REPO | yes | backup_irreplaceable job | jamespcino/asxos-backups | Private GitHub repo for DIY dumps |

### Appendix B — Database schema reference

| Table | PK | Notable columns | Indexes |
|-------|----|------|---------|
| securities | symbol | name, sector, currency, is_active, delisted_at | (is_active) WHERE is_active |
| prices | (symbol, dt) | open/high/low/close NUMERIC(18,6), adj_close, volume | (symbol, dt DESC) |
| fundamentals | (symbol, as_of) | pe_ratio, pb_ratio, eps, market_cap | (as_of DESC) |
| signals | (model_name, model_version, symbol, as_of) | prob_up, expected_return, signal_label, confidence, rank, regime, shap JSONB | (as_of DESC, signal_label), (symbol, as_of DESC), GIN(shap) |
| model_versions | (model_name, version) | trained_at, metrics JSONB, classifier_path, regressor_path, features_json_path, is_active | UNIQUE(model_name) WHERE is_active |
| holding_lots | lot_id BIGSERIAL | symbol, acquired_at, currency, qty, cost_per_unit_aud, fx_rate_at_acquisition, account_type, disposed_at | (symbol) WHERE disposed_at IS NULL |
| regulatory_events | event_id BIGSERIAL | source, url UNIQUE, published_at, title, body, symbols TEXT[], parsed_kind | (published_at DESC), GIN(symbols) |
| decisions | decision_id BIGSERIAL | kind, symbol, qty, rationale, snapshot JSONB, outcome JSONB | (symbol, created_at DESC) |
| job_runs | run_id BIGSERIAL | job_name, started_at, finished_at, status, rows_written, error, dependencies_ok | (job_name, started_at DESC) |
| supabase_migrations.schema_migrations | (version) | Supabase-managed; written to by `mcp__supabase__apply_migration` | n/a |

Views:
- `current_holdings` — aggregates `holding_lots` WHERE disposed_at IS NULL.
- `latest_signals_per_symbol` — most recent row per (model_name, symbol).
- `regulatory_events_today` — fetched_at >= today.

### Appendix C — systemd unit file reference

| Unit | Runs | Cadence | Command |
|------|------|---------|---------|
| asxos-api.service | continuous | continuous | uvicorn asxos.api.main:app |
| asxos-sync-prices.timer | weekdays 06:30 AET | Mon–Fri | python -m asxos.jobs.sync_prices |
| asxos-sync-fundamentals.timer | daily 04:00 AET | daily | python -m asxos.jobs.sync_fundamentals |
| asxos-generate-signals.timer | weekdays 06:50 AET | Mon–Fri | python -m asxos.jobs.generate_signals |
| asxos-ingest-regulatory.timer | daily 06:55 AET | daily | python -m asxos.jobs.ingest_regulatory |
| asxos-compose-brief.timer | weekdays 07:00 AET | Mon–Fri | python -m asxos.jobs.compose_brief |
| asxos-retrain-model-a.timer | Sundays 02:00 AET | weekly | python -m asxos.jobs.retrain_model_a |
| asxos-backup.timer | daily 23:30 AET | daily | /opt/asxos/scripts/backup.sh |

Commands for inspection:
- `systemctl list-timers 'asxos-*'`
- `systemctl status asxos-compose-brief.timer`
- `journalctl -u asxos-generate-signals.service -n 200 --no-pager`
- `journalctl -u 'asxos-*' --since '08:00' --until '09:00'`

---

End of build guide. Eight to ten weeks. Read M1 in Part 5 and start.
