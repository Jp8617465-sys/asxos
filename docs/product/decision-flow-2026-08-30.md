# Decision flow — how asxos decides, end to end

**Status:** current
**Scope:** a single trace of how a decision travels across the governance docs, the agent
and command layer, the hooks, and the code seams. `docs/README.md` maps *which doc governs
which area*; this file maps *how a decision moves through the areas*.
**Last verified:** 2026-09-01 (every `file:line` below re-verified at write time, 2026-08-30;
§1, §4C and §6 re-verified against `main` `f10b392` on 2026-09-01)
**Owner:** James (governor). Descriptive only — it grants nothing and binds nothing.
**Superseded by:** N/A
**Revisions:** 2026-09-01 — §1 workflow count 12 → 13 (`nightly-check.yml`, PR #169); §4C
caveat corrected in place for PR #183 (decision spine persisted, migration `0048` applied);
§6 gains the `0048` append-only-trigger row. Corrections of fact only — no new ruling.

> **Self-demotion clause — read this before citing anything here.**
> This is a **`compiled_view`** in the sense of `doc-truth-map-2026-08-13.md:48`: a
> reconciliation *of* sources, always potentially stale. It is **not authoritative**. If it
> contradicts an authority doc or live state, **the authority doc wins** and this file must
> be corrected or demoted to historical.
>
> That map's own finding (`:53`) is that *"the dominant failure mode in this corpus is a
> `compiled_view` that has drifted from its source"* — 8 of its 10 recorded contradictions.
> This file is deliberately built to fail safely into that: it is **dated in its filename**,
> and it **points at authority docs rather than restating their tables**, because a restated
> table is a copy that can drift while the original moves.
>
> The part worth maintaining is §4 — the five end-to-end traces. Those exist nowhere else.
> Everything before and after §4 is orientation and should be read as a map, not a rule.

---

## 1. Three layers, one page

asxos has **two decision systems** that deliberately do not share machinery, plus a
mechanical floor beneath both.

```
 ┌─ GOVERNANCE LOOP ─ what gets built ──────────────────────────────────┐
 │  James (governor) → arbi (operating controller) → Guilfoyle (exec    │
 │  lead) → specialist agents → draft PR → James merges                 │
 │  Ladder: I0–I6   ·   Charter: arbi-constitution.md                   │
 └──────────────────────────────────────────────────────────────────────┘
 ┌─ PRODUCT RUNTIME ─ what gets surfaced about capital ─────────────────┐
 │  GitHub Actions cron → jobs/ → domain gates → brief / memo → James   │
 │  → James's broker (outside the system, always)                       │
 │  Ladder: P0–P6   ·   Charter: portfolio-manager-charter.md           │
 └──────────────────────────────────────────────────────────────────────┘
 ┌─ MECHANICAL FLOOR ─ what is physically possible ─────────────────────┐
 │  settings.json deny · 4 always-on hooks · branch protection ·        │
 │  Postgres audit triggers · Pydantic fail-closed contracts ·          │
 │  P6 enforced by tool absence                                         │
 └──────────────────────────────────────────────────────────────────────┘
```

**Why two ladders and not one.** `arbi-permission-model.md:24` states it: the two capacities
get separate ladders *"so one can never be used to reach the other."* arbi steering the
roadmap and arbi producing a portfolio memo are different authorities; collapsing them would
let track record earned on docs unlock something capital-adjacent.

**Where decisions execute.** GitHub Actions is the scheduler — Render was deleted 2026-08-12
(CLAUDE.md non-negotiable #2). Thirteen workflows: `daily-brief`, `weekly-research`,
`us-positions`, `pipeline-health`, `backup`, `issue-snapshot`, `migration-drift`,
`migration-integration`, `nightly-check` (15:17 UTC daily — the full pytest suite against
`main` on a fixed clock, with a Healthchecks deadman ping on success so a run that never
happens is as visible as one that fails; PR #169), `full-check`, `targeted-ml-tests`,
`claude-execute`, `pr-review-agent`. A decision that never reaches one of these never
executes.

**The organising principle is not autonomy.** `arbi-constitution.md:57`: the line is
**reversible vs irreversible**. Broad standing autonomy for reversible work (read, prioritise,
draft, docs, draft PRs); slow and review-gated for everything irreversible (merge, deploy,
migrate, prod-DB write, secrets, capital, boundary change). The permission table's real
column is "Reversible?", not "Autonomous?" (`arbi-permission-model.md:50`).

---

## 2. Who decides what

Pointer table. **The binding doc is authoritative; this column is a signpost.**

| Decision class | Decider | Binding doc | Mechanical backstop |
|---|---|---|---|
| Priority / THE ONE THING | arbi | `.claude/agents/arbi.md` | none — advisory, brief-only |
| Challenge THE ONE THING | `arbi-red-team` | `.claude/agents/arbi-red-team.md` | none — act-time gate, manual |
| One-file reversible build | main loop via `/build` | `harness-profiles.md:58` | deny array + hooks |
| Multi-node mission plan | Guilfoyle (plans only) | `.claude/agents/guilfoyle.md` | read-only tool set |
| Large parallel mission | `/arbi-team` | `.claude/commands/arbi-team.md` | plan-approval gate |
| Docs write (I2) | arbi, command-invoked | `arbi-permission-model.md` | `authority-guard.sh` |
| Open a PR | main loop | `arbi-permission-model.md` I3–I4 | `pr-draft-guard.sh` — `draft:true` or denied |
| Merge to `main` | **James** | `arbi-harness.md` I6 | branch protection + `push-guard.sh` |
| Apply a migration | **James** | `james-inbox.md:37-41` | `migrations/**` Edit-denied |
| `approved_for_allocation` | **James** | `portfolio-conventions.md` | `production_gate.py` — §4A |
| Governance status transition | human via CLI | `transitions.py` | Postgres BEFORE UPDATE trigger — §4B |
| Memory promotion | **James** (CODEOWNER merge) | `arbi-promotion-gate.md` | advisory only — see §6 |
| Portfolio analysis (P0–P1) | agents, command-invoked | `/pm-review` | read-only DB role |
| Action memo (P2) | `/pm-review` synthesis | `recommendation-schema.md` | `model_independence` assertion |
| Allocation proposal (P3–P4) | **not granted** | `arbi-permission-model.md:169-170` | — |
| Capital-policy change (P5) | **James** | draft-only, forever | — |
| **Execute a trade (P6)** | **James, in his broker** | `north-star.md` §2 | **no tool is mounted** |
| Dark-launch flip | **James** | `dark-launch-exit-plan.md` | env gates |

**The five classes reserved to James** (`james-inbox.md:37-41`): capital · merge approval ·
migration approval · policy/conviction · broker execution. arbi surfaces every open row each
wake and never treats one as resolved until James rules.

**P6 is enforced by absence, not policy.** `arbi-permission-model.md:389` —
*"P6 (execution) is trivially enforced because no broker/execution tool is ever mounted."*
No track record unlocks it. The gap between the best memo and one dollar moving is James
reading it (`:177`).

---

## 3. Conflict resolution

Every conflict resolves through the ladder in `arbi-authority.md:17-29`. **Higher wins**, and
a lower level may never override a higher one:

**0** James's instruction → **1** law / hard safety → **2** constitution + rule #11 →
**3** live state → **4** repo docs → **5** arbi ledgers → **6** approved memory →
**7** dream candidates → **8** transcript.

Two load-bearing consequences:

- Live state and repo docs (3–4) outrank arbi's own memory (5–6), and both outrank dreams (7).
- **Stale-beats-fresh only downward** (`:45`). A fresh dream never beats a stale-but-
  authoritative doc; it flags the doc and proposes an update through the promotion gate.

### Worked conflict — memory vs repo truth

arbi memory says "Model A is cleared." `CLAUDE.md:25` says quarantined. Memory is level 6;
rule #11 is level 2. **Rule #11 wins.** Letting the memory win would trip circuit breaker 8
(*"no memory/dream output overriding repo truth or live state"*, `arbi-scorecard.md`), which
zeroes the run.

### Worked conflict — live and unreconciled, right now

`docs/README.md:48` records one the repo has **not** resolved: D10 in the architecture
decision record calls `roadmap-state.md` frozen and moves actionable work to GitHub Issues,
contradicting the "Backlog / session state" row at `:46` and read-first item 4 at `:27`.

The resolution is not a silent pick. Both rows sit at ladder level 4, so per
`arbi-authority.md:64` the tie escalates to James — and the map says so in place:

> *"Until James reconciles, those rows stand and D10 is ratified-but-not-in-force."*

That is the ladder working: a conflict named, the safer side held, and the decision routed to
the only role that can settle it — rather than an adjudication invented to make it go away.

---

## 4. Five worked traces

**This is the part of the file worth maintaining.** Each trace follows one decision from
evidence to enforcement.

### A. Rule #11 — one policy, four enforcement points

**Evidence.** 19,032 matured `signal_outcomes`; `corr(ml_prob, 21d) = −0.03`; STRONG_BUY
returned −0.09% at 21d vs HOLD's +5.07% — conviction inverted at the top (`CLAUDE.md:25`).

**Decision.** James shelved the ML engine, 2026-07-11
(`docs/product/ml-engine-shelf-2026-07-11.md`).

**State today — retirement, not dormancy.** The code is *gone*. PR #144/#149 deleted the
training chain, feature engine, signal machinery, and the last `signals` readers;
`.claude/rules/ml-conventions.md` is now a retirement placeholder ("retired 2026-08-19").
Any doc describing Model A as a live-but-gated engine is stale.

**The gate that survived it is generic.** `asxos/domain/models/production_gate.py:20,47` —
`ModelGateDormant` / `resolve_production_model()`. It gates *any* model, not Model A
specifically. Rule #11 operates **through** a general approval gate; it does not own a
bespoke one.

Then it propagates into four mechanically distinct places:

1. **The allocator refuses.** `asxos/domain/portfolio/build.py:209-213` queries
   `model_versions WHERE is_active AND approved_for_allocation` and calls the gate with
   `required=True`. Zero rows → `ModelGateDormant`. The comment at `:195` is emphatic —
   *"DO NOT DELETE. This is rule #11's mechanical enforcement point… It contains no Model A
   token, so a token-driven cleanup cannot see it."* The gate **deliberately outlives the
   query it used to feed**: the signals read is gone (mission P1-04),
   `load_allocation_candidates` at `:224` now raises `CandidateSourceUnavailable`, and the
   ordering is pinned by
   `tests/test_portfolio_build.py::test_model_gate_runs_before_the_candidate_source` so any
   replacement candidate source must load *below* the gate.
2. **Dormant is distinguishable from broken.** `asxos/jobs/utils/job_monitor.py:131-132` maps
   `ModelGateDormant` to `job_runs.status='blocked'`, not `'failure'`, and Healthchecks is not
   pinged. A deliberate quarantine does not page as an outage. The `>1 rows` case still alerts
   as failure — that is real misconfiguration.
3. **The brief degrades instead of dying.** The same function called `required=False` returns
   `None`, so display-only paths skip the cosmetic model line and the model-independent
   cards — tax, regulatory, job-failure, portfolio, discipline — still render. Risk R9. One
   function, two modes, because a capital gate and a display gate need opposite failure
   behaviour.
4. **The decision contract refuses to represent it.**
   `asxos/domain/decision_engine/types.py:466` declares `model_independence: Literal[True]` —
   unconstructable otherwise. `:496` `validate_decision_gate` regex-scans the manifest via
   `_MODEL_A_RE` (`:56`) and raises *"Model A and v1_5 are quarantined from the decision
   basis"* (`:528`). `model_a_quarantine` is also one of the `UNIVERSAL_CONSTRAINTS` (`:45`).

**Plus a meta-rule.** Re-proposing "run the decay check" is classified as **recency overfit**
by `arbi-red-team` challenge 1. A resolved P0 is done; re-litigating it is not diligence.

**And the honest gap.** At agent level this is prompt-only. `.claude/commands/pm-review.md:88`
says it plainly: *"The read-only role permits any SELECT, so the frozen `signals` table is
still reachable; not reading it is the control."* Revoking SELECT for the agent role
(`m14_candidate_agent_db_role_scoping`) is the only control that would survive a prompt edit.

### B. An agent proposes new content — `/discover-macro`

The invariant this trace demonstrates: **no governed state changes without an audit row.**

1. Main loop dispatches `macro-economist` — read-only, Supabase RO only.
2. Agent returns structured JSON: proposals with **catalyst** and **falsifier**, plus an
   evidence array with tiers (verified / inferred / speculative) and replayable snapshots.
   No parseable block → the command *stops and says so* (`discover-macro.md:36-38`):
   *"do not invent a proposal or retry silently."*
3. **The command persists, never the agent.** `asx agent-run log` writes `agent_runs` +
   `agent_evidence`. The agent holds no write path.
4. A human runs `asx macro-thesis open --from-agent-run` → row lands at `pending_review`.
5. A human runs `asx macro-thesis approve` → `apply_governance_transition()`.

Step 5 is where it becomes mechanical.
`asxos/domain/governance/transitions.py:37` does **INSERT `governance_events` (`:68`) THEN
UPDATE (`:81`)**, and the order is load-bearing: the audit triggers (migrations 0034/0036) are
`BEFORE UPDATE` and check via `pg_current_xact_id()` that a matching event row is already
visible in the same transaction. A direct `UPDATE theses SET governance_status='approved'`
**fails at the database.**

**The lesson attached to it** (module docstring, and `.claude/rules/portfolio-conventions.md`):
the original helper did UPDATE-then-INSERT and passed *every mocked unit test, two full review
loops, and a manual live verification* — because mocked connections do not enforce trigger
semantics, and the manual check verified hand-written SQL that happened to be in the right
order rather than the sequence the Python actually emits. Phase 1's `asx thesis approve` would
have failed on first real use.

Encoded rule: any code performing a governance transition must have its **emitted statement
order** live-verified against the real triggers at least once. Mocked tests do not count.

### C. The fail-closed capital gate

`asxos/domain/decision_engine/types.py:496-529` is the crispest statement of how a capital
decision is *permitted to exist*. An action state (`initiate` / `add` / `trim` / `exit_review`)
is only representable if all of:

- `as_of` equals the UTC `knowledge_cutoff` date — one point-in-time cutoff
- `knowledge_cutoff <= created_at < expires_at`
- expiry equals the F3 default (5 trading days for action states, 21 for
  watch/avoid/abstain), or is *strictly earlier* with a named non-default reason
- **`missing_or_uncertain_inputs` is empty** — *"unresolved inputs cannot produce an action
  state"*
- **`tax_assessment_reference.readiness == "pass"`** — *"unresolved tax readiness cannot
  produce an action state"*
- the manifest carries `composition`, `llm`, `market_data`, `code_contract`, uniquely, with no
  Model A token
- non-action states carry a **zero size range**

At the `Contract` base: **floats are rejected at input**, datetimes must be UTC, and
content-addressed artifacts self-verify their hash. `DecisionCase` then validates the whole
citation chain — thesis→evidence, challenge→thesis, challenge→evidence — so a packet cannot
cite a challenge that examined a different thesis.

**Honest caveat, required whenever this is cited:** these are the **frozen canonical
contracts** — *"deliberately independent of databases, agents, and renderers"* (`types.py:3`,
unchanged). They define what a valid capital decision looks like. As first written
(2026-08-30) they were *not yet a live end-to-end capital pipeline*; since PR #183 (`main`
`f10b392`, 2026-09-01) they are **persisted end-to-end for one symbol** — a live
**persistence spine**, still **not a live *capital* pipeline**:

- `asxos/domain/decision_engine/repository.py` (`save` / `load` / `load_case` /
  `supersede`) writes the five-artifact chain into the five append-only tables of
  `migrations/0048_decision_packets.sql` — **APPLIED** 2026-09-01, ledger version
  `20260901062502`. Every table carries a `BEFORE UPDATE OR DELETE` trigger
  (`_decision_engine_forbid_mutation()`) that hard-fails any mutation; `supersede()` inserts
  a new row pointing at the old one and never touches it. Reconstruction is *exclusively*
  `model_validate(payload)`, never a shadow column — a `NUMERIC(18,6)` round-trip can change
  the string form of an equal value and silently break `verify_content_hash()`.
- `builder.py::build_cba_decision_case` composes the first real packet,
  `dpk-cba-1-2026-09-01` (CBA.AU, `thesis_id=1`), from the live `theses` row and
  research-store fundamentals. It is persisted and **live-verified**: content hash valid
  after the DB round-trip, upstream hash bindings hold, and the trigger rejected a test
  `UPDATE`.
- The packet is honestly **`abstain`**, and could not be anything else: no independent
  challenger exists until Slice 2.5 (`architecture-decision-record.md` §6), and
  `tax_assessment_reference.readiness` is honestly `unknown` — there is no real
  dividend/realised-gains feed, so the builder reuses `unresolved_tax_assessment_reference()`
  rather than fabricate a `pass`. Under the gate above, an action state therefore remains
  **mechanically impossible** until Slice 2.5 lands.

*(One live drift instance, same class as §4D: `repository.py`'s module docstring still
describes migration `0048` as "NOT YET APPLIED". The migration header and the ledger are the
truth.)*

### D. A discipline finding reaching James

This is the north-star's own success criterion — *discipline events reach him before they cost
money* — written because a HUBS stop breach went unseen for three weeks when the alert crons
had never been provisioned.

**The path is live, not designed-and-dormant.** `asxos/domain/theses/discipline.py:656`
`evaluate_discipline()` is imported by `asxos/brief/compose.py:120-127`, loaded at `:1264`,
and rendered into the email `daily-brief.yml` sends. *(The module docstring still describes
itself as "wired to nothing" from its PR1 state — that line is stale; the import graph is the
truth. A small live instance of exactly the drift this file warns about.)*

Three properties worth knowing:

- **Model-independent by construction** (`discipline.py:19`). It reads only thesis-authored
  fields plus a native price; never `signals`, `shap_factors`, `prob_up`, never
  `resolve_production_model()`. *"If a future check needs a model input, it does not belong
  here."*
- **`error` is a distinct level from `red`** (`:78`) — it means a check *could not be
  computed*. A silently-skipped check is the exact failure mode the lane exists to fix, so it
  surfaces loudly. `compose.py:513-516` wraps the loader in fail-loud isolation for the same
  reason.
- **The data-sanity check** (`:61`, `_DATA_SANITY_TARGET_MULTIPLE = 2`). A live price at ≥2×
  the recorded target is almost certainly a stale ladder, not a genuine hit — CBA carried
  target 60 against a live ~168. It emits a data-sanity finding *and suppresses* the spurious
  ABOVE_TARGET. Unanswered for a full 30-day revisit cycle, it escalates.

**Currency safety (R10).** `holding_lots.cost_base_normal` is **AUD** — the FX-converted CGT
base, not native. Dividing it by quantity and comparing to a USD close made two analysis agents
report HUBS at −29% and stop-violated when it was roughly flat. `discipline.py` anchors native
against native, so the trap is structurally impossible in that module.

**Two gates guard the surface:** `ASXOS_PERSONAL_USE=1` (the s766B firewall) and
`ASXOS_PORTFOLIO_BRIEF_ENABLED=1` (the paper-trade gate, still 0). And the language rule:
*"review overdue", "N× the target", "X% of portfolio" — **never** "sell", "trim", "exit", or
"overvalued".*

### E. A decision reaching James, and being closed

`james-inbox.md:55` — the migration `0044` row — is the full lifecycle:

🔴 open + time-boxed → applied 2026-08-21 → **resolved with verification at the primary
source** (`schema_migrations = 97`, the column present, the version string — not a claim that
it was done) → two postscripts as residuals discharged, each marked *"annotation only — no new
ruling"* so `Last verified` stays honest.

Rows are **closed by deciding, not by deleting** (`:65-75`).

**The process note embedded in that row is the most valuable line in the file:**

> *this row stayed 🔴 for the rest of the day after the work was done, and on 2026-08-21 two
> independent advisors read it and both escalated the migration as the single most
> time-critical item in the repo — inheriting urgency from a stale row. A doc asserting a
> state production had already left, exactly the failure class the same session was fixing
> elsewhere.*

That is the failure class this architecture is built against, catching the architecture
itself. It is also the reason for this file's self-demotion clause.

---

## 5. The wake and learning loop

**Why the main loop does the work.** One constraint shapes the topology: a Claude Code subagent
cannot spawn subagents or run shell/MCP probes. So arbi holds `Read, Glob, Grep` only and the
main loop does all gathering, fan-out, and persistence (`.claude/commands/arbi.md:13-19`). Same
pattern for `/pm-review` and `/discover-macro`.

```
James → /arbi → arbi-red-team (ONE THING or large envelope only)
      → /build XOR /arbi-mission XOR /arbi-team
      → main loop fans out specialists → draft PR → James merges
      → /arbi-close
```

Guilfoyle is a read-only planner. **Orchestration and mutation never share a process.**

**The wake** (`.claude/commands/arbi.md:21-78`):

1. Capture live state — `/sprint-state` + `/catchup` probes. *A probe's service unavailable →
   record the gap, never invent a value.*
2. Diff against the **Last wake snapshot** block in `roadmap-state.md`.
3. Hand the snapshot to the `arbi` subagent with a fixed 10-document read order. It returns ten
   sections; the main loop presents them **verbatim**.
4. Refresh the living state. **A scheduled run skips this step entirely** (`:61-64`) — an
   unattended run has no James-invocation to authorise the I2 write (PR 7a).
5. Stop. Brief-only.

**The red-team gate fires at act-time, not inside the brief** (`:85-96`). When James says go,
the main loop dispatches `arbi-red-team` first: recency overfit · task-switching ·
cleanup-as-progress · low-trust-memory-over-repo-truth · perfectionism-blocking-a-ship. PASS or
CHALLENGE, file-cited. Its closing boundary is unusually honest: *"When arbi is right, say so
and stop — manufacturing a challenge to look useful is its own failure mode."*

**Three speeds** (`harness-profiles.md:54-60`): `/build` (one file) · `/arbi-mission`
(multi-node) · `/arbi-team` (large parallel only).

**The close** (`/arbi-close`): append one row to `decision-log.md` — last wake's ONE THING,
what was done, and *did it work* — append-only, never delete; compute the session's
`episode_score` and write it into `arbi-run-ledger.md`, replacing the `—` placeholder, never
leaving one; write the handoff; remind, don't push.

**Scoring is deliberately anti-Goodhart** (`arbi-scorecard.md`). Hard gates first (nine circuit
breakers; any failure zeroes the run and pauses arbi), then a ten-dimension vector, then a
weighted `episode_score` used for **trend**, not maximisation. The sharpest detail:
`autonomy_efficiency` is measured but carries **zero weight** — *"an agent that optimises
'reduce human messages' would learn to stop escalating — so it is tracked, not rewarded."*
Likewise, while the quarantine stands, *"reward arbi for killing bad assumptions, not for
finding trades."* The grader is never the agent that did the work.

**Grading path:** `arbi-evals.md` + five fixtures in `docs/product/evals/` + five rubrics in
`docs/product/rubrics/` feed the scorecard's Layer 2. Promotion requires an improvement with
**no** regression in hard gates, state accuracy, or risk controls (`arbi-promotion-gate.md`).

**Memory-poisoning defence** (`arbi-memory-policy.md`): arbi never writes to a store it reads as
authority. It writes working memory only — classified untrusted-until-reviewed — and promotion
is the only bridge. Dreams may consolidate but *"do not compress away safety"*: an item that
would blur rule #11 or the s766B firewall is preserved verbatim, not summarised. A dream that
did not complete cleanly is archived and ignored.

**The loop's real failure mode, and its fix.** The ledger's own invariant — every run leaves a
row — was **not satisfied**. The gap reached **19 of 22** merged `claude/**` PRs uncited before
it was measured, after being manually rediscovered three times, and it silently broke the
promotion gate's evidence base (the 2026-08-14 promotion recorded holdout evals and score trend
as NOT RUN precisely because no rows existed). `scripts/check_ledger_coverage.sh` now enumerates
merged `claude/**` PRs and fails on any not cited. It **deliberately cannot write a row** — a
backfilled record is a worse defect than an absent one, so it reports and a human closes.

---

## 6. Mechanical vs prompt-only

The honest split. `arbi-permission-model.md` §Runtime enforcement honesty is the authority.

**Mechanically enforced**

| Control | What it actually stops |
|---|---|
| Postgres audit triggers (0034/0036) | A governance status change with no audit row, or written in the wrong order |
| Postgres append-only triggers (0048) | Any `UPDATE`/`DELETE` on a persisted decision-engine artifact — a packet can only be superseded, never edited (§4C) |
| `production_gate.py` + `build.py:209-213` | Allocation when no model is approved |
| `job_monitor.py:131-132` | A deliberate dormancy paging as an outage |
| Pydantic validators (`types.py`) | An invalid capital decision being representable at all |
| `settings.json` deny array | Direct edits to authority files (and recognised Bash file commands) |
| `authority-guard.sh` | Interpreter-mediated writes and symlink aliases to authority paths |
| `pr-draft-guard.sh` | `create_pull_request` without `draft:true`; un-drafting |
| `push-guard.sh` | Force/delete pushes at `main`, PR merge/ready shapes, `gh run rerun` |
| Branch protection + `full-check` | Direct pushes and unreviewed merges to `main` |
| **P6 tool absence** | Any trade, ever |

**Process- or prompt-only — do not overclaim these**

| Control | The honest limit |
|---|---|
| `.github/CODEOWNERS` | **Advisory.** `required_approving_review_count: 0`. Raising it to 1 was tried 2026-08-12 and reverted: GitHub forbids a PR author approving their own PR and James is the only human, so it turned every merge into an admin bypass — weaker audit evidence for zero added enforcement. Needs a second identity. |
| Branch protection | `enforce_admins: false` — an admin-scoped token bypasses all of it. Binds agents, not James. |
| Agent "SELECT-only" instructions | The Supabase grant permits arbitrary SQL. The `asxos_agent_ro` repoint is still open. |
| Rule #11 at agent level | Not reading the frozen `signals` table **is** the control (`pm-review.md:88`). |
| `push-guard.sh` regexes | Variable indirection, aliases, command substitution defeat them — falls through to a prompt, never a silent allow (`authority-guard.sh:23-27`). Deny-only by **asymmetric risk**: a false negative on a deny falls through to a human; on an allow it executes silently. The converse also holds — the guard substring-scans raw command text, so it can deny a *safe* command that merely contains a dangerous-looking string (writing this file's tables tripped it). That direction costs a retry; the other direction costs a breach. |
| Executor-arbitrary-code path | A pre-allowed test runner calling the git/GitHub API directly never produces a `git push` string and is invisible to the hook. Backstop is branch protection — minus the admin caveat. |
| Cursor agents (R17) | Do not honour `.claude/settings.json` or the hook fence at all. |
| Ledger discipline | A ritual, now with a coverage check — see §5. |

---

## Conventions that make the corpus legible

- **Every authority doc carries** `Status` / `Scope` / `Last verified` / `Owner` /
  `Superseded by`. A changed fact is superseded **in place**; the old reading stays as the
  record of what was true then.
- **Ledgers are append-only.** Corrections are postscripts. An annotation that adds no ruling
  says so and leaves `Last verified` alone.
- **Verify at the primary source, not from a claim** — the `0044` row's
  `schema_migrations = 97` is the pattern.

## James-owned follow-up

| Action | Why it is yours |
|---|---|
| Add a `docs/README.md` map row for this file | `docs/README.md` is Edit-denied to agents. Precedent: `harness-profiles.md:141` carries the identical follow-up. |
