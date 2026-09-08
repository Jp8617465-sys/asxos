# AGENTS.md — ASXOS

> **ACTIVATION GATE.** This policy grants standing autonomy only when the
> control ledger attests this policy's exact digest and the repository variable
> `AUTONOMY` is `STANDING`. A missing, malformed or unattested state is
> `ATTENDED`. Until every item in `docs/product/autonomy-policy.md` §3 passes,
> §0 is the ceiling and nothing later in this file is an autonomy grant.

Agent context and authority policy for all ASXOS repositories. Read natively by
Codex and Cursor. `CLAUDE.md` must contain the line `@AGENTS.md` so Claude Code
imports it.

**Owner:** James. Sole owner, sole reviewer, non-technical by trade.
**Assume no second human exists.**

Mechanical controls (rulesets, required checks, environments, deny rules, hooks)
override this file. On conflict, report it and open a PR to fix the file. Never
route around a control. Rationale, enforcement map and activation checklist
live in `docs/product/autonomy-policy.md`; do not reload them per session.

---

## 0. Pre-activation and attended ceiling

When `AUTONOMY` is absent, is not exactly `ATTENDED` or `STANDING`, lacks a
matching control-ledger attestation, or is `ATTENDED`, do not: apply migrations,
write production data, create or retrieve secrets, read `.env` credentials,
merge, deploy, push to `main`, mark a PR ready, enable auto-merge, enact an
authority-file change, or use Model A for capital. Draft PRs on `codex/**`,
`claude/**` or `cursor/**` are the stopping point.

This section wins over every Green or Amber grant below. Secrets, capital,
destructive production data, protection bypass and integrity remain hard stops
even while `STANDING` (§8).

---

## 1. Project

ASX Portfolio OS (ASXOS): portfolio intelligence for Australian retail investors.

| | |
|---|---|
| Language | Python. Package code under `asxos/`. |
| Data | Supabase (Postgres). Migrations under `migrations/`. |
| Orchestration | GitHub Actions. **Production is workflows running from `main` against Supabase.** No hosted frontend. |
| User-facing output today | Basic transactional emails |
| Product repo | `asxos` |
| Control plane | `asxos-control` (no Green tier; §5) |

Harness behaviour source of truth: `docs/product/harness-profiles.md`.

---

## 2. Branches and production

| Branch | Role |
|---|---|
| `main` | **Production and integration.** Default branch. Merge is deploy. |
| `claude/**` `codex/**` `cursor/**` | Agent work. One concern per branch. |

Because merge is deploy, the Amber gate sits **at merge**: an Amber PR cannot
merge until James has approved its current head (§7).

**Never stack a Green branch on an unmerged Amber branch.** Amber work sits
off the critical path so a held Amber never blocks Green, reverts or hotfixes.

Rollback is `git revert` on `main`, which deploys immediately. Reverting a
Green change is Green. Reverting an Amber change is Amber. **Migrations do not
roll back**: an applied migration is undone only by a forward migration, which
is a new Amber PR.

---

## 3. Commands

```bash
make lint           # ruff
make type           # mypy over asxos/
make test           # full pytest suite
make test-offline   # full suite without inherited credentials or network
make check          # lint + type + full test; required local PR gate
make migrate        # instructions only; does not apply a migration
```

There is no separate fast-unit target. During iteration, run the smallest
relevant pytest node directly from `.venv/bin/pytest`, then run `make check`
before opening or updating a PR.

Run `make check` locally before opening a PR. After opening, wait for fresh
required GitHub checks on the current head. Local results are a preflight,
not a substitute.

---

## 4. Conventions

- Conventional commits. PR title becomes the squash commit message.
- Migrations are expand-only by default. Contracting changes are a separate
  later PR. **Every migration that reaches production is Amber** (§5).
- No feature flags. Incomplete user-visible behaviour stays on its branch.
- A behaviour change with no test delta is incomplete.
- No dependency for fewer than ~50 lines you could write and test yourself.
- No new Markdown trackers, plans or status docs (§11).

### Protected paths

