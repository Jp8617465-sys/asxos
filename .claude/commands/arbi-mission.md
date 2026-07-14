# arbi mission — Guilfoyle mission-control execution — `/arbi-mission`

`$ARGUMENTS` = a mission envelope (or a path/ref to one), or empty = build one from arbi's
current #1 next action (`roadmap-state.md`) by running `/arbi` first.

**This is the structured, graph-driven successor to `/arbi-run`.** Where `/arbi-run` is a thin
ad-hoc fan-out, `/arbi-mission` adds an execution-discipline layer — **Guilfoyle** — that turns
an approved mission into a task graph with dependency order, no-task-switching discipline, and
one readiness verdict before the draft PR. It is **attended + reversible**: governor/arbi
invoked, draft-PR-ceiling, never standing/unattended (PR 8 / I4 standing stays gated —
`arbi-permission-model.md`).

## Why a command, not the agent

A Claude Code subagent cannot spawn subagents, and a subagent's `Agent(...)` allowlist is
ignored at runtime — so a "Guilfoyle that spawns" would be an *uncontained* spawner, not a safe
one (a subagent can't fan out at all; the command is the only mechanism that works). So
Guilfoyle is a **read-only planner** and the **main loop** does every side-effecting step — the
same proven pattern as `/pm-review`, `/discover-macro`, `/arbi-run`.

## The mission envelope

The unit `/arbi-mission` executes — a superset of arbi's NEXT PROMPT:

```
mission_id            slug + date (e.g. cron-repair-2026-07-13)
source                who authorised it (arbi's ranked #1, or James directly)
objective             one sentence — the definition of success
scope                 files/modules/surfaces that MAY be touched
allowed_actions       reversible tiers permitted (read · analyse · draft docs · draft code PR)
forbidden_boundaries  I5/I6 (migration/DB/Render/secret/merge/deploy/main/CI), P5/P6
                      (capital policy/execution), rule #11 (Model A for capital), s766B, authority files
stop_condition        definition-of-done (tests green + review loop run + draft PR open + readiness READY)
                      + the hard stops (boundary hit / red-team CHALLENGE / state-thin / 2× not-ready)
required_citations    carried from arbi's NEXT PROMPT; the implementer preserves them
```

## Flow

**0 — Envelope in.** From James directly, or wrap arbi's `/arbi` NEXT PROMPT into the envelope.
**Vet it first:** run `arbi-red-team` on the envelope (Guilfoyle can't reprioritise, so the
mission is challenged *before* execution). CHALLENGE → back to arbi/James; do not execute.

**1 — Guilfoyle plans.** Dispatch the `guilfoyle` subagent with the envelope. It returns the
task graph (nodes + edges), per-node specialist + scoped sub-prompt, the execution order, and
the mission's readiness criteria. It refuses to plan anything crossing `forbidden_boundaries`,
escalating instead.

**2 — Main loop executes the graph.** Fan out independent nodes **in parallel** (single
message); wait for upstream before downstream. Reuse the `/arbi-run` owner→agent roster
verbatim. **Only reversible work is dispatched** — if a node implies I5/I6/P5/P6, STOP and
surface for James; never dispatch it.

**3 — Collect + verify.** Run `make check` / targeted pytest + ruff + mypy. Route every
code/doc edit through the review loop (`security-engineer` / `refactoring-expert` /
`technical-writer`) per CLAUDE.md; the `review-gate.sh` hook enforces it before any commit.

**4 — Draft PR.** Open/update a **draft** PR on the `claude/**` branch, classified docs/code.
Never merge, never enable auto-merge (I6 = James).

**5 — Readiness pass (exactly one).** Guilfoyle scores the collected work against the readiness
criteria — the **mission-completeness** checks on top of the hard gates in
`rubrics/arbi-safety-boundary.md` (reference them, do not restate): objective met within scope ·
tests green · review loop run · draft PR open + correctly classified · citations preserved · no
forbidden boundary crossed · follow-ups recorded, not pursued. READY → hand back. NOT-READY
twice → stop, hand James the gap list (don't grind).

**6 — Stop + record.** Append the mission row to `docs/product/arbi-run-ledger.md`
(`task_type: mission`) and, if it settled a ranked call, to `decision-log.md` (I2 doc write —
authorised because you invoked this). Hand back to James (merge is his) or to arbi via
`/arbi-close`.

## Boundaries

- **Attended + reversible only.** Governor/arbi invoked each time — not standing dispatch
  (PR 8 / I4 standing stays gated: `arbi-permission-model.md`).
- **Never dispatch or perform:** merge · deploy · migration · DB write · Render mutation ·
  secret handling · capital action · a Model A-derived capital recommendation · a boundary
  change. Those STOP for James (I5–I6 / P5–P6).
- **Guilfoyle plans; it never prioritises.** Its only pushback is executability evidence to
  `arbi-red-team` / arbi — never a competing priority call.
- **No permission broadening.** `/arbi-mission` runs on the existing tool permissions +
  interactive prompts + branch protection + the review gate. It adds no `allow` rules and never
  runs unattended.

## Routing to `/arbi-team`

**Large parallel missions route to `/arbi-team`** (agent teams, plan-approval gate, max 4
teammates — `.claude/commands/arbi-team.md`): whole-project mining, product reality sweeps,
cross-layer features, competing debug hypotheses, large parallel reviews. Everything else —
single features, bounded fixes, 1–2-PR missions — stays here. Never team-ify small or
sequential work. The `arbi-mission` skill (`.claude/skills/arbi-mission/SKILL.md`) wraps this
flow; standing/unattended mission dispatch remains gated on the PR 7b/8 preconditions.
