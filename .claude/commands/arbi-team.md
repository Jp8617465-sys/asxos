# arbi team — agent-teams mission execution — `/arbi-team`

`$ARGUMENTS` = a mission envelope (or a path/ref to one). No default: a team mission is never
inferred — arbi (or James) names it explicitly.

**This is the agent-teams form of `/arbi-mission`, for LARGE parallel missions only.** Same
envelope, same red-team vet, plus a team topology. Agent teams are Anthropic-experimental;
this command runs only with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (set in
`.claude/settings.json` `env` — see `docs/product/runbooks/agent-team-mission.md`). Teams are
experimental in Claude Code: if one misbehaves, fall back to `/arbi-mission` (`AGENTS.md` §9).

## Qualifying gate — refuse and reroute if the mission is not team-shaped

**This list is canonical** — other files (the `agent-team-mission` skill, the runbook,
`guilfoyle-mission-control.md`, `/arbi-mission`'s routing note) summarise or link here;
edits happen here first:

- **GOOD:** whole-project mining pass · product reality sweep · cross-layer feature
  (DB + domain + CLI + brief + tests) · competing debugging hypotheses · large parallel
  review/audit.
- **BAD → refuse, route to `/build`, `/arbi-mission`, or a single specialist:** one-file edits ·
  same-file refactors · sequential bugs · tiny fixes · heavy shared mutable state · anything
  blocked on James's judgement before progress (`AGENTS.md` §2).

Teams add real overhead (tokens, coordination, conflict risk); a mission that doesn't
genuinely parallelise is *slower* as a team.

**Two-speed routing:** one-file edits go to `/build`; `/arbi-mission` is the multi-node
dispatcher. See `AGENTS.md` §9 and `.claude/agents/README.md`.

## Flow

**0 — Envelope in + red-team vet.** Exactly as `/arbi-mission` step 0: `arbi-red-team`
challenges the mission before execution; CHALLENGE → re-rank and say why in the log.

**1 — Guilfoyle plans the team topology.** Dispatch `guilfoyle` with the envelope. Beyond the
task graph, its team plan states: teammates (**max 4 by default**), each teammate's
**file-area ownership** (disjoint wherever possible), each teammate's **expected artifact**,
and the readiness criteria.

**2 — Sanity-check the plan before any teammate implements.** Not a gate that waits on
anyone — arbi applies it and proceeds. A plan that **omits tests**, **does not state file
ownership**, or **does not name each teammate's expected artifact** is not ready to
implement: send it back to Guilfoyle rather than starting. A plan that crosses `AGENTS.md`
§2 stops and goes to James.

**3 — Teammates execute in owned areas.** Each teammate follows `reversible-work-builder`
conduct: `claude/**` branches and the **PR transaction discipline** block
(`docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`) — binding on every
teammate that touches a branch. File-ownership conflicts detected → pause the overlapping
teammate, resolve in the plan, resume.

**4 — Collect + verify.** `make check` and the risk-tiered consult on the combined diff, per
`CLAUDE.md`. Where a lane runs the suite as its own workflow step against the pushed branch,
that is the verification — not a teammate's self-report.

**5 — ONE PR.** Converge to a single PR (or one per genuinely independent module if the plan
said so), opened **ready**, carrying its reversal-cost class and, for Amber, the mitigation
taken (`AGENTS.md` §6).

**6 — One readiness pass, then land.** `pr-readiness` checklist; NOT-READY twice → stop with
the gap list. arbi lands it (`AGENTS.md` §8), watches the first production run that exercises
it, and records the ledger row (`task_type: team-mission`).

## Boundaries

- **`AGENTS.md` §2 is the only stop:** capital, `north-star.md` and the personal-use
  invariant, spend above the cap. Surface those; never plan around them.
- **Rule #11** — never dispatch or accept a Model A-derived capital recommendation.
- **Secrets** — never print, expand or paste a secret value anywhere (`AGENTS.md` §13).
- **Guilfoyle plans; it never prioritises.** Its only pushback is executability evidence to
  `arbi-red-team` / arbi — never a competing priority call.
- **No permission broadening.** `/arbi-team` runs on the existing tool permissions and the
  `main` ruleset. It adds no `allow` rules and never uses `bypassPermissions`.

## Design principles (required citations — James, 2026-07-14)

arbi decides · arbi-red-team challenges · Guilfoyle orchestrates · reversible-work-builder
mutates · specialists execute/review · agent teams only for large parallel work ·
skills/allowed-tools remove prompt friction · the `main` ruleset and secret scanning stop
dangerous work · **arbi lands the result and watches the run that exercises it**.
