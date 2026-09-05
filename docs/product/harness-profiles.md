# Harness profiles — official permission modes and two-speed routing

**Status:** current
**Scope:** how Claude Code's official permission modes (`plan` / `auto` / `dontAsk`)
map onto asxos work; the main-loop fan-out topology; the two-speed command split
(`/build` vs `/arbi-mission`); the hard owner→agent roster; rejected alternatives
**Last verified:** 2026-08-24 (Amendment G — identity path + auto-merge + user `auto` measurement; modes table unchanged)
**Owner:** James (governor) applies local mode; arbi / the main loop obey this file
**Superseded by:** N/A
**Supersedes as operating SoT:** the profile / review-ceremony claims in
`docs/proposals/permission-and-guard-friction-2026-08-21.md` and
`docs/proposals/production-loop-optimisation-2026-08-20.md` §5–§6. Those files
stay as the measured evidence and six-point record; they are not the operating
map. The blast-radius ladder stays `arbi-permission-model.md`.

This file is the source of truth for *which official Claude Code mode a session
uses* and *which command carries the work*. It does not change I0–I6 or P0–P6.

---

## Official modes only — not a custom 3-profile JSON

| Official mode | asxos use | Ladder slice | Command |
|---|---|---|---|
| `plan` | Wake, explore, Guilfoyle planning, red-team | I0–I1 | `/arbi`, `arbi-red-team`, `guilfoyle` as planner |
| `auto` | Attended reversible build | I2–I4 | `/build`, `/arbi-mission` |
| `dontAsk` | Locked-down CI / `claude-execute` | I0–I4 on the existing allowlist | CI, `claude-execute.yml` |

`bypassPermissions` is **forbidden for every launch**. `acceptEdits` is not the
standing default. `defaultMode: "auto"` in project `settings.json` is inert;
James applies it in `~/.claude/settings.json` — see
`docs/product/runbooks/claude-code-user-settings.md`.

Deny rules and hooks still bind in every mode. `authority-guard.sh` is ALWAYS-ON.

---

## Orchestration topology — the main loop fans out

A Claude Code **subagent cannot spawn subagents**
(`docs/proposals/orchestrator-mode-2026-07-13.md`). Live chain:

```
James → /arbi → arbi-red-team (ONE THING / large envelope only)
      → /build  XOR  /arbi-mission  XOR  /arbi-team
      → main loop fans out specialists / reversible-work-builder
      → draft PR → James merges
```

Guilfoyle is a read-only planner. Orchestration and mutation never share a process.

---

## Two speeds

| Speed | Command | Shape |
|---|---|---|
| Fast | `/build` | One file, same-file refactor, tiny sequential fix |
| Mission | `/arbi-mission` | Multi-node reversible work, 1–2 PRs |
| Team | `/arbi-team` | Large parallel only |

Empty `/arbi-mission` arguments wrap arbi's current #1 from `roadmap-state.md`.

---

## Hard owner→agent table

If a command's copy diverges, **this file wins**.

| Owner (work shape) | Agent / command | Mutates? |
|---|---|---|
| priority / THE ONE THING | `arbi` via `/arbi` | no |
| challenge THE ONE THING or a large envelope | `arbi-red-team` | no |
| mission graph + readiness | `guilfoyle` (plans only) | no |
| one-file / same-file / tiny sequential | `/build` | yes (that file) |
| multi-node reversible mission | `/arbi-mission` main-loop dispatcher | via specialists |
| large parallel (team-shaped only) | `/arbi-team` | via teammates |
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

Only reversible work is dispatched. I5/I6 / P5/P6 STOP for James.

---

## Risk-tiered consult (production-loop §6, now SoT)

The review-gate hook is **removed**. Quality is `make check` + `full-check` CI.

| Tier | Surface | Consult |
|---|---|---|
| **A** | `asxos/**`, `jobs/**`, `scripts/*.py`, behaviour-bearing tests | `security-engineer` when triggered; `refactoring-expert`; `technical-writer` |
| **B** | `docs/**` and non-authority config | At most one `technical-writer` on load-bearing docs. None on session records |
| **C** | Authority paths still deny-listed | James only |

---

## Cursor / R17

Cursor Cloud Agents do not honour `.claude/settings.json` allow/deny or this
repo's Claude hook fence (`risk-register.md` R17). `AGENTS.md` plus
`.cursor/hooks.json` (I5/I6, failClosed, no cwd-fail-closed) are the prepared
port. An out-of-fence red-team PASS is not a vet (`arbi-evals.md` G8).

