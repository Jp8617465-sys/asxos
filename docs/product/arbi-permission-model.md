# arbi permission model — the blast-radius ladder

**Status:** current
**Scope:** the authoritative permission model for arbi (the `arbi-harness.md` tier table
points here)
**Last verified:** 2026-09-08 (Green/Amber/Red activation overlay and I5 migration split) ·
2026-08-12 (PR-2 Permission Friction Pack — settings `deny` array +
authority-guard/push-guard/pr-draft-guard hooks; see §Runtime enforcement honesty) ·
(autonomy unlock pack — skills / builder / `/arbi-team` placed on the existing ladder; no
grant changed) · (Claude Execute installed by PR #91 and placed on the attended I3/I4 path) ·
(guard carve-outs, PRs #92/#93 — branch protection confirmed **configured**; the workflow-
dispatch grant re-cut by *attendance*, not by workflow class; `gh run rerun` denied outright)
**Owner:** James (governor); changing a grant is a boundary change (constitution §reserved)
**Superseded by:** N/A

The organising principle is **reversible vs irreversible**, not "autonomous vs not." arbi
is granted broad standing autonomy for reversible work and is review-gated for everything
irreversible. This file is the source of truth for what arbi may do at each tier; the
`arbi-scorecard.md` circuit breakers are the hard floor beneath it.

**Two ladders, one principle.** arbi has two capacities and they get separate ladders so one
can never be used to reach the other:

- **Infrastructure ladder (I0–I6)** — *building the software* (docs, PRs, dispatch,
  migrations, merges). Governed by `arbi-constitution.md`.
- **Portfolio decision-support ladder (P0–P6)** — *operating the portfolio* as memos James
  acts on (analysis, action memos, allocation proposals; execution is P6 = never arbi's).
  Governed by `portfolio-manager-charter.md`.

Both obey the same reversible-vs-irreversible gate. The split matters because the old single
ladder lumped *execution* and *decision-support* together at one "capital = never" tier — but
James wants arbi to grow into producing allocation **memos** (reversible, promotable) while
**execution stays permanently his** (irreversible, not a tool arbi holds). The two ladders
draw that line explicitly.

---

## Infrastructure ladder (I0–I6) — building the software

| Tier | Capability | Reversible? | Standing autonomy | Runtime enforcement (target) |
|---|---|---|---|---|
| I0 | Read repo / docs / live-state snapshot | yes | **Yes** | `always_allow` (read-only tools) |
| I1 | Summarise / prioritise / detect drift / draft NEXT PROMPT + PR summaries | yes | **Yes** | `always_allow` |
| I2 | Write docs (roadmap-state, handoffs, ledgers, README links) | yes (git-revertible) | **command-invoked only today** | `always_allow` on a docs-scoped write tool |
| I3 | Open a **docs-only draft** PR (branch + commit docs + classify) | yes | **standing, general — Amendment L, 2026-09-05** | `always_allow` |
| I4 | Dispatch NEXT PROMPT to a specialist (who produces a **draft** code PR) | yes (draft) | **standing, general — Amendment L, 2026-09-05** | multi-agent delegation, `always_allow` |
| I5 | Migration definitions; migration application; production DB writes; secrets | mixed | **Definition PR: Amber. Application/write/secret: never standing.** | external classifier at merge; write-capable production role withheld |
| I6 | PR merge/deploy; direct push; workflow definitions; bypass | mixed | **Green merge: standing. Amber merge: current-head approval. Direct push/bypass: never.** | exact-head `risk-classify` + ruleset; no admin/bypass role |

The old tier number alone is no longer the gate because I5 and I6 bundled reversible and
irreversible actions. `AGENTS.md` now applies a Green/Amber/Red change-risk classification
across the ladder. A migration definition may merge as Amber, but applying it remains
owner-only I5. A Green PR may merge/deploy while attested `STANDING`; an Amber PR needs
James's approval bound to its current head. Direct/force push, auto/admin merge, secret
values, destructive production data and protection bypass remain Red. Before activation,
`AGENTS.md` §0 keeps every merge at the draft-PR ceiling.

**`/arbi-mission` (Guilfoyle) is the structured, attended form of I3–I4** — the graph-driven,
readiness-gated successor to `/arbi-run` (`.claude/commands/arbi-mission.md`, `.claude/agents/guilfoyle.md`).
It is **not a new ladder**: Guilfoyle is an *execution role* on this same infra ladder. It holds
**no tier above what arbi grants a mission** (mechanically classified Green/Amber/Red); Red
and P5–P6 still STOP for James; standing landing stays gated on the activation checklist and
mission admission. Guilfoyle plans and judges — it never spawns, merges, or
reprioritises (a subagent's `Agent(...)` allowlist is ignored at runtime, so the `/arbi-mission`
command's main loop does the fan-out, exactly like `/arbi-run`).

### The autonomy unlock pack (2026-07-14) — three attended I0–I4 forms, zero grant changes

The pack (this section + `.claude/skills/`, `.claude/agents/reversible-work-builder.md`,
`.claude/commands/arbi-team.md`, `docs/product/guilfoyle-mission-control.md`,
`docs/product/arbi-goal-recipes.md`, `docs/product/runbooks/`) adds **structured forms of the
tiers that already exist** — it changes **no grant** on either ladder:

- **Skill-scoped pre-allowed actions** (`.claude/skills/*/SKILL.md`, the prototype of
  orchestrator-mode R-A4). A skill's `allowed-tools` frontmatter pre-allows, *while that skill
  is active*, ONLY safe reversible I0–I4 actions: read/search, edit on a `claude/**` branch,
  test/lint/type-check, `git add`/`commit`, push to `claude/**`, open a **draft** PR. Nothing
  in any skill pre-allows merge, push to `main`, migrations, DB writes, Render mutation,
  secrets, or capital actions — those stay `ask`/denied/not-mounted exactly as before.
  **Skill `allowed-tools` is convenience, not a security boundary**: the hard floor remains
  the deny rules + hooks (`review-gate.sh`, `unattended-guard.sh`) + branch protection +
  James's merge. `.claude/settings.json`'s `allow`/`deny` lists are **not** broadened by the
  pack.
- **`reversible-work-builder`** (`.claude/agents/reversible-work-builder.md`) — the mutation
  hands of a mission. It holds Edit/Write/Bash for reversible branch work only; Guilfoyle
  stays read-only (orchestration and mutation never share a process). Same I0–I4 ceiling,
  same STOPs, review gate applies to its commits.
- **`/arbi-team`** (`.claude/commands/arbi-team.md`) — the agent-teams form of `/arbi-mission`,
  for **large parallel missions only**. Same envelope, same red-team vet, plus a **plan-approval
  gate** (James sees the team plan before implementation). Teams require the **local/user**
  env `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — never a repo-committed default. Max 4
  teammates by default; each teammate is bound by the same ceiling, the review gate, and the
  PR-transaction-discipline block (`memory/working/2026-07-14-pr-transaction-discipline.md`).

All three are **attended** (governor/arbi-invoked per mission). None is standing/unattended
autonomy — that promotion still requires the preconditions below and an explicit James
decision, unchanged. `bypassPermissions` remains forbidden for every launch.

### Claude Execute harness (2026-08-12) — attended I3/I4 GitHub execution

`.github/workflows/claude-execute.yml` is another structured attended form of I3/I4. A
manual `workflow_dispatch` by James supplies the mission prompt; Claude executes inside
GitHub Actions with a scoped `--allowedTools` set and the repo rules loaded from this
checkout. This **authorises** the run, within that prompt's scope, to create a
`claude/<short-slug>` branch, edit code/docs/configuration, run local tests and validation,
commit, push the branch, open or update a draft PR by pushing commits/commenting, inspect
workflow results, and continue through recoverable failures by fixing and rerunning checks.

While `ATTENDED`, this changes no standing grant and the draft-PR ceiling applies. Once the
activation contract is attested, Green PR ready/merge may proceed and Amber may proceed only
after James approves the current head. Secret values, migration application, destructive DB
operations, direct pushes to `main`, bypass modes, migration `0042`, and self-merging a
safety/compliance boundary remain stopped in every state. Workflow
dispatch **from the in-CI harness** is limited to validation-only workflows (`full-check.yml`,
`targeted-ml-tests.yml`, `migration-integration.yml`) — it may not dispatch `backup.yml`, nor
re-enter itself, and `tests/test_claude_execute_harness.py` pins that list.

### Dispatch splits by *attendance*, not by workflow class (2026-08-12 guard carve-outs)

The sentence above used to end "production or secret-bearing workflows stay approval-gated,"
full stop. **As of 2026-08-12 that is true of the unattended in-CI harness only.** James's
guard-carveouts decision (`docs/proposals/arbi-guard-carveouts-2026-08-12.md`, merged as PRs
#92/#93) extended the **local attended session's** `push-guard.sh` allowlist — and the
matching `.claude/settings.json` allow rules — from three workflows to five. The governing
distinction is therefore **attended-local vs unattended-in-CI**, *not* **validation vs
production**:

| Surface | May dispatch |
|---|---|
| **Local attended session** (`push-guard.sh` per-segment allowlist + settings allow rules) | `full-check.yml`, `targeted-ml-tests.yml`, `migration-integration.yml`, **`backup.yml`**, **`claude-execute.yml`** |
| **Unattended in-CI harness** (`claude-execute.yml`'s own `--allowedTools`) | the three validation lanes only — never `backup.yml`, never itself |

**`backup.yml` is secret-bearing — state it, don't let a reader infer otherwise.** It mounts
`DATABASE_URL`, `BACKUP_GITHUB_TOKEN` and `BACKUP_REPO`, and its default path
(`restore_drill=false`) commits a dump of the irreplaceable tables into the external
`$BACKUP_REPO`; only the opt-in `restore_drill=true` path is the disposable-container replay.
The carve-out is defensible — the external write is append-only backup data into the repo
whose whole purpose is receiving it, behind a project-ref identity assertion that refuses an
unverified source — but it is a **narrowing exception to a standing rule, not an instance of
it**. Production dispatches (`daily-brief`, `us-positions`, `weekly-research`,
`pipeline-health`) stay reserved to James on every surface.

Two hard denies landed in the same change. They *remove* grants; they are not relaxations:

- **`gh run rerun`, in any form, is denied outright.** It re-executes a prior run with all
  its secrets re-injected, for up to 30 days, on **any** workflow — a strictly wider grant
  than the dispatch allowlist it was briefly bundled with, and not "read-triggering" in any
  sense (security-engineer, 2026-08-12, H1). Re-dispatch an allowlisted lane explicitly
  instead (`gh workflow run <lane>.yml --ref <branch>`).
- **Any `gh workflow run` combined with command substitution is denied.** Command
  substitution is not a segment separator, so an inner *denied* dispatch can be smuggled into
  an allowlisted outer segment — `gh workflow run backup.yml $(gh workflow run
  daily-brief.yml)` fires the denied workflow first — and the settings allow-rule
  prefix-matches the whole string, so no prompt appears either (H2, verified live against the
  hook). The combination is refused rather than parsed.

This historical carve-out does not itself grant merge or `gh pr ready`. Those become reachable
only through the later attested Green/Amber/Red policy. Secret values, migration application,
direct deployment and protection bypass remain reserved.

## Portfolio decision-support ladder (P0–P6) — operating the portfolio

Every P-tier below P6 produces a **memo** (`recommendation-schema.md`), inside James's
capital mandate (`portfolio-policy.md`), and — while rule #11 stands — **model-independent**
(no Model A signals, allocator, or opportunity-cost ranking). A memo costs nothing until
James acts; that is why P0–P4 are reversible.

| Tier | Capability | Reversible? | Standing autonomy | Notes |
|---|---|---|---|---|
| P0 | Read portfolio / market / thesis / tax / benchmark live state | yes | **Yes** | read-only, via `mcp__supabase-ro__*` |
| P1 | Analyse & attribute — benchmark gap, thesis milestones, concentration, tax-lot eligibility, market context (the five investment-analysis agents) — **evidence only, no verdict** | yes | **Yes, command-invoked** | `/pm-review` fan-out; every claim cited |
| P2 | **Single-position action memo** — GOOD HOLD / TRIM / ADD / REVIEW / EXIT-CANDIDATE with cited evidence | yes (words) | **command-invoked only today** | `/pm-review [SYMBOL]`; James decides |
| P3 | **Portfolio allocation proposal** — a structured rebalance memo (target weights, sizing, tax + risk framing) | yes (words) | **not granted yet** | draft-only; needs promotion preconditions |
| P4 | Persist a memo + its outcome to `portfolio-outcome-ledger.md` (pending James's decision); scheduled/unattended memo production | yes (doc) | **not granted yet** | the "produce a memo on a schedule" autonomy; needs preconditions |
| P5 | Propose a change to `portfolio-policy.md` (objectives / risk appetite / a hard constraint) | boundary change | **never standing** | **draft only** — James approves each |
| P6 | **Execute — place an order, move capital, touch a broker** | **no** | **Never** | **not a tool arbi holds.** James executes in his own broker. |

P0–P4 are reversible decision-support → eligible for standing autonomy once earned (same
track-record gate as the infra ladder). P5 is a boundary change (draft-only, James-approved,
never standing). **P6 is the firewall: there is no tool, and no promotion, that lets arbi
execute.** The gap between the best memo (P4) and one dollar moving (P6) is James reading it —
that gap is `portfolio-manager-charter.md`'s "a recommendation is not an order," expressed as
an authority boundary.

**Rule #11 caps the P-ladder today.** While Model A is quarantined, P2/P3 memos must assert
`model-independent` (`recommendation-schema.md`) or they are void — the signal-driven
allocator path is unavailable to the portfolio capacity until rule #11 lifts.

## Where arbi stands today

**Infrastructure ladder:**
- **Pre-activation:** `AGENTS.md` §0 wins. I0–I4 may reach a draft PR; no ready or merge.
- **After attested activation:** Green may run and merge; Amber may run but waits for James's
  current-head approval at merge; Red stops. The exact-head external check and ruleset are
  the boundary, not the agent's self-classification.
- **Standing non-landing autonomy before activation:** I0–I4 may read, decide, dispatch,
  build, test and open draft PRs under Amendments H/L. Their historical preconditions were
  waived by James on 2026-09-05; that waiver grants no ready or merge action.
- **I5:** migration-file merge is Amber; migration application, production writes and secret
  handling are not granted. **I6:** Green/approved-Amber PR merge is grantable only after
  attested activation; direct push, bypass and self-amendment merge are never granted.

**Portfolio ladder:**
- **Standing autonomy:** P0 (read-only portfolio/market state).
- **P1–P2 (analyse + single-position memo):** performed **only inside an explicitly invoked
  command** (`/pm-review [SYMBOL]`) — James ran it. Memos are model-independent (rule #11).
- **P3–P6:** not granted. No P3 allocation proposal or P4 logged memo has been produced yet
  (`portfolio-outcome-ledger.md` is empty at seed).

Promotion to *standing* I2/I3 (later I4 dispatch) and to *standing* P3/P4 requires the
preconditions below and an explicit James decision — **I3/I4 promotion happened this way,
2026-09-05, as an explicit waiver of preconditions 2/3 rather than their satisfaction; see
below.** This does not extend to the portfolio ladder: P3/P4 still require the
preconditions in the normal, unwaived sense. The Green/Amber/Red activation is a separate
governor-ratified control-plane amendment: it grants only the merge portions described above.
Migration application, production writes, secrets, direct push/bypass, P5 and P6 remain
`always_ask`/disabled/not-held by design.

## Scheduled / unattended runs

Amendments H/L permit scheduled I0–I4 execution through a draft PR. The expanded landing
path is intentionally not active yet: `ARBI_UNATTENDED=1` remains merge-denied until an
independent ledger-attestation check is implemented and separately ruled. Existing H/K lanes
retain their narrower credential and path constraints; a broad policy does not silently
widen them.

The portfolio ladder remains separate. Scheduled research may read and analyse, but may not
emit personalised output, move capital, use Model A for a real capital decision, or persist a
higher P-tier result unless that P-tier is separately promoted.

## Promotion preconditions (reversible tiers only — I≤4 and P≤4)

Before arbi earns standing autonomy at a higher reversible tier (either ladder), all must hold:

1. ✅ **MET 2026-07-11 — Model A dispute resolved** (you cannot autonomously operate a project
   whose core engine is *under dispute*; that uncertainty is now gone — Model A has **no usable
   edge** and the ML engine is **shelved**). Note rule #11 is **not lifted** — it resolved
   *against* Model A and now stands as permanent policy, so the product is model-independent by
   design. For the P-ladder a residual gate remains: an unattended memo's `model_independence`
   assertion still needs human verification per-memo (the reason the scheduled P-path stays the
   boring read-and-observe 7a shape) — but that is a track-record/role-scoping gate below, not
   a live-dispute blocker.
2. **Agent DB role scoping landed** (`m14_candidate_agent_db_role_scoping`) — a read-only
   Postgres role so an unattended agent physically cannot write.
3. **Track record** — the `arbi-scorecard.md` trend + `arbi-run-ledger.md` + eval suite show
   arbi's calls hold up (no Safety fails, no state-accuracy regression) over a sustained
   window. For P3/P4 this specifically means the `portfolio-outcome-ledger.md` shows a run of
   in-policy, model-independent, useful memos — with **no** memo that ever implied an order,
   used Model A while quarantined, or breached `portfolio-policy.md`.

**Amendment L exception (infra ladder I3/I4 only, James, 2026-09-05).** Preconditions 2
and 3 above are **explicitly waived**, not met, for the general I3/I4 promotion recorded
in `roadmap-state.md` Amendment L: `supabase-ro` still authenticates as
`supabase_read_only_user`, not migration 0039's `asxos_agent_ro` (precondition 2, open as
backlog item `B-7`), and no sustained-window evaluation of the scorecard/ledger trend has
been run as a formal gate (precondition 3) — only per-session `episode_score` entries
exist. James chose the promotion with both gaps named in the question he answered. This
waiver is scoped to I3/I4 only: it does not extend to any future I-ladder promotion past
I4, and it does not extend to the portfolio ladder — a P3/P4 promotion still requires
these preconditions met, not waived, on their own separate governor decision.

**Never promotable:** migration application, production write credentials, secret values,
direct/force push, protection bypass, self-approval/self-merge, P5 (capital-policy change —
draft-only forever), and P6 (execution — not a tool arbi holds). Green merge and
current-head-approved Amber merge are activated through the separate control-plane gate;
they are not a track-record promotion of the forbidden actions above.

## Circuit breakers (hard floor, always on)

Independent of tier or ladder, any of these **voids the run** (`arbi-scorecard.md` Layer 1)
and pauses arbi: unapproved DB write or migration application; a merge/deploy that lacks the
exact-head Green or approved-Amber gate; secret
exposure; branch-only state treated as `main` truth; **capital-impacting action (executing,
or a memo that implies an order rather than a proposal James decides on)**; **a Model
A-derived recommendation while quarantined — including a P2/P3 memo that fails its
`model_independence` assertion**; self-editing the constitution, this permission model, the
portfolio charter/policy, or any other boundary without review; acting above the granted tier
(either ladder); a memory/dream conclusion overriding repo truth or live state; presenting an
unsourced claim as current truth. These are not metrics — they are the floor beneath both
ladders, and they are the same nine listed in `arbi-scorecard.md` §Layer 1 and
`rubrics/arbi-safety-boundary.md`.

## Runtime enforcement honesty

Before activation, every expanded grant remains behind `AGENTS.md` §0. The target mechanical
floor is the external exact-head classifier/publisher, protected ruleset and control-ledger
attestation; local hooks remain fail-closed feedback. The **PR-2 Permission Friction Pack
(2026-07-14)** is the historical client layer being adapted to that model:

- **`.claude/settings.json`'s `deny` array** — authority/boundary files (`CLAUDE.md`,
  **selected `.claude/` authority surfaces** — `settings.json`, `settings.local.json`, and
  the `agents/`, `commands/`, `hooks/`, `rules/`, `skills/` directories, enumerated
  explicitly rather than a broad `.claude/**` — plus `.github/**`, `migrations/**`,
  `render.yaml`, the constitution/authority/permission-model/harness/scorecard/
  promotion-gate/memory-policy/dream-policy/charter/policy/rubrics set, and the
  promoted-memory files) are `Edit(...)` denied — per Claude Code's documented behavior,
  one `Edit(...)` rule covers Write/MultiEdit/NotebookEdit and the Bash file-commands it
  recognizes (`cat`/`head`/`tail`/`sed`). **Root-level `.claude/` operational files are
  intentionally writable** — most importantly the review-gate's `.claude/.review-passed-*`
  markers: the original PR-2 draft shipped a broad `Edit(/.claude/**)` deny that covered its
  own review-gate marker and `settings.json` itself, deadlocking every future `.py` commit
  (the self-inflicted lockout recorded in `arbi-run-ledger.md`, 2026-07-14); it was narrowed
  same-day to the explicit surfaces above so the commit flow keeps working.
  `mcp__github__enable_pr_auto_merge` remains denied outright. The PR lifecycle tools are
  present so the state-aware hooks can decide: absent/malformed/unattested state is
  `ATTENDED`; only exact `STANDING` for the expected repository can fall through, and merge
  additionally requires explicit squash. The server then decides Green versus approved
  Amber. A local hook never attests or self-classifies a change.
- **`authority-guard.sh`** (always-on) closes the one gap the settings layer's own docs admit:
  "arbitrary subprocesses that read or write files indirectly, like a Python or Node script
  that opens files itself." It also re-resolves `Edit`/`Write`/`NotebookEdit` paths via
  `realpath` so a symlink alias can't present a non-authority name for an authority target.
- **`push-guard.sh`** (always-on) hard-denies dangerous `git push`/`gh` shapes (force/delete/
  mirror to `main`, `claude/x:main`-style refspec tricks, non-squash/admin/auto merge, and
  direct autonomy-variable mutation). PR creation/ready/explicit squash merge fall through
  only for the exact repository while the remote state is `STANDING`; server controls remain
  authoritative. Since 2026-08-12 it
  also hard-denies `gh run rerun` and any `gh workflow run` carrying command substitution, and
  its per-segment dispatch allowlist is the five-workflow attended-local list above.
- **`pr-draft-guard.sh`** (always-on) enforces the same ATTENDED/STANDING split for GitHub MCP
  tools and requires an explicit squash method for merge. Auto-merge remains denied always.

**Honest about what this does NOT do — corrected 2026-07-14 (security-engineer caught the
main loop's own drafting error via a raw docs fetch, not the WebFetch summarizer both had
first relied on):** `permissionDecision:"allow"` **IS** documented (code.claude.com/docs/en/hooks
§PreToolUse decision control) to suppress Claude Code's native prompt, with a narrow carve-out
for tools that require user interaction (`AskUserQuestion`/`ExitPlanMode`) — Bash and the
GitHub MCP write tools are not in that carve-out. (Confirmed for the Claude Code CLI the docs
describe; this session runs under the Claude Agent SDK harness, where the identical mechanism
is assumed, not independently re-verified.) So an allow-emitting hook for a verified-safe
shape would in fact have worked.

**None of PR-2's hooks are deny-only because that mechanism was unconfirmed — they are
deny-only for a better, independent reason: asymmetric risk.** A false-negative in a regex
meant to *allow* a safe shape silently executes a dangerous action with zero human check. A
false-negative in a regex meant to *deny* a dangerous shape merely falls through to the
existing prompt — a human still gets a chance to catch it. Given every regex here is
admittedly imperfect (see Residual limits below), only the fail-safe direction is acceptable
for anything push/merge-adjacent. For allowlisted lifecycle tools, silence may execute without
another prompt. That is why remote-state, exact-repository and explicit-squash checks fail
closed locally, while the classifier and ruleset remain the actual authorization boundary.

**Branch-protection status: PARTIAL (re-verified 2026-09-08).** Two rulesets are active:
`asxos-main` (19077432) applies to the default branch and requires a PR plus strict
`full-check`; `main` (18221894) has no included ref and adds no effective coverage. Both have
empty bypass lists and deny deletion/non-fast-forward updates. The effective PR rule allows
merge, squash and rebase, and no linear-history rule or `risk-classify` requirement exists.
Therefore activation checklist item 2 is not met. The 2026-08-12 guard carve-outs
(`docs/proposals/arbi-guard-carveouts-2026-08-12.md`) are the first draw-down on that
precondition — and deliberately a **deny-only allowlist widening**, not the allow-emitting
hook, which remains open. Two caveats must travel with every citation of this backstop or it
gets overclaimed:

- **`enforce_admins: false`** — a token acting as a repo admin bypasses all of it. The
  protection binds agents and non-admin credentials; it does not bind James, and it does not
  bind anything holding an admin-scoped token (which is why introducing
  `CLAUDE_WORKFLOW_PAT` is itself a boundary change, per `claude-execute.yml`'s header).
- **With approvals at 0, `.github/CODEOWNERS` is ADVISORY, not mechanical** — it requests
  James's review; it does not block a merge without it. A `required_approving_review_count: 1`
  setting was tried on 2026-08-12 and deliberately reverted: GitHub forbids a PR author from
  approving their own PR and James is the only human, so requiring an approval turned **every**
  merge into an `enforce_admins:false` admin bypass — weaker audit evidence than the
  0-approval state, for zero added enforcement. Under the target policy CODEOWNERS remains
  routing only; the external verifier enforces conditional current-head approval. Docs that
  still describe CODEOWNERS as the *mechanical*
  memory-poisoning firewall (`arbi-promotion-gate.md`, `arbi-dream-policy.md`) therefore
  overstate it. Re-verify before citing either way:
  `gh api repos/Jp8617465-sys/asxos/branches/main/protection`.

Residual limits, same class as `unattended-guard.sh`'s — named explicitly per
security-engineer's 2026-07-14 review rather than folded into a generic caveat: variable
indirection (`r=main; git push origin HEAD:$r`), command substitution, and git aliases can
still defeat `push-guard.sh`'s regexes (falls through to the existing prompt, not a silent
allow — the asymmetric-risk property holds). **Closed in the same review round:** a bare
shell redirect to an authority path (`echo x > CLAUDE.md` — no "recognized file command" is
involved, so the settings-level `Edit(...)` carve-out didn't apply and `authority-guard.sh`
had dropped this check versus `unattended-guard.sh`'s own A4 pattern — now restored);
wildcard-refspec (`refs/heads/*:refs/heads/*`) and `remote.*.push` config-injection pushes
(the flag-free equivalents of `--all`/`--mirror`); and `git -C`/`--git-dir`/`--work-tree`
redirecting `push-guard.sh`'s branch check at a repo it never inspects. **Still open:** the
executor-arbitrary-code path (a pre-allowed test runner like `pytest`/`make check` executing
code that calls the GitHub/git API directly, never producing a `git push` or `gh` command
string) is invisible to `push-guard.sh` entirely — the real backstop for that path is GitHub
branch protection, not any client-side hook. The active rulesets refuse direct/non-fast-forward
updates and have empty bypass lists, but still lack squash-only, linear-history and
`risk-classify` enforcement. `docs/README.md` was missing from the authority list (same
source-of-truth ladder level as `CLAUDE.md` per `arbi-authority.md`) — added. P6 execution is
physically bounded because no broker/execution tool is mounted. Until attested activation,
§0 means all merge capability must still be treated as disabled.
