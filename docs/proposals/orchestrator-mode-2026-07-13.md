# Orchestrator mode — arbi plans, Guilfoyle runs (lean sketch)

**Status:** proposed — lean sketch, NOT a build order. Deliberately deferred behind product work.
**Scope:** how arbi (decides *what*) and Guilfoyle (orchestrates *how*) compose into a multi-agent
execution loop **without** violating the nested-spawn constraint, the permission ladders, or the
personal-advice / Model-A firewalls.
**Last verified:** 2026-07-13
**Owner:** arbi drafts; James approves. Guilfoyle's charter + `/arbi-mission` land in PR #31 (pending merge);
this proposal is the layer *above* that PR, not part of it.
**Depends on:** PR #31 merged **and exercised once** (a real `/arbi-mission` dry run); R13 (PR #35) closed;
branch protection on `main`; agent read-only DB role (`docs/proposals/agent-db-readonly-role-design-2026-07-11.md`, R2).
**Superseded by:** N/A

---

## The decision (already made, recorded here for the record)

- **arbi** is the product / operating authority. It decides **what** gets built and in what order,
  reconciles state against the north star, and names the mission. It never fans out on its own and
  never trades (`.claude/agents/arbi.md`, `docs/product/arbi-constitution.md`).
- **Guilfoyle** is mission-control / execution lead. Given a mission arbi has named, it decides **how**:
  which specialists, in what topology (fan-out, pipeline, verify-then-synthesize), and drives them to a
  reviewable artifact. It decides execution mechanics, never product direction or capital.
- **Specialists** (the existing 21 subagents) are the workers. Unchanged.

This is a controller/executor split, not a demotion of arbi: arbi stays the GOAT that sets the objective;
Guilfoyle is the hands that carry a *single named mission* to done.

## The one constraint that shapes the whole design: no live nested spawn

A Claude Code **subagent cannot fan out.** A subagent's `Agent(...)` allowlist is ignored at runtime —
only a **main-thread** agent (the one the CLI launched, `claude --agent <name>`) has an enforceable
spawn allowlist. So "arbi spawns Guilfoyle, Guilfoyle spawns a team" **cannot work as a live call chain**:
whichever of the two is a subagent has an inert `Agent` tool.

Everything below follows from accepting this rather than fighting it. This is also why the existing fan-out
commands (`/pm-review`, `/arbi-run`, `/discover-macro`) do their fan-out from the **main loop**, not from
inside a subagent — the same pattern generalizes here.

## Guilfoyle's two modes (same charter, different launch context)

| Launch context | What Guilfoyle can do | Use |
|---|---|---|
| **As a subagent** (spawned by the main loop) | Read-only planner: `Read/Glob/Grep` + `supabase-ro`. Returns a **mission plan** as text — roster, topology, stop conditions, review gates. Its `Agent` tool is inert; it does not run anyone. | arbi/main-loop asks "how would you run mission X?" and gets a plan. |
| **As the main-thread agent** (`claude --agent guilfoyle`) | Live orchestrator: its `Agent(roster)` allowlist is enforceable, so it actually fans the roster out and drives the mission to a draft PR. | James (or a gated scheduler) launches Guilfoyle to *execute* a mission arbi already scoped. |

The charter (`.claude/agents/guilfoyle.md`, PR #31) ships as the **read-only planner** first. The live mode
is a *separate launch*, gated (below), added only after the planner has been exercised.

## The bridge: a mission-brief, not a live handoff

Because arbi-led and Guilfoyle-led are separate launches, decide→do is bridged by an **artifact**, not a
call:

1. **arbi** (`/arbi`) names the single highest-leverage mission and writes it down (decision-log + a mission
   brief: objective, boundaries, definition-of-done, reversibility class).
2. **Guilfoyle** is launched as the main-thread agent against that brief (attended, by James) — or, in
   planner mode, is asked for the execution plan which the main loop then runs via `/arbi-mission`.
3. Guilfoyle fans out the roster, gathers results, and produces **one reviewable draft PR**.
4. arbi (`/arbi-close`) records what got built and whether it worked.

No step requires a subagent to spawn another subagent. The brief is the seam.

## Permission posture — the orchestrator holds no hands

From the security review of this design:

- **Guilfoyle gets `Agent(roster)` + `Read/Glob/Grep` + `supabase-ro` and nothing else — no `Bash`, no `Edit`.**
  An orchestrator that can also mutate is two authorities in one process. Mutation capability lives on a
  dedicated **`reversible-work-builder`** specialist that Guilfoyle *dispatches*; the builder is where
  `Edit`/`Bash` (and the review gate) apply. Orchestration and mutation stay in separate processes.
- **Only two floors are mechanical today:** no broker/execution tool is ever mounted (P6 is enforced by
  absence), and secrets are gitignored. Everything else on the ladders (`docs/product/arbi-permission-model.md`)
  is prompt+doc enforced.
- **`unattended-guard.sh` does not cross process boundaries.** It is a same-process pre-filter; it cannot
  police a separately-launched teammate. So a *standing/unattended* Guilfoyle is out until the mechanical
  backstops exist.
- **`bypassPermissions` is forbidden** for any of these launches.

## Prerequisites (gates) — none of this goes standing until these land

1. **R13 (PR #35)** — the review gate no longer races same-step staging. *Closed — merged 2026-07-14.*
2. **Branch protection on `main`** — currently NOT configured (confirmed when PR #26 merged with no
   required-review block). This is the layer-2 backstop for any merge authority; must exist before any
   standing dispatch.
3. **Agent read-only DB role (R2)** — `agent-db-readonly-role-design-2026-07-11.md`. Until agents hit a
   role that *cannot* write, the SELECT-only instruction is prompt-level only.

Until all three: orchestrator mode is **attended-only, reversible-only, draft-PR ceiling** — exactly the
envelope the overnight window ran under.

## Minimal first step (after #31 merges and is exercised once)

Enable the **planner** path end-to-end: `/arbi-mission` asks Guilfoyle-as-subagent for a plan, the main loop
runs the named roster, one draft PR results. That needs no new capability — the roster already exists and the
fan-out is main-loop, as with `/pm-review`.

The **live main-thread Guilfoyle** is a one-line allowlist addition — but per the red-team, that "one line" is
really a **constitutional boundary amendment** (it grants standing dispatch authority), so it is
**James-approved, not self-enacted**, and only after the three gates above.

## Explicitly deferred (red-team challenge, accepted)

- **Full agent-teams / standing unattended multi-agent mode** is **infrastructure, not moat.** It stays behind
  the product work (roadmap item #29 / the model-independent moat). Build the thing that makes the product
  worth orchestrating *for* before scaling the orchestration.
- **Before committing to the roster-allowlist approach, prototype the skill-scoped `allowed-tools` alternative**
  (red-team R-A4): a `/arbi-mission` *skill* that scopes tools per invocation may give the same control with
  less standing surface than a always-on main-thread agent. Compare the two on a real mission before picking.

## What this proposal is not

Not a green light to build teams. It records the agreed shape, the hard constraint that rules out the naive
"spawn-a-team-that-spawns-a-team" design, and the gates. The next action it authorizes is small: land + exercise
PR #31's planner, keep everything attended and reversible, and revisit the live-orchestrator line item only after
the moat work and the three gates.
