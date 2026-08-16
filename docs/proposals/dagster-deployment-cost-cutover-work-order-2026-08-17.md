# Dagster deployment / cost / cutover work order — 2026-08-17

**Work order:** `P3-01` — F5's named prerequisite: *"Stage 1 must deliver the
deployment/cost/cutover work order first"* (`docs/product/roadmap-state.md:256`).
**Scope label:** `RENDER-RETIRE` (shared with `P1-03`), per `docs/product/roadmap-state.md`
defect #4.
**Authority chain:** Amendment B execute-to-completion chaining + the parallel-authorization
rider (James, 2026-08-17, `docs/product/roadmap-state.md:147-159`: SB1-01 ∥ P3-01 ∥ P2-04);
`arbi-red-team` vet PASS (conditional; both preconditions satisfied before branch).
**Status:** DRAFT — a proposal for James. Nothing in this document has been performed.
No account exists, no credential was created, nothing was installed, no schedule was touched.

Dagster is the **ruled** target scheduler (F5, `roadmap-state.md:256`). This work order does
not re-litigate that choice; it prices and sequences it.

---

## 0. Method and observation discipline

Per the execution plan's §2.3 recency rule
(`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md:110-113`):
every live claim below carries a source and an `observed_at`; unknowns are marked
`unavailable`. Derived figures are labelled **derived** and show their inputs.

- **Base SHA:** branch `claude/p3-01-dagster-work-order` from `origin/main` =
  `4c7406de8b559eadcd8d47aca984c8cbf0084736` (fetched `observed_at=2026-08-16T22:10Z`).
- **Repo observation window:** all `gh` CLI observations below were made read-only in the
  window `2026-08-16T22:12–22:25Z` (session anchor `date -u` → `2026-08-16T22:12:14Z`).
  This document is dated 2026-08-17 AEST; run timestamps are UTC.
- **Web observations:** public pricing/docs pages only, fetched read-only in the same window.
  **No vendor-interactive probing was performed**: no pricing API, no contact-sales, no trial,
  no signup, no benchmark. Pro/Enterprise tiers are "Contact Sales" and were therefore left
  `unavailable` by design.
- **Authoritative scheduler record:** `docs/product/scheduler-inventory-2026-08-13.md`
  ("the inventory"). This work order builds on it and does not restate it.

---

## 1. Fleet state as observed — the cutover's FROM state

Ten workflows exist in `.github/workflows/` (source: repo tree at base SHA,
`observed_at=2026-08-16T22:12Z`). Five are scheduled; four are event-driven CI
(`full-check`, `targeted-ml-tests`, `migration-integration`, `pr-review-agent`); one is
manual-only (`claude-execute`). **Only the five scheduled workflows are cutover subjects** —
CI and the manual harness are GitHub-native (they trigger on GitHub events) and stay put.

| Workflow | Cron (UTC) | Source (at base SHA) | Latest scheduled run observed | Result |
|---|---|---|---|---|
| `daily-brief.yml` | `30 20 * * 0-4` | `:39` | 2026-08-16T20:45:42Z | success |
| `us-positions.yml` | `30 21 * * 1-5` | `:18` | 2026-08-14T21:49:41Z | success |
| `pipeline-health.yml` | `0 22 * * *` | `:14` | 2026-08-15T22:24:43Z | **failure** (see 1.2) |
| `backup.yml` | `30 13 * * *` | `:20` | 2026-08-16T13:51:12Z | success |
| `weekly-research.yml` | `0 16 * * 6` | `:24` | 2026-08-15T16:29:59Z | **cancelled** (see 1.1) |

(Run data source: `gh run list --workflow=<wf> --json event,status,conclusion,createdAt`,
`observed_at=2026-08-16T22:14–22:16Z`. Additional greens observed behind each latest run:
daily-brief 2026-08-13 and 2026-08-12 success; us-positions 2026-08-13 success;
pipeline-health 2026-08-14 and 2026-08-13 success; backup 2026-08-15 success.)

