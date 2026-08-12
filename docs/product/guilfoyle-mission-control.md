# Guilfoyle mission-control — how a mission gets built

**Status:** current (autonomy unlock pack, 2026-07-14)
**Scope:** the narrative of the arbi → Guilfoyle → builders execution stack; routing rules for missions
**Last verified:** 2026-08-12 (branch-protection gate status corrected in §Enforcement honesty; routing, ownership and grants unchanged) · 2026-07-14
**Owner:** James (governor); Guilfoyle's charter is `.claude/agents/guilfoyle.md`, its command is `.claude/commands/arbi-mission.md` — those are normative, this doc narrates
**Superseded by:** N/A

## The design principles (James, 2026-07-14 — verbatim required citations)

**arbi decides · arbi-red-team challenges · Guilfoyle orchestrates · reversible-work-builder
mutates · specialists execute/review · agent teams only for large parallel work ·
skills/allowed-tools remove prompt friction for reversible work · hooks/permissions/branch
protection stop dangerous work · the draft PR is the durable stopping point.**

## The stack

```
James        governor — objectives, risk, capital, boundaries, every merge/deploy
  ↓
arbi         product/operating authority — reconciles state, chooses THE ONE THING,
             names the mission; never fans out, never trades
  ↓
arbi-red-team  challenges THE ONE THING / the envelope BEFORE execution
  ↓
Guilfoyle    mission-control — task graph, specialist assignment, team topology,
             readiness verdict; read-only (plans and judges, never spawns/merges/prioritises)
  ↓
reversible-work-builder + specialists / agent teams
             the hands — edit, test, commit (through the review gate), on claude/** only
  ↓
draft PRs    the durable stopping point
  ↓
James        merge / deploy / capital / boundary decisions
```

Two structural facts keep this honest:

1. **No live nested spawn.** A subagent's `Agent(...)` allowlist is inert at runtime, so
   "arbi spawns Guilfoyle spawns a team" cannot be a live call chain. The command's **main
   loop** does every fan-out; Guilfoyle plans and judges only. Decide→do is bridged by a
   written mission envelope, not a handoff call
   (`docs/proposals/orchestrator-mode-2026-07-13.md`).
2. **Orchestration and mutation never share a process.** Guilfoyle holds `Read, Glob, Grep` —
   no Bash, no Edit. Mutations live on `reversible-work-builder` (and teammates built on its
   conduct), where the review gate and the PR-transaction-discipline block apply.

## Mission routing

| Work shape | Route |
|---|---|
| Single focused task (one fix, one doc, one analysis) | one specialist, directly |
| Multi-node mission, 1–2 PRs, bounded reversible work | `/arbi-mission` (Guilfoyle graph) |
| Large parallel: whole-project mining · product reality sweep · cross-layer feature · competing debug hypotheses · large parallel review | `/arbi-team` (topology + plan-approval gate, max 4 teammates) |
| One-file edits · same-file refactors · sequential bugs · tiny fixes · shared-mutable-state work · anything blocked on James's judgement | **never a team** — smallest sufficient route above |

Subagents are the default (low overhead, isolated context, report back); teams are the
exception that must earn their coordination cost. Teams additionally require the **local/user**
env `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — never a repo default.

## What Guilfoyle owns vs what it must never own

| Owns — plans and judges (the main loop executes each) | Never owns (routes up) |
|---|---|
| task graph + dependency order | product priority / THE ONE THING |
| teammate/specialist selection + file-area ownership | the north star |
| plan-approval criteria application (tests present, no boundary crossed, ownership + artifact stated — James's affirmative approval when attended-live) | risk appetite, capital policy |
| parallel-work tracking, conflict detection | merge / deploy (I6 = James) |
| the plan for test/review orchestration and draft-PR prep (main-loop steps 3–4 of `/arbi-mission`) | DB / Render mutations (I5 = James) |
| the readiness verdict (the window's morning report is assembled by the main loop from it) | its own charter (draft-via-PR only) |

Its single pushback channel is **executability evidence** routed to arbi/`arbi-red-team` —
never a competing priority call. This is the line that keeps arbi the authority: *arbi
chooses the mission; Guilfoyle executes the mission.*

## Enforcement honesty

Today the stack is prompt + doc + hook enforced: the review gate (R13-hardened) on commits,
`unattended-guard.sh` on unattended runs, no broker tool ever mounted (P6), secrets
gitignored. Skill `allowed-tools` is friction-removal, **not** a security boundary; deny
rules and hooks are the floor (`arbi-permission-model.md` §Runtime enforcement honesty).
Standing/unattended operation of any of this remains gated on branch protection for `main`,
the agent read-only DB role (R2), and the scorecard track record — unchanged by the pack.

**Gate status, recorded 2026-08-12: one of those three is now satisfied — standing autonomy
is still NOT granted.** Branch protection on `main` is **configured** (two rulesets live
since 2026-07-17, `asxos-main` id 19077432 and `main` id 18221894; classic protection
re-asserted 2026-08-12: PR required, `full-check` required, force-push and deletion blocked).
The other two gates — the agent read-only DB role (R2) and the scorecard track record —
are unchanged and still open, so the gate itself still holds and every mission stays
**attended, reversible, draft-PR-ceilinged** exactly as described above. Two caveats travel
with the satisfied gate: `enforce_admins: false`, so an admin-owned token bypasses it; and at
`required_approving_review_count: 0`, `.github/CODEOWNERS` is **advisory, not mechanical** —
so "hooks/permissions/branch protection stop dangerous work" (the design principle above)
holds for agents and non-admin credentials, not for an admin-scoped token. Verify before
citing: `gh api repos/Jp8617465-sys/asxos/branches/main/protection`. Rationale and full
record: `docs/proposals/arbi-guard-carveouts-2026-08-12.md`.
