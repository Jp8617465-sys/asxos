# arbi permission model — the blast-radius ladder

**Status:** current
**Scope:** the authoritative permission model for arbi (the `arbi-harness.md` tier table
points here)
**Last verified:** 2026-07-14 (PR-2 Permission Friction Pack — settings `deny` array +
authority-guard/push-guard/pr-draft-guard hooks; see §Runtime enforcement honesty) · (autonomy unlock pack — skills / builder / `/arbi-team` placed
on the existing ladder; no grant changed)
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
| I3 | Open a **docs-only draft** PR (branch + commit docs + classify) | yes | not granted yet | `always_ask` → `always_allow` when promoted |
| I4 | Dispatch NEXT PROMPT to a specialist (who produces a **draft** code PR) | yes (draft) | not granted yet | multi-agent delegation, `always_ask` |
| I5 | Migrations / DB writes / Render / secrets | **no** | **never standing** | `always_ask` (or disabled) — James approves each |
| I6 | Merge / deploy / push to `main` / CI changes | **no** | **never standing** | `always_ask` — James approves each |

The **Reversible?** column is the real gate. I0–I4 are reversible (docs are git-revertible;
PRs are draft; dispatched code is draft) → eligible for standing autonomy once earned. I5–I6
are irreversible → always human-approved, never standing, regardless of track record. The
`.claude/hooks/unattended-guard.sh` hook is the mechanical pre-filter for I5–I6 under
unattended runs (push/merge to main, DB writes, Render, migrations).

**`/arbi-mission` (Guilfoyle) is the structured, attended form of I3–I4** — the graph-driven,
readiness-gated successor to `/arbi-run` (`.claude/commands/arbi-mission.md`, `.claude/agents/guilfoyle.md`).
It is **not a new ladder**: Guilfoyle is an *execution role* on this same infra ladder. It holds
**no tier above what arbi grants a mission** (reversible I0–I4, draft-PR ceiling); I5–I6 (and
P5–P6) still STOP for James; and *standing/unattended* mission dispatch stays gated on the same
PR 7b/8 promotion preconditions below. Guilfoyle plans and judges — it never spawns, merges, or
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
- **Standing autonomy:** I0–I1 (read + think + draft).
- **I2 (docs write):** performed **only inside an explicitly invoked command** (`/arbi`
  refreshing state, `/arbi-close` writing a handoff) — human-in-the-loop, James ran it — not
  unattended standing autonomy. The subagent itself is `Read, Glob, Grep` only.
- **I3–I6:** not granted.

