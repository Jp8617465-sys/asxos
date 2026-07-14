# arbi team — agent-teams mission execution — `/arbi-team`

`$ARGUMENTS` = a mission envelope (or a path/ref to one). No default: a team mission is never
inferred — arbi (or James) names it explicitly.

**This is the agent-teams form of `/arbi-mission`, for LARGE parallel missions only.** Same
envelope, same red-team vet, same draft-PR ceiling — plus a team topology and a
**plan-approval gate**. Agent teams are Anthropic-experimental and disabled by default; this
command runs only when the operator has set **local/user** config
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (never committed as a repo default — see
`docs/product/runbooks/agent-team-mission.md`). It is **attended + reversible**:
governor/arbi invoked, never standing/unattended (the PR 7b/8 promotion preconditions in
`arbi-permission-model.md` stay gated).

## Qualifying gate — refuse and reroute if the mission is not team-shaped

**This list is canonical** — other files (the `agent-team-mission` skill, the runbook,
`guilfoyle-mission-control.md`, `/arbi-mission`'s routing note) summarise or link here;
edits happen here first:

- **GOOD:** whole-project mining pass · product reality sweep · cross-layer feature
  (DB + domain + CLI + brief + tests) · competing debugging hypotheses · large parallel
  review/audit.
- **BAD → refuse, route to `/arbi-mission` or a single specialist:** one-file edits ·
  same-file refactors · sequential bugs · tiny fixes · heavy shared mutable state · anything
  blocked on James's judgement before progress.

Teams add real overhead (tokens, coordination, conflict risk); a mission that doesn't
genuinely parallelise is *slower* as a team.

## Flow

**0 — Envelope in + red-team vet.** Exactly as `/arbi-mission` step 0: `arbi-red-team`
challenges the mission before execution; CHALLENGE → back to arbi/James.

**1 — Guilfoyle plans the team topology.** Dispatch `guilfoyle` with the envelope. Beyond the
task graph, its team plan states: teammates (**max 4 by default** — more requires explicit
James approval in the envelope), each teammate's **file-area ownership** (disjoint wherever
possible), each teammate's **expected artifact**, and the readiness criteria.

**2 — Plan-approval gate (before ANY implementation).** Approval criteria: the plan
**includes tests** · **crosses no DB/Render/merge/deploy/capital boundary** · **states file
ownership** · **states the expected artifact** per teammate. **Who approves (canonical
resolution, red-team 2026-07-14):** the lead/Guilfoyle *applies the four criteria*
mechanically — a plan failing any criterion never proceeds, no one can waive that. On top:
**attended-live**, James sees and approves the plan before implementation; **inside a
James-granted window** (the recipe grant is the standing authorisation), Guilfoyle's
criteria-application is the gate and the full approved plan lands **verbatim in the morning
report** — a borderline plan is a JAMES_NEEDED pivot, not a judgement call. No teammate
implements before this gate passes.

**3 — Teammates execute in owned areas.** Each teammate is the builder pattern
(`reversible-work-builder` conduct): `claude/**` branches, review gate on commits, and the
**PR transaction discipline** block
(`docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`) — binding on every
teammate that touches a branch. File-ownership conflicts detected → pause the overlapping
teammate, resolve in the plan, resume.

**4 — Collect + verify.** Tests + the review loop on the combined diff, per CLAUDE.md.

**5 — ONE draft PR.** Converge to a single draft PR (or one per genuinely independent module
if the approved plan said so). Never merge, never auto-merge (I6 = James).

**6 — One readiness pass + stop + record.** `pr-readiness` checklist; ledger row
(`task_type: team-mission`); hand back to James or `/arbi-close`. NOT-READY twice → stop with
the gap list.

## Boundaries

Carried verbatim from `/arbi-mission`:

- **Attended + reversible only.** Governor/arbi invoked each time — not standing dispatch
  (PR 8 / I4 standing stays gated: `arbi-permission-model.md`).
- **Never dispatch or perform:** merge · deploy · migration · DB write · Render mutation ·
  secret handling · capital action · a Model A-derived capital recommendation · a boundary
  change. Those STOP for James (I5–I6 / P5–P6).
- **Guilfoyle plans; it never prioritises.** Its only pushback is executability evidence to
  `arbi-red-team` / arbi — never a competing priority call.
- **No permission broadening.** `/arbi-team` runs on the existing tool permissions +
  interactive prompts + branch protection + the review gate. It adds no `allow` rules, never
  uses `bypassPermissions`, and never runs unattended.

## Design principles (required citations — James, 2026-07-14)

arbi decides · arbi-red-team challenges · Guilfoyle orchestrates · reversible-work-builder
mutates · specialists execute/review · agent teams only for large parallel work ·
skills/allowed-tools remove prompt friction for reversible work · hooks/permissions/branch
protection stop dangerous work · **the draft PR is the durable stopping point**.