Observed run durations (inputs to §3's compute estimate): `daily-brief` completes in
~2.5 min (created→updated 2026-08-16: 20:45:42→20:48:09Z; 2026-08-13: 21:12:38→21:15:07Z;
2026-08-12: 21:12:49→21:15:28Z — same source and window). Durations for `us-positions`,
`pipeline-health`, `backup`: not captured this window — `unavailable` (assumed small in §3,
assumption labelled).

### 1.1 The 2026-08-15 `weekly-research` scheduled run — G6's first real test

The inventory's gap **G6** (`scheduler-inventory-2026-08-13.md:242`) said the Saturday
2026-08-15 run would be the first real test of the PIT-batching fix (`36b07fb`, PR #85).
It ran, and the result is worse than a pass or a clean fail:

- Run `31895667938`, `event=schedule`, created 2026-08-15T16:29:59Z (+29m59s cron drift),
  head SHA `d1b8420791b8715936e152be7e0ba300dd5936c8`, **conclusion: cancelled**
  (source: `gh run view 31895667938 --json …`, `observed_at=2026-08-16T22:15Z`).
- Step-level detail (same source): `Sync universe` success (7s) · `Sync security master`
  success (8s) · **`Sync corporate actions` success but 1h 28m 06s** (16:30:47→17:58:53Z) ·
  **`Sync financial statements` cancelled at 18:00:15Z**, ~1m22s in ·
  **`Derive fundamentals PIT` skipped · `Sync fundamentals` skipped.**
- Mechanism: the job carries `timeout-minutes: 90` (`weekly-research.yml:37`, comment:
  *"sync_financial_statements is the long pole"*). 16:30:03→18:00:15 is the 90-minute
  budget, exhausted; GitHub cancelled the job mid-step.

**Three consequences, recorded for James:**

1. **G6 remains open — the PIT fix is still unproven on schedule.** The step it fixes was
   never reached. The chain is now **0-for-2** on scheduled runs (2026-08-08 failure at the
   PIT step; 2026-08-15 timeout before it).
2. **A new anomaly surfaced:** `sync_corporate_actions --active-only` consumed 88 of the 90
   budget minutes. The workflow's own comment expected `sync_financial_statements` to be the
   long pole, not corporate actions. Whether 88 min is a regression, a backlog catch-up, or
   the new normal is `unavailable` from run metadata alone — it needs a diagnosis before any
   cutover of this chain (precondition in §4, wave 2).
3. **The failure mode is substrate-shaped.** A single wall-clock budget shared across six
   chained steps, cancellation mid-step, no retry-from-failed-step, downstream steps skipped
   — these are properties of a monolithic Actions job. They are precisely the class of
   problem an orchestrator with per-op timeouts, per-op retry policy, and
   re-execution-from-failure addresses. This is evidence *for* the F5 ruling, not a reason
   to patch the Actions job further.

### 1.2 `pipeline-health` 2026-08-15 failure — the watchdog, probably working

`pipeline-health` went red once in the window (2026-08-15T22:24:43Z), the same day as the
`weekly-research` cancellation. Its two prior scheduled runs (2026-08-14, 2026-08-13) were
green; the 2026-08-16 run was not yet due when the observation window closed, so whether it
recovered is `unavailable`. Per the inventory's G9 precedent, `check_cron_health.py`
hard-fails when it finds stuck/missing/degraded `job_runs` — the exit 1 *is* the alarm.
**Inference, flagged as such:** the 08-15 red is most plausibly the watchdog correctly
reporting the weekly-research chain's missing `job_runs`. The run's logs were not pulled
this window — root cause `unavailable`; do not "fix" the watchdog on this evidence.

---

## 2. Deployment options

Constraint set: Render is **DELETED** (governor ruling, authority ladder level 0,
2026-08-12, `roadmap-state.md` defect #4) **and must not return** — no Render option
appears below. F5 bars new GitHub production schedules, so "stay on Actions" is
time-bounded safety coverage, not an option. Single user, ~20 adopted jobs, minutes-scale
compute, one 90-min+ weekly chain, secrets = `DATABASE_URL` (Supabase prod), `EODHD_API_KEY`,
Resend key.

### Option A — Dagster OSS, self-hosted on a small VM

A self-hosted deployment requires three long-running components: **webserver** (UI/GraphQL),
**daemon** (schedules, sensors, run queuing — schedules do not fire without it), and a
**code location server**; run/event storage is SQLite by default with Postgres as the
swappable production choice (source: `docs.dagster.io/deployment/oss/oss-deployment-architecture`,
`observed_at=2026-08-16T22:20Z`).

Where it would run, given Render is gone: a plain VM in **AWS ap-southeast-2** (Lightsail or
EC2 — region-aligned with F6's S3 target) or a DigitalOcean Sydney droplet. Pricing in §3.
Storage: a local Postgres on the same VM ($0, one more thing to operate and back up) or the
existing Supabase Postgres (couples the orchestrator's event log to the product DB on a free
tier — noisy writes against a storage-capped instance; not recommended without a quota check,
which is `unavailable` here).

- For: cheapest ($12–24/mo, §3); zero new SaaS; secrets never leave own infra.
- Against: James operates the orchestrator — patching, upgrades, disk, the Postgres event
  log, and the "who watches the watchman" problem (the daemon itself needs the
  Healthchecks.io deadman). This recreates the pet-server class Render's deletion removed.

### Option B — Dagster+ Serverless (Solo plan)

Dagster hosts both control plane and compute. Zero infrastructure.

- For: lowest operational burden of all; managed UI, alerting, run history.
- Against: **secret custody** — `DATABASE_URL` (production Supabase), `EODHD_API_KEY`, and
  the Resend key would execute inside a third party's compute. Runtime fit is unverified:
  whether Serverless accommodates the 90-min+ weekly chain and the `pip install -e ".[ml]"`
  image is `unavailable` (not probed — verifying it properly means a trial, which is barred
  here and James-gated later).

### Option C — Dagster+ Hybrid (Solo plan) — RECOMMENDED

Dagster hosts the control plane (UI, schedule evaluation, run queuing, alerting); *"your
Dagster code is executed within your environment"* inside containers managed by an agent
you operate, with the agent making outbound connections — no inbound access to your infra
(source: `docs.dagster.io/deployment/dagster-plus/hybrid`, `observed_at=2026-08-16T22:22Z`;
that page does not explicitly document secret storage — the mechanism is that runtime env
vars live agent-side, on the VM). Hybrid deployments carry **no serverless compute charge**
(source: `support.dagster.io` May-2026 pricing article, `observed_at=2026-08-16T22:17Z`).

**Recommendation: Dagster+ Hybrid on the Solo plan, agent on one small VM in
AWS ap-southeast-2 (Lightsail 2 GB, $12/mo).** Reasoning:

1. **Secrets stay on own infrastructure** (the deciding factor vs Serverless, for a repo
   whose governance posture treats credential custody as load-bearing).
2. **No stateful orchestrator to operate** (the deciding factor vs OSS): no event-log
   Postgres, no webserver to expose/secure, schedules evaluated in the managed control
   plane and surviving agent restarts. The self-operated surface shrinks to one agent
   process — which still gets a Healthchecks.io deadman, per the existing monitoring stack.
3. **Runtime headroom**: the 90-min weekly chain runs on own VM — no serverless runtime-limit
   unknowns.
4. **Region alignment**: the VM lands in ap-southeast-2, same region as F6's target S3
   store; one cloud account services both work orders (account creation is James-only
   either way).
5. Cost delta between all three options is ≤ ~$25/mo (§3) — immaterial; the decision is
   operational, not financial.

Runner-up: Serverless (if James prefers zero self-managed compute and accepts third-party
secret custody plus a runtime-limits verification step). Cost floor: OSS (if James prefers
no new SaaS and accepts operating the orchestrator). The choice is James's — decision
point D2, §6.

---

## 3. Cost estimate

Every observed figure: source + `observed_at`. Every derived figure: labelled, inputs shown.
Unknowns: `unavailable`.

### 3.1 Observed pricing

| Item | Figure | Source | observed_at |
|---|---|---|---|
| Dagster+ Solo base | $10/month | `dagster.io/pricing` | 2026-08-16T22:16Z |
| Dagster+ Solo credits | $0.040/credit, **zero included** (since 2026-05-01) | `dagster.io/pricing` + `support.dagster.io` article "Dagster+ Solo and Starter pricing updates (May 2026)" | 2026-08-16T22:16–22:17Z |
| Credit definition | 1 credit per asset materialization or op executed | `dagster.io/pricing` | 2026-08-16T22:16Z |
| Serverless compute | $0.010/minute (**$0 on Hybrid**) | `dagster.io/pricing` + same support article | 2026-08-16T22:16–22:17Z |
| Dagster+ Starter | $100/month + $0.035/credit | `dagster.io/pricing` | 2026-08-16T22:16Z |
| Dagster+ Pro / Enterprise | `unavailable` (Contact Sales — not probed, by constraint) | `dagster.io/pricing` | 2026-08-16T22:16Z |
| AWS Lightsail 2 GB / 2 vCPU / 60 GB (IPv4) | $12/month; Sydney gets half the listed transfer allowance | `aws.amazon.com/lightsail/pricing/` | 2026-08-16T22:18Z |
| AWS Lightsail 4 GB tier | $24/month | `aws.amazon.com/lightsail/pricing/` | 2026-08-16T22:18Z |
| DigitalOcean 2 GiB / 1 vCPU droplet | $12/month (Sydney listed as a datacenter; per-product SYD availability not confirmed on the page) | `digitalocean.com/pricing/droplets` | 2026-08-16T22:19Z |

### 3.2 Derived workload model

Inputs: the observed fleet (§1) mapped 1 job-step → 1 op/credit (coarse; the idiomatic
Dagster port may model finer-grained assets — see sensitivity below).

- Ops/week: daily-brief 12×5 + us-positions 1×5 + pipeline-health 1×7 + backup 1×7 +
  weekly-research 6×1 = **85/week** ≈ **370 credits/month** (85 × 365.25/7/12).
- **Derived credit cost (Solo): ≈ $14.80/month.**
- Compute minutes/week (Serverless only): daily-brief 2.5×5 = 12.5 (observed, §1) +
  weekly-research ~90×1 (observed ceiling, §1.1) + us-positions/pipeline-health/backup
  **assumed** 3–5 min each (durations `unavailable`, §1) ≈ 15+21+35 → total ≈ 174 min/week
  ≈ 755 min/month. **Derived Serverless compute: ≈ $7.60/month.**

Sensitivities: (a) credits scale linearly with asset granularity — modelling the brief chain
as ~30 fine-grained assets instead of 12 ops roughly doubles credit spend to ~$30/mo; keep
the port coarse (1 op per existing job) in v1. (b) weekly-research's true runtime is unknown
until the corporate-actions anomaly (§1.1) is diagnosed; each extra hour/week costs +$2.60/mo
on Serverless and $0 on Hybrid/OSS.

### 3.3 Totals by option (derived)

| Option | Monthly estimate | Composition |
|---|---|---|
| A — OSS self-hosted | **$12–24** | Lightsail 2 GB $12 (4 GB $24 if webserver+daemon+Postgres+runs contend — untested, `unavailable`); $0 SaaS |
| B — Dagster+ Serverless Solo | **≈ $33** | $10 base + ≈$14.80 credits + ≈$7.60 compute |
| C — Dagster+ Hybrid Solo (recommended) | **≈ $37** | $10 base + ≈$14.80 credits + $0 compute + $12 VM |

FROM-state baseline: the repo is private (source: `gh repo view --json visibility`,
`observed_at=2026-08-16T22:24Z`), so Actions minutes draw on the account plan's included
allowance; estimated current usage ≈ 755 min/month (derived above) against a 2,000-min
GitHub Free allowance — the account's actual plan and billing state are `unavailable`
(not probed). Observed marginal cost of the current substrate: effectively $0.

**Adverse-cost clause:** these totals ($12–37/mo) are assessed **not adverse** against F5.
If James judges otherwise at any tier, the path is stated in §7 — an F5 amendment drafted
for James, never a silent substitution.

---

## 4. Cutover plan — FROM GitHub Actions, TO the deployed Dagster instance

### 4.1 Scope and exclusions (binding constraints)

- **In scope:** the ADOPTED work now carried by the five scheduled workflows (§1) — the 20
  ADOPTED services of inventory §2.
- **The three DECIDE rows are inputs, not resolutions.** `asxos-api` (service 1),
  `build-portfolio` (16), `detect-theme-stages` (21) — inventory §2/§6 — remain **unresolved
  by this document**; see 4.4.
- **No RETIRE-Model-A service appears in this plan.** Services 10, 15, 20, 27, 28
  (inventory §2, RETIRE — Model A) are excluded entirely: they are not cutover subjects,
  not Dagster jobs, not schedules, not backlog items here. Inventory §3 proves the executing
  scheduler never invokes them; porting them in any form is barred (rule #11; the 2026-07-11
  shelf decision).
- **`build-portfolio` is explicitly excluded** pending its DECIDE ruling. It sits at rule
  #11's mechanical enforcement point (`approved_for_allocation` → production gate →
  `ModelGateDormant`), and manifest E4's warning applies: re-scheduling it produces a weekly
  dormancy alert forever — the alert-fatigue failure mode that gets quarantines quietly
  reverted. It is not scheduled today and this work order does not schedule it.
- **Direction of travel only removes GitHub schedules** (F5: no new GitHub production
  schedules). Event-driven CI and `claude-execute` are out of scope.

### 4.2 Preconditions (before wave 1)

P0. James approves this work order (which, per §7, is not Stage 1 authorization — Stage 1's
    own gate is separate) and rules decision points D2–D4 (§6).
P1. Deployment stood up per §2's ruled option: accounts, credentials, VM — each a hard stop
    executed by James or under his explicit per-item authorization.
P2. Jobs ported as coarse Dagster ops invoking the existing `jobs/*.py` entry points —
    same code, same `JobMonitor`/`job_runs` writes, same env contract (including
    `ASXOS_PERSONAL_USE=1` where the job requires it — the in-code gates are untouched).
    Schedules **OFF**.
P3. Observability wired: Healthchecks.io deadman pings from Dagster runs; the agent (Hybrid)
    or daemon (OSS) gets its own deadman.
P4. Per-job validation runs on the new substrate. These are real production writes (that is
    what the jobs do), so each first validation run is James-triggered or explicitly
    James-authorized — never agent-initiated (Amendment B hard stops: production writes,
    scheduler cutover).
P5. The weekly-research corporate-actions runtime anomaly (§1.1) diagnosed — precondition
    for wave 2 specifically, not for wave 1.

### 4.3 Waves, order, rollback

Mechanics common to every wave: the flip is **one James-approved PR** that removes the
`on.schedule` block from the workflow (keeping `workflow_dispatch` as a manual fallback
during soak) while the corresponding Dagster schedule is enabled. `.github/**` is an
authority path (inventory §7), and scheduler cutover is an Amendment B hard stop — so every
flip is James-gated twice over. **Never both schedules enabled at once** for the same job.
**Rollback per step** = revert the flip PR (restores the Actions cron) + disable the Dagster
schedule; two actions, minutes, no data migration involved in either direction because job
state lives in `job_runs`/the product DB, not in the scheduler.

| Wave | Moves | Why this order | Soak before next wave |
|---|---|---|---|
| 1 | `us-positions` | Smallest unit: one job, weekdays, trivially verified against `job_runs`. Lowest blast radius first. | 1 green week on Dagster |
| 2 | `weekly-research` (6-step chain) | Moves early *because* it is the substrate-shaped failure (§1.1): per-op timeouts, per-op retries, and re-execution-from-failed-step replace the shared 90-min guillotine. Requires P5. | 2 consecutive green Saturdays — which also finally closes G6's question on the PIT fix |
| 3 | `daily-brief` (12-step chain) | The payload. Moves only after the chain pattern is proven on wave 2. Step order preserved as the dependency graph; the three post-brief steps stay ordered after the send so their failure can never cost the brief (current design, kept). | 1 green week |
| 4 | `pipeline-health` | The watchdog moves late deliberately: `check_cron_health.py` reads `job_runs`, which is substrate-agnostic, so it keeps watching the whole fleet from Actions throughout waves 1–3 — independent-observer value during the transition. | 1 green week |
| 5 | `backup` | Most safety-critical single job, and the one exact declared/executing schedule agreement in the old fleet — it moves last, only after the rest of the fleet is green on Dagster for 4 consecutive weeks (mirrors the M13.8 four-week sign-off pattern). Restore-drill capability must be preserved or re-homed with it. | — (cutover complete) |

Post-cutover cleanup (only after wave 5 soak): remove the residual `workflow_dispatch`-only
workflow files via one more James-approved PR. That PR is **not** the `render.yaml` removal
PR (§5).

### 4.4 The three DECIDE rows — inputs only

Enumerated as required; **none is resolved here**; each stays a governor call (inventory §6):

1. **`asxos-api` (service 1)** — a hosting question, not a scheduler one. Input noted: if
   the Hybrid VM exists (§2C), it is a *candidate* co-host for the API; whether the API
   needs a host at all is the prior question. Not resolved here.
2. **`build-portfolio` (16)** — excluded from this cutover entirely (4.1). If James later
   rules it back into service, its scheduling lands as a Dagster schedule under whatever
   alerting design answers E4 — a future work order, not this one.
3. **`detect-theme-stages` (21)** — the inventory's "strongest candidate for adopted-and-
   missed." Input noted: if James rules ADOPT, F5 forbids a new GitHub schedule, so its
   re-homing is a Dagster schedule after wave 3 — making the DECIDE cheaper to say yes to
   post-cutover. The decision itself remains James's. Not resolved here.

---

## 5. `render.yaml` removal — inherited by reference, not bundled

The removal plan is **inventory §5** (`docs/product/scheduler-inventory-2026-08-13.md`,
§5.1–5.4), adopted here **by reference in its entirety** — including its
`tests/test_render_backup_build.py` disposition, its CLAUDE.md rule-#2 / `docs/README.md` /
Makefile consequences, and its sequencing after `P1-02`. Per §5.4, that removal is
**independent of this cutover and must not be bundled with it**: retiring dead config is not
a scheduler cutover. No wave in §4.3 touches `render.yaml`, and the removal PR is its own
James-approved unit whenever James triggers it.

---

## 6. Hard stops and James decision points

**Hard stops** (unchanged from Amendment B; restated because every one is load-bearing here):
credentials and secret creation · account/org/tenant signup (Dagster+ org, AWS account, VM
provisioning) · migrations · destructive DB operations · production writes (including §4.2 P4
validation runs) · **scheduler cutover** (every §4.3 flip) · new GitHub production schedules
(F5) · direct pushes to `main` · merge/ready/un-draft/self-approval · authority or permission
changes (CLAUDE.md, `docs/README.md`, `render.yaml`, `.github/**`) · personalised financial
instructions · capital execution · any Model A boundary (rule #11).

**Decision points for James:**

| # | Decision | Default in this document |
|---|---|---|
| D1 | Approve/reject this work order | — (and see §7: approval ≠ Stage 1 authorization) |
| D2 | Deployment option (A/B/C, §2) and plan tier | C — Dagster+ Hybrid, Solo |
| D3 | Create the Dagster+ org and (if C) the AWS account/credentials | James-only, hard stop |
| D4 | Provision the VM (if A or C); region | ap-southeast-2, Lightsail 2 GB |
| D5 | Trigger/authorize each first validation run (P4) and approve each wave-flip PR | one PR per wave |
| D6 | The three DECIDE rulings (§4.4) | not resolved here |
| D7 | CLAUDE.md rule #2 amendment (inventory §6 item 4) | James-only, authority-guarded — see §7 |
| D8 | The `render.yaml` removal PR (§5, by reference) | independent unit, James-triggered |
| D9 | If any cost tier is judged adverse | F5 amendment path, per §7 |

---

## 7. Self-limiting statements

- Approval of this work order is not Stage 1 authorization (`roadmap-state.md` Stage 1 row).
- This work order does not amend CLAUDE.md rule #2 — that edit is James-only and
  authority-guarded.
- If the cost estimate is adverse, the recommendation is an F5 amendment drafted for James —
  not a silent substitution of a different orchestrator.

---

## 8. Provenance

- Branch `claude/p3-01-dagster-work-order` from `origin/main` = `4c7406d`; pre-flight
  verified the Amendment B parallel-authorization rider present on `origin/main`
  (`roadmap-state.md:147`) before branching.
- Evidence gathered read-only: `.github/workflows/` (10 files, read at base SHA), `gh run
  list`/`gh run view`/`gh repo view` (window 2026-08-16T22:12–22:25Z), four public web pages
  (§3.1 sources). No account created, nothing installed, no dependency file touched, no
  workflow/Makefile/`render.yaml` edit, no schedule mutated, no benchmark run, no DB query,
  no production action.
- This file is the mission's only change.