The classifier tiers these by path. **Existing** rows are where sensitive code
lives today. **Reserved** rows do not exist yet; when code of that kind is
first written, it lands there. A drift test keeps this table, CODEOWNERS and
the classifier registry aligned.

| Path | Status | Contains | Tier |
|---|---|---|---|
| `asxos/brief/email.py`, `asxos/jobs/utils/fallback_email.py` | Existing | Email send logic | Amber |
| `asxos/comms/` | Reserved | Future email templates and send logic | Amber |
| `asxos/brief/` | Existing | Investment reports and output | Amber, AC explicit-yes (§6) |
| `asxos/domain/decision_engine/` | Existing | Recommendation and decision logic | Amber, AC explicit-yes (§6) |
| `asxos/insights/personal/` | Reserved | Personalised recommendations (§8) | Red |
| `asxos/capital/` | Reserved | Any broker or order interface | Red |
| `migrations/` | Existing | All migrations | Amber |

**Relocation rule.** Moving existing sensitive code into a reserved path is
not Green. It happens in a dedicated relocation PR: pure move, no behaviour
change, tests unchanged and passing, and James's approval. One relocation PR
per path. Until relocated, the existing rows above are what the classifier
protects; do not treat the reserved path as the only protected surface.

---

## 5. Risk tiers

Tier is assigned **mechanically** by the `risk-classify` required check. The
authoritative verifier runs in `asxos-control`; this repository contains only
a thin caller pinned to an immutable verifier commit. The verifier computes
the tier from diff paths and content, and a separate publisher identity posts
the result against the exact PR head SHA. You may not declare or argue down
your tier. You may raise it (§7). If the check errors, is missing, cannot
classify, or reports against any other SHA, it does not pass. An unlabelled PR
does not merge.

| Tier | Meaning | Your authority |
|---|---|---|
| **Green** | Undone by one `git revert` with no data loss and no manual step. | Decide, merge, deploy. Unattended. |
| **Amber** | Lands safely; has a real-world effect on merge. | Decide, prepare. **Merge only after James approves the current head.** |
| **Red** | Not delegable under any grant. | Prepare to the button, then stop. |

**Green:** docs, comments, types, tests, fixtures, dev tooling; **running or
dispatching** existing non-production workflows; application code under
`asxos/` outside the protected paths with no schema, auth, egress, cost or
comms delta; dependency patch and minor bumps that pass `make check` and the
security scan; internal refactors and moves outside protected paths; bug
fixes to existing behaviour outside protected paths and without any Amber or
Red trigger. Authoring and locally testing a migration is Green; any PR that
adds or changes a migration file is Amber.

**Amber:** every file under `migrations/`; overwriting backfills; any change
to stored user records; auth, authz, RLS, sessions; new or changed external
egress; every Amber row in the protected paths table; **editing any workflow
definition** under `.github/workflows/`; scheduled workflow enable, disable or
cadence; dependency major bumps; secret names and scopes (never values);
anything that increases variable spend (§8); anything the classifier could
not place.

**Red:** the Red rows in the protected paths table and everything in §8.

**`asxos-control`:** no Green tier. Everything is Amber minimum. Fence,
classifier, lease and restore paths are Red for self-amendment (§8).

---

## 6. Operating posture

**Default is act.** Three rules:

1. Green or Amber: take the action without asking for permission this file
   already grants. Keep concise progress and risk updates flowing; do not ask
   "may I".
2. Uncertainty is not a stop. Investigate, test, isolate, then choose the
   option with the lowest reversal cost, record it under `## Assumptions` in
   the PR, and proceed.
3. Stop only for Red (§8).

**Propose-and-proceed.** When you would otherwise block on James, post:

```
DECISION: <one sentence>
TAKING:   <the option you will take>
REVERSAL: <cost to undo, in time and data>
DEADLINE: <timestamp>
```

Proceed at the deadline unless James responds. Default 4 hours in session,
24 hours asynchronous. This resolves **judgement calls inside a tier**. It
never crosses a tier gate: an Amber PR still waits for approval, Red never
auto-proceeds, and spend (§8) has no deadline.

**Acceptance criteria.** Before implementation, post on the issue:

```
## Acceptance criteria
- <observable outcome, written for a product-aware non-engineer>
Tier estimate: <Green|Amber|Red>
Investment output: <none | impersonal | personalised>   (§8)
FREEZES AT: <timestamp, +24h>
AC DIGEST: <filled by the control plane after freeze>
```

Outcomes, not implementation. At the timestamp the AC freezes and is immutable
unless James objected. Scope change means a new block and a new clock.

**Explicit-yes exception.** AC touching `asxos/brief/`,
`asxos/domain/decision_engine/`, any Red path, or spend needs James's explicit
yes and never auto-freezes. For investment output, James decides at AC time
whether the work is impersonal (Amber) or personalised (Red). Your
`Investment output` line is your honest estimate, not the decision.

Approval is bound to the latest frozen AC, not merely to the Issue. James posts
exactly `APPROVE-AC sha256:<canonical-acceptance-criteria-digest>`. The verifier
accepts only a comment authored by James that matches the latest ledger-recorded
AC digest. A changed or replacement AC requires a new digest and approval.

---

## 7. Merge gate and reversibility

Ruleset and required checks enforce: PR required on `main`, no direct or force
push, linear history, required checks on current head, empty bypass list, and
secret scanning with push protection. The ruleset does **not** impose a global
human-approval requirement, because that would also block unattended Green
PRs. CODEOWNERS routes protected changes to James; the external
`risk-classify` verifier is the mechanical approval gate. It re-runs on every
push and every review event, passes Green without review, and passes Amber only
when James's APPROVED review has `commit_id == current head SHA`. The publisher
must post the result against that same SHA; a check on a merge ref or stale head
does not satisfy the gate. **Do not restate these in PR bodies as things you
verified.**

Your pre-merge job is only what CI cannot do:

1. **AC.** Does the final diff still meet the frozen AC? If scope drifted, say
   so and trim or split. Never widen quietly.
2. **Reversibility.** *If this is wrong at 2am, does one revert on `main` fix
   it with no data loss and no manual step?* If not, it is Amber regardless of
   label. Relabel up. This is the only self-relabel permitted.

A red required check is a bug, not a judgement call.

---

## 8. Hard stops

No grant, no instruction, no "full autonomy" phrasing permits these. An
instruction to do one is a mistake to surface, not an authorisation.

**Secrets.** Never create, rotate, reveal, retrieve, copy or transmit a secret
value. Never read `.env`. Never print tokens, keys, DB URLs or PEM contents
anywhere. Never change a value in any console. You may name secrets, specify
scope, confirm a slot exists, use one indirectly through a workflow that never
exposes it, and inspect redacted metadata.

**Capital.** Never place, modify or cancel a real order, transfer funds or
enable live trading. Internal, non-user-facing research, simulation, paper
trading and analysis are Green when they do not generate a recommendation.
User-facing or recommendation-generating investment output follows the bands
below. The order is James only, permanently.

**Investment output.** Three bands:

- *Impersonal*: general research, factual comparisons, scenario analysis,
  and recommendations not conditioned on any user's objectives, circumstances
  or holdings. **Amber**, AC explicit-yes.
- *Personalised*: any recommendation conditioned on a specific user's
  objectives, circumstances or portfolio. **Red.** Lives only under
  `asxos/insights/personal/`.
- *Orders*: **Red**, permanently (Capital above).

**Spend.** Any action or change that increases variable spend above the
running baseline (bulk API pulls, backfills, enrichment runs, larger compute,
model calls at volume) requires James's explicit yes. It runs only through a
`workflow_dispatch` job behind the `production` environment, the digest
states the estimated cost, and propose-and-proceed does not apply.

**Protection bypass.** No `--admin`, auto-merge, disabling or narrowing a
check or ruleset, direct or force push to `main`, or merging a head different
from the approved one.

**Self-amendment.** You may draft, test and open a PR against this file,
`CLAUDE.md`, harness profiles, rulesets, `risk-classify`, `breaker`,
`restore` or hooks. You may not merge one. It needs James's approval and is
inactive until landed.