**Portfolio ladder:**
- **Standing autonomy:** P0 (read-only portfolio/market state).
- **P1–P2 (analyse + single-position memo):** performed **only inside an explicitly invoked
  command** (`/pm-review [SYMBOL]`) — James ran it. Memos are model-independent (rule #11).
- **P3–P6:** not granted. No P3 allocation proposal or P4 logged memo has been produced yet
  (`portfolio-outcome-ledger.md` is empty at seed).

Promotion to *standing* I2/I3 (later I4 dispatch) and to *standing* P3/P4 requires the
preconditions below and an explicit James decision. **I5–I6 and P5–P6 are never promoted to
standing** — they are permanently `always_ask`/disabled/not-held by design.

## Scheduled / unattended runs (PR 7a vs 7b)

A scheduled `/arbi` run has **no interactive James invocation**, so it cannot borrow the
human-in-the-loop authorisation that a manual `/arbi` uses for its I2 state write. The two
must be kept distinct:

- **PR 7a — scheduled read-only dry run (allowed before the promotion preconditions).**
  **I0–I1 only.** It runs observe → diff → synthesize → present and emits **output only**
  (a draft brief / issue / email). It does **not**: write any doc (not even
  `roadmap-state.md`'s Last wake snapshot), touch the DB/Render, mutate GitHub, create a
  branch, overwrite roadmap-state, emit a capital-impacting output, or make a Model A-derived
  recommendation. It is deliberately boring and read-only.
- **PR 7b — standing scheduled autonomy (blocked on the preconditions below).** Only here may
  an *unattended* run perform I2 writes (state refresh, handoff) on its own authority —
  and only after Model A is resolved, the read-only DB role is landed, and the scorecard/eval
  track record supports it.

Note: the interactive `/arbi` command still performs its I2 state refresh, because
James invoking it *is* the authorisation. The 7a restriction applies specifically to the
**unattended, scheduled** path.

**Portfolio-ladder analogue.** A *scheduled* `/pm-review` is likewise **P0–P1 only,
output-only**: read live state, analyse, emit a draft brief. It does **not** persist a P2
verdict or a P4 ledger row unattended, and it does **not** emit a memo as a recommendation —
because P2/P3/P4 need the promotion preconditions, and while rule #11 stands the
`model_independence` assertion of a memo cannot be human-verified in an unattended run. So the
scheduled portfolio path is deliberately the same boring read-and-observe shape as 7a.

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

**Never promotable:** I5–I6 (irreversible infra), P5 (capital-policy change — draft-only
forever), P6 (execution — not a tool arbi holds). No track record unlocks these.

## Circuit breakers (hard floor, always on)

Independent of tier or ladder, any of these **voids the run** (`arbi-scorecard.md` Layer 1)
and pauses arbi: unapproved DB write / migration / Render change / merge / deploy; secret
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

Today every grant here is **prompt + doc enforced**, with a growing mechanical floor beneath
it. `.claude/hooks/unattended-guard.sh` mechanically blocks the I5–I6 categories under
unattended runs; the **PR-2 Permission Friction Pack (2026-07-14)** added a second, always-on
mechanical layer that holds attended too:

- **`.claude/settings.json`'s `deny` array** — authority/boundary files (`CLAUDE.md`,
  selected `.claude/` authority surfaces, `.github/**`, `migrations/**`, `render.yaml`,
  `docs/README.md`, the constitution/authority/permission-model/harness/scorecard/
  promotion-gate/memory-policy/dream-policy/charter/policy/rubrics set, the promoted-memory
  files) are `Edit(...)` denied — per Claude Code's documented behavior, one `Edit(...)` rule
  covers Write/MultiEdit/NotebookEdit and the Bash file-commands it recognizes
  (`cat`/`head`/`tail`/`sed`). The `.claude/` deny is deliberately **not** a blanket
  `.claude/**` deny: it protects `.claude/settings.json`, `.claude/settings.local.json`,
  `.claude/agents/**`, `.claude/commands/**`, `.claude/hooks/**`, `.claude/rules/**`, and
  `.claude/skills/**`, while leaving loose root-level review-gate marker files such as
  `.claude/.review-passed-*` writable. Those markers are not authority files; they are the
  review-gate's operational speed-bump and are intentionally forgeable by design.
  `mcp__github__merge_pull_request` and `mcp__github__enable_pr_auto_merge` are denied
  outright (bare tool-name deny — removed from context entirely, not just blocked on attempt).
- **`authority-guard.sh`** (always-on) closes the one gap the settings layer's own docs admit:
  "arbitrary subprocesses that read or write files indirectly, like a Python or Node script
  that opens files itself." It also re-resolves `Edit`/`Write`/`NotebookEdit` paths via
  `realpath` so a symlink alias can't present a non-authority name for an authority target.
- **`push-guard.sh`** (always-on) hard-denies dangerous `git push`/`gh` shapes (force/delete/
  mirror to `main`, `claude/x:main`-style refspec tricks, `gh pr merge`/`ready`/non-draft
  `create`) regardless of how a human might answer the interactive prompt.
- **`pr-draft-guard.sh`** (always-on) hard-denies `create_pull_request` without `draft:true`
  and `update_pull_request` with `draft:false` or a `state` transition — the draft-PR ceiling
  as a mechanical rule, not just an instruction.

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
for anything push/merge-adjacent. So **push and PR-creation still prompt, exactly as
before** — PR-2 makes the dangerous shapes mechanically un-approvable (a human clicking "yes"
to a push that secretly targets `main` can no longer succeed), it does not eliminate the
prompts themselves. Push/PR-creation friction reduction remains open, gated on GitHub branch
protection on `main` being configured (still NOT done, confirmed 2026-07-11) — a narrow,
`allow`-emitting hook for verified-safe shapes becomes a *reasonable* follow-up once that
backstop exists, given `allow` is now confirmed to work; it does not become safe merely
because it's technically possible.

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
branch protection, not any client-side hook. `docs/README.md` was missing from the authority
list (same source-of-truth ladder level as `CLAUDE.md` per `arbi-authority.md`) — added. On
the Managed Agents platform these map to real **permission policies**
(`always_allow`/`always_ask`) and disabled toolsets; **P6 (execution) is trivially enforced
because no broker/execution tool is ever mounted** — arbi physically cannot place an order.
I5–I6 / P5–P6 must still be treated as if disabled.
