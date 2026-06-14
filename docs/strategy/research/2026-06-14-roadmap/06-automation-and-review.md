# 06 — Automation and Review

> **Status: DESIGN SKETCH ONLY. No tables, no automation, nothing approved.**
> The schema below is a *proposal* to think against, not a migration to apply.
>
> **The governing rule:** `event → review` is acceptable later;
> `event → production mutation` is **not** acceptable until a signed-off
> governance layer exists. No autonomous DB / Render / Git changes.

---

## 1. The problem

ASXOS is unattended most of the time. Today, the only feedback channels are:
the morning brief (in-band, but only if `compose_brief` succeeds), Healthchecks.io
deadman emails (out-of-band, per job), and `job_runs` (queryable, but nobody is
querying it automatically — `check_cron_health` is not deployed).

There is no structured place where "something happened that a human should look
at" is recorded, triaged, and turned into an action. That is what an
events → reviews layer provides — and it scales operator attention **without**
giving the system permission to change production on its own.

## 2. Why automatic *remediation* is not yet allowed

The Phase B postmortem's central lesson is that silent self-managing behaviour
(`logger.warning(...); continue`) is what let the predecessor rot while
reporting healthy. Automatic remediation is the same risk with more power: a
system that mutates production in response to its own signals, unsupervised, can
turn a small incident into a large one with no human gate. ASXOS will not do
this until there is a governance layer with: human approval gates, a reversible-
action whitelist proven over months of human-handled history, and full audit.

Until then: **the system may propose; only a human disposes.**

## 3. Proposed objects (PROPOSAL — not to be created)

```
ops_events        — append-only fact log of anything noteworthy
review_queue      — actionable items derived from events (human-worked)
review_decisions  — what the human decided for a review item
review_artifacts  — supporting data attached to a review (SQL output, diffs, logs)
review_prompts    — generated, scoped Claude/Opus prompts for a review
review_outcomes   — what actually happened after the decision (closes the loop)
```

### `ops_events` (sketch)

| Column | Type | Notes |
|---|---|---|
| event_id | BIGSERIAL PK | |
| source | TEXT | `job_runs`, `signals`, `backup`, `model`, `portfolio`, `data_quality` |
| event_type | TEXT | `job_failure`, `stale_signal`, `missed_backup`, `model_drift`, `dq_flag`, `drawdown` |
| severity | TEXT | `S1`..`S4` (see §5) |
| payload | JSONB | structured detail (job_name, error, ages, metrics) |
| created_at | TIMESTAMPTZ | |
| dedup_key | TEXT | so the same condition does not spam (e.g. one row per job per day) |

### `review_queue` (sketch)

| Column | Type | Notes |
|---|---|---|
| review_id | BIGSERIAL PK | |
| event_id | BIGINT FK → ops_events | |
| status | TEXT | `open` / `ack` / `in_progress` / `resolved` / `dismissed` |
| severity | TEXT | inherited, may be escalated |
| suggested_prompt_id | BIGINT FK → review_prompts | the pasteable next step |
| assigned | TEXT | single user; trivial today |
| opened_at / resolved_at | TIMESTAMPTZ | for MTTR/TTD metrics |

`review_decisions`, `review_artifacts`, `review_prompts`, `review_outcomes` hang
off `review_queue` to record the human's decision, the evidence, the generated
prompt, and the eventual result.

## 4. Automatic review creation (event sources)

All of these write `ops_events` → `review_queue`. **None mutate production.**

| Trigger | Source | Detection |
|---|---|---|
| Job failure | `job_runs.status='failure'` | the existing `check_cron_health` consecutive-failure logic |
| Stale signals | `signals` | `MAX(as_of) < CURRENT_DATE - 1` on a trading day |
| Missed backup | backup `job_runs` row (depends on tech-debt T3) | no success row in 26h |
| Model drift | `check_model_staleness` finding | feature/prediction distribution shift |
| Data-quality flag | `data_quality_flags` insert | new flag row |
| Portfolio drawdown | `portfolio_daily_snapshots` | drawdown beyond a pre-set bound |

`check_cron_health` is the natural first producer — it already detects stuck
jobs, missing successes (36h), and consecutive failures, and currently *emails*.
The review layer would have it *also* write events.

## 5. Review severity model (proposal)

| Severity | Meaning | Channel | Example |
|---|---|---|---|
| S1 | Loop-breaking; act today | brief top + deadman | core-loop job failed; signals stale on a trading day |
| S2 | Degraded; act this week | brief + review | peripheral job failing; healthcheck gap |
| S3 | Maintenance; backlog | review only | drift; legacy orphan; docs |
| S4 | FYI | review only (digest) | informational, no action |

## 6. Claude/Opus prompt generation

Each review can carry a **generated, scoped prompt** (like those in
`10-future-prompts.md`): the incident context, the hard constraints, the
read-only-first tasks, the deliverable, and a stop condition. The operator
pastes it to drive a diagnosis/fix session — **with a human deciding whether to
apply anything**. The prompt is a convenience, not an authorization.

## 7. Human approval gates (mandatory)

```
ops_event → review_queue → [generated prompt] → human reviews → human approves → action
                                                              └─ human dismisses → closed
```

There is no path from `ops_event` to a production change that does not pass
through a human approval. This is the line that the whole design exists to hold.

## 8. What this unlocks vs what it must never become

| Acceptable (later) | Never (until governance exists) |
|---|---|
| Auto-create review rows | Auto-modify Render services |
| Generate diagnostic prompts | Auto-run jobs in response to events |
| Surface severity in the brief | Auto-apply migrations or commits |
| Track MTTR / TTD metrics | Auto-roll credentials / env vars |
| Suggest a fix | Apply a fix unsupervised |

## 9. Sequencing

- **Now:** nothing. This is a design sketch.
- **Lane B, after loop stable:** design review with `system-architect`; decide
  storage (these tables live in the ASXOS schema, not the legacy superset);
  prototype `ops_events` population from `check_cron_health` (read + write events
  only; still no remediation).
- **Much later, evidence-gated:** consider a tiny, provably-reversible
  auto-remediation whitelist — only after months of human-handled `review_queue`
  history (see `03-architecture-tradeoffs.md` TO-9).