---

## Rejected list

1. Custom 3-profile JSON beside official modes
2. `bypassPermissions` / `Bash(*)` / `acceptEdits` as default
3. Fighting nested spawn (use main-loop fan-out)
4. `/arbi-run` as the live dispatch bridge
5. Mandatory three-agent review on every change
6. `defaultMode: "auto"` in project settings
7. Standing / unattended mission dispatch (still gated)
8. Allowlisting rotating MCP UUIDs
9. Docs-only auto-merge of `docs/product/**` — **widened 2026-08-24 (Amendment G ruling 3):** no auto-merge of any path. Keep the click. Not earned until the check suite is trustworthy and a CFR/MTTR baseline exists.
10. Session lift-and-reinstate guards
11. `gh run rerun`

---

## James-owned follow-ups

| Action | Where |
|---|---|
| Set `permissions.defaultMode` to `"auto"` in `~/.claude/settings.json` | `docs/product/runbooks/claude-code-user-settings.md` — Amendment G ruling 1; re-read permission log ~2026-08-31 before any hook `allow` rewrite |
| Pin `supabase-ro` alias / OAuth MCP servers | friction proposal §4 |
| GitHub App reviewer (`asxos-arbi-approver`) | `docs/product/runbooks/arbi-approver-github-app.md` — Amendment G ruling 2; second *account* runbook is the rejected alternative |
| `supabase-ro` → `asxos_agent_ro` re-point | agent-db-readonly-role design |
| Standing 7b / Guilfoyle-as-main-thread | later, on evidence |
| `docs/README.md` map row for this file | deny-listed; James applies |

---

## Standing dispatch — lane C: `backlog-roll` (Amendment K, 2026-09-05)

Added under the same seven conditions Amendment H (2026-09-02, carried by #199) binds
every standing lane to; this section is appended here rather than into that section so
the two PRs merge in either order. Lanes A (`nightly-triage`) and B (`weekly-toolwatch`)
are **reactive** — a red run, a weekly changelog. Lane C is **proactive**: a deterministic
picker decides, before any agent runs, which backlog items this fire may build.

| | Lane C |
|---|---|
| Workflow | `.github/workflows/backlog-roll.yml` — owner-only `workflow_dispatch` while the producer write-token P1 is open; explicit per-run acknowledgement required |
| Pre-gate | `scripts/backlog_next.py` over `docs/product/backlog.yaml` — no model. Eligible = arbi-owned, `route` build/mission, `status` open, every `depends_on` done, every `paths` entry outside the denied set copied from `unattended-guard.sh` + `settings.json` (drift-tested). Exit 3 = nothing buildable; the click-list is still emitted and the fire records a heartbeat |
| Arming | job-scoped `ARBI_UNATTENDED=1` + STEP-0 self-check. The producer receives OAuth, deadman, and repo write tokens; that surface is an explicit gated residual, not a secret-free boundary |
| Agent | `claude-code-action`, `--allowedTools` identical to lane A — no `pytest`, no `gh pr create`, no MCP. One branch per item off `main`, never stacked; touches only the item's `paths`; sets that item `built-unmerged` in `backlog.yaml` on its own branch only |
| Verify | separate `contents: read` matrix jobs at validated immutable SHAs, `persist-credentials: false`, no OAuth/deadman/write token. A red matrix opens no PR |
| PR | separate `pull-requests: write` publisher rechecks each remote SHA, then `gh pr create --draft` |
| Artifact-per-fire | separate record job, which never checks out agent-authored code, appends one row to `docs/product/backlog-ledger.md` on `claude/backlog-ledger` |
| Deadman ★ | `HC_BACKLOG_URL`, checked at **STEP 0** — unset **fails the run** (condition 5, hardened). Pings the check on success and `/fail` otherwise |

**Primary product is the click-list.** Once the Amendment H train lands the backlog is
mostly James's, and most fires will exit at the pre-gate having only re-stated what is
blocked on him. That is the intended behaviour, not a defect. The builder half earns its
keep on the residue: proposal drafts, doc-drift sweeps, test hygiene, `m14_candidate_*`
items as they are un-parked.

**What it cannot do, unchanged from lanes A/B:** merge, un-draft, push to `main`, apply
a migration, touch a secret, edit `.github/**` or any authority path, touch
capital-adjacent code, flip a dark surface, approve a theme member, or calibrate risk.
Standing dispatch was granted; standing landing was not. The workflow remains manually gated.
Automatic triggers stay blocked until backlog item A-22 closes the branch-scoped credential P1.
