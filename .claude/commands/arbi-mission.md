# arbi mission — Guilfoyle mission-control execution — `/arbi-mission`

`$ARGUMENTS` = a mission envelope (or a path/ref to one), or empty = build one from arbi's
current #1 next action (`roadmap-state.md`) by running `/arbi` first.

**This is the multi-node dispatcher.** arbi fans out specialists against a Guilfoyle task
graph. One-file / same-file / tiny sequential work is `/build`, not this command. A
genuinely parallel programme is `/arbi-team`. Routing by shape: `AGENTS.md` §9.

## Why a command, not the agent

A Claude Code subagent cannot spawn subagents. Guilfoyle is a **read-only planner** and
arbi — the main loop — does every side-effecting step.

## Hard owner→agent table

Canonical copy: `.claude/agents/README.md`. Consult the owner of a work shape rather than
doing its job inline — it is cheaper in context and better reviewed.

## Flow

**0 — Envelope in.** Empty args = current #1. Red-team on THE ONE THING, a large envelope,
or a call that follows a ONE THING that didn't land.

**1 — Guilfoyle plans.** Task graph, specialist per node, execution order. One-file graphs
reroute to `/build`.

**2 — arbi executes the graph.** Surface rather than plan around: `AGENTS.md` §2 (capital,
`north-star.md`/the personal-use invariant, spend over the cap) and rule #11.

**3 — Collect + verify.** `make check` / targeted pytest. Risk-tiered consult per
`CLAUDE.md`. No mandatory three-agent review.

**4 — PR** on `claude/**`, opened **ready**, with its reversal-cost class and, for Amber,
the mitigation taken (`AGENTS.md` §6).

**5 — One readiness pass.** NOT-READY twice → stop with the gap list.

**6 — arbi lands it** (`AGENTS.md` §8) and watches the first production run that exercises
it. A red run is an incident (§7). Record the ledger row `task_type: mission`.
