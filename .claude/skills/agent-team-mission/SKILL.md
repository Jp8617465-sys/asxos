---
name: agent-team-mission
description: Run a LARGE parallel asxos mission with experimental agent teams under Guilfoyle's plan — whole-project mining, product reality sweeps, cross-layer features, competing debugging hypotheses, large parallel reviews. Requires local CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 and a James-visible team plan before implementation. Not for small or sequential work.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
---

# agent-team mission (skill)

**Authority: `.claude/commands/arbi-team.md`** — this skill wraps that flow. Teams are
Anthropic-experimental and **disabled by default**; they run only when the operator has set
**local/user** config `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — never a repo-committed
default (see the runbook: `docs/product/runbooks/agent-team-mission.md`).

## Qualifying-mission test (hard gate — refuse and reroute if it fails)

Teams are for missions where **parallelism has real value**:

- GOOD: whole-project mining pass · product reality sweep · cross-layer feature (DB + domain
  + CLI + brief + tests) · competing debugging hypotheses · large parallel review/audit.
- BAD (reroute to `/arbi-mission` or a single specialist): one-file edits · same-file
  refactors · sequential bugs · tiny fixes · anything needing lots of shared mutable state ·
  anything requiring James's judgement before progress.

## Team rules (binding, from James 2026-07-14)

- **Max 4 teammates by default.** More needs explicit James approval in the envelope.
- **Teammates own separate file areas** wherever possible — the plan states each teammate's
  file ownership and expected artifact.
- **Plan approval before implementation.** The team plan (topology, ownership, artifacts) is
  approved before any teammate implements. The four criteria (the lead/Guilfoyle applies them
  mechanically — a failing plan never proceeds): include tests · cross no
  DB/Render/merge/deploy/capital boundary · state file ownership · state the expected
  artifact. **Attended-live, James's affirmative approval gates implementation; inside a
  James-granted window, the criteria-gate stands in and the approved plan lands verbatim in
  the morning report** (canonical resolution: `.claude/commands/arbi-team.md` step 2).
- Every teammate is bound by: the reversible I0–I4 ceiling + draft-PR stopping point, the
  review gate on commits, and the **PR transaction discipline** block
  (`docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`) — the lessons apply
  to every builder/teammate that touches a branch.
- Output converges to **one draft PR** (or one per genuinely independent module, stated in
  the plan) — never a spray of unreviewed branches.

## What this skill pre-allows

Dispatch/read only (`Agent` + read/search). Mutation runs on builder/teammates under
`reversible-work-window`. Nothing irreversible is pre-allowed; the hard floor
(hooks/deny-rules/branch protection/James's merge) is unchanged.