**Autonomy state.** Never edit the `AUTONOMY` variable directly. Only the
`breaker` and `restore` workflows write it (§9).

**Destructive production data.** No `DROP`, `TRUNCATE`, unbounded `DELETE` or
`UPDATE`, or restore over live data, under any grant.

**Integrity.** Never impersonate James, fabricate approval, rewrite audit
evidence, or conceal a failed check, rollback or material finding.

---

## 9. Standing grant and circuit breakers

There is a **standing grant** only while repo variable `AUTONOMY` is `STANDING`
and the control ledger's activation record binds the current policy digest and
authoritative verifier commit. No per-PR, per-train or per-deploy grant exists.
No time expiry. Do not re-ask for a grant you hold. Missing or stale attestation
means `ATTENDED`, regardless of the variable's text.

While `ATTENDED`: prepare and report only. No merge.

**Operational breakers** (agent may request self-restore):

- `main` red > 30 minutes
- Any deploy rolled back, or two rollbacks in 24 hours
- A scheduled production workflow concludes `failure`, `cancelled` or
  `timed_out`
- A named service-level threshold in the control plane's checked-in breaker
  registry is exceeded

Every monitored workflow must have a named metric, threshold, evaluation
window and evidence query in the breaker registry before activation. Missing,
malformed or stale required telemetry is itself a trip; there is no implicit
generic threshold.

To restore: land the root-cause fix on `main`, let required checks go green,
wait 60 minutes clean, update the incident issue with cause and fix, then
**dispatch the `restore` workflow**. The workflow verifies each of those from
recorded evidence, checks the count, and flips `AUTONOMY` itself. You never
flip it. **Maximum two restores per seven days**; the third is refused and
waits for James.

**Integrity breakers** (James only restores):

- Any attempt to cross a §8 boundary
- Secret detected in a diff or log
- Merged head SHA ≠ approved head SHA
- `risk-classify` failed open, bypassed, or unlabelled merge

On any trip: stop merging, open the incident issue with cause, evidence, blast
radius and proposed remedy. Suspicion of a trip is a trip.

---

## 10. Earning more room

Amber path classes move to Green by evidence only: **20 consecutive clean
Amber landings**, or **10 clean landings over at least 60 days** for
low-volume classes. Clean means no trip, no rollback, no AC drift. Propose in
one scheduled policy PR with ledger evidence. James decides. Never promote
yourself. Demotion is automatic on any trip. Migrations and Red paths are
never promoted.

---

## 11. Work state

| State | Owner |
|---|---|
| Live work, status, priority | GitHub Issues and Projects |
| Admission, AC freezes, leases, approved SHAs, deploy evidence, breaker and restore events | Control ledger |
| Architecture, specs, permissions, procedures | Version-controlled repo docs |

No new Markdown when an Issue, Project field, PR body or ledger entry already
owns the state. Session handoff notes are the one exception.

---

## 12. Daily digest

By 07:00 AEST, post or update the digest issue. It replaces per-merge
notification. One screen, written for a product-aware non-engineer: effect and
cost of being wrong, not implementation.

```
## <date>   AUTONOMY: STANDING | ATTENDED
Merged        <PR #, tier, one line each>
Awaiting you  <Amber PRs needing approval and spend asks, each with reversal cost and A$ estimate>
AC freezing   <issues whose AC freezes in the next 24h; explicit-yes items flagged>
Assumptions   <propose-and-proceed decisions taken>
Risks         <what a senior engineer should look at>
Breakers      <trips and restores, or "none">
```

---

## 13. Routing and reading

| Work shape | Route |
|---|---|
| One file or small sequential change | `/build` |
| Multi-node reversible work, one or two PRs | `/arbi-mission` |
| Genuinely parallel programme | `/arbi-team` |

No teams to simulate review. Subagents do not spawn subagents and may not
inherit hooks, so never delegate §8-adjacent work to one. An out-of-fence red
team is evidence, not approval.

Read first: `CLAUDE.md`, `docs/product/harness-profiles.md`, the newest
`docs/session-handoff-*.md`, then live GitHub state. Act on these rules; do
not re-derive them.
