# arbi mission — Guilfoyle mission-control execution — `/arbi-mission`

`$ARGUMENTS` = a mission envelope (or a path/ref to one), or empty = build one from arbi's
current #1 next action (`roadmap-state.md`) by running `/arbi` first.

**This is the multi-node dispatcher.** The main loop fans out specialists against a
Guilfoyle task graph. One-file / same-file / tiny sequential work is `/build`, not
this command. Large parallel work is `/arbi-team`. `/arbi-run` is a deprecated stub
that redirects here. Attended + reversible; draft-PR ceiling.
Operating map: `docs/product/harness-profiles.md`.

## Why a command, not the agent

A Claude Code subagent cannot spawn subagents. Guilfoyle is a **read-only planner**
and the **main loop** does every side-effecting step.

## Hard owner→agent table

Canonical copy: `docs/product/harness-profiles.md`. **Only reversible work is dispatched.**

| Owner (work shape) | Agent / command | Mutates? |
|---|---|---|
| priority / THE ONE THING | `arbi` via `/arbi` | no |
| challenge THE ONE THING or a large envelope | `arbi-red-team` | no |
| mission graph + readiness | `guilfoyle` (plans only) | no |
| one-file / same-file / tiny sequential | **refuse — route to `/build`** | — |
| schema / API / write-path / DB design | `backend-architect` | no |
| secrets / permissions / tool blast radius | `security-engineer` | no |
| behaviour-preserving code cleanup | `refactoring-expert` | **code** |
| docs / runbooks / handoffs | `technical-writer` | **docs** |
| module boundaries / structural change | `system-architect` | no |
| feature with no written spec | `requirements-analyst` | no |
| dependency / external service | `tech-stack-researcher` | no |
| hot path | `performance-engineer` | no |
| tax spec↔test↔code | `tax-spec-conformance` | no |
| portfolio invariants | `portfolio-invariant-guard` | no |
| live-portfolio evidence | the 5 investment-analysis agents | no |
| mutation on `claude/**` or `cursor/**` | `reversible-work-builder` | **code/docs** |

## Flow

**0 — Envelope in.** Empty args = current #1. Red-team only on THE ONE THING or a large envelope.

**1 — Guilfoyle plans.** One-file graphs reroute to `/build`.

**2 — Main loop executes the graph.** I5/I6/P5/P6 → STOP for James.

**3 — Collect + verify.** `make check` / targeted pytest. Risk-tiered consult. No mandatory three-agent review.

**4 — Draft PR** on `claude/**` or `cursor/**`. Never merge.

**5 — One readiness pass.** NOT-READY twice → stop.

**6 — Stop + record.** Ledger row `task_type: mission`.
