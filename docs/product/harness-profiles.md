# Harness profiles — official permission modes and two-speed routing

**Status:** current
**Scope:** how Claude Code's official permission modes (`plan` / `auto` / `dontAsk`)
map onto asxos work; the main-loop fan-out topology; the two-speed command split
(`/build` vs `/arbi-mission`); the hard owner→agent roster; rejected alternatives
**Last verified:** 2026-09-08 (`AGENTS.md` state and risk contract; Amendments H/K remain
the narrower scheduled-producer profile and stay draft-only)
**Owner:** James (governor) applies local mode; arbi / the main loop obey this file
**Superseded by:** N/A
**Supersedes as operating SoT:** the profile / review-ceremony claims in
`docs/proposals/permission-and-guard-friction-2026-08-21.md` and
`docs/proposals/production-loop-optimisation-2026-08-20.md` §5–§6. Those files
stay as the measured evidence and six-point record; they are not the operating
map. The blast-radius ladder stays `arbi-permission-model.md`.

This file is the source of truth for *which official Claude Code mode a session
uses* and *which command carries the work*. `AGENTS.md` is the authority source;
`arbi-permission-model.md` maps the legacy I0–I6/P0–P6 names to it.

---

## Official modes only — not a custom 3-profile JSON

| Official mode | asxos use | Ladder slice | Command |
|---|---|---|---|
| `plan` | Wake, explore, Guilfoyle planning, red-team | I0–I1 | `/arbi`, `arbi-red-team`, `guilfoyle` as planner |
| `auto` | Attended reversible build | I2–I4 | `/build`, `/arbi-mission` |
| `dontAsk` | Locked-down CI / `claude-execute` | I0–I4 on the existing allowlist | CI, `claude-execute.yml` |
| `dontAsk` | **Standing gated lanes (Amendments H/K)** | I0–I4, per-workflow allowlist, `ARBI_UNATTENDED=1` | `nightly-triage.yml`, `weekly-toolwatch.yml`, `backlog-roll.yml` |

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
      → draft PR
          ATTENDED: James merges
          attested STANDING: risk-classify gates agent-requested squash merge
            Green: checks pass
            Amber: checks pass + James approves current head

owner-only workflow_dispatch (current gated posture) → workflow fires /arbi-mission with a fixed envelope
      → same fan-out, same specialists
      → draft PR → James merges          ← ARBI_UNATTENDED remains draft-only
