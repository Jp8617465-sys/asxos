# Repo navigation audit and Claude planning prompt

**Status:** historical — EXECUTED
**Scope:** docs information-architecture audit (origin of the docs map)
**Last verified:** 2026-07-04
**Read priority:** background
**Superseded by:** `docs/README.md` (this proposal shipped in PR #16 / commit 718f125)

> **HISTORICAL — EXECUTED (banner added 2026-07-04).** This proposal produced the
> docs map now at `docs/README.md` on `main`. Kept as the origin/rationale record for
> that map; do not re-action.

**Date:** 2026-07-04  
**Audience:** Claude Code / future repo-cleanup planning session  
**Status:** read-only audit input; no implementation implied  
**Related PR:** #15 (`docs: Claude fundamentals audit handoff`)  
**Companion doc:** `docs/research/claude-fundamentals-audit-handoff-2026-07-04.md`

This document packages a read-only audit of the repo's information architecture. It exists because a Claude Code session had difficulty finding the new fundamentals audit and had to search for it. The root cause is not only that the audit file was branch-only; the repo's documentation/source-of-truth structure is also fragmented enough that an agent can reasonably start from the wrong place.

---

## 1. Executive finding

The implementation code has meaningful domain structure, but the **repo navigation and documentation layer is not clean enough for reliable agent discovery**.

The repo currently has:

- multiple plausible “read first” docs;
- current, historical, stale, and branch-only docs mixed together;
- root README guidance that points toward old foundation material before current handoff state;
- conflicting architecture descriptions across README, CLAUDE.md, render.yaml, and foundation docs;
- no global docs index that labels documents by status/scope/read priority;
- stale-looking session kickoff material that still says “paste this into Claude”; and
- important planning/audit material sitting on a draft PR branch, not on `main`.

This is enough to confirm the user's theory: Claude Code can get lost here without an explicit path.

---

## 2. Evidence and observations

### 2.1 The fundamentals audit file is branch-only until PR #15 merges

The file `docs/research/claude-fundamentals-audit-handoff-2026-07-04.md` was created on branch:

```text
claude/fundamentals-audit-report-2026-07-04
```

It is part of draft PR #15 and is not on `main` until that PR is merged. A Claude session on `main` will not find it unless it checks out the branch, fetches the PR, or is explicitly pointed to it.

**Implication:** short-term confusion around this file is expected and not solely a repo-structure problem.

---

### 2.2 Root README is not a current-state map

The README says the architecture has “Eight Render cron services” and repeats lessons about a smaller stack with “Eight cron services” and “ten tables.” Current `render.yaml` declares one web service and 28 cron services, and CLAUDE.md says the migrations now cover roughly 40 tables across many subsystems.

**Implication:** README is useful as a high-level identity statement, but not reliable as an up-to-date operating map.

**Recommended classification:** partially stale / background only.

---

### 2.3 CLAUDE.md is closer to the current entry point, but not sufficient

CLAUDE.md says to read `docs/session-handoff-2026-07-04.md` first, followed by build guide, postmortem, and tax spec. That is better than README, but it does not include the new fundamentals audit until PR #15 merges or CLAUDE.md is updated later.

**Implication:** CLAUDE.md is currently the best root entry point, but it still needs a better docs map behind it.

**Recommended classification:** current, but incomplete as a global navigation map.

---

### 2.4 There are multiple competing handoff / next-session docs

Current-looking docs include at least:

```text
docs/session-handoff-2026-07-04.md
docs/next-session-backlog.md
docs/next-session-kickoff.md
docs/research/session-handoff.md
docs/research/research-store-schema.md
docs/research/alpha-research-audit.md
docs/research/operating-model-architecture.md
docs/research/claude-fundamentals-audit-handoff-2026-07-04.md  # PR #15 branch only
```

Some are whole-repo handoffs, some are research-store handoffs, some are prompt/kickoff docs, and some are historical architecture/planning docs. File paths alone do not tell Claude which one should govern the next action.

**Implication:** the repo needs a docs index with status, scope, and read priority.

---

### 2.5 `docs/next-session-kickoff.md` appears dangerous as an entry point

`docs/next-session-kickoff.md` says “Paste the block below verbatim into a new Claude Code session.” It references an old branch, old PR state, migrations 0029/0030, and `REQUIRED_MIGRATIONS = 84`. Current `api/main.py` has moved beyond that migration count.

**Implication:** this file should not remain a prominent session entry point without a warning or archive move.

**Recommended classification:** stale / archive candidate.

---

### 2.6 Foundation architecture docs conflict with live architecture

`docs/foundation/phase-4-architecture-system-architect.md` describes a VPS/systemd/local Postgres/Hetzner architecture. Current CLAUDE.md and render.yaml describe Supabase Postgres and Render cron services.

**Implication:** foundation architecture is historical/background unless explicitly revalidated. README currently points to it as “the chosen architecture,” which is misleading.

**Recommended classification:** historical / superseded by CLAUDE.md + render.yaml for live operations.

---

### 2.7 Some docs solve the problem locally, but not globally

`docs/proposals/governance-first-architecture-2026-06-30.md` explicitly labels sections `[CURRENT]`, `[PLANNED]`, `[FUTURE]`, or `[HISTORICAL]` and explains that an earlier combined document was unsafe because it mixed current, proposed, completed, and historical states.

That is good local hygiene, but the repo as a whole lacks the same metadata discipline.

**Implication:** copy that status-labeling pattern to the repo documentation map.

---

## 3. Diagnosis

The repo's documentation problem is not “too many docs.” The problem is **missing information architecture**.

Each important document should carry three pieces of metadata:

1. **Status:** current / historical / superseded / stale / branch-only.
2. **Scope:** whole repo / research store / governance / tax / portfolio / operations / one-off session handoff.
3. **Read priority:** read first / read if touching X / background only / archive.

Without this, Claude must infer hierarchy from filenames and prose, which is brittle.

---

## 4. Recommended cleanup plan

This should be a small docs-only planning/cleanup effort. Do not alter code, migrations, DB, Render, or Healthchecks as part of the first pass.

### Phase 0 — Read-only confirmation

Claude should first produce a table of current docs and classify each one:

| Path | Status | Scope | Read priority | Why | Contradictions |
|---|---|---|---|---|---|
| README.md | partial/stale | repo intro | background | cron/table counts stale | render.yaml/CLAUDE mismatch |
| CLAUDE.md | current | agent guide | read first | points to handoff | needs docs map |
| docs/session-handoff-2026-07-04.md | current | whole repo/session | read first | active Model A dispute | time-sensitive |
| docs/next-session-backlog.md | current-ish | backlog | read after handoff | P(-1) points to handoff | may include historical detail |
| docs/next-session-kickoff.md | stale | old session prompt | archive | old branch/migration state | migration count mismatch |
| docs/research/session-handoff.md | domain-current | research store | read if research-store work | canonical for research store | date-limited |
| docs/foundation/phase-4-architecture-system-architect.md | historical/superseded | architecture | background only | VPS/systemd conflicts with live Render/Supabase | README points to it too strongly |
| docs/research/claude-fundamentals-audit-handoff-2026-07-04.md | branch-only until PR #15 merges | whole-repo audit | read with PR #15 | not on main yet | none, but branch-only |

### Phase 1 — Add a docs map

Create `docs/README.md` or `docs/INDEX.md`.

Minimum contents:

```text
# asxos docs map

## Read first
1. ../CLAUDE.md
2. docs/session-handoff-2026-07-04.md
3. docs/next-session-backlog.md
4. docs/research/claude-fundamentals-audit-handoff-2026-07-04.md  # after PR #15 merges

## Current source-of-truth docs
- Runtime/deployment: ../render.yaml + ../CLAUDE.md
- Schema: ../migrations/
- Tax: docs/foundation/spec/tax-alpha.md
- Governance: docs/proposals/governance-first-architecture-2026-06-30.md
- Research store: docs/research/research-store-schema.md plus live DB verification
- Alpha evaluation: asxos/domain/research/alpha_eval.py plus tests/test_alpha_eval.py

## Historical/background docs
- docs/foundation/phase-*.md unless explicitly marked current
- docs/strategy/V2_*.md unless explicitly marked current

## Stale / do not use as session entrypoint
- docs/next-session-kickoff.md until reviewed/archived
```

### Phase 2 — Update README

Root README should become a stable overview and point to the docs map. It should not carry stale counts such as “eight cron services” or “ten tables” unless explicitly framed as historical.

Suggested README replacement shape:

```text
## Current operating guide
- Claude/agent guide: CLAUDE.md
- Current session handoff: docs/session-handoff-2026-07-04.md
- Docs map: docs/README.md
- Live deployment source: render.yaml
- Canonical schema: migrations/

## Historical foundation
See docs/foundation/ for rebuild history and design rationale. Some foundation docs are historical and may not match the current deployed architecture; check docs/README.md status labels before treating them as current.
```

### Phase 3 — Mark or archive stale prompt docs

`docs/next-session-kickoff.md` should either move to an archive path or get a warning header:

```text
# STALE / ARCHIVED — do not paste into a new Claude session

This file references old branch and migration state. Use CLAUDE.md and docs/session-handoff-2026-07-04.md instead.
```

### Phase 4 — Add status headers to important docs

Add standard headers:

```text
**Status:** current | historical | superseded | stale | branch-only
**Scope:** whole repo | research store | governance | tax | portfolio | operations
**Last verified:** YYYY-MM-DD
**Read priority:** read first | read if touching X | background only | archive
**Superseded by:** path or N/A
```

Do this first for:

- README.md
- CLAUDE.md
- docs/session-handoff-2026-07-04.md
- docs/next-session-backlog.md
- docs/next-session-kickoff.md
- docs/research/session-handoff.md
- docs/research/research-store-schema.md
- docs/research/alpha-research-audit.md
- docs/research/operating-model-architecture.md
- docs/foundation/phase-4-architecture-system-architect.md
- docs/proposals/governance-first-architecture-2026-06-30.md

---

## 5. Claude prompt to orchestrate the plan

```text
You are working in repo `Jp8617465-sys/asxos`.

Task: orchestrate a READ-ONLY documentation/source-of-truth cleanup plan. Do not edit files yet. Do not change code, migrations, DB, Render, or Healthchecks.

Start by reading:
1. CLAUDE.md
2. docs/session-handoff-2026-07-04.md
3. docs/next-session-backlog.md
4. docs/research/claude-fundamentals-audit-handoff-2026-07-04.md if present on this branch / PR #15
5. docs/research/repo-navigation-audit-and-plan-prompt-2026-07-04.md if present on this branch / PR #15
6. README.md
7. docs/next-session-kickoff.md
8. docs/research/session-handoff.md
9. docs/foundation/phase-4-architecture-system-architect.md
10. render.yaml

Goal: confirm or correct the theory that the repo is hard for Claude Code to navigate because docs are fragmented, stale, or insufficiently labeled.

Deliver a plan with:

## 1. Current documentation map
For each major doc, classify:
- path
- status: current / historical / superseded / stale / branch-only / unknown
- scope: whole repo / research store / governance / tax / portfolio / ops / session handoff
- read priority: read first / read if touching area / background / archive
- evidence: exact file:line references
- contradictions or risks

## 2. Source-of-truth proposal
Define which documents should be authoritative for:
- repo overview
- Claude session entry
- live deployment
- schema/migrations
- tax math
- governance
- research store
- Model A / alpha evidence
- portfolio/risk
- backlog/session state

## 3. Cleanup PR plan
Propose a docs-only PR broken into small commits:
1. Add docs/README.md or docs/INDEX.md.
2. Update root README to point to CLAUDE.md, docs map, current handoff, render.yaml, and migrations.
3. Mark or archive stale docs/next-session-kickoff.md.
4. Add standard status headers to key docs.
5. Add a short note to CLAUDE.md pointing to docs/README.md once it exists.

## 4. Do-not-change list
Explicitly avoid:
- code changes
- migrations
- DB writes
- Render changes
- Healthchecks changes
- changing actual product behavior
- rewriting historical foundation docs beyond status headers

## 5. Proposed exact file edits
Do not apply them yet. Show the proposed edits/diffs in prose or fenced blocks for review.

Rules:
- Every repo claim must cite exact file paths and line numbers.
- Do not trust README as current without checking CLAUDE.md and render.yaml.
- Treat older foundation/strategy docs as historical unless they explicitly prove current status.
- Do not delete docs; prefer status headers or archive moves after approval.
- This is a planning session only.
```

---

## 6. Bottom line

The repo does not need a code rewrite to fix this issue. It needs a **documentation source-of-truth layer**.

The smallest high-leverage fix is:

1. merge or explicitly reference PR #15;
2. add `docs/README.md` / `docs/INDEX.md`;
3. update root README;
4. mark `docs/next-session-kickoff.md` stale/archive;
5. standardize status headers on important docs.

After that, Claude should be able to start from one clear path instead of searching and guessing.
