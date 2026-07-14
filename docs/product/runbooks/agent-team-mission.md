# Runbook — running an agent-team mission

**Status:** current (autonomy unlock pack, 2026-07-14)
**Scope:** operator steps for James to enable, gate, and audit an `/arbi-team` mission
**Last verified:** 2026-07-14
**Owner:** James (operator); the command is `.claude/commands/arbi-team.md`, the skill `.claude/skills/agent-team-mission/SKILL.md`
**Superseded by:** N/A

## Prerequisite — enablement is local, never repo

1. Agent teams are Anthropic-experimental and **disabled by default**. Enable them in your
   **user/local** Claude Code config only:
   ```json
   { "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
   ```
   This never lands in `.claude/settings.json` — a repo default would silently enable teams
   for every session and actor; local scoping keeps the choice per-operator, per-machine.
2. `bypassPermissions` stays off. asxos touches GitHub, Supabase, Render, and
   capital-adjacent logic — the isolated-container justification for it does not apply here.

## Qualify the mission (30 seconds — this gate does the most work)

3. Apply the test from the skill: **teams are only for** whole-project mining · product
   reality sweeps · cross-layer features · competing debug hypotheses · large parallel
   review. If it's one-file, sequential, tiny, shared-mutable-state, or blocked on your
   judgement → run `/arbi-mission` or a single specialist instead. When in doubt, don't
   team — teams are the expensive tool.

## Run

4. Provide the envelope to `/arbi-team` (objective, scope, boundaries, stop condition). The
   flow enforces: red-team vet → Guilfoyle team topology (max 4 teammates, disjoint file
   ownership, expected artifact each) → **plan-approval gate**.
5. **The plan-approval gate is yours.** You see the team plan before any teammate implements.
   Approve only if it: includes tests · crosses no DB/Render/merge/deploy/capital boundary ·
   states file ownership per teammate · states each teammate's expected artifact. Anything
   missing → send it back; implementation must not start.

## During

- Teammates work in owned areas on `claude/**` branches; the review gate and the PR
  transaction discipline block bind each of them.
- File-ownership conflicts pause the overlapping teammate — resolution happens in the plan,
  not ad hoc.
- The mission converges to **one draft PR** (or one per independent module only if the
  approved plan said so).

## Teardown + audit

6. Verify the draft PR(s): diff ⊆ the approved plan's ownership map · CI green · review loop
   run · body names every teammate's artifact.
7. Verify the ledger row (`task_type: team-mission`) and the readiness verdict (one pass;
   NOT-READY ×2 means you get a gap list instead of a PR — that is correct behaviour, not
   failure).
8. Unset the env var if you don't want teams available in subsequent sessions on that
   machine. Merge is yours.
