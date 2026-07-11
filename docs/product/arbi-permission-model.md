# arbi permission model — the blast-radius ladder

**Status:** current
**Scope:** the authoritative permission model for arbi (the `arbi-harness.md` tier table
points here)
**Last verified:** 2026-07-10
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

**Mechanical realization for *attended* runs (2026-07-11, governor-directed):** the reversible
tiers are encoded as the `permissions.allow` list in `.claude/settings.json` — read-only
Supabase (`supabase-ro`), GitHub read methods, reversible git incl. push to `claude/*`,
test/lint tooling, `make check-drift` — so James is not re-prompted for what he'd always
approve. The irreversible tiers stay in `permissions.ask` / default-prompt (main push, RW
Supabase, migrations, PR create/merge, GitHub file-writes; raw Render curl left gated because
a prefix rule can't separate GET from POST). arbi **cannot** write this file itself — the
harness auto-mode classifier denies editing the permission config (self-permission-grant = the
remit-expansion firewall); James applied it via `/fewer-permission-prompts`. This is the
attended analogue of the unattended-guard: allow-list reduces friction on reversible ops; the
guard hardens the irreversible ones. See `docs/product/proposed-permission-allowlist.md`.

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

Today every grant here is **prompt + doc enforced** — arbi is instructed to obey it; the
`.claude/hooks/unattended-guard.sh` pre-filter mechanically blocks the I5–I6 categories under
unattended runs, but it is a same-process filter, not a boundary (the same limitation the
security-engineer flagged for agent DB access). On the Managed Agents platform these map to
real **permission policies** (`always_allow` / `always_ask`) and disabled toolsets; **P6
(execution) is trivially enforced because no broker/execution tool is ever mounted** — arbi
physically cannot place an order. Until the platform lands, the harness + this doc + the guard
hook are the enforcement, and I5–I6 / P5–P6 must be treated as if disabled.
