# Overnight research agent — design (NOT yet enabled)

A scheduled, autonomous Claude Code session that runs nightly to **find bugs,
data-quality issues, and bounded optimization opportunities**, and reports them
for human review. This document is the design + guardrails. It is deliberately
**not wired to a schedule** — turning it on is a safety-significant decision (an
autonomous agent with repo + DB + Render access on a live investing system).

---

## 1. The core risk (why this is mostly a containment problem)

An overnight agent that can change code, write to the DB, or touch Render is a
standing source of unsupervised, hard-to-reverse actions on a system that moves
real money decisions. The value (catching the next `sync_prices` cadence bug
while you sleep) is real, but the failure modes are severe: a confidently-wrong
"fix" merged to `main`, a destructive migration, a secret leaked into a log, an
infinite cost loop, or quiet scope creep into trading logic.

**Design stance: advisory-only, propose-never-apply, bounded, killable.** The
agent's only durable output is a **report and (at most) a draft PR**. It never
merges, never deploys, never writes to prod tables, never changes env vars.

---

## 2. What it does each night (bounded task rotation)

"Find a bug or an optimisation" is too open — an unconstrained agent wanders and
burns budget. Instead it picks **one task** from a defined catalogue per run
(round-robin or priority-ordered), time-boxed.

**A. Sentinels (read-only health detectors)** — the highest-value, lowest-risk:
- price coverage: interior non-holiday gaps (the bug we already hit), stale
  `MAX(prices.dt)`, partial-day residue (the 2-row 06-22 case)
- signal freshness + `signal_outcomes` null `ml_prob` / staleness
- cron health: `job_runs` failures/blocked in the last 24h
- portfolio scoreboard: `paper_portfolio_run_metrics` regressions
- migration drift: applied count vs `REQUIRED_MIGRATIONS`
- benchmark gap: `AXJO.INDX` still uningested

**B. Regression checks (read-only, uses the alpha_eval engine):**
- run `scripts/alpha_eval.py`; diff IC-by-horizon / calibration / decile spread
  vs the last stored run; flag material drift (with the effective-N guard so it
  never alarms on noise from too-few dates)
- cost/turnover drift on persisted portfolio builds

**C. Code health (read-only → propose):**
- `make check` (ruff + mypy + pytest); if red, open a draft PR with the fix
- targeted static scans for known anti-patterns (e.g. `logger.warning(...); continue`
  on infra paths — a CLAUDE.md non-negotiable)

**D. One bounded optimization experiment (research-only):**
- from a curated `docs/research/experiment-backlog.md`, run exactly one
  pre-approved experiment via the alpha_eval framework (e.g. "does a normalized
  composite beat prob_up?", "does a 10-day holding variant improve net decile
  spread?"), and append results to a report. **Never** mutates production scoring
  or model artefacts.

The agent does **not** invent its own experiments on trading logic. New
experiment ideas go into the backlog as *proposals* for a human to approve.

---

## 3. Guardrails (the actual product)

| Guardrail | Rule |
|---|---|
| **Kill switch** | `ASXOS_NIGHTLY_AGENT_ENABLED=1` required; default off. Flip to disable instantly. |
| **No main writes** | Work only on `nightly/<date>-<task>` branches. Never push to `main`. |
| **Propose, never apply** | Output is a **draft PR** + report. No merges, no deploys, no Render env changes. |
| **No prod DB writes** | Read-only SQL only. Schema changes are *migration files in a PR*, never `apply_migration`. |
| **Secret hygiene** | Never print env values; run the repo's secret-scan on any diff before opening a PR. |
| **Budget cap** | Hard wall-clock + token/cost ceiling per run; abort + report on breach. |
| **Idempotency** | One PR per (date, task); re-runs update, never duplicate. Skip if an open nightly PR is unreviewed. |
| **Scope lock** | Touch only an allowlisted path set per task; refuse diffs outside it. |
| **Locked surfaces** | Never modify `thresholds.py`, model artefacts, or anything marked "do not modify without explicit instruction." |
| **Deadman** | Healthchecks.io ping on success; you get alerted if a night is silently skipped. |
| **Full audit** | Every run writes a dated report to `docs/research/nightly/` and links the PR. |

---

## 4. Implementation options

1. **GitHub Actions (recommended).** A `schedule:`-triggered workflow launches a
   Claude Code session (Anthropic's GitHub app / action) with the curated prompt,
   `ASXOS_NIGHTLY_AGENT_ENABLED` gate, and least-privilege secrets. PRs land in
   GitHub for review. Native fit with the existing repo + PR flow.
2. **Render cron** invoking the Claude Agent SDK headless. Reuses the existing
   cron + Healthchecks pattern, but Render crons aren't the natural home for
   code-PR workflows (no PR surface) — better for the read-only *sentinel* subset
   that just writes a report / sends the brief.
3. **Claude Code on the web scheduled trigger** (this very environment), pointed
   at a saved prompt. Simplest to start; same guardrails apply.

A clean split: **Render cron** runs the read-only **sentinels** nightly (cheap,
safe, emails you anomalies via the existing brief/Resend path); **GitHub Action**
runs the heavier **code-health + one experiment** weekly and opens draft PRs.

---

## 5. Skeleton (manual-dispatch only — copy out when ready)

```yaml
# .github/workflows/overnight-research.yml  — NOT scheduled until you uncomment.
name: overnight-research
on:
  workflow_dispatch:        # manual only to start
  # schedule:
  #   - cron: "0 18 * * *"  # 18:00 UTC ≈ 04:00 AEST — after data syncs
permissions:
  contents: write           # branches only; branch protection blocks main
  pull-requests: write
jobs:
  research:
    if: ${{ vars.ASXOS_NIGHTLY_AGENT_ENABLED == '1' }}
    runs-on: ubuntu-latest
    timeout-minutes: 30     # hard budget
    steps:
      - uses: actions/checkout@v4
      - name: Run nightly research agent
        uses: anthropics/claude-code-action@v1   # propose-only prompt below
        with:
          prompt_file: .claude/prompts/nightly-research.md
          allowed_tools: "read,grep,bash:make check,mcp:supabase.read_only"
          # NO deploy, NO apply_migration, NO env writes, NO push-to-main
```

The companion prompt (`.claude/prompts/nightly-research.md`) hard-codes: pick one
catalogue task, stay in the allowlisted paths, open a **draft** PR or write a
report, run secret-scan before any PR, and STOP rather than guess on anything
touching trading logic or locked surfaces.

---

## 6. Phased rollout (earn trust before autonomy)

1. **Report-only (week 1–2):** sentinels + alpha_eval regression → nightly
   markdown report only. No PRs. Confirm signal-to-noise.
2. **Draft-PR for code health (week 3+):** allow `make check` fixes as draft PRs
   in allowlisted paths. You review/merge.
3. **One backlog experiment / week (later):** research-only, results appended to
   reports. Still no production change.
4. **Never:** auto-merge, auto-deploy, prod DB writes, threshold/model edits,
   capital actions.

---

## 7. Honest assessment

The *sentinel* tier is high-value and low-risk — it would have caught the
`sync_prices` cadence bug and the partial-day residue automatically, and it's
essentially the existing `check_cron_health` pattern extended. Start there.

The *autonomous-fix* tier is where the danger lives; keep it propose-only and
path-scoped indefinitely. An overnight agent that opens a well-scoped draft PR
you review with coffee is a force multiplier. One that merges its own fixes to a
live investing system is how you wake up to a quiet, confident disaster. The
guardrails in §3 are not optional extras — they are the feature.
