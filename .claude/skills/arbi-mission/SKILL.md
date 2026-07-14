---
name: arbi-mission
description: Procedural skill wrapping the /arbi-mission flow — envelope, red-team vet, Guilfoyle task graph, main-loop fan-out, review loop, draft PR, one readiness pass. Use when executing a single approved mission as structured reversible work. For large parallel missions use agent-team-mission instead.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
---

# arbi mission (skill)

**Authority: `.claude/commands/arbi-mission.md`** — this skill wraps that flow; it duplicates
nothing normative. Read the command file first and follow its six steps exactly:

0. **Envelope in + red-team vet** (CHALLENGE → back to arbi/James; do not execute).
1. **Guilfoyle plans** (dispatch the `guilfoyle` subagent; it returns the task graph,
   per-node specialist + sub-prompt, execution order, readiness criteria).
2. **Main loop executes the graph** — parallel where independent; reversible nodes only;
   any I5/I6/P5/P6 node STOPs for James. Mutation nodes go to `reversible-work-builder`.
3. **Collect + verify** — tests + the review loop per CLAUDE.md.
4. **Draft PR** (never merge, never auto-merge).
5. **One readiness pass** (Guilfoyle scores; READY → hand back; NOT-READY ×2 → stop with the
   gap list).
6. **Stop + record** (ledger row `task_type: mission`; decision-log if a ranked call settled).

## What this skill pre-allows

Only the dispatch/read spine (`Agent` for guilfoyle/specialists/builder + read/search). The
build work itself runs under `reversible-work-window` (its own allow surface); everything
irreversible prompts or is denied as always. No settings.json rule is added or implied.

## Routing rule

Single task → one specialist directly. Multi-node mission → this skill. Genuinely parallel
large mission (whole-project mining, cross-layer feature, competing debug hypotheses, large
parallel review) → `agent-team-mission`. Never team-ify one-file edits, sequential tasks,
tiny fixes, or work blocked on James's judgement.
