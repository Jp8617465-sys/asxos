---
name: arbi-mission
description: Procedural skill wrapping the /arbi-mission flow — envelope, red-team only on THE ONE THING or a large envelope, Guilfoyle task graph, main-loop fan-out, risk-tiered consult, draft PR, one readiness pass. Use when executing a multi-node approved mission. One-file work is /build.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
---

# arbi mission (skill)

**Authority: `.claude/commands/arbi-mission.md`**. Read that file first.

0. Envelope in. Empty args = current #1. Red-team only on THE ONE THING or a large envelope.
1. Guilfoyle plans. One-file graphs reroute to `/build`.
2. Main loop executes the graph. Mutation nodes → `reversible-work-builder`.
3. Collect + verify — risk-tiered consult. No mandatory three-agent review.
4. Draft PR (never merge).
5. One readiness pass.
6. Stop + record (`task_type: mission`).
