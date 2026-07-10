# arbi run — attended multi-agent dispatch — `/arbi-run`

`$ARGUMENTS` = the objective (e.g. `clean up the roadmap docs`, `audit the tax module for
rule-#11 leaks`), or empty = arbi's current #1 next action from `roadmap-state.md`.

**This is how you get arbi to call agents today.** The `arbi` subagent cannot spawn
subagents — but the main loop can. So `/arbi-run` has arbi **plan** the work and name the
specialists, then the main loop **fans them out in parallel** and collects the results.
It is **attended** (you invoked it) and **reversible** — the governor-directed bridge to
real self-dispatch, deliberately distinct from *standing unattended* dispatch (PR 8, which
stays gated on Model A resolved + DB role scoping + track record).

## Why a command, not the agent

A Claude Code subagent cannot spawn other subagents (the same reason `/pm-review` and
`/discover-macro` are commands). arbi decides *what/who/success/must-not-touch*; the main
loop executes the fan-out and reuses the existing specialist agents as-is.

## Step 1 — arbi plans

Dispatch the `arbi` subagent with `$ARGUMENTS` (or "use your current #1 next action from
roadmap-state.md"). It returns the ranked work and, for each item to dispatch, a scoped
**NEXT PROMPT**: *mission · owner (which specialist agent) · success criteria · what must
NOT be touched · required citations*. arbi resolves conflicts via its authority ladder and
honours the circuit breakers — it will **refuse to plan** anything irreversible or
capital-facing, surfacing it for James instead.

## Step 2 — the main loop fans out the specialists

For each NEXT PROMPT arbi produced, dispatch the named specialist agent **IN PARALLEL**
(single message), scoped exactly to that prompt. Owner → roster:

| Owner | Agent | Mutates? |
|---|---|---|
| schema / API / write-path / DB design | `backend-architect` | no (advisory) |
| secrets / permissions / tool blast radius | `security-engineer` | no |
| behaviour-preserving code cleanup | `refactoring-expert` | **code** (runs tests) |
| docs / runbooks / handoffs | `technical-writer` | **docs** |
| module boundaries / structural change | `system-architect` | no |
| tax spec↔test↔code | `tax-spec-conformance` | no |
| portfolio invariants | `portfolio-invariant-guard` | no |
| live-portfolio evidence | the 5 investment-analysis agents | no |

**Rule: only REVERSIBLE work is dispatched autonomously** (read · analyse · draft · docs ·
draft-PR). If arbi's plan implies an **irreversible** step — merge, deploy, migration, DB
write, secret handling, capital action — **STOP and surface it for James; do not dispatch
it.** If an agent reports "can't do this without X," record the gap; don't invent a
substitute.

## Step 3 — collect, synthesize, record

Wait for all specialists. Synthesize their outputs into: what was found/done, the concrete
diffs proposed, and the refreshed NEXT PROMPT. For reversible doc/code edits, apply them
**only after the review loop** (`security-engineer` / `refactoring-expert` /
`technical-writer` on the staged diff); for anything larger, present the plan. Append the
run to `docs/product/arbi-run-ledger.md` and, if it settled a ranked call, to
`docs/product/decision-log.md` (Tier-2 doc write — authorised because you invoked this).

## Boundaries

- **Attended + reversible only.** Governor-invoked each time — this is **not** standing
  unattended dispatch (PR 8 / Tier 4 standing), which is gated (`arbi-permission-model.md`).
- **Never dispatch or perform:** merge · deploy · migration · DB write · secret handling ·
  capital action · a Model A-derived capital recommendation · a boundary change. Those stop
  for James (Tiers 5–7).
- Every specialist output cites evidence; arbi's synthesis carries the citations. No
  unsourced claim presented as current truth (circuit breaker).
- Respect rule #11: arbi may dispatch work to *investigate/resolve* Model A (e.g. the decay
  check), never to *act on* its output for capital.