```

Guilfoyle is a read-only planner. Orchestration and mutation never share a process.

---

## Two speeds

| Speed | Command | Shape |
|---|---|---|
| Fast | `/build` | One file, same-file refactor, tiny sequential fix |
| Mission | `/arbi-mission` | Multi-node reversible work, 1–2 PRs |
| Team | `/arbi-team` | Large parallel only |
| Standing | gated lane → `/arbi-mission` | Owner-dispatched, one finding per fire until the credential P1 closes |

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

Only reversible work is dispatched. Scheduled `ARBI_UNATTENDED=1` remains at the
draft-PR ceiling. Interactive standing landing follows `AGENTS.md` §5–§9;
P5/P6 and every Red boundary remain James-only or permanently unavailable.

---

## Risk-tiered consult (production-loop §6, now SoT)

The review-gate hook is **removed**. Quality is `make check` + `full-check` CI.

| Tier | Surface | Consult |
|---|---|---|
| **A** | `asxos/**`, `jobs/**`, `scripts/*.py`, behaviour-bearing tests | `security-engineer` when triggered; `refactoring-expert`; `technical-writer` |
| **B** | `docs/**` and non-authority config | At most one `technical-writer` on load-bearing docs. None on session records |
| **C** | Authority paths still deny-listed | James only |

---

## Standing dispatch — Amendment H (2026-09-02)

James's ruling as governor: lift the attended-only clause so an approved mission envelope may
run on a schedule. This supersedes the "Attended only" sections in `.claude/agents/guilfoyle.md`,
`.claude/agents/reversible-work-builder.md` and `.claude/commands/arbi-team.md`.

**What was granted:** standing *dispatch* — a scheduled workflow may fire `/arbi-mission`
unattended, fan out specialists, build on a `claude/**` branch, and open a **draft** PR.

**What was NOT granted to these scheduled producer lanes:**

- **No scheduled landing** — `ARBI_UNATTENDED=1` cannot ready or merge a PR,
  deploy, push to `main`, apply a migration, write production data or handle a
  secret. The interactive attested-`STANDING` merge path in `AGENTS.md` is a
  separate profile and does not flow into these workflows.
- **No auto-merge, any path** — rejected-item 9, widened 2026-08-24 (Amendment G ruling 3).
  Keep the click.
- **P5/P6 untouched** — no capital-policy change, no execution. s766B firewall stands.
- **Rule #11 untouched** — no Model A output as a basis for capital.

So the two-key property survives by construction: `.claude/settings.json` denies
`Edit(/.github/**)` and automatic triggers work only from the default branch, so an agent can
neither author nor arm one. Merging installs a lane for manual use; a later reviewed change is
required to add an automatic trigger.

**Conditions every standing lane must meet** (a lane that cannot meet these is not eligible):

1. `ARBI_UNATTENDED=1` in the workflow's job-level `env:` — scoped to that workflow, never the
   shared interactive environment.
2. **Credential-free verification.** Agent-authored code runs only in a separate
   `contents: read` job at a validated immutable SHA, with `persist-credentials: false` and no
   OAuth, deadman URL, or write token. The producer's repo write token remains the open P1.
3. **Verification runs as a workflow step, not an agent Bash call.** `unattended-guard.sh:285-287`
   denies unscrubbed `pytest`; running the suite as its own step sidesteps that *and* converts a
   self-report into a CI fact.
4. **Artifact-per-fire, written mechanically.** Every fire appends a findings-log row as a
   workflow step — including nothing-cycles. This is not a style preference: the two prior loops
   (7a, secperf) both died as *unobserved silence*, and `roadmap-state.md:1254` records that
   their "quality and liveness problems are the same problem." A fire that leaves no commit is
   indistinguishable from a fire that never happened.
5. **A Healthchecks deadman per lane**, pinged every fire. `nightly-check.yml:77-87` is the pattern.
6. **Owner-only `workflow_dispatch` while the producer-token P1 is open.** A green manual run is
   necessary evidence but is not authority to add `schedule` or `workflow_run`; automatic
   triggers require the branch-scoped credential control to be designed and red-teamed first.
7. **A change-detector pre-gate** where the lane's evidence base is commit-driven (skip for
   calendar-driven lanes like production-timing trend, which regress with zero commits).

**Dissent recorded.** `guilfoyle` returned NOT-READY on the original envelope and `system-architect`
recommended amending *narrowly* (lane-scoped) rather than broadly. James ruled broad. Both
advisories are preserved in the 2026-09-02 session record; the conditions above are the parts of
their objections that survived the ruling as mechanical requirements.

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
7. ~~Standing / unattended mission dispatch~~ — **LIFTED 2026-09-02 (Amendment H).** Now
   permitted on the Actions substrate under the conditions in §Standing dispatch below. The
   draft-PR ceiling is unchanged and item 9 is unaffected: standing *dispatch* was granted,
   standing *landing* was not.
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
| ~~Standing 7b~~ — **granted 2026-09-02 (Amendment H)**; lanes are installed for owner-dispatched use. Remaining James steps are providing the per-lane Healthchecks URLs and later ruling on a red-teamed branch-scoped credential before any automatic trigger | §Standing dispatch above |
| Guilfoyle-as-main-thread | later, on evidence |
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
Standing dispatch was granted to the lane; scheduled standing landing was not.
The workflow remains manually gated. Interactive landing, when activated, follows
the separate `AGENTS.md` contract.
Automatic triggers stay blocked until backlog item A-22 closes the branch-scoped credential P1.
