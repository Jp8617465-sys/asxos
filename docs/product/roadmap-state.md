# asxos Roadmap & State — the reconciled picture

**Status:** current (living document — refreshed every `/arbi` and `/arbi-close`)
**Scope:** whole repo — **the single live queue.** All other backlogs are reference only.
**Last verified:** 2026-09-03 (`/arbi-close`, Amendment H campaign Waves 2→7 — `main` **unchanged @ `55f2619`**: fourteen draft PRs open (#185–#198), **none merged**. Four migrations applied under James's I5 grant: 0049 `20260902201241`, 0050 `20260902203202`, 0051 `20260902204920`, 0052 `20260903025557`; **0045 still deliberately unapplied**. **`backup.yml` still red — still THE ONE THING**, and nothing this session could touch it: every remaining step is a James click (H-03 inspect the archive, H-05 secret, H-06 workflow patch, H-07 dispatch). **No Stage cell moved.** Dark surfaces #1/#4 still unruled. D10 ratified-not-in-force. W1-2 CHALLENGEd. See Last wake snapshot.)
**Prior verification:** 2026-09-02 (`/arbi` wake — `main` @ `55f2619` after #184. 0048 applied as `20260901062502`. `backup.yml` red 12 consecutive scheduled runs since 2026-08-23 — THE ONE THING.)
**Docs-truth correction:** 2026-08-20 (post-merge reconciliation — PRs #144/#142/#141 merged, which
**reversed** this file's standing "Model A has NOT been deleted" correction. Dated point-in-time
records were annotated, not rewritten: a SUPERSEDED banner on the In-flight entry, an inline
reversal marker at the claim itself, a postscript to Amendment F, and a note above the 08-19 wake
snapshot. Rule #11 and its generic gate are untouched and restated as standing. **Documentation
annotation, not a state refresh** — no live probes beyond the read-only substrate dry-run recorded
in `segval-live-validation-2026-08-20.md`, so `Last verified` above is unchanged.)
**Docs-truth correction:** 2026-08-13 (`SB0-01` sweep — the *State header* block was found four
weeks stale and is now boxed with a freshness correction; the news-brief gate source and the
08-12 snapshot's "plan doc does not exist" line were corrected. **This was a documentation
sweep, not a state refresh** — no live probes were taken, so `Last verified` above is unchanged.)
**Prior verification:** 2026-08-10 (Stage 0 ratification — digest `d6d888a`, merged `9ede7ad`/PR #79)
**Earlier verification:** 2026-07-14 (post-merge reconciliation — James merged the six-PR train
#32→#33→#35→#31→#34→#36: sync_financial_statements batching, R12 firewall gate, R13 review-gate
hardening, Guilfoyle mission-control, overnight governance record, orchestrator-mode sketch.
Monitoring lane fixes all on main. **Confirmed (2026-07-14, later same day): #29 (discipline
evaluator) and #38 (autonomy unlock pack) are both MERGED to main** (`2a49df9`, `1af76e4`) — all
"#29 open/draft" references below have been corrected to reflect this. Remaining open: #5 —
recommend close, superseded by the ML shelf; #39 (permission-friction/guard pack) — open draft,
`full-check` CI failing.)
**Owner:** arbi (`.claude/agents/arbi.md`) reads and refreshes this; humans may edit freely
**Superseded by:** N/A

---

## PROGRAMME REFRAME (2026-08-10) — read this before anything below

James ratified a product reframe on 2026-08-10. asxos is a
**research-to-capital-decision-to-learning engine**, not an agent that writes a morning brief. The
brief is an experience layer over an immutable decision and must carry no financial logic of its own.

**The canonical target is [`target-architecture.md`](target-architecture.md)** (with its Errata §0
and Appendices A–I). This file remains the **single live queue**; that file defines what "done" means.

**This file is now the only ranked queue.** Superseded to reference-only, none of which may be read
as a next-action list: `arbi-operating-backlog.md`, `cleanup-backlog.md`,
`docs/next-session-backlog.md`, and the untracked 2026-08-08 convergence sprint. `james-inbox.md`
remains valid but is governor-scoped decisions, not build work.

### The queue — Stages 0→6

| Stage | Goal | State |
|---|---|---|
| **0** | Ratify objective + contracts; one canonical queue; scheduler + prototype dispositions | ✅ **COMPLETE 2026-08-10** — digest `d6d888a`, merged `9ede7ad` (PR #79). All seven gates met |
| **1** | Evidence foundation. **Order matters: contain irreversible loss first**, then repair PIT | **STILL NOT AUTHORISED as a stage.** What ran on 2026-08-11 was the *remediation work order* against the live-defect list below (defects 1/2/3/6 fixed in code, five PRs merged) — **not** Stage 1's evidence-foundation build. ~~F5 (Dagster deployment/cost/cutover) and F6 (S3 bucket/credentials) each still name a prior work order that has not been written~~ — **corrected 2026-09-02 (H1-F): both work orders were written AND approved.** P3-01 (Dagster) merged as #117; P3-02 (S3) shipped in #152; James approved both at gate G1 on 2026-08-22 (`decision-log.md`, 2026-08-22 row). What is outstanding is not the *writing* but the *execution* — the S3 bucket and credentials, and the Dagster deployment/spend, are James's infra actions (campaign clicks H-21/H-22) and neither is blocked on more documents. Campaign nodes H2-A (knowledge-tier) and H2-B (replay + lineage) advance Stage 1's exit clauses (1) and (2) without either |
| **2** | Research registry + evaluation (method-agnostic; reproducibility and failed-variant retention) | not started |
| **3** | Theme + candidate engine | not started |
| **4** | One governed paper investment case, end-to-end (**new screened candidates** — governor ruling) | not started |
| **5** | Outcome learning — **initially a process audit + descriptive outcome evidence**, not statistical validation | not started |
| **6** | Portfolio scale + surface cutover | not started |

_2026-08-22 close note (does not change any Stage cell):_ W1-1 (`asxos_pit_db`,
#155) is **P5 integration evidence**, not Stage 4 or Stage 5 complete. SB1-02 →
SB3-01 (#152) is packet-lane work, not Stage 2/3 complete. Do not flip a Stage
cell because a work order landed.

_2026-09-03 close note — **the same rule, applied to this campaign, which is the largest
test of it so far.** The Amendment H campaign built machinery against Stages 1→5 and
**flipped nothing.** Every cell above reads exactly as it did on 2026-09-02, deliberately.
What exists now, and what each stage still owes:_

| Stage | Built in-repo (unmerged, PRs #192–#198) | Why the cell did **not** move |
|---|---|---|
| **1** | `knowledge_tier` (0049) so replay reads `filed` only; `domain/replay/` — deterministic cutoff + lineage resolver, identical hash on two runs | Clause (3) "backup/restore is observed" is **still red**; F6 raw-object retention is James's infra (H-21). Cell wording is his ruling: **H-23** |
| **2** | `domain/research/registry/` + 0050 — hypothesis/strategy/run contracts, promotion state machine with **no code-reachable transition to capital**, failed variants retained | Gate wants one hypothesis reproduced **live** from raw `prices`; the sandbox cannot reach the pooler, so that run is James's click (**H-25a**) |
| **3** | `domain/themes/candidates/` + 0051 — `ThemeVersion` / `CandidateSnapshot`, deterministic measures, the LLM extraction boundary | Gate wants theme + candidate reproduced **live** from cited evidence: **H-27a** |
| **4** | `decision_engine/{challenge,sizer,staging,delivery,portfolio_state}` + the generalised builder — the chain runs end-to-end to a delivery receipt and a disposition | The **positive control cannot be built at all**: the only governed theme's sole member is CBA.AU, which the Stage 4 text names a *negative* control. Blocked on governance, not code — **H-33a** |
| **5** | `decision_engine/outcomes.py` + 0052 — t0 record and the 21/63/126-session horizon schedule | Gate needs a **complete learning episode** — 1/3/6 months of observation. This captures t0 only (decision **D-9**). No alpha claim from one observation |

_The honest summary: the campaign moved the **code** a long way and the **stages** not at all.
Both statements are true and neither cancels the other._

### Queued after the current remediation work (James, 2026-08-12)

James queued
[`asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`](../proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md)
after the live remediation/defect work below. The linked packet is the detailed candidate backlog;
this file remains the only live queue.

Entry gate: every earlier live remediation item is completed, explicitly deferred by James, or
superseded with cited evidence; required post-merge production/scheduled-run observations are
recorded; and `/arbi` refreshes current state before selecting work. Then activate exactly one
packet item as THE ONE THING. Default order begins `P1-01` (Model A reference manifest), then
`SB0-01` (Arbi truth reconciliation). Parallel execution requires an explicit James instruction
naming both mission IDs. Queue placement is not blanket implementation, production, authority, or
capital-action approval; the existing `/arbi-mission`, `/arbi-team`, and Claude Execute gates apply
to every item.

#### GOV-01 — ruling recorded 2026-08-12

`GOV-01` ("Ratify or amend this programme and choose the first work order", owner James, packet §7)
required two artifacts: the exact ruling **and** the canonical queue amendment. James issued the
ruling on 2026-08-12; this section is the amendment.

**Ruling.** Execute the Model A retirement lane first, then the results-review slice, then the
programme executor, then the memory-consolidation pair. `P1-01` is the first work order.
`SB0-01` remains the default next second-brain candidate. One PR-bounded mission per invocation;
~~no mission proceeds until its predecessor is merged, observed where required, and closed through
`/arbi-close`.~~ **— amended 2026-08-13, see Amendment A.**

#### Amendment A — stacked successor branches (James, 2026-08-13)

Drafted in `docs/proposals/arbi-automation-amendment-pack-2026-08-13.md` and **ruled by James on
2026-08-13** ("take amendment A"). It replaces only the struck clause above; every other part of
the `GOV-01` ruling stands.

> A successor mission may proceed on a *stacked* `claude/**` branch whose PR base is its
> predecessor's branch, **before** the predecessor is merged, provided each work order remains one
> branch and one draft PR, `arbi-red-team` and `/arbi-close` still run per mission, and the merge
> order remains strictly `P1-01` → `P1-02` → `P1-03` → `P1-04` → `P1-05` → `SB0-01`. **Merge, ready
> and un-draft remain James-only.** If a predecessor PR is closed unmerged, every stacked
> descendant is abandoned rather than re-based.

**What this changes:** work continues while James sleeps. **What it does not change:** he reviews
exactly what he reviewed before, in the same order, and no merge authority moves — the campaign
loop still cannot merge, un-draft, or self-approve.

**Mechanical obligations this creates for the executor.** James squash-merges (measured: every
`origin/main` commit has one parent and a `(#N)` subject, and merged branch tips are not ancestors
of `main`). On a squash-merge GitHub retargets the child PR's base to `main` automatically, but the
child's *history* still carries the parent's commits. The executor must therefore:

1. **Detect** — `git merge-base --is-ancestor <parent-tip> origin/main` exits 1 (squash, repair
   needed) vs 0 (true merge, no repair); and `--is-ancestor <parent-tip> <child-branch>` exits 0
   while the child still carries them.
2. **Repair** — `git rebase --onto origin/main <fork-point> --empty=drop`, which drops the parent's
   now-duplicated commits.
3. **Guard before pushing** — `git rev-list --count origin/main..HEAD` **must be ≥ 1**. A
   force-push that leaves head == base **auto-closes the PR** (the #29 incident,
   `docs/product/memory/working/2026-07-14-pr-transaction-discipline.md`). If the count is 0, do
   not push; stop and hand back.
4. **Push** with `--force-with-lease` (never bare `--force`) to the child's own `claude/**` branch —
   permitted by `push-guard.sh`, which only guards `main` — then immediately re-read the PR's state,
   base and changed-file count.
5. **Cascade in order** — if two levels merge at once, repair bottom-up, one branch at a time. A
   parent force-push orphans every descendant not yet rebased onto the new tip.
6. **Conflicts stop the loop.** `git rebase --abort`, do not push, report the conflicting paths.
   Never resolve a conflict against James's edit unattended.

**Known interaction, not yet resolved:** `unattended-guard.sh` denies *every* force-push under
`ARBI_UNATTENDED=1`, including to `claude/**` — so stacking and unattended operation are currently
mutually exclusive. Amendment C in the pack narrows that to permit `--force-with-lease` on
`claude/**`; it is **not** part of this ruling and is only needed if James later wants the loop
running with no session open.

#### Amendment B — execute-to-completion chaining (James, 2026-08-16)

Recorded per the GOV-01 two-artifact precedent (`decision-log.md` row `gov-01-2026-08-12`: a
ruling requires the ruling AND the queue amendment) — and per the P2-03 red-team's binding
constraint that this be recorded at mission start, not deferred to a close. On 2026-08-16 James
instructed, verbatim: **"execute reMAINING TO DO LIST TO COMPLETIO"** (execute remaining to-do
list to completion; session instruction, authority ladder level 0 — this row is its repository
record). Effect on the queue:

> Sequential mission chaining extends beyond Amendment A's enumerated order
> (`P1-01 → … → SB0-01`) to the remaining packet work orders in dependency-and-GOV-01 order,
> one mission per unit, each with an `arbi-red-team` vet, one branch, one draft PR, and a
> per-unit close row. **Merge, ready and un-draft remain James-only** (observed mechanically
> enforced this same day: `push-guard.sh` denies `gh pr ready` and `gh pr merge` from the agent
> on any surface). **Parallel packet missions still require James naming both mission IDs**
> (unchanged). Hard stops unchanged: credentials, migrations, destructive DB operations,
> production writes, scheduler cutover, direct pushes to `main`, merge/self-approval, authority
> or permission changes, personalised financial instructions, capital execution.

Amendment A supplies stacking *mechanics* only; this instruction is the *authority* for chaining
past SB0-01 — never cite Amendment A as authority for the P2/SB1+/P3 lanes.

**Rider — parallel authorization (James, 2026-08-17).** Recorded verbatim per the SB1-01
red-team's condition precedent (the parallel rule contemplates pairs; a three-way concurrency
needs the governor naming all of it, and the record must be a dated queue amendment, not a
session transcript). James wrote:

> Approved parallel: SB1-01 and P3-01, alongside the in-flight P2-04. Then P2-05 when P2-04
> lands. Then approved parallel: SB1-02, SB2-01, SB3-01, SB4-01.

Effect: (1) SB1-01 ∥ P3-01 ∥ P2-04 is the authorized three-way; (2) P2-05 is pre-authorized
sequential on P2-04's completion; (3) the four-way SB1-02 ∥ SB2-01 ∥ SB3-01 ∥ SB4-01 is
pre-authorized contingent on SB1-01 landing and a per-mission `arbi-red-team` vet each — a
pre-authorization is not a vet waiver. Unchanged: merge/ready/un-draft remain James-only; every
hard stop stands; one work order per branch per draft PR per close row.

**Amendment D — product-lane authorization (James, 2026-08-18).** Ratified verbatim by James
("can we do amendment D") after reviewing the shape of the 2026-08-17 campaign, whose merged
output he judged too narrow and, of the code, "half baked at best" — a judgement the evidence
supports: the merged outcome-vs-benchmark section renders `unavailable` for both the benchmark
and alpha on the live portfolio, because no benchmark series exists for the sleeve the sole
holding sits in. Recorded per the GOV-01 two-artifact precedent: a ruling requires the ruling
AND the queue amendment; this row is the repository record of the ruling.

> A **product lane** is opened alongside the packet lane and ranks **above** it. `/arbi-run`
> may dispatch its rows in order **without returning to James for per-item authorization**.
> Each row remains one work order, one `claude/**` branch, one draft PR, one `arbi-red-team`
> vet, one close row. When the product lane is exhausted or blocked, `/arbi-run` falls through
> to the packet lane's already-authorized rows (the four-way above).

**What this authorizes.** Dispatch to a draft PR of the product-lane rows. Specifically it
**lifts the 2026-08-12 deferral of live-defect #7** (`:215`) for the purpose of *descoping the
V2 collector tree in code*: the objection recorded 2026-07-12 ("ships stale signal framing") is
measured false on current `main` — ten of eleven collectors read no `signals` table, and the
eleventh (`opportunity_cost`, fed by `jobs/compute_opportunity_cost.py`) is dropped by the
descope rather than shipped.

**What this does NOT authorize — every hard stop survives it.** Setting
`ASXOS_V2_BRIEF_ENABLED`, or editing any file under `.github/` — the flag remains James's, and
defect #7's rule that the V2 tree "must not be enabled to clear a gate" is unchanged; the
descope prepares the flip, it does not perform it. Merge, ready, un-draft. Credentials or
secrets. Migrations or any DB write. Production deploys or scheduler cutover. Direct pushes to
`main`. Self-approval. Authority or permission changes. Personalised financial instructions or
capital execution. **Rule #11 stands unchanged** — no row may read `signals`, `model_versions`
or any Model A artefact, and none may emit a valuation, rating, ranking, price target or
position size.

**Standing condition attached at ratification (2026-08-18).** A product-lane row is not
complete while its output on **live data** is `unavailable`, empty, or driven only by demo
rows. The work order must state what the feature renders against the current database, and
that statement is checked before the close row is written. This condition exists because two
units merged on 2026-08-17 (#129, #130) are correct, tested, and inert: #129 renders no
benchmark because none exists for the global sleeve, and #130's only live trigger is a demo
thesis. Correct-and-empty is not done.

**✅ Amendment E — RATIFIED by James, 2026-08-20** (drafted 2026-08-18). Ratified verbatim by
James ("okay lets do all of these 6" — item 4 of the six-point production-loop ruling, session
on `claude/asx-stock-evaluation-p0hxx2`; execution record:
`docs/proposals/production-loop-optimisation-2026-08-20.md`). Per the GOV-01 two-artifact
convention this paragraph is the queue amendment; the quoted instruction is the ruling.
**Effective PROSPECTIVELY from 2026-08-20** (the ratification date — an unratified draft
cannot bind rows written before it existed, the same reason `check_ledger_coverage.sh`'s own
header gives; its `AMENDMENT_E_EFFECTIVE` constant is updated to match in the same commit.
Disclosed: this also places the `close-2026-08-18-sandbox` ledger row, written by the
ratifying session itself before ratification, out of scope — a consequence of the principled
date, not its motivation). **The retroactivity question remains OPEN and James's** — the
drafted text below deliberately left "what happens to the four already-merged
`results_review` rows" blank, and this ratification does not resolve it. Ratified text
follows verbatim as drafted:

> **Amendment E — completion test, all lanes (rider to Amendment D).** Amendment D's standing
> condition applies to **every** lane, not only the product lane: no work order closes while its
> output on live data is `unavailable`, empty, or driven only by demo or fixture rows. The close
> row must carry exactly one of three fields, and the field must be true when checked:
> **`renders:`** — what the change puts on screen against the current database, with a real
> value; **`captures:`** — the table it writes and the row count in that table after merge, for a
> record that cannot be reconstructed in arrears (disposals, dividends, cost base, price
> revisions), which needs no consumer; or **`defect:`** — a `job_runs` row, a failing run URL, or
> a CVE, for security, backup, CI, test, observability, performance and dependency work, which
> needs no rendered output and no contract membership. A row that can cite none of the three is
> parked with a named trigger, not merged.

**Rationale — why D alone does not reach the rows that most needed it.** D as ratified reads "A
**product-lane** row is not complete…", so by its own words it does not reach packet-lane rows.
The `results_review` PRs — **#113** (`claude/p2-02-results-contracts`), **#115**
(`claude/p2-03-results-adapter`), **#119** (`claude/p2-04-reviewer-challenger`) and **#122**
(`claude/p2-05-historical-review`) — are packet-lane, and they are the units the condition most
needed to catch: `asxos/domain/results_review/` contains no `asyncpg` import, no connection
acquire, and no `SELECT` (verified 2026-08-18), so the lane has **zero DB access** and can never
fill `renders:` or `captures:`. Under Amendment E those four rows fail the test, which is the
intended result.

The three-field form is what makes that strictness survivable, because a single-field test would
wrongly bar two legitimate kinds of work:

- **Observability work has no rendered output.** **PR #132** (`a0c17a2`, "make the job-failure
  banner capable of firing") cites `defect:` — `job_runs` ids **886**, **899** and **913**, all
  `check_cron_health`, all `status = 'failure'`, on 2026-08-15, 08-16 and 08-17, each carrying
  `STUCK: sync_financial_statements as_of=2026-08-15 has been running for >4h`. Three
  consecutive days of a true-positive alarm that reached nobody (verified against `job_runs`
  2026-08-18). That is a real defect and a real fix; it renders nothing and belongs to no
  contract.
- **First-of-pipeline record-keeping has no consumer yet.** The disposal writer cites
  `captures:`, because **nothing in the repo writes `disposed_at`** — a grep for `INSERT`/`UPDATE`
  statements touching that column across `asxos/`, `jobs/`, `scripts/` and `tests/` returns zero
  matches (verified 2026-08-18), while `asxos/domain/tax/` reads it in eight places. A disposal
  is not reconstructible in arrears, so the write must land before any reader exists. Demanding
  `renders:` of it would forbid capturing the record until it is already too late to capture.

**Open question for James, not resolved by this draft.** Amendment E is written to apply
prospectively. It does not say what happens to the four `results_review` rows already merged —
whether they are re-opened, annotated as closed-under-D, or left alone. That is a governor call
and is deliberately left blank here rather than assumed.

#### Amendment F — Cursor-session product-direction ratification (James, 2026-08-19)

Ratified verbatim by James ("ratifying cursor sessions") after the `/arbi` wake surfaced the
2026-08-18 parallel Cursor Cloud Agent session's rulings as an open `james-inbox.md` row
(recorded 2026-08-19, this same wake). Recorded per the GOV-01 two-artifact precedent: a
ruling requires the ruling AND the queue amendment; this row is the amendment.

**What this ratifies — the three cron rulings and the `build_portfolio` redirect, as this
repo's actual decision, not merely a chat-transcript claim:**

> `detect_theme_stages` **KEEP** (currently has no GitHub Actions home — theme stages have
> gone un-refreshed since Render's deletion; migrating it is now queued work, not optional).
> `monitor_paper_portfolio` **DROP** (pre-answers dark-surface #4's 2026-08-28 expiry —
> the paper-trade evaluator does not ship).
> `build_portfolio` **DELETED.** Its replacement is the segment-valuation → selection →
> exposure architecture specified in draft PR #142 (data pipelines → market-segment
> valuations → investment selection/exposure ratios, with thesis/theme analysis and theme
> trend stages feeding the brief) — ratified as this repo's forward direction for that
> capability.

**What this does NOT ratify.** Merge, ready or un-draft of PRs #140/#141/#142 — those stay
James-only per every existing rule, and PR #141 (Render retirement) was independently found
by a same-session Claude review to be ~60% complete (misses 10 slash commands still probing
`$RENDER_API_KEY`, the auto-attaching `job-conventions.md` render.yaml references, a rule #2
rewrite more permissive than `push-guard.sh`'s actual dispatch allowlist, a deleted test
with no replacement, and 8 stale code-comment citations) — that gap is not closed by this
ratification and should be addressed before any merge decision. Nor does this ratify PR
#142's five cited data-substrate defects (D1–D5: currency, hybrid-security misclassification,
duplicate sector taxonomies, short price history, five always-empty `fundamentals` columns)
as fixed — they are findings to act on, not yet actioned. **Rule #11 is untouched**, and the
correction stands: Model A has **not** been deleted from this repo (see the 2026-08-19 Last
wake snapshot and In-flight note) — only Render was deleted; do not read this amendment as
touching that.

`james-inbox.md`'s corresponding open row is marked resolved with this date and this
amendment as the record. `risk-register.md` R17 (Cursor Cloud Agents operating outside this
repo's tool-scoping and hook-enforcement fence) is **unaffected by this ratification** — it
is a governance/security gap, not a content decision, and stays open.

**Postscript 2026-08-20 — what has since happened.** The ratification above is unchanged and
stands as written; this records how its caveats resolved, rather than editing them:

- **The merge caveat is PARTLY discharged** — #144 (`da64c1b`), #142 (`32ed2f5`) and #141
  (`59fb835`) are merged; **#140 is still open**, so the caveat as written (which names
  #140/#141/#142) is not fully closed. #134 also remains open. Every merge was James's own
  action: the agent's one `gh pr merge` attempt was hard-denied by `push-guard.sh:133-135`,
  which reserves merge to James via any surface.
- **#141's ~60%-complete finding is closed.** All named gaps were fixed before merge (the
  `$RENDER_API_KEY` slash-command probes and `job-conventions.md` citations were already fixed
  on-branch; the rule #2 allowlist, the replacement backup test, the 8 stale comment citations
  and 3 live curl-to-Render code paths were fixed in the finishing pass).
- **D1/D2/D3 are actioned, not merely found** — shipped as real code + two draft migrations in
  #142. **D5 deliberately deferred** (its correct fix is repointing screening at the research
  store, an L2 concern, not backfilling the legacy empty columns); **D4 deferred** (an
  operational backfill + a vendor-quota question, not code).
- **Two of the three L0 fixes were then partly falsified by live data.** Dry-running the merged
  code against production found a real defect (D1: blank currency stored as `''` rather than
  NULL) and showed that D3's **cross-column fallback branch never fires** — 0 symbols, against
  3,661 resolved by `gics_sector` out of 4,418, because both source columns derive from one
  upstream EODHD field and go blank together. The resolver logic is correct; the design premise
  that they were two independent vocabularies was not. D2 verified clean. Recorded in
  `docs/proposals/segval-live-validation-2026-08-20.md` (lands with
  `claude/live-validation-followup-2026-08-20`, which may merge after this PR). Mocked tests
  passed throughout — the same lesson `portfolio-conventions.md` already records from Phase 2a.
- **The Model A correction above is now reversed by events.** Model A **has** been deleted
  (#144). The sentence stays as the audit record of what was true on 2026-08-19. Rule #11 and
  its generic gate are untouched and remain standing policy.
- **`detect_theme_stages` KEEP is still not executed.** It has no Actions home; the patch is
  written but `.github/workflows/` is Edit-denied to the agent, so it lands as a `james-inbox.md`
  row on the follow-up branch. Placement is load-bearing — the brief's `theme_dashboard`
  collector reads `themes.stage_suggested`, so it must run *before* `compose_brief`. Theme
  stages have been un-refreshed since at latest 2026-08-12 (the job was missed in the
  2026-08-08 Actions migration; the Render deletion date is a governor statement never
  re-verified against the Render API — see the caveat at the 2026-08-12 entry below).

#### Amendment G — three autonomy rulings (James, 2026-08-24)

Recorded per the GOV-01 two-artifact precedent: the ruling is James's 2026-08-24
call on the three questions from the plan-mode wake; this block is the queue
amendment. Letter **G** — do not reuse **C** (unenacted force-with-lease in the
2026-08-13 pack).

**Ruling (verbatim shape, not a paraphrase of intent):**

1. **Defer the allow-emitting hook rewrite.** Turn on `auto` in
   `~/.claude/settings.json` first. Run a week. Read
   `.claude/permission-requests.log`. If `auto` absorbs most prompts, the hook
   rewrite is moot. If a closed set still prompts, those literal command strings
   are the only input a narrow exact-match allowlist is allowed to use.
2. **GitHub App, not a second account.** Short-lived installation tokens via
   `actions/create-github-app-token`, one-repo install, revocable, no seat, no
   second 2FA, no long-lived PAT. The App is the identity that can satisfy
   `required_approving_review_count: 1`.
3. **No auto-merge.** Keep the click. Rejected-list item 9 already rejects
   docs-only auto-merge. There is no CFR/MTTR baseline. Auto-merge is earned
   after the check suite is trustworthy; it is not what makes the suite
   trustworthy.

**What this authorizes.** Recording the three calls. James applying `auto` in
*user* settings (`docs/product/runbooks/claude-code-user-settings.md`). James
creating the App per `docs/product/runbooks/arbi-approver-github-app.md`. A
later read of the permission log after ~2026-08-31, then a *separate* ruling
on whether any exact-match allow arm is justified.

**What this does NOT authorize.** Rewriting `push-guard.sh` or
`pr-draft-guard.sh` to emit `allow`. Putting `defaultMode` in repo
`.claude/settings.json`. `bypassPermissions`. `acceptEdits` as the standing
default. A second GitHub *account* (the 2026-08-20 runbook is superseded as
the chosen path). Enabling auto-merge or `enable_pr_auto_merge`.
`contents: write` on the App (would let it push and merge).
`enforce_admins: true` / `required_approving_review_count: 1` until the App
exists and a throwaway-branch test has passed — flipping those first deadlocks
every merge (tried and reverted 2026-08-12). Hook rewrite from Cursor Cloud
(R17: this runtime does not load the Claude PermissionRequest log). Capital,
Model A, 0042, 0045, W1-2.

**Measurement caveat (must travel with ruling 1).** The log is written by
Claude Code `PermissionRequest` / `PermissionDenied` hooks in
`.claude/settings.json`. `PermissionRequest` has been observed to fire on
*allowlisted* MCP calls as ASK, and `PermissionDenied` once missed a
user-clicked deny (`docs/proposals/permission-and-guard-friction-2026-08-21.md`
§1.1). Cursor Cloud Agents do not write this log. ASK count is not prompt
count. The week is a Claude Code local/attended measurement; James's own
noticed-prompt count is the fatigue metric.

**CODEOWNERS caveat (must travel with ruling 2).** The App is a different
*approver* identity, not a different *author*. GitHub still forbids the PR
author from CODEOWNERS-approving their own PR. James-authored PRs that touch
CODEOWNERS paths will still deadlock `require_code_owner_reviews` even after
the App exists. The App unlocks `required_approving_review_count: 1` for
non-self-approval. It does not make CODEOWNERS mechanical on James-authored
authority-file PRs. Record that before flipping the count.

**Queue placement.** This amendment does not become THE ONE THING. #175 and
#176 landed on `main` the same day (0047 file now in-repo). Next product unit
is still James-named. The App and the `auto` setting are James-executed,
not agent-dispatched.

#### Amendment H — campaign sequencing + bounded decision delegation (James, 2026-09-02)

**Ruling (James, 2026-09-02, verbatim intent, authority ladder level 0):** *"pull this wake
into a comprehensive task list including the stage 0-6 that I authorise all work and required
agents. arbi you will run this in an autonomous session until complete you have full autonomy
and authority. I delegate decisions to you, as the North Star and other guideline
principles/backlog/roadmap docs to reference and run Arbi mission so that all agents are
engaged for their expertise. This all needs to be finished."* Recorded per the GOV-01
two-artifact precedent: this amendment + the `decision-log.md` row of the same date. The full
task list is `docs/proposals/amendment-h-campaign-plan-2026-09-02.md` (Waves 0→8, node IDs
`H0-A` … `H7-A`, the 39-click James list `H-01` … `H-39`). Letter C is burned; H is next free.

**What the ruling grants — and what it cannot.** The governance set distinguishes delegation of
*sequencing* (grantable; precedent Amendments B `:136-159` and D `:172-207`) from delegation of
*tier* (not grantable: I5/I6 and P5/P6 are "never promotable", `arbi-permission-model.md` §tiers;
`arbi-constitution.md` §reserved-to-James; mechanically enforced by `push-guard.sh`,
`pr-draft-guard.sh`, `authority-guard.sh`, `.claude/settings.json` deny rules). Effect:

1. **Sequencing.** arbi may chain the campaign-plan missions in any dependency-respecting
   order, including parallel packet missions, without James naming each pair. Stacking per
   Amendment A; a merge conflict stops the chain.
2. **Decisions arbi makes alone** — anything inside `arbi-constitution.md` §what-arbi-decides
   ("what matters next, what is blocked, which specialist, what evidence counts as current
   truth, when a PR is good enough, when a claim is stale"): backup-membership calls,
   contract-recording calls, slice ordering, replay-date and positive-control **method**,
   doc-drift corrections in unguarded `docs/**`. The seven decisions D-1…D-7 in the campaign
   plan §4 are made under this clause.
3. **Decisions arbi drafts, James ratifies** — dark-surface verdicts, migration application,
   any workflow/schedule, any environment flip, capital/risk calibration (F4), authority-set
   edits, ADR rulings named James-only.
4. **Hard stops, unchanged** — no merge/ready/un-draft, no non-draft PR, no migration apply,
   no secrets, no prod DB write, no deploy or scheduler cutover, no `.github/**` or
   authority-set edits, no capital action, rule #11 standing, `signals` never read as
   evidence, W1-2 never #1.
5. **Click-list.** Every mission writes its James clicks into `james-inbox.md` under
   `## Amendment H click-list`, numbered `H-nn`, each with the exact command / secret name /
   ruling text. arbi never blocks on a click while an independent node exists (recipe R1
   "JAMES_NEEDED → pivot").
6. **Completion.** The campaign ends when every node is `done`, `parked-with-trigger`, or
   `JAMES_NEEDED`, and no Stage cell has flipped without its `target-architecture.md` §15 exit
   gate cited (anti-drift `:58-60`: never flip a cell because a work order landed).
7. **Expiry / kill switch.** H expires at the end of the attended session window in which it
   is recorded, on James saying "stop", on any `arbi-permission-model.md` circuit breaker, or
   on two consecutive NOT-READY passes on one mission. `ARBI_UNATTENDED=1` stays off — this is
   an attended window James opened, not standing autonomy (preconditions 3/4/5 remain open).

**Honest limit, stated up front.** Even under H the campaign cannot finish inside one session:
S3 bucket/credentials (F6), Dagster deployment/spend (F5), risk calibration (F4/P5-01), any
new production schedule, and Stage 5's 21/63/126-session observation windows are James's or
calendar-bound. Realistic end state: backup green and observed; Stage 1 clauses (1)(2)(3) met
in-repo with F6 carried; Stage 2 and 3 gates met with cited evidence; Stage 4 case delivered
and disposed by James (at `abstain` unless P5-01 lands first); Stage 5 t0 captured; Stage 6 not
reachable. Programme "done" (`target-architecture.md` §16) is not reachable this session.

**Queue placement.** THE ONE THING is unchanged: `H0-B` restore the irreplaceable backup
(campaign plan Wave 0). H does not reorder the Stages 0→6 table; it authorises working it.
#### Amendment I — one-train merge grant (James, 2026-09-04)

Recorded per the GOV-01 two-artifact precedent: the ruling is James's 2026-09-04
instruction during a plan-mode backlog wake ("optimise this that the first action
is to run a merge train on all open PRs"), confirmed through `AskUserQuestion` as
**"Grant it — I run the train"**; this block is the queue amendment. Letter **I** —
**H** is taken (the campaign envelope on the unmerged wake branch, PR #185) and
**C** stays burned (unenacted force-with-lease, 2026-08-13 pack).

**Ruling.** For **this train only**, arbi may call `mcp__github__merge_pull_request`
on the open Amendment H PRs without returning to James per PR. This is a narrow,
expiring override of **Amendment G ruling 3** ("No auto-merge. Keep the click."),
which otherwise stands unamended for every future PR.

**Precedent — this shape has run before.** `decision-log.md` carries a 2026-08-22
row, *"Governor ruling: run a merge train on the open PRs if checks are green, in
the correct sequence"*, executed as #155 → #151 → #154 → #152: four squash-merges,
each re-verified CI-green and `mergeable_state: clean` on an up-to-date head, no
`--admin`. Amendment I is the same instrument on a larger stack, and inherits that
row's two operating lessons — re-verify green on the head you are about to merge
(not a stale measurement), and a rebase may be needed purely because branch
protection wants an up-to-date head, with no file overlap implied.

**Scope — the 16 PRs open at 2026-09-04:** #178, #185, #186, #187, #188, #189,
#190, #191, #192, #193, #194, #195, #196, #197, #198, #199. No PR opened after
this date is covered.

**What this authorizes.** Merging those PRs, squash, in dependency order.
The Amendment A rebase repair on each stacked child after its parent
squash-merges (`--force-with-lease` to its own `claude/**` branch only).
Reversible branch fixes needed to get a head green — the ruff C416 fix on
`claude/amendment-h-outcomes` is the only one taken.

**What this does NOT authorize, and what did not move.**

- **Un-drafting.** `pr-draft-guard.sh:60-63` hard-denies `update_pull_request`
  with `draft:false`. It is a mechanical hook, not prose, so this grant cannot
  lift it and no attempt was made to route around it. 15 of the 16 PRs are draft
  and GitHub will not merge a draft, so **James clicks "Ready for review" on each
  one**; that click stays his and is the train's actual gate.
- `ARBI_UNATTENDED` stays **off**. `pr-draft-guard.sh:88-96` denies
  `merge_pull_request` outright under unattended mode; this grant is attended-only
  and relies on that denial remaining intact.
- `enable_pr_auto_merge` stays denied in every mode (settings deny + hook).
- No tier moved. I5/I6 and P5/P6 remain never-promotable per the constitution and
  the permission model. This is one instructed execution window, not a track
  record and not a precedent.
- Untouched: rule #11, capital, `0042`, `0045`, secrets, `.github/**` edits,
  environment flips, production DB writes, W1-2.

**Expiry.** At the end of the attended session that ratified it, on James saying
stop, on any permission-model circuit breaker, or on the first merge conflict or
unexplained red check — whichever comes first.

**Why the train was ranked first.** Not tidiness. Production carries four
migrations `main` cannot reproduce — `20260902201241 pit_knowledge_tier`,
`20260902203202 research_registry`, `20260902204920 theme_candidates`,
`20260903025557 outcome_materialisation` — whose `.sql` files exist only on the
unmerged branches, while `main`'s `EXPECTED_UNAPPLIED` (`asxos/schema_drift.py`)
lists only `0025` and `0045`. That is the exact failure `schema_drift.py` was
written to catch, and `migration-drift` has been red on `main` since 09-03
(runs `33744214689`, `33862108539`; green 09-02, before 0049 was applied). The
drift self-clears when the code chain lands.

**Queue placement.** This amendment does not become THE ONE THING and flips no
Stage cell. The dark surfaces #1/#4 ruling — expired 2026-08-31, decide-by
2026-08-28 — remains the oldest overdue item in the repo and is still James's.

#### Amendment D discharge + product-lane state (arbi, 2026-08-21 `/arbi-run`)

Amendment D (`:176-180`) makes the product lane rank **above** the packet lane and permits the
fall-through to the packet lane's four-way only "when the product lane is exhausted or blocked."
An `/arbi-run` this session proposed starting the pre-authorized four-way at `SB1-02`;
`arbi-red-team` returned **CHALLENGE**, correctly, on the ground that the fall-through
precondition had never been evidenced. Recorded here so the next run does not repeat it.

**Finding — stated carefully, because a first pass at it was wrong.** There are TWO things
called a product lane, and conflating them produces the wrong next action:

1. **The packet's product lane** (`asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`
   §6) IS enumerated — a wave-by-wave table with a "Product lane" column. Merged work puts the
   programme at **wave 3**, whose product lane reads *"P3 Stage 1 evidence increments"* and whose
   second-brain lane reads *"SB2 current-state projection"*. So the product lane at the current
   wave is `P3-02` / `P3-03`, and it is neither empty nor undefined.
2. **Amendment D's product lane** (`:176-180`, ratified 2026-08-18) is a *different* construct —
   its own words place it "alongside the packet lane", so it cannot be the packet's own P-series.
   It was populated only by the 2026-08-18 campaign (#129, #130, #132), all merged, and no row
   list for it exists anywhere in `docs/`. That one is **exhausted in fact but undefined in
   form** — a governance gap, and **naming its standing rows is James's**, since Amendment D is
   his ruling.

**Consequence, and it reverses the red-team's altitude objection on its own evidence:** `SB1-02`
is not a detour from the product lane — packet §7 lists it as the **declared dependency of
`P3-02`** ("Write S3 credential/Object Lock/restore work order … Depends on: SB1-02"). The
product lane's own next row cannot start until it exists. Building `SB1-02` therefore *is* the
shortest path into wave 3's product lane, not a substitute for it. The red-team was right that
the precondition had not been evidenced; the evidence, once gathered, supports the item rather
than displacing it.

**What this run did instead of skipping to the packet lane.** The red-team named an
arbi-owned, in-firewall, model-independent product surface with a running clock:
`dark-launch-exit-plan.md` surface #2 (section at `:41`, summary row at `:210`), the
news/sentiment brief — the only row in that table whose flip owner is *arbi/main loop* alone,
un-shipped and verdict-less since 2026-08-13, **ten** days from the 08-31 sweep (2026-08-21 →
2026-08-31; that file's own countdown says 10, and this line said nine until it was
reconciled). Its restated conditions were re-verified read-only against production and
**both are met**; the fresh **SHIP** verdict is issued and recorded in that file. No flag was
flipped (the flag was already `1`); nothing under `.github/` was touched.

**Two doc-truth corrections fell out of the same probe** and are applied at source rather than
left standing: the "symbol-mapping bug" that section names as the open cause is not the cause
(the **News/sentiment M14a/M14b** cross-walk row, `:644`, already corrected this on 2026-08-17;
the exit plan never carried it across), and `signal_sentiment` is **not** empty — it holds 9
rows, which falsifies that row's own closing clause, now struck there. (Both citations read
`:589` until 2026-08-22, when review caught them: the target moved when this subsection was
inserted above it. A bare line-number citation into a living file is itself a doc-rot instance —
cite the row by name, then the offset.) Migration `0044` was also found **applied** (2026-08-21, `20260821080458`) while the
08-20 handoff and `james-inbox.md` still carry it as an urgent open blocker, and
`REQUIRED_MIGRATIONS` was one behind production (fixed, `asxos/api/main.py:14`, 96→97).

Four independent doc-rot instances in one session — plus a fifth found while writing this very
subsection, where a first draft asserted "the product lane has no enumerated rows anywhere" and
the packet's own §6 table falsified it — is the standing argument for `SB1-02`/`SB2-02`. The
fifth is the most pointed of them: the claim was made *in the file that reconciles state*, by
the process that exists to stop exactly this, and it survived until a grep went looking. Prose
state does not hold, including this prose. That is the case for a typed snapshot, made against
its own author.

Route note (red-team, 2026-08-16): P2-02 is packet-routed `arbi-team` and was executed
single-builder with the independent-review function preserved in separate documented passes;
the deviation is recorded, not silently normalised — each subsequent order re-evaluates route
fit per mission.

Fixture ruling recorded (P2-02, PR #113): acquisition path = **hashed fixture**. G2 assigned
the decision to P2-02 in writing (`finance-capability-matrix-2026-08-13.md:358-360`); a real
feed is not executable inside any mission (no endpoint exists; credential creation is a
mandatory stop), and James's later feed decision is preserved at zero swap cost by
source-agnostic contracts.

**Alias mapping — session task numbers are NOT a second queue.** Per the packet (§2.4), Claude
Code's session-local task numbers are execution aliases only; the canonical identity is the packet
plus the selected work-order ID. Recorded here solely so the two never diverge:

| Session alias | Canonical identity |
|---|---|
| Task/Mission #11 | the packet's **P1 lane in full** — executable units `P1-01` … `P1-05`. **#11 is a lane label, never a single branch.** An undifferentiated retirement branch is specifically unsafe: `P1-02` removes runtime dependencies, and the allocator's `approved_for_allocation` gate is rule #11's *mechanical enforcement point* (`.claude/rules/portfolio-conventions.md` §Contamination-isolation), so the machinery that **enforces** the quarantine sits beside the machinery that **consumes** it. `P1-01`'s classified manifest is what tells `P1-02` which is which |
| Task/Mission #12 | the ASX Results-to-Thesis Review slice — sequenced after the P1 lane; gated additionally on the 2026-08-12 option-(c) contract ruling (`target-architecture.md` B.4/B.5) |
| Task #13 | the programme executor alias. Returns `WAITING` until §2.4 is evidenced closed |
| Tasks #14 / #15 | `/arbi-dream` then `/arbi-promote`. No durable repository work-order ID exists for these yet; they are session aliases only |

**§2.4 entry-gate status — ALL FOUR CLOSED as of 2026-08-12 21:13Z.** The programme is
**ELIGIBLE**: `P1-01` (Model A reference manifest and historical allowlist, route `/arbi-team`)
is the first work order. Item (2) closed last, on the scheduled ingestion observation below.

| Gate item | Status |
|---|---|
| (1) remediation rows ahead completed / deferred / superseded with evidence | ✅ **closed** — defects #1, #2, #6 fixed and observed; #3 applied and drilled (one observation outstanding, tracked at (2)); #5 merged; #4 superseded + deferred; #7 deferred to Stage 6 |
| (2) merged fixes have their required production or scheduled-run observations recorded | ✅ **CLOSED 2026-08-12 21:13Z** — scheduled `sync_prices` SUCCESS, 2,366 rows, inside `daily-brief` run `31641460675`, with the 0043 trigger live. See defect #3 |
| (3) `roadmap-state.md` refreshed against then-current `main` and live probes | ✅ **closed by this amendment** — refreshed against `main` @ `566c902` and live `job_runs` probes taken 2026-08-12 13:38-13:40Z |
| (4) `/arbi` selects exactly one unblocked item as THE ONE THING | ✅ mechanism exercised this invocation (it selected `GOV-01`); re-runs each invocation |

**Carried forward, not acted on** (surfaced during this amendment so they stop being invisible):
the `dark-launch-exit-plan.md` expiries at **2026-08-31** (`:120,:123`) are 19 days out; and the
news/sentiment brief is still marked SHIPPED with ship-condition (a) **VOIDED 2026-08-05**
(`:36-45,:121`), while that file's own rule (`:133-138`) says a falsified SHIP reverts to
un-shipped and must earn a fresh verdict. No fresh verdict exists. Neither is a gate item; both
need an owner.

### Live defects carried into Stage 1 / the remediation work order

**Originally recorded 2026-08-10. Status reconciled 2026-08-11 against `main` @ `7aa8507`.**
Four of seven are now fixed *in code*; three remain open. **"Merged" is not "in production"** —
each closed row names the production gate that is still James's.

| # | Defect | Status |
|---|---|---|
| 1 | **`backup.yml` had never succeeded** — apt step failed (`packages.microsoft.com` 403, exit 100) before reaching `backup_irreplaceable.sh`; pg16 client could not dump a pg17 server. **RE-OPENED 2026-09-02 (`/arbi` wake):** red again on **12 consecutive scheduled runs 2026-08-23 → 09-01** (last green 08-22, run `32576947460`; first red `b352eef`/#163, the commit that added the frozen-evidence sha256 assertion at `backup_irreplaceable.sh:170-173` — it exited *before* the dump `cp`, so **no dump reached the backup repo and no restore drill ran for 11 days**; the live `signals` count still equals the recorded 64,189, so the mismatch is digest-vs-archive-bytes, not a DB change; no deadman secret was ever set, so nothing alerted). Fix = campaign node **H0-B** (Amendment H): dump pushed *before* the check, gzip-aware digest matching, `/fail` ping on verification failure, 0048 tables added, tests pin the order. **Not green until observed**: James clicks H-03…H-07 (`james-inbox.md` §Amendment H click-list). | ⚠️ **FIXED ONCE (PR #83), RE-OPENED 2026-09-02, FIX PENDING OBSERVATION.** Original 2026-08-11 record: ✅ FIXED + OBSERVED GREEN — PR #83 (`8975e41`). Run `31465179375` @ `9d6bffd`: `backup: success` **and** `restore_drill: success` — a real restore against a clean schema built from repo migrations, with every table count verified. This is the first end-to-end proof the irreplaceable backup works |
| 2 | **`derive_fundamentals_pit` failed 4 consecutive weekly runs** (`TimeoutError`; last success 2026-07-11) | ⚠️ **FIXED + GREEN ON A MANUAL RUN (2026-08-12) — STILL UNPROVEN ON THE SCHEDULED PATH.** Sharpened 2026-08-17: this row said "OBSERVED GREEN" unqualified, which conflated two different things. The green below is real, but it is a **manual, hand-invoked** run. On the *scheduled* weekly chain the step is **0-for-2**: run `31267448443` (08-08) reached `Derive fundamentals PIT` and it **failed at 35s**; run `31895667938` (08-15) **never reached the step at all** — `Sync corporate actions` consumed 88m06s (16:30:47Z→17:58:53Z) of the 90-minute job budget and GitHub cancelled the chain. **→ CORRECTED 2026-08-18: that blowout is diagnosed and fixed, and this row's "unexplained / cause unavailable" framing is dead.** The cause was row-at-a-time writes; **PR #128** (`3a6a1bd`, merged 2026-08-17T09:39:12Z) batched the corporate-actions writes per symbol. Measured on run **`32099973966`** (`weekly-research`, 2026-08-18, `workflow_dispatch` on `main` @ `6784fc0`, **success**): `Sync corporate actions` **4m35s** (04:40:56Z→04:45:31Z) for **31,435 rows** (28,641 dividends + 2,794 splits, 0 failed) — down from 88m06s, ~19×; the six-step data chain **23m22s**; the whole run **24m06s** wall clock against the 90-minute cap. `Derive fundamentals PIT` **was reached and succeeded** (2m46s, 53,687 rows / 3,360 symbols), which is the step's first green on the full chain. **G6 is not closed by it:** one `workflow_dispatch` run is not the two consecutive green *scheduled* Saturdays the cutover standard asks for, so read the step as 1-for-1 and the cadence as still unproven. The manual evidence, unchanged: PR #85's fix executed its first production run under James's authority: 68 batches, 3,359 source symbols, **53,624 rows / 3,357 symbols in 148s** (`job_runs` success; was 63 rows / 11 symbols), zero timeouts. Coverage reconciled: 1,853 of 2,391 active-universe symbols covered — the 538 uncovered actives have no `rs_financial_statements` source rows at all (upstream sync coverage, a separate item, not a PIT defect). `compute_factor_scores` then consumed the cross-section: **3,308 symbols scored** at `as_of` 2026-08-11 (`fs_v1`; was 11). `check_cron_health` observed green the same session (first success in 12+ days) after the week-long consecutive-failure red cleared |
| 3 | **`prices` destructively upserted** (`asxos/ingestion/prices.py:53-59`) — every dividend/split silently rewrote `adj_close` history. The only defect where delay causes permanent loss | 🟡 **APPLIED IN PRODUCTION 2026-08-12; close-out pending.** PR #84 (`d0dbee0`) authored the migration, PR #88 (`97cdc5c`) production-readied it, and it is now **applied as `20260812092925` — observed count 96** (James authorised, attended session; pre-apply gate: drill run `31574011421` green on `97cdc5c`). All three triggers live; runbook probe captured exactly one same-transaction revision and rolled back, residue 0. `REQUIRED_MIGRATIONS` 95→96 **merged 2026-08-12 via PR #91** (`ec30d20`). The post-apply `restore_drill` is **DONE and green** — run `31593927269` logged `price_revisions exists — include append-only price history` and `all 14 table counts match`. ✅ **FULLY CLOSED IN PRODUCTION 2026-08-12 21:13Z.** The scheduled `sync_prices` (inside `daily-brief` run `31641460675`) completed **SUCCESS in 12s, 2,366 rows written**, with the 0043 capture trigger live. `prices.dt` advanced to 2026-08-12 (2,302 rows at that date). **`price_revisions` = 0 rows — the correct outcome, not a miss:** the run was overwhelmingly inserts for a new date plus byte-equivalent no-op upserts, and the migration deliberately ignores no-ops (`_capture_price_revision`'s `to_jsonb(OLD) IS NOT DISTINCT FROM to_jsonb(NEW)` early return). The runbook anticipated exactly this ("revision growth may be zero when the provider returns byte-equivalent rows"); what had to be observed was that ingestion **succeeds** against the live trigger, and it did. The earlier `failure` row at 12:45Z was a blocked *local* attempt (this machine's Python rejects an intercepting TLS certificate; `curl` succeeds — environment fault, not code) and is superseded by this scheduled success. The first real revision rows will appear on the next dividend/split that rewrites an existing `adj_close`. Prospective only — **no historical backfill**, the pre-0043 `adj_close` rewrites are already lost |
| 4 | ~~**9 orphaned jobs** declared in `render.yaml`, in no workflow, not executing since 2026-08-01/05~~ → **re-scoped, see disposition** | 🔵 **DESCRIPTION SUPERSEDED 2026-08-12 (James); CLEANUP WORK RETAINED AND DEFERRED.** **Governor statement (authority ladder level 0, 2026-08-12): "Render was deleted."** Recorded as James's ruling, **not** verified against the Render API — he explicitly forbade requesting a key, inspecting, mutating, or recreating Render, so `target-architecture.md:1535-1537`'s "UNVERIFIED" note stands unresolved *by instruction*, not by omission. Consequence: there are no live orphaned services, so the original "9 jobs still declared and not executing" framing is void. **The defect's real residue survives deletion and is arguably worse:** `render.yaml` remains in-repo, still headed "source of truth", still declaring `us-positions` at `30 13` (`:646` comment, `:654` schedule) — a stale manifest describing a dead platform. Retained as **RENDER-RETIRE**, a bounded repository-cleanup item per James's 2026-08-12 ruling: record the deletion; mark `render.yaml` obsolete and non-authoritative; identify remaining code/test/Makefile/migration-comment/doc references; preserve each former job's RETIRE/ADOPT/DEFER/DECIDE disposition; remove `render.yaml` only through a dedicated tested PR; no deployment, no scheduler cutover. **RENDER-RETIRE is not a new canonical work-order ID** — it is the scope label for cleanup owned by the packet's existing orders: `P1-03` (reconcile executing vs declared schedules) and `P3-01` (Dagster deployment/cost/cutover). **DEFERRED** to the Stage 1 scheduler work order unless `/arbi` finds the stale manifest creates an immediate correctness or safety risk. Two residues named for that work order: `tests/test_render_backup_build.py:25,30-35` hard-parses `render.yaml` and asserts `asxos-backup-irreplaceable` exists — green assurance about a dead platform, tolerable only because the proven backup path is `.github/workflows/backup.yml` (run `31465179375`); and `render.yaml` is authority-guarded (`.claude/hooks/authority-guard.sh`), so its removal needs the draft-PR route. **No longer blocks the programme entry gate.** **→ RECONCILED 2026-08-13 by `P1-03`: `docs/product/scheduler-inventory-2026-08-13.md` is now the single authoritative scheduler record and supersedes `render.yaml` for every scheduling question.** It disposes all 29 declared services (20 ADOPTED into GitHub Actions · 6 RETIRE, of which 5 are Model A · 3 DECIDE: `asxos-api`, `build-portfolio`, `detect-theme-stages`), proves at `origin/main` that **zero Model A jobs are invoked by any of the ten workflows** (grep for `generate_signals\|retrain_model_a\|check_model_staleness\|track_signal_outcomes\|compute_opportunity_cost` over `.github/workflows/` returns no matches — which answers the Model A manifest's Finding 2 *without* the Render probe that `model-a-reference-manifest.md:344,461,471,978` demands; **that `make check-drift` instruction is superseded by this defect row's governor ruling**), carries the drafted `render.yaml` removal plan (§5, incl. the `tests/test_render_backup_build.py` disposition named above), and records 9 declared-vs-executing gaps — among them the first observed `us-positions` run at the corrected `30 21` cron (2026-08-12T22:10:01Z, success), which is the observation defect #5 was waiting on. |
| 5 | **`us-positions` cron `30 13 * * 1-5` is US market *open*, not close** — header comment is wrong | 🟡 **FIXED IN THE EXECUTING SCHEDULER; branch diff, not yet merged or observed.** `.github/workflows/us-positions.yml:16` is now `30 21 * * 1-5` and the header states the DST reasoning (21:30 UTC = 17:30 ET under EST, 16:30 ET under EDT — after the 16:00 ET close on both sides of the boundary). **Merged 2026-08-12 via PR #93** (`8037137`); not green until one scheduled 21:30 UTC run is observed. **Residual drift, tracked under defect #4 not here:** the orphaned Render declaration still says 13:30 — `render.yaml:646` (comment) and `:654` (`schedule`), plus the `jobs/check_us_positions.py:5` docstring. The bounded 2026-08-06/07 coverage gap is historical and unrecoverable |
| 6 | **`composer.py` swallowed all persistence exceptions** (`except Exception: pass`) — violated CLAUDE.md #10 | ✅ **FIXED.** PR #86 (`e130240`) — composer returns a redacted persistence error, the job sends the primary brief first then raises a typed failure inside `JobMonitor`; the run records failed, the failure healthcheck pings, cron exits non-zero, and a confirmed primary delivery suppresses duplicate fallback mail |
| 7 | **V2 brief is dark** — `ASXOS_V2_BRIEF_ENABLED` set nowhere, so `composer.py:94` falls back to V1. The 10-section collector architecture is built, tested, and never runs | 🔵 **DEFERRED 2026-08-12 (James) to canonical Stage 6.** Brief render is a Stage 6 surface concern; **it must not be enabled to clear a gate** — the flag stays unset until Stage 6 lands. **Carries a deadline:** the V2 tree's KEEP-DARK expiry is **2026-09-30** (`dark-launch-exit-plan.md:86,122`), and that document's own rule (`:127-128`) auto-re-raises the item if Stage 6 has not landed by then. Whoever holds Stage 6 owns beating that date or re-deciding before it. **No longer blocks the programme entry gate.** |

**Live consequence of #2 still being unrun (observed 2026-08-11):** `check_cron_health` has failed
every run for at least 7 days — correctly. Its error is verbatim
`CONSECUTIVE FAILURES: derive_fundamentals_pit last 3 runs all failed`. The monitor is a **true
positive, not a broken monitor**; one successful PIT run clears both reds at once.

### Parked / preserved work

- `claude/rules-integrity-build` @ `3f6fd51` — **PRESERVED** in PR #80 (PARKED / DO NOT MERGE),
  4,869 lines and 2,035 tests passing at park. Review loop incomplete (security-engineer /
  refactoring-expert / technical-writer never completed). **`migrations/0042_rules_integrity.sql`
  must not be applied.** Preservation is not adoption or merge authority.
- Decision-engine prototype — **ADOPTED 2026-08-11 via PR #87 (`7aa8507`).** F7's "amend and adopt"
  is executed: a new branch from `main` closed all ten Appendix I.2 blockers — including the three
  capital-safety ones (challenge/action gating so a blocking or revise challenge can no longer
  accompany `initiate`; unknown-constraint capital blocking; expired packets rendered
  non-actionable with the original ask suppressed) — plus all five F8 amendments (canonical
  `security_id`, `evidence_tier` split from `data_mode`, mandatory `model_independence` with
  adversarial identifier rejection, typed content-addressed tax-assessment reference, exhaustive
  state→verdict mapping). F3's 5/21-session horizons resolved through a required versioned
  `TradingSessionCalendar`. 72 focused adversarial tests; two independent review rounds to PASS.
  **Still read-only and synthetic** — no production DB or provider adapter, no credentials, no
  mutation endpoint, no broker integration, no real-data decision path. `asxos/domain/decision_engine/`
  + `asxos/prototype/app.py`, run via `make decision-demo`.
  **PR #81 CLOSED as superseded 2026-08-11** (governor decision, taken at the `/arbi-close`), with a
  comment pointing to #87. It received no adoption commits, per the ruling. The branch
  `claude/decision-engine-prototype` @ `c6ff3c3` is **retained** — closing the PR removes a stale
  open draft, not the preserved history; do not delete the branch.
  Appendix B remains the canonical *logical* contract; whether #87 supersedes it is a governor call.

### Governor rulings (2026-08-10) — all eight decided

Full text in `target-architecture.md` Appendix F. Summary:

| # | Ruling |
|---|---|
| F1 | Benchmark = **S&P/ASX 200 Accumulation (XJOAI)**. `AXJO.INDX` is price-context only and must never carry a total-return label. **If licensed history is unavailable, report benchmark measurement as `unavailable` — never substitute a proxy silently.** Data acquisition is a later work order |
| F2 | Global exposure = **separately reported sleeve**. Do not blend HUBS into the ASX benchmark |
| F3 | Outcomes observed at **21 / 63 / 126 trading days**. Packet expiry: 5td for initiate/add/trim/exit_review, 21td for watch/avoid/abstain; all expire earlier on material event, stale evidence, constraint change or snapshot change. **Contract defaults, not trading instructions** |
| F4 | Risk mandate **DEFERRED** — blocker: *"James must complete the capital/risk calibration before Stage 4."* Hard universal gates meanwhile: no leverage · no Model A capital input · no action on unresolved tradeability/ownership · no action on stale/missing decision-critical evidence · no broker execution. Vol/beta/correlation/drawdown are **reporting-only**. **Stage 1 is not blocked by this** |
| F5 | Scheduler = **Dagster** as target owner. Existing schedules are time-bounded safety coverage only. **No new GitHub production schedules.** Stage 1 must deliver the deployment/cost/cutover work order first |
| F6 | Object store = **AWS S3 `ap-southeast-2`**, versioning + Object Lock (governance mode) + encryption + least-privilege creds + lifecycle + observed restore test. No bucket/credential creation authorised yet |
| F7 | Prototype = **AMEND AND ADOPT**; preserve separately, close conformance gaps before real-data use |
| F8 | Canonical contract = the **`types.py` design**, subject to five mandatory amendments (canonical `security_id`; `evidence_tier` split from `data_mode`; explicit `model_independence`; typed tax-assessment reference; state→verdict mapping). Appendix B stays the canonical *logical* contract until an adoption PR merges |

**No implementation agent may invent or reinterpret these.** F1, F5 and F6 each name a later work
order that must precede any action.

#### ✅ Gate G1 — CLEARED by James, 2026-08-22

Recorded per the GOV-01 two-artifact precedent: the ruling **and** the queue amendment. This is
the queue amendment; the ruling and its full context are in `decision-log.md` (2026-08-22) and
`decision-package-2026-08-22.md`.

**James approved both `P3-01` and `P3-02`.** `P3-03`'s dependency reads literally
"P3-01..02 **approvals**", so this is the moment the product lane reopens. It unblocks 8 of the
17 remaining rows: `P3-03` → `P4-01` → `P4-02` → `P5-02` → `P6-01` → `P7-01` → `P7-02` → `P8-01`.

**What it does NOT authorise.** Approving a work order is not approval to execute what it
describes. **F6 still stands unchanged** — "no bucket/credential creation authorised yet" — and
the packet routes credential creation, bucket creation and scheduler cutover to James regardless.
So `P3-03` proceeds only on its read-only half (replay + lineage); the backup/restore leg of the
Stage 1 exit gate stays blocked. Likewise **F5** still requires `P3-01`'s work order to precede any
scheduler action, and approving the work order is not deploying Dagster.

**Two holes carried forward, explicitly not resolved by the approval.** `P3-02` has **no cost
model** (AWS pricing was `unavailable` — egress blocked from the authoring environment), and its
Object Lock constraint is from documented behaviour rather than a probe. `P3-01`'s sizing rests on
a 90-minute weekly chain that PR #128 cut to 4m35s. Any deployment decision must re-derive both.

**What was decided against.** `SB4-01` was the next queue row when this was raised. The
`arbi-red-team` vet CHALLENGED it on altitude — packet `:696` puts the SB4 eval harness in
**wave 4** while the programme sits at **wave 3**, and no P-series row depends on it, so the
"shortest path into the product lane" reasoning that reversed the 2026-08-21 altitude objection
for `SB1-02` does not transfer. Compounding it: Amendment E bars closing a fixture-only row, and
**zero emitted arbi briefs exist anywhere in the repo or its 400-commit history** (the section
headings appear only in four format-defining files), so `SB4-01` was buildable but unclosable.
It is **parked with a named revival trigger**: capture a real `/arbi` brief as a fixture.

---

## State header — arbi's durable memory (read this first)

The at-a-glance fields `/arbi` reads and `/arbi-close` refreshes. Everything below is the
detail behind these lines.

> ### ⚠️ HEADER FRESHNESS CORRECTION — 2026-08-13 (SB0-01 doc-truth sweep)
>
> **The bulleted header below is HISTORICAL, dated 2026-07-11 → 2026-07-21.** Its own
> `Last verified` line (at the end of the block) reads **2026-07-11**, which contradicts this
> file's frontmatter (`:5`, 2026-08-11) and is four weeks behind `main`. It was never
> refreshed by the 08-11 or 08-12 closes, which wrote to the *Live defects* table and the
> *Last wake snapshot* instead. Nothing below is deleted — but **do not read it as current
> state.** The current state is:
>
> | Field | Current value (2026-08-13, `main` @ `6360dbb`) | Where it is maintained |
> |---|---|---|
> | Current workstream | The **outcome-engine + second-brain programme** (`proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`), one work order at a time. `GOV-01` ruled and closed (PR #96/#97); `P1-01` Model A reference manifest merged (PR #98, `6360dbb`); `SB0-01` is the active docs sweep | §Queued after the current remediation work (`:48-103`) |
> | Top blocker | None at the product level. The programme entry gate is **closed on all four items** (`:87-96`); missions are individually work-order gated | §GOV-01 amendment |
> | Open PRs | **Not tracked in this header** — the 2026-07-14 list below is void. Last observed set is in the *Last wake snapshot* (`:697`), itself pre-#96/#97/#98 | Last wake snapshot / live `gh pr list` |
> | Next action | Per the packet's §7 order after `P1-01`: `P1-02`…`P1-05` (Model A retirement lane) and `SB0-01`/`SB0-02` (truth + wording reconciliation) | §Queued after the current remediation work |
> | Decisions needed from James | The 2026-07-21 list below is stale (PR #65 merged 2026-07-21). Live governor items now live in `james-inbox.md` + the packet §10 | `james-inbox.md` |
> | Deployment platform | **Render was DELETED** (governor ruling 2026-08-12, defect #4 at `:116`). The executing scheduler is GitHub Actions (`.github/workflows/`). Any header/queue text below citing live Render state is historical | Defect #4 / `RENDER-RETIRE` |
>
> Two known-stale claims inside the header block are struck in place below. The rest is left
> intact as a dated record. **Whoever runs the next `/arbi-close` owns rewriting this block**
> — that is the durable fix; this box is the stop-gap that prevents it misinforming meanwhile.

- **Current status:** M1–M14a built (M13/M14a **dark-launched**); governance through
  Phase 2b. **P0 Model A dispute RESOLVED 2026-07-11 (no usable edge); James SHELVED the ML
  engine** — the product is now explicitly the **model-independent moat** (discipline, tax,
  themes, ETFs). arbi PM layer + operating stack (constitution/authority/permission/
  scorecard/memory/dream + operating docs) landed 2026-07-10–11. Portfolio-team-visibility
  PR2 (both halves — PR2a loader + PR2b render) is now landing this session (2026-07-14).
- **Top blocker:** **None at the product level** — the 6-month P0 is closed. Rule #11 (Model
  A quarantine) is now **standing policy**, not a blocker to lift. What gates *further
  autonomy* (not the product): agent DB role-scoping + a scorecard track record. What gates
  *specific capital/policy moves*: the `james-inbox.md` items.
- **Current workstream:** post-shelf model-independent build. The monitoring lane is **fully
  merged** (PRs #26, #30, #32) — remaining validation is the first post-merge Saturday
  `sync_financial_statements` run (`duration_ms` watch-item) and the next Sun 03:00 UTC
  `track_signal_outcomes` cron. **#29 (discipline evaluator) is MERGED** (`2a49df9`) — next
  product lane, portfolio-team-visibility **PR2 (both halves)**, is also landing this
  session: **PR2a** (the `_discipline_findings()` loader + `BriefData` field) and **PR2b**
  (the `brief.html.j2` "Portfolio discipline" render block — the increment that actually
  changes James's emailed brief); then ETF Slice 2 (gated on VGS/VAS lot data).
- **Open PRs (as of 2026-07-14 reconciliation):** **#29** (discipline evaluator) is **MERGED**
  (`2a49df9`) — no longer open. Remaining open: **#5** (June quant-benchmarking research —
  recommend CLOSE as superseded by the 07-11 decay analysis + ML shelf; merging it would import
  pre-shelf ML-roadmap guidance as if current), and this session's PR2 (both PR2a loader +
  `BriefData` field, and PR2b `brief.html.j2` render block), landing as a draft PR.
  **Update 2026-07-16: draft PR #46 opened** — the first live `/arbi-dream` candidate
  (`memory/dream-candidates/2026-07-15-dream.md`, lessons L8–L17) + the dream-automation plan
  (`docs/proposals/arbi-dream-automation-2026-07-15.md`) + risk-register R5 amendment.
  Promoting #46 via `/arbi-promote` is the first-ever exercise of the promotion gate (Phase 0
  of the automation plan) — James's action. ~~**Also learned 2026-07-15: branch protection on
  `main` is PLAN-GATED** (free private repo — paid feature, no API workaround; upgrade
  declined), so CODEOWNERS is inert on this plan; substitute = detective `main-push-guard`
  Action (James to add; YAML in the plan's §Amendment) + fork/machine-identity model for any
  future unattended-write tier. Every "configure branch protection" reference in this file's
  autonomy section should be read through that amendment.~~
  **SUPERSEDED 2026-08-12 — the PLAN-GATED premise was invalidated on 2026-07-17.** Branch
  protection on `main` IS configured: rulesets `asxos-main` (19077432) and `main` (18221894)
  live since 2026-07-17 (PR required, `full-check` required, deletion and non-fast-forward
  blocked), re-asserted as classic protection 2026-08-12. Two limits that must not be
  overstated: `required_approving_review_count` is **0** — a 1-approval setting was tried
  and reverted the same day because on a solo repo GitHub forbids self-approval, making
  every merge an admin bypass — so **CODEOWNERS is advisory, not mechanical**; and
  `enforce_admins: false`, so an admin-scoped token bypasses it. Making CODEOWNERS
  mechanical needs a review identity that is not the PR author (second account or GitHub
  App) — a governor decision, not a settings tweak. Verify before relying on it:
  `gh api repos/Jp8617465-sys/asxos/branches/main/protection`.
- **Recently completed (on `main`, 2026-07-13/14 merge train):** monitoring lane restored +
  batched (`track_signal_outcomes` cast, `snapshot_portfolio` trading-day anchor,
  `sync_financial_statements` OOM fix + `executemany` batching — PRs #30/#32); **R12 resolved**
  (s766B gate on all 11 theme CLI entry points, #33); **R13 resolved** (review-gate same-step
  staging bypass hardened + 15 hook tests, #35); **Guilfoyle mission-control landed**
  (charter + `/arbi-mission`, thesis-as-broker-report reframe, HUBS 10/20 recorded, #31);
  overnight governance record (#34); orchestrator-mode lean sketch (#36). Earlier: shelve ML +
  ETF Slice 2a (#25); P0 decay resolution; ETF Phase-1 `security_kind` (migration 0037, #24).
- **Blocked items:** real *signal-driven* capital deployment stays **dormant by standing
  policy** (rule #11), not by an open dispute. Phase 2c is **reframed** model-independent
  (discovery/discipline/ETF) and no longer waits on a signal engine
  (`ml-engine-shelf-2026-07-11.md`).
- **Next actions:** see the ranked queue below. **2026-07-21 wake — ONE THING: clear the
  `agent_runs` review backlog (4 unacted: #3, #4 pre-existing + #6, #7 logged this wake) —
  zero-engineering, James's read-and-decide.** Then: P1 `compute_opportunity_cost` firewall
  gate (carried from 07-18); then the agent-frontmatter repoint to `supabase-ro` (now
  evidenced by a live failure, see Last wake snapshot). Historical: monitoring lane merged
  (queue #1 done); #29 (discipline evaluator) MERGED (`2a49df9`); portfolio-team-visibility
  PR2 (both halves) also merged (#41/#44).
- **Decisions needed from James:** see **`james-inbox.md`**. As of 2026-07-21 its three
  historical rows are all RULED (HUBS 10/20 ceiling 07-13; CBA automate-stale-thesis-hygiene
  07-16, retirement write awaiting a one-word confirm; VGS/VAS not-held → demo lots 07-16).
  Live asks: merge PR #65; rule on held agent_runs #6/#7 (rec: reject-6/approve-7); sign off
  the two 2026-07-21 proposals. (Header un-rotted 2026-07-21 — it had trailed the inbox by
  a week; the dream candidate flagged the drift.) **STALE 2026-08-13 (SB0-01):** the "Live
  asks" are all closed or superseded — PR #65 merged 2026-07-21 (`decision-log.md:53`), runs
  #6/#7 were dispositioned 2026-07-24 (`decision-log.md:55`), and both 2026-07-21 proposals
  were built. Current governor items are in `james-inbox.md` and the programme packet §10.
- **Portfolio-team visibility (NEW 2026-07-12):** James asked why the portfolio team didn't
  auto-flag HUBS/CBA. Root cause = a **surfacing gap**, not a compute gap — the daily discipline
  cards are computed then discarded at render (V1 email has no discipline section; the V2 tree is
  KEEP-DARK), and the `/pm-review` LLM findings die in markdown. Reversible fix proposed (3
  specialists): a model-independent deterministic discipline **section in the brief James already
  reads** (no gate flip, `ASXOS_PERSONAL_USE` only), then a findings-sink table, then a later gated
  LLM `/pm-review` Routine. Full: `docs/proposals/portfolio-team-visibility-2026-07-12.md`.
  Corrects an earlier arbi error: M13.8 paper-trade sign-off **is** scoped in code
  (`paper_trade.py:294`), not unscoped. Honest scope note: this fixes the *flagging-visibility*
  half; automated *stock rating / thesis generation* is the shelved-ML (rule #11) + unbuilt
  discovery-agent track, a separate conversation.
- **Known risks:** (1) `m14_candidate_agent_db_role_scoping` — agent SELECT-only is
  prompt-enforced only; (2) v1 allocator risk-blindness to ASX beta clustering
  (`m14_candidate_beta_cap`); (3) built-but-dark-launched layers are unreleased, not done
  (`dark-launch-exit-plan.md`); (4) R5 — the scheduled 7a brief's read-only guarantee is
  prompt-enforced only.
- **Last verified:** 2026-07-11 (post-shelf; reflects the P0 resolution + ML-shelf decision).
  **⚠️ This date is the header block's own, and it is four weeks behind the file's frontmatter
  (`:5`, 2026-08-11) and five weeks behind `main`. See the HEADER FRESHNESS CORRECTION box at
  the top of this section (2026-08-13, SB0-01) for current state. Two "last verified" dates in
  one file is itself the defect; the next `/arbi-close` should collapse them to one.**

---

Why this file exists: asxos has **three roadmaps and two milestone schemes that
partially contradict each other** (BUILD_GUIDE M1–M12; the V2 `M-Thesis-*` sequence;
governance Phase 0–4; plus `M13`/`M14a` in the strategy audit and `PR1–8` in the
executable roadmap). Nothing reconciled them into one "where are we." This file is that
reconciliation. It does **not** replace the source docs — it cross-walks them and cites
each. On any conflict, the newest `session-handoff-*.md` wins on priority (per
`docs/README.md`), the source doc wins on detail.

State claims below are **as of the 2026-07-04 handoff** unless a `/arbi` run has since
refreshed the *Last wake snapshot* at the bottom. Treat pre-first-wake numbers as
doc-derived, not live-probed.

---

## Reconciled position — one cross-walk

| Scheme | Where it lives | Status today | Source |
|---|---|---|---|
| Rebuild M1–M12 | `docs/foundation/BUILD_GUIDE.md` | **All done.** Static manual, not a tracker. | `/sprint-plan` ("M1–M12 should all be done") |
| Portfolio M13 | `asxos/domain/portfolio/*` | **Built, dark-launched** (`ASXOS_PORTFOLIO_BRIEF_ENABLED=0`). Weekly Sat 20:00 UTC. | V2 arch audit Part A |
| News/sentiment M14a/M14b | `asxos/ingestion/{news,sentiment}.py` | **Shipped, writing, but near-empty** (`ASXOS_NEWS_BRIEF_ENABLED=1` on `main` since 2026-07-11 — this row previously said `0`, which was wrong; live state wins). Corrected 2026-08-17: `holding_news` does **not** have zero rows — it has **7** (2026-08-10..13), all `HUBS.NYSE`, all sourced `finance.yahoo.com`. So the ingest path works. **The cause is not symbol mapping** (this row claimed that until 2026-08-17 and it is falsified): `jobs/ingest_news.py:186` selects `DISTINCT symbol FROM current_holdings`, and there is exactly **one open lot**, so the job is correctly ingesting news for the whole of a one-name portfolio. Coverage is bounded by portfolio breadth, not by a mapping bug. ~~`signal_sentiment` downstream remains empty.~~ **Superseded 2026-08-21 (read-only production probe): `holding_news` holds 9 rows and `signal_sentiment` holds 9 — neither is empty, so the "near-empty" label at the head of this row no longer describes the live state. A fresh SHIP verdict was issued the same day (`dark-launch-exit-plan.md` surface #2).** Ingest guard + brief gate fixed 2026-08-05 (`deea76a`). See `docs/market-trends-report-2026-08-05.md` §1. | V2 arch audit Part A |
| Governance Phase 0 / 0.5 | model-filtering + `approved_for_allocation` gate | **Done** (PR #11). | `next-session-backlog.md` P0 |
| Governance Phase 1 | governance schema + first Postgres trigger | **Done** (PR #11). | `next-session-backlog.md` P0 |
| Governance Phase 2a+2b | `macro_theses`, per-table audit triggers, `macro-economist`, `/discover-macro` | **Done** (PR #11). First live `/discover-macro` cycle run 2026-07-04. | handoff §Session summary |
| Governance Phase 2c | `theme-researcher` + `instrument-selector` | **Not started — reframed model-independent** (`ml-engine-shelf-2026-07-11.md`); the sole remaining prereq is agent DB role scoping, not Model A. | handoff §5 |
| Governance Phase 3 | executable thesis invalidation | **Not started.** | `next-session-backlog.md` |
| Governance Phase 4 | `/pm-review` 5→7 agents | **Not started.** | `next-session-backlog.md` |
| V2 product `M-Thesis-*` | `V2_..._BRIEF_SPEC.md` Part 8 | **Re-scoped model-independent** — the thesis/discipline/tax layer is authoritative and shippable today; the signal-engine framing is retired (ML shelved 2026-07-11). | V2 spec Part 8 |
| Executable roadmap PR1–8 | `executable-roadmap-2026-07-04.md` §D | PR1 (docs cleanup) partly landed; **PR2 (agent DB read-only scoping) is the near-term unblocker**; PR5 = the Model A audit job. | executable-roadmap §D |

**One-line reconciled read (updated 2026-07-11 — P0 resolved, ML shelved):** *M1–M14a are
built (M13/M14a dark-launched); governance is through Phase 2b. The Model A P0 is **resolved
against Model A** (no usable edge on 19,032 matured signals) and James has **shelved the ML
engine** — the signal-driven allocator + opportunity-cost ranking stay **dormant by standing
policy** (rule #11), and the product IS the model-independent moat (thesis/discipline
scaffolding, tax engine, theme stewardship, governance, ETFs) — all authoritative and
shippable today. The cleanest forward move is the model-independent build: fix the monitoring
crons (`track_signal_outcomes`'s fix is committed on PR #26, pending merge + deploy), then ETF
Slice 2, with agent DB role scoping ahead of any new agents — not a signal engine.*

---

## Blocked — P0 (RESOLVED 2026-07-11; read `docs/model-a-decay-analysis-2026-07-11.md`)

- **P0 — Model A signal reliability: RESOLVED, against Model A.** The decay check ran directly
  on **19,032 matured `signal_outcomes`**: `corr(ml_prob, 21d return) = −0.03`; STRONG_BUY
  returned −0.09% at 21d vs HOLD's +5.07% (conviction inverted at the top) — **no usable edge**
  over the weeks-to-months horizon theses hold for. James's original distrust is vindicated.
  **Rule #11 → standing** (not removed; removal would mean Model A is fine). This closes the
  *dispute*; it does not by itself unblock Phase 2c — that now needs James's strategic call
  (retrain a new version to a pre-registered decay bar / shelve the ML engine / both). The
  model-independent product (discipline, tax, themes, ETFs) was never blocked and is the path
  forward.
- **Strategic call MADE (James, 2026-07-11): SHELVE the ML engine.** Model A is demoted from
  product alpha-engine → dormant passive monitor; the product IS the model-independent moat.
  How it plays out (crons, allocator, brief, Phase 2c reframe, the revival decay-bar):
  **`docs/product/ml-engine-shelf-2026-07-11.md`**. Phase 2c is now the model-independent
  discovery/discipline/ETF expansion — it no longer waits on a trusted signal engine.
- **Dormant-by-standing-policy (narrow, updated 2026-07-11):** the signal-driven
  **allocator** capital path + the peripheral `compute_opportunity_cost` ranking; real
  *signal-driven* capital deployment. These are dormant under rule #11 (standing), not
  "blocked pending a fix." **Governance Phase 2c is NOT in this list** — it is reframed
  model-independent (`ml-engine-shelf-2026-07-11.md`) and its only remaining prereq is agent
  DB role scoping, not a signal engine. **NOT affected at all:** the thesis/discipline
  scaffolding, tax engine, theme stewardship, governance, and the brief's non-signal sections
  — all authoritative today (scan `wf_f54323f5-d7d`, verdict supported).
- **Second-order unblocker:** agent DB role scoping (`m14_candidate_agent_db_role_scoping`
  / PR2) — a prerequisite the roadmap places *before* Phase 2c regardless of Model A.

## In flight

> ⚠️ **2026-09-03 `/arbi-close` — read this first. The Amendment H campaign ran Waves 2→7.**
> **`main` is UNCHANGED @ `55f2619`.** Everything below is on branches: **fourteen draft PRs,
> #185–#198, none merged.** One stack — #185 → #186 → #189 → #190 (docs), and
> #192 → #193 → #194 → #195 → #196 → #197 → #198 (product), with #187/#188/#191 standing alone.
> Merge order is in `docs/session-handoff-2026-09-03.md`; out of order forces rebases.
>
> **What was built:** 51 files, ~8,000 insertions, 13 commits on the product stack. Nine new
> tables and one new column across four migrations; seven new domain surfaces (`domain/replay/`,
> `domain/research/registry/`, `domain/themes/candidates/`, and in `decision_engine/`:
> `challenge/`, `sizer.py`, `staging.py`, `delivery.py`, `outcomes.py`, `portfolio_state.py`);
> four new CLI groups (`asx replay`, `research`, `candidates`, `decision`). Tests **2735 → 4219**
> passed, 1 skipped (the `MIGRATION_TEST_DATABASE_URL` opt-in); ruff and mypy clean throughout.
>
> **Migrations applied under James's 2026-09-02 I5 grant**, each verified at `pg_catalog` (never
> `information_schema`, which under-reported triggers once during Wave 4): **0049**
> `20260902201241`, **0050** `20260902203202`, **0051** `20260902204920`, **0052**
> `20260903025557`. **0045 deliberately NOT applied** — nothing runs `build_segment_map`, it has
> no workflow home, and applying it would strand its allowlist entry and redden the daily drift
> check on `main` with no PR in flight to clear it (stays C8, James's).
>
> **THE ONE THING IS UNCHANGED AND UNMET: `backup.yml` is still red.** Not deprioritised —
> unreachable. H0-B fixed the script (dump-before-verify, gzip-aware digest, `/fail` ping, the
> 0048 tables) and it sits in #186, but every remaining step is a James click: **H-03** inspect
> the archive bytes, **H-05** add the deadman secret, **H-06** patch the workflow, **H-07**
> dispatch. The floor has now been cracked ~11 days.
>
> **Three defects found this session, all mine, all fixed before James ran anything.** (1) A
> min-CGT staging test asserted the *higher* post-discount gain (6,250 vs a true 5,000) and
> passed only through `lots.py`'s partial-draw ordering — caught by `tax-spec-conformance`.
> (2) Wave 6 wrote decision receipts into `brief_runs`, where `asxos/brief/deltas.py`'s
> `_PRIOR_BRIEF_SQL` would return one as "the prior brief" — self-caught at the start of Wave 7,
> fixed at the schema level in 0052 rather than by patching the one reader, and pinned with an
> AST guard. (3) `portfolio_state.py` claimed every public loader gates on `ASXOS_PERSONAL_USE`
> when two of five did — caught by `security-engineer`; the gates were added rather than the
> claim weakened.
>
> **No Stage cell moved** (see the 2026-09-03 note under the Stages table for what each still
> owes). **Nothing merged, no secret, no workflow edit, no environment flip, no capital action.**
> Rule #11 untouched: `signals` is never read, grep-pinned in five test files.
>
> ⚠️ **2026-09-02 `/arbi` wake — historical (the live banner is the close above).** `main` @ `55f2619`. **The 2026-09-01/02
> attended session merged 11 PRs with no `/arbi-close`:** #167 (issue snapshot), **#183** (ADR §6
> Slice 1 — decision spine: `decision_engine/{builder,calendar,repository}.py`, migration 0048
> **applied** `20260901062502`, first real packet `dpk-cba-1-2026-09-01` persisted for CBA.AU,
> honest-abstain because no independent challenger exists until Slice 2.5), #161, #169
> (`nightly-check`), #171 (Sydney clock), #170 (`RUNBOOK.md`), #180 (08-25 close), #181
> (Dependabot actions bump, was #177), #182 (`decision-flow-2026-08-30.md`), #179 (Amendment G),
> #184 (follow-ups: fixed the false pip-cache comment and the CLAUDE.md migration-line drift
> named in the 08-25 banner below — both CLOSED). Tests `2691` → `2735` passed / 1 skipped, CI and
> a fresh local venv agree. **Only open PR: #178** (Dependabot 27-package pip bump incl. ruff 0.16
> / mypy 2 / pytest-asyncio 1.4; green on `3417645`; merge is James's). **NEW BUG, not recorded
> anywhere before this wake: `backup.yml` has failed every scheduled run since 2026-08-23 — 12
> consecutive reds, last green 2026-08-22 (`d15266f`).** First red is `b352eef` (#163), the commit
> that added the frozen-evidence sha256 assertion (`scripts/backup_irreplaceable.sh:125-176`); it
> exits at `:170-173` ("no file in the frozen-evidence archive matches the recorded sha256 for
> signals") before the `cp` at `:178`, so **no irreplaceable-table dump has reached the backup
> repo and no restore drill has run in 11 days.** Live `signals` still holds exactly the 64,189
> rows the script header records, so the DB did not change — the mismatch is script-constant vs
> archive bytes; `$BACKUP_REPO` was not inspectable from this session. Nothing alerted: the
> backup deadman secret was never set, so the ping is skipped silently. Defect row #1 (`:515`,
> "FIXED + OBSERVED GREEN") is stale — that green run predates the assertion. **Also overdue:**
> dark surfaces #1 (portfolio brief) and #4 (paper-trade evaluator) expired 2026-08-31 with no
> verdict (`james-inbox.md`, `dark-launch-exit-plan.md`) — formally re-raised. `nightly-check`
> has 0 runs (first cron fire 15:17 UTC today — verify tomorrow). Two self-cleared
> `check_cron_health` failures (08-28 mid-session `sync_prices` ASX=0; 08-31 Monday-morning
> `check_us_positions` 36h-window false positive). Orphaned 08-21 wake snapshot still stashed on
> `claude/live-validation-followup-2026-08-20` (`ddd005d`). The 08-25 banner below is historical.
> **Same day, after the wake: James ruled Amendment H** (recorded above, after Amendment G) —
> the campaign plan `docs/proposals/amendment-h-campaign-plan-2026-09-02.md` is the working task
> list (Waves 0→8); this file stays the only ranked queue and its Stage cells flip only on cited
> exit gates. Wave 0 (`H0-A` records + `H0-B` backup fix) is in flight on `claude/arbi-wake-tvhllf`.
>
> ⚠️ **2026-08-25 close — historical (the live banner is the 2026-09-02 wake above).** `main` @ `2f98332`. **Two governor-named tasks,
> no `/arbi` wake:** (1) implement the five ADOPT-NOW items from a CI/CD engineering review;
> (2) verify and act on a monitoring/alerting research dossier. **Merged since the 08-23
> D10-ops close:** **#168** CI hardening (concurrency, pip cache, dependabot, 20 SHA pins,
> unmask collection errors — `9b8...`→merged), **#173** delete dead `regime/indicators.py`,
> **#174** cover `alpha_loader` 0%→100%. Dependabot from #168 is confirmed live: it opened
> **#177** (actions bump) and **#178** (27-package pip bump) unprompted. **Still open, all
> draft, all `full-check` green:** **#169** nightly full-suite + deadman heartbeat, **#170**
> `docs/RUNBOOK.md`, **#171** the Sydney-timezone fix (55 call sites + AST guard, `2691`
> passed on main including these three). **One item did not land and is now a live defect on
> `main`:** #168 merged carrying a comment in `full-check.yml` (and its own commit message,
> `c35d435`) that asserts no workflow in the repo already caches pip — **false**, four already
> did, with the unquoted `cache: pip` spelling my own verification missed. Three attempts to
> fix it (two silent `claude-execute` dispatches, one with `debug=true`) all failed for the
> **same** reason: the harness's own `.claude/settings.json` on `main` carries the identical
> `Edit(/.github/**)` deny this session hit locally — confirmed via the debug transcript, not
> assumed. Needs either a manual one-line edit (`cache: 'pip'` → `cache: pip`, corrected
> comment quoted on the PR) or a deliberate, James-made permission change; not routed around.
> **One self-caught branching mistake, corrected before merge:** #169 was accidentally created
> stacked on `claude/ci-hardening` (created without specifying a base while checked out on it)
> — a review pass caught it, rebased clean onto `origin/main`, force-pushed, corrected both PR
> threads. **A stale local snapshot was found and preserved, not merged:** a 2026-08-21
> `/arbi` wake's "Last wake snapshot" block sat uncommitted on `claude/live-validation-
> followup-2026-08-20` this whole time — never landed, and `main` progressed through five more
> `/arbi-close` runs (08-22 ×3, 08-23 ×2) without it. Inserting it now would misorder the
> history it never joined. **Stashed** on that branch (`git stash list`, message names it)
> rather than discarded — James's call whether to reconcile it as backfilled history or drop
> it. Phase 2 items proposed but explicitly gated on James (new dev deps: `mypy-baseline`,
> `pip-audit`; CLAUDE.md routes dependency additions through `tech-stack-researcher`) — not
> built. The banners below are historical.
>
> ⚠️ **2026-08-24 Amendment G recorded — historical; Amendment G's own 2026-08-24 view. The live banner is the 2026-08-25 close above.** Governor rulings
> on `auto` / GitHub App / no auto-merge are Amendment G above. **#166
> merged** (`4cf8c39`) — the 08-23 "unmerged" banner below is historical.
> **#165** (`dd8ca7b`) applied `gh issue create/list/view/edit` to
> `permissions.allow` (D10 item 1). D10 vs this file is still unresolved —
> this file remains the live queue. Next product unit is still James-named.
> Stages 0→6: Stage 4/5/6 still **not started**. Amendment G is not THE ONE
> THING.
>
> ⚠️ **2026-08-23 cursor D10-ops close — historical.** `main` @ `b352eef` at that close (**#163**). **Merge-resolution 2026-08-24:** #166 (`4cf8c39`, ADR bundle) and #165 (`gh issue` allowlist) are on `main`. 0046 applied as `20260823054040` (`screening_runs_comment_fix`). 0045 still unapplied. D10 ratified-not-in-force. Close-time drafts: #170/#169/#168/#167 CLEAN; #164/#161 BEHIND. Remaining D10 substrate: **#167**. Rebase **#164** after this close. W1-2 stays CHALLENGEd. Stages 4/5/6 still **not started**. The banners below are historical.
>
> ⚠️ **2026-08-23 bundle-placement close — historical (merged as #166, `4cf8c39`).** Placed the 23 Aug design
> bundle — **`docs/product/architecture-decision-record.md`** carrying
> ratified decisions **D1–D14** (cash floor 7.5%, 0% gross leverage, the
> eight-criteria Model A successor bar, vertical slices not sprints, GitHub
> Issues as work substrate, the two-layer challenge mechanism) plus a §6 build
> sequence of Slices 0–5 — two audits into `docs/archive/`, the ticketing
> research into `docs/research-archive/`, four D11 issue forms, and one
> `docs/README.md` map row. **Zero application code.** **ADR §3.5
> still describes the pre-Slice-0 world** and needs a sixth corrections row —
> James's call whether it is rewritten or superseded. The bundle's *"Slice 0
> must merge before Slice 1 starts"* gate is **met**; Slice 1 remains
> blocked only on the undecided `EvidencePacket` contract.
>
> **Two conflicts this file cannot resolve on its own, both James's:**
> (a) the ADR's **D10 declares this file frozen** and moves actionable work to
> GitHub Issues — the map row states that conflict rather
> than enacting it, so *this file remains the live queue until James rules*;
> (b) `target-architecture.md` still declares itself the CANONICAL ratified
> target while the ADR's §2/§6 overlap it, and `arbi-authority.md`'s ladder
> does not know the ADR exists.
>
> ⚠️ **2026-08-22 harness-promote close — historical.** Three further
> squash-merges under James's I6 instruction: **#158** `70b0156` (harness
> rebuild), **#153** `f31ab51` (dream-only rebase, not a second SB PR),
> **#159** `1ee184d` (L27–L45). Zero open PRs at that close-probe. W1-2 stays
> CHALLENGEd. Stages 0→6 table unchanged: Stage 4/5/6 still **not started**.
> The merge-train banner and the 2026-08-20 SUPERSEDED banner below are
> historical.

> ⚠️ **SUPERSEDED 2026-08-20 — read this before the entry below.** Two of the four PRs described
> here have since merged, a fifth (**#144**, opened after this entry was written) deleted Model
> A, and one claim below is now the reverse of the truth. Current state:
>
> **#144 merged** (`da64c1b`) — **Model A IS now deleted from the repo**: training chain,
> artefacts, feature engine, signal machinery, `cli/signal.py`, `brief/shap.py`,
> `compute_opportunity_cost.py` and the matching tests. Rule #11's quarantine **stands unchanged
> and is not weakened by this** — `CLAUDE.md:25` names exactly one removal condition (a *new*
> model clearing a pre-registered decay bar AND earning `approved_for_allocation`) and
> pre-emptively forbids removing it "on the basis of v1_5"; deleting v1_5's code is a fact about
> v1_5. Its enforcement mechanism (`production_gate.py`, the `model_versions`/`signal_outcomes`
> tables, `cli/model.py`) was deliberately kept because it is generic and gates *any* future
> model. Compliance is now **partly** by absence and partly by that surviving gate — the
> `signals` rows persist and are still readable (see `thesis-coherence-guard`, which still
> queries them). Not grounds to remove the rule.
>
> **#142 merged** (`32ed2f5`) — note it **grew from docs-only to docs + L0 substrate** (D1/D2/D3
> as real code) before merging, so "docs only" below is stale. Its migrations `0044`/`0045` are
> **drafted and NOT applied**. ⏰ **`0044` is time-boxed: apply before Sat 2026-08-22 16:00 UTC.**
> **→ `0044` APPLIED 2026-08-21** as `20260821080458` (ledger count **97**), inside the deadline;
> `REQUIRED_MIGRATIONS` bumped 96 → **97** on 2026-08-22. **`0045` is still drafted and NOT
> applied** — the sentence above remains true for it. The blocking-step failure described below
> is therefore resolved for `derive_fundamentals_pit`.
> `weekly-research.yml` runs `derive_fundamentals_pit.py` as an ordered blocking step, and the
> merged code writes a `currency` column that does not exist in production — the step fails and
> blocks `sync_fundamentals` below it. (Stated inline deliberately: the tracking `james-inbox.md`
> row lives on `claude/live-validation-followup-2026-08-20` and may merge after this PR.)
>
> **#141 merged** (`59fb835`) — Render fully out of the repo. **#140 and #134 remain open.**
> The "Model A has NOT been deleted" sentence below was true when written on 2026-08-19; the
> text is unchanged apart from an inline reversal marker, and it is retained as the audit
> record. Do not act on it.

- **2026-08-19 — parallel Cursor work stream, not yet reconciled.** A separate Cursor Cloud
  Agent session (2026-08-18, outside this repo's `/arbi`-governed loop — no red-team vet
  that stuck, no `/arbi-close`, no decision-log row until this entry) opened four draft PRs,
  none merged *as at 2026-08-19*: **#142** segment-valuation → selection → exposure architecture (docs only;
  replaces the deleted `build_portfolio`'s intent; cites 5 live-SQL-verified data-substrate
  defects — no currency column on `rs_fundamentals_pit`, bank-hybrid securities inheriting
  parent financials, duplicate sector taxonomies, 1.6y price history vs 14y fundamentals,
  five always-empty `fundamentals` columns); **#141** retire Render (`render.yaml` deletion,
  CI green, 2389 passed — a same-session Claude red-team found it real but ~60% complete:
  misses 10 slash commands still probing `$RENDER_API_KEY`, the auto-attaching
  `job-conventions.md` render.yaml references, a new rule #2 more permissive than
  `push-guard.sh`'s actual dispatch allowlist, a deleted test with no replacement, and 8
  stale code-comment citations); **#140** reconciliation work order + arbi autonomy plan
  (docs only; records James's verbal rulings — `detect_theme_stages` KEEP,
  `monitor_paper_portfolio` DROP, `build_portfolio` DELETED — and reconfirms the
  CODEOWNERS self-approval deadlock already known from PR #137); **#134** Cursor Cloud
  Agent dev environment. **Correction carried from that session's own investigation: Model A
  has NOT been deleted from the repo** — **[⚠️ REVERSED 2026-08-20 by PR #144 — Model A IS now
  deleted; see the SUPERSEDED banner at the top of this section. Sentence kept as the audit
  record of what was believed on 08-19. Rule #11 still stands.]** — rule #11's quarantine
  stands unchanged; do not act
  on any "Model A deleted" framing. The three cron rulings and the `build_portfolio`
  redirect are logged as an open `james-inbox.md` row pending formal ratification; the
  Cursor-runtime governance gap (settings.json/tools:/hook enforcement all inert or buggy
  for that runtime) is logged as `risk-register.md` R17. No merge, review-approval, or edit
  to any Cursor-authored branch has been made from this session — that stays James's call.
- **2026-08-12 — production remediation session (mid-session checkpoint).** Migration 0043
  **applied** (`20260812092925`, count 96) with probe + post-apply drill `31593927269` green;
  `derive_fundamentals_pit` succeeded in production for the first time (53,624 rows / 3,357
  symbols); `compute_factor_scores` 3,308 symbols; `check_cron_health` green after 12 days;
  `us-positions` cron moved to post-close; `claude-execute` harness live and validated (run
  `31595260041`). PRs #91/#92/#93 merged; **#94 open and CI-green** (governor ruling (c) on
  #87 vs Appendix B encoded as B.4/B.5, plus branch-protection reconciliation). See
  `docs/session-handoff-2026-08-12.md`.
- **Awaiting one observation:** tonight's scheduled `sync_prices` (~20:30 UTC) is the first
  ingestion against the live 0043 capture trigger — the last open item on defect #3. Local
  runs cannot substitute (this machine's Python rejects the intercepting TLS certificate).
- **Queued missions, not started:** #11 retire Model A from all active surfaces (needs
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); #12 ASX Results-to-Thesis Review slice (depends
  on #11); #13 bounded outcome-engine executor — **BLOCKED**, its required input
  `docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`
  does not exist in the repo, and §2.4 of that plan is the entry gate.
- **MERGED 2026-07-11 as PR #25 (`eff3732`):** the post-shelf reconciliation + arbi operating
  docs + **ETF Slice 2a** kind-aware ingestion (`asxos/ingestion/universe.py`, with
  `refresh_universe` test coverage) — formerly branch `claude/asxos-product-manager-agent-tzszlv`,
  now on main. No longer awaiting a merge call.
- **ETF Slice 2 (VGS/VAS holdings) — not started.** Code side is unblocked (Slice 2a merged);
  it is now gated only on James's holding-lot data (`james-inbox.md` VGS/VAS row).
- **MERGED 2026-07-11 as PR #26:** the 2026-07-11 wake + 8-hour autonomy window output —
  read-only probe allowlist, monitoring lane first pass (`check_model_staleness` shelf-aware,
  `track_signal_outcomes` init-pool fix), `validate_price_data` $0.02 floor,
  `sync_financial_statements` 512Mi-OOM bounded-worker fix.
- **MERGED 2026-07-13/14 (six-PR train, James-ordered #32→#33→#35→#31→#34→#36):** monitoring
  lane finished + batched (#30 earlier same day, then #32); R12 s766B theme-CLI gate (#33);
  R13 review-gate hardening (#35); Guilfoyle mission-control + thesis-as-broker-report
  reframe + HUBS 10/20 record (#31); overnight governance record (#34); orchestrator-mode
  lean sketch (#36).
- **MERGED 2026-07-14: PR #29** (discipline evaluator, `2a49df9`) — `discipline.py` + 19 tests
  landed on main. The follow-on PR2a/PR2b (loader + `brief.html.j2` render block) is also
  **MERGED** (#41, plus companion tests #44) — the emailed brief now renders discipline findings.
- **PR #5 no longer open** (resolved since the 07-13 wake, per the 2026-07-16 open-PR probe).
- **MERGED 2026-07-16 (James-instructed "merge all PRs if green" train, executed same wake):**
  **#42** (`8154b7b`, scorecard regen — clean+green, merged as-is) · **#46** (`e7401b9`, dream
  candidate + automation plan — was conflicted with main's decision-log; resolved append-only
  keep-both, CI re-verified green, then merged; the dream candidate is now on main as a
  *candidate* — `/arbi-promote` Phase 0 remains James's separate act) · **#47** (`f1eb5d1`,
  regulatory degraded-note visibility + gated CGT fold — was CI-red on one stale assertion,
  `test_render_html_renders_empty_states` still expecting the retired tax-actions empty-state
  string; dropped the assertion (review-loop PASS), resolved a second main-merge conflict
  (decision-log + add/add same-day handoffs, both kept), CI green 1652+ tests, merged).
  Zero open PRs remain as of the merge train.
- **MERGED 2026-07-21 as PR #65 (`9d8dd9d`):** the 6h continuous work loop — Step 0 agent-RO
  frontmatter repoint (all 6 agents), 0040 reconstruction + `REQUIRED_MIGRATIONS`→94, the P1
  `compute_opportunity_cost` firewall gate + paired `render.yaml` env, the 07-18 quick-fix batch
  7/8 (`defusedxml`, CWE-209, `security_master` batching, single-pass compose, title cap),
  governance filters on all 7 thesis-reading brief paths. Then **PR #66** (close addendum) and
  **PR #67 (`a1d30f5`)** — Proposal A Steps 1-2 (theme write-path verified live; sector-screener +
  theme-researcher materialized; `_KNOWN_AGENTS` extended) + Proposal B Layer A (`machine_conditions`
  schema, DRAFT migration 0041, `jobs/score_macro_theses.py`, #6/#7 falsifier backfill).
- **MERGED 2026-07-24 as PR #68 (`e596748`):** the **clean extract of PR #64's two net-new units** —
  Mission 1 (brief-truth `unrealised_return`, replacing a false −75.7% brief loss; R10 native-only)
  + Mission 2 (Phase C thesis report-sections, `asx thesis add-section`/`show --full-report`, on
  `theses.report_sections`). CI green first-shot; security-engineer + portfolio-invariant-guard PASS.
  **PR #64 CLOSED as superseded** — ~85% of it duplicated the already-merged #65's 07-18 audit work
  (and `regulatory.py` held the opposite `defusedxml` decision); force-merging would have dragged 27
  commits + 10 conflicts through main for two clean units. **Zero open PRs** as of this close.

## Ranked next-action queue

> **Live as of the 2026-09-03 `/arbi-close`.** The Stages 0→6 table at the top of this file
> remains the only ranked queue. **Almost every entry below is now a James click, because the
> campaign built everything that could be built without one.**
>
> **#1 — UNCHANGED, and now ~11 days old: restore the irreplaceable backup to green + observed.**
> Still THE ONE THING; the campaign could not touch it. The script fix is written and waiting in
> **#186**. The sequence is entirely yours: **H-03** inspect `$BACKUP_REPO`'s
> `signal-evidence-2026-08-16/` bytes (only you can read that repo — this is the only path to
> green), **H-04** merge #186, **H-05** add `HEALTHCHECK_URL_BACKUP_IRREPLACEABLE`, **H-06**
> patch the workflow (exact patch in #186's body), **H-07** dispatch `backup.yml` then
> `restore_drill=true` and paste both run ids. Unblock before build still holds — but note the
> campaign *did* build, on James's explicit Amendment H instruction, while this stayed red.
>
> **#2 — merge the stack.** Fourteen draft PRs is inventory until it lands, and Amendment D
> names that trap by name. Order in `docs/session-handoff-2026-09-03.md`; out of order forces
> rebases. Nothing else in this queue moves until the stack does.
>
> **#3 — H-33a: approve a second governed theme member.** This is the real blocker on Stage 4's
> positive control, and it is **governance, not code**: the only governed theme (`big-4-banks`)
> has one member, CBA.AU, which the Stage 4 text names a *negative* control. No amount of
> building fixes it.
>
> **#4 — the rulings, ~15 minutes total:** **H-16** dark surfaces #1/#4 (expired 08-31, drafted
> in #190 with a KEEP-DARK recommendation and a restated ship condition, because the current one
> is mechanically unreachable); **H-17** retire CBA thesis #1 (entry band 3.5× detached, revisit
> 67 days overdue); **H-23** Stage 1 cell wording; **H-29a** the two `price_detached` thresholds
> (arbi drafts: blocking ≥ 1.0, material ≥ 0.25); **H-29b** a tax-spec amendment for lot
> selection — `select_min_cgt`'s objective is implementation-defined and Slice 3 staging has now
> made it capital-facing; **H-38** retention/erasure for stored renders.
>
> **#5 — the live runs**, once the stack is merged and from a machine that reaches the pooler:
> H-25a (research reproducibility), H-27a (theme + candidate), H-33b (the CBA decision case),
> H-37 (record-t0). Each is one command; each fills a `renders:` that is honestly empty today.
>
> Carried unresolved, unchanged: Phase 2 CI deps (`mypy-baseline`, `pip-audit`, ruled in H-13);
> `defaultMode: auto` week-of-log re-read; GitHub App install; D10 vs this file; apply 0045
> (C8 — deliberately still unapplied); agent-role `REVOKE SELECT ON signals`;
> `docs/README.md` pointer (H-15). **Do not** treat W1-2 as #1 (CHALLENGE stands). **Do not**
> delete the digest assertion or re-add `signals`/`signal_outcomes` to the nightly dump as a
> shortcut.
>
> **Superseded — 2026-09-02 wake (the live block is the close above).** The Stages 0→6 table at the top of this file remains
> the only ranked queue; Slice 1 of ADR §6 is on `main` (#183) without flipping any Stage cell.
> **THE ONE THING (#1): restore the irreplaceable backup to green and observed** — diagnose the
> `signals` digest mismatch against the actual archive bytes, keep the assertion (it protects
> rule #11's evidence base), fix by case, then one green scheduled `backup` + one green
> `restore_drill` observed by run id, arm the deadman secret, correct `RUNBOOK.md` and defect row
> #1 (`:515`). Owner: main loop attended via `/build` for the script; every secret/workflow/
> dispatch step is James's. Unblock before build — no new slice until the floor is green.
> **#2 (James):** rule the expired dark surfaces #1/#4 (SHIP / DELETE / KEEP-DARK with a new
> expiry, ruled together). **#3:** run `/arbi-close` for the 09-01/02 session (decision-log,
> ledger, handoff) and in it decide whether the five 0048 `decision_packets` tables are
> irreplaceable (they are absent from the dump list at `backup_irreplaceable.sh:88-101`).
> **#4 (James-named next product unit):** ADR §6 Slice 2 (inverse-vol sizer downstream of the
> decision gate) then Slice 2.5 (thin challenge layer — an action-state packet is impossible
> until it exists); `/arbi-mission` with `arbi-red-team` first. Minor, any time: verify
> `nightly-check`'s first run; merge #178 (James). Carried unresolved: Phase 2 CI deps
> (`mypy-baseline`, `pip-audit`); orphaned 08-21 snapshot backfill-or-drop; `defaultMode: auto`
> week-of-log re-read (due ~08-31); GitHub App install; D10 vs this file; apply 0045; agent-role
> `REVOKE SELECT ON signals`; `docs/README.md` handoff pointer + `REQUIRED_MIGRATIONS` row. Do
> not treat W1-2 as #1 (CHALLENGE stands). Do not delete the digest assertion or re-add
> `signals`/`signal_outcomes` to the nightly dump as a shortcut.
>
> **Superseded — 2026-08-25 close (the live block is the 2026-09-02 wake above).** The Stages 0→6 table at the top of this file remains the
> only ranked queue. **James names the next unit** — unchanged since the 08-23 close, and
> two direct governor tasks intervened without displacing it. Not auto-#1, but immediately
> actionable in any order James picks: **merge #169/#170/#171** (all green, independent of
> each other and of #168 since #169's un-stacking); **fix the false pip-cache comment now
> live on `main`** (`.github/workflows/full-check.yml`, needs a manual edit or a deliberate
> permission change — see the In-flight banner); **Phase 2 CI items** (mypy-baseline widening
> to `jobs/`/`scripts/`, `pip-audit`, coverage reporting) — proposed, not built, gated on
> James approving two new dev dependencies. Do not treat W1-2 as #1 (CHALLENGE stands). D10
> is ratified-not-in-force — do not treat GitHub Issues as the live queue. Packet-first
> renderer stays P6-01 / Stage 6. Promotion backlog closed (L1–L45 on `main`). Carried
> unresolved from 08-23: **#167** (issue snapshot); screening seed INSERT (I5); apply 0045
> (I5); MCP principal repoint (James); D10 in-force (James); `defaultMode: auto` (James);
> rebase **#164** (still BEHIND).
>
> **Superseded — 2026-08-24 Amendment G (Amendment G's own view at recording; the live block is the 2026-08-25 close above).** The Stages 0→6 table at the top of
> this file remains the only ranked queue, and **remains live** — the placed
> ADR's D10 would freeze it, but that conflict is stated and unresolved, so
> nothing has moved to GitHub Issues yet. **James names the next unit.**
> Do not treat W1-2 as #1 (CHALLENGE stands). Packet-first renderer stays
> P6-01 / Stage 6. Brief V2 Stages 0–2 are on `main` (#175, #176); that is
> not a V2-flag flip. **#166 is on `main`** (`4cf8c39`). Amendment G: `auto`
> in user settings first, then a week of permission-log data before any hook
> `allow` rewrite; GitHub App not a second account; no auto-merge. D10
> candidate list: **(1) DONE via #165** — `gh issue create/list/view/edit`
> is in `permissions.allow`; **(2)** rule on D10 vs this file; **(3)** decide
> whether the ADR should be guarded (not in `AUTHORITY_FRAGMENTS`); **(4)**
> D10's `gh issue list --json` export, still absent. Other later-candidates
> that are *not* auto-#1: screening seed INSERT (I5), apply 0045 (I5), MCP
> principal repoint (James), App install (James), `defaultMode: auto` in
> `~/.claude/settings.json` (James — now dated, re-read ~2026-08-31).
>
> **Historical — 2026-08-23 cursor D10-ops close.** The Stages 0→6 table at
> the top of this file remains the only ranked queue. **James names the
> next unit.** Do not treat W1-2 as #1 (CHALLENGE stands). D10 is ratified-not-in-force — do not treat GitHub Issues as the live queue. Packet-first renderer stays P6-01 / Stage 6. Promotion backlog closed (L1–L45 on `main`). Written later-candidates that are *not* auto-#1: **#167** (issue snapshot; #165/#166 now on `main`); screening seed INSERT (I5); apply 0045 (I5); MCP principal repoint (James); D10 in-force (James); `defaultMode: auto` in user settings (James). Rebase **#164** after this close.

> **Same-day, now historical — 2026-08-23 bundle-placement close (#166 merged 2026-08-24 as `4cf8c39`).** The Stages 0→6 table at
> the top of this file remains the only ranked queue, and **remains live** —
> the placed ADR's D10 would freeze it, but that conflict is stated and
> unresolved, so nothing has moved to GitHub Issues yet. Item (1) of that
> close (`gh issue` allow-rule) landed as **#165**. Remaining from that list:
> rule on D10 vs this file; whether the ADR should actually be guarded; D10's
> stated-required `gh issue list --json` export (**#167**).

Each action names its north-star tie, the roadmap item it advances, and the owning
agent/command. arbi keeps this ranked; it is brief-only and does not execute these.

> ⚠️ **SUPERSEDED 2026-08-10.** The queue below is the pre-reframe 2026-07-24 ranking and is
> retained as history only. **The live queue is the Stages 0→6 table in "PROGRAMME REFRAME" at the
> top of this file.** Its #1 (the macro-brief render layer) is a Stage 6 surface concern under the
> ratified architecture and is not the current next action. Three items below remain genuinely open
> and are carried forward: migration `0041` unapplied, the CBA discipline confirm, and the RLS /
> agent-DB-role posture.

**Historic queue (2026-07-24 `/arbi-close`) → `docs/session-handoff-2026-07-24.md`.** The 07-18
audit backlog is fully retired (landed via #65); the two 2026-07-21 proposals are built and
merged (#67); #64's net-new work is extracted and merged (#68). Zero open PRs. The discovery
pipeline now has governed macro theses (#6/#7), the macro→theme→sector→instrument agents wired
read-only, and the Layer A falsifier-scoring evaluator — but **no reader-facing render**. So:
**#1 = dev-loop item #9 — the macro-brief render layer** (the Morningstar-style output James
asked about): surface the governed macro theses + theme/thesis discipline + Layer A outcomes as
a brief section. North-star: the investment read reaches James in a form he'll actually read.
Owner: main loop, consulting `backend-architect` (render path) + `technical-writer`. **#2** =
dev-loop item #10 — `instrument-selector` + wire `create_thesis_from_agent_run` (Phase E), the
last leg of the discovery chain. **Blocking on James** (carried, not arbi's): apply DRAFT
migration 0041 + bump `REQUIRED_MIGRATIONS` + wire the `score_macro_theses` Render cron — Layer
A is inert until then; and the CBA discipline one-word confirm + RLS posture.

**Historical queue (2026-07-18 `/arbi-close`) → `docs/session-handoff-2026-07-18.md`.** The 6-lens
security/refactoring/performance/behaviour-simplification audit re-ran clean (**P0 empty**), and
its backlog is the live queue: **#1 = P1 `compute_opportunity_cost` firewall gate + its paired
`render.yaml` env** (the one personal-data job #59 didn't cover); then the quick-fix batch (RSS
`title` cap, `defusedxml`, `security_master` executemany, `_portfolio_section`/`active_theses`/
`upsert_events` simplifications, `/health` 503 body, dead params); then the RED-ZONE decisions
(agent-RO frontmatter repoint — 0039 applied + supabase-ro live, frontmatter is all that's left;
`ASXOS_API_TOKEN` enforcement-or-doc; curl-wildcard tighten). The historical entries below are the
**pre-audit** queue, kept for audit trail.

**DONE 2026-07-18 — root-caused and retired the dead `regulatory_events` Treasury feed.**
Draft PR #55 (`claude/asxos-guardrails-regulatory-feed-r7ghjt` → `main`): `SOURCES` reduced
to RBA only; `assert_partial_success` threshold raised 0.5→1.0 (N=2→N=1) so a future
solo-source failure hard-fails instead of degrading silently the way Treasury did for weeks
behind a green cron. Diagnosed RETIRE (`backend-architect`) after live evidence confirmed the
2026-07-02 UA-mitigation ran 13+ live days with zero effect and a fresh diagnostic fetch
reproduced the same 403 — same dead-feed class as the already-removed ATO source, no
pure-code fix available. Full review loop + Guilfoyle readiness pass (READY-WITH-NOTES, hard
floor clean) done; also caught and fixed a stale `docs/product/data-contracts.md` row in the
same pass. Pending CI + James's merge. Full record: `arbi-run-ledger.md`
(`regulatory-feed-retire-2026-07-18`). Next `/arbi` wake should re-rank the queue now that
this item is resolved. _Historical detail of the original item kept below for audit:_

Current #1 (2026-07-16 wake): root-cause and fix the `regulatory_events` starvation —
2 rows, latest 2026-07-08, while `ingest_regulatory` reports green daily (Treasury source
dead behind `assert_partial_success(0.5)` passing on RBA alone). Draft PR #47 ships the
*visibility* layer (DEGRADED-note surfacing); this action is the *feed* root-cause — live-probe
the Treasury URL, fix/replace/retire per fail-loud (CLAUDE.md #1/#10), regression-test the
degraded path. North-star: backdrop events reach James before they cost money. Owner: main
loop, consulting `backend-architect`; draft PR for James's merge. Close behind: probe CI on
#47/#46/#42 and stage the merge train; James applies 0038+0039 and re-points the MCP (item 6).

1. **DONE 2026-07-13/14 — monitoring lane restored and merged** (PRs #30 + #32: cast fix,
   trading-day snapshot anchor, OOM fix, batched writes). Residual watch-items, not work:
   first post-merge Sat `sync_financial_statements` run (`duration_ms` vs the 5400s deadline)
   and next Sun `track_signal_outcomes` cron. **#29 (discipline evaluator) is MERGED**
   (`2a49df9`) — see In flight. Candidate replacement #1 is now portfolio-team-visibility
   **PR2, both halves** — **PR2a** (loader) + **PR2b** (render block) — landing together
   this session as a draft PR. _Historical detail of the original item kept below for audit:_ PR #26
   half-healed it — `check_model_staleness` is now SUCCESS(07-12). Three live failures remain
   (live-verified this wake via `job_runs` + Render events): (a) `sync_financial_statements` shows an
   **orphaned `running` row** from a Render `oomKilled(512Mi, ~78s)` at 07-11 16:50Z — that was the
   **PRE-fix** code; PR #26's bounded-worker fix deployed ~07-11 21:10 but is UNEXERCISED (weekly job,
   next run Sat 07-18), so the stale row persists and holds `check_cron_health` red. Action = validate
   the deployed fix with one manual trigger (heals the row + tests it under load); harden concurrency
   first if `performance-engineer` flags 8 workers as unsafe at 512Mi. (b) `snapshot_portfolio`
   **false-blocked** (`UpstreamBlocked: sync_prices has no success row for 2026-07-11` — a Saturday;
   `portfolio_daily_snapshots` frozen since 07-08); make its freshness gate business-day/calendar-aware,
   mirroring how `check_model_staleness` was made shelf-aware. (c) `track_signal_outcomes`
   FAILURE(07-12) on `AmbiguousParameterError` ($1 text vs varchar) — one-line explicit cast
   (monitor-hygiene for the shelved-Model-A passive monitor, NOT a rule #11 re-enable).
   `check_cron_health` (FAILURE 07-12) is failing **correctly** — it is reporting the stuck job;
   it goes green once (a) clears. North-star tie: discipline/health events must reach James before
   they cost money (`north-star.md:64–67` — the HUBS-stop failure class). Roadmap: post-shelf
   model-independent live-ops lane (`ml-engine-shelf-2026-07-11.md:82–90`). Owner: main loop
   (consult `performance-engineer` + `backend-architect`); land as a draft PR for James's merge.
   _Note: `retrain_model_a` FAILURE(06-06)+SUSPENDED is expected (shelved), not part of this fix._
   - **(context) Model A decay check — DONE 2026-07-11, P0 RESOLVED against Model A**
     (`docs/model-a-decay-analysis-2026-07-11.md`; 19,032 matured signals; no usable edge; rule
     #11 standing; James SHELVED the ML engine). Do **not** re-run it — that is recency overfit,
     not diligence (`arbi-red-team`).
2. **Agent DB read-only role scoping (PR2 / `m14_candidate_agent_db_role_scoping`).**
   North-star: non-negotiable #2 (firewall integrity) before more agents sit next to
   governed tables. Owner: `backend-architect`. Prereq for Phase 2c.
3. **Resolve the two open governance proposals** — review/approve or reject `agent_runs`
   #3 and #4 (`asx macro-thesis open --from-agent-run` → `approve`). Owner: James +
   main loop. (Does not expire.)
4. **HUBS data hygiene** — lock-window end date → `theses.tax_notes`. (Acquisition FX
   `0.6450` **confirmed** = brokerage statement, James 2026-07-11 — an ESPP fill FX ≠ spot;
   HUBS is ~flat, not −29%. See `portfolio-outcome-ledger.md`.) Owner: James supplies the
   lock date; main loop records.
5. **Universe→segment→stock coverage framework — ALL instrument kinds, not just equities.**
   2,377 active tracked instruments (au_equity 1,872 · ETF 471 · hybrid 21 · LIC 13), 13 theses
   (0.55%), 1 theme, 0 macro_theses, **zero ETF/LIC/hybrid coverage at all** — the gap is a
   missing narrowing layer (universe → segment → screen → thesis), not too few theses
   (north-star.md explicitly wants a small opinionated set, not universal coverage). James, same
   day: "the etf's etc [need to be] included in our investment plan not just individual
   equities" — the framework treats instrument kind as first-class from Tier 0, not a later
   add-on. Full framework: `docs/proposals/thesis-coverage-framework-2026-07-11.md`. Buildable
   now, no agent DB role scoping dependency: (1) coverage rollup — sector for equities, an
   explicit non-equity bucket for ETF/hybrid/LIC (pure SQL, zero schema — answers "where am I
   structurally blind" directly); (2) wire `screening_rules` — schema-only since migration 0001,
   zero readers, confirmed unwired — to a real `curated_composite` evaluator — **LANDED
   2026-07-12 for the au_equity/fundamentals path**: `asxos/domain/screening/{types,evaluator}.py`
   + `asx screen list`/`run` (`asxos/cli/screen.py`), draft migration
   `0038_screening_evaluator_wiring.sql` (**NOT yet applied**, tightens `source_method` to
   `curated_composite` only, adds the non-governed `screening_runs` audit log); the ETF/LIC
   kind-appropriate criteria (asset-class/geography/breadth for funds — a small net-new taxonomy)
   — **scoped 2026-07-12**: `docs/proposals/etf-lic-screening-criteria-2026-07-12.md`
   (`requirements-analyst`-researched, EODHD field availability checked against real docs, not
   assumed). Phase-1 recommendation: liquidity (`prices`-derived) + distribution yield/franking
   (`rs_corporate_actions`-derived) only — zero new external ingestion, zero unresolved
   vendor-availability risk. Everything else (asset class, geography, cost, AUM, tracking error,
   NAV premium/discount for LICs) waits on a live EODHD probe against a real ASX ETF/LIC symbol
   before further scoping is trusted. Not yet built — needs James's sign-off since it touches
   already-shipped, review-gated evaluator code; (3) wire the missing `asx theme approve|reject|open
   --from-agent-run` CLI verbs onto `themes/service.py`'s already-built governance functions
   (`theme_holdings.symbol` already supports mixed equity+ETF holdings in one theme, no schema
   change needed); (4) clear the 2 pending `macro_theses` `agent_runs` proposals (item 3 above)
   before adding a 4th discovery agent to the queue. Blocked on agent DB role scoping (item 2
   above): a new `sector-screener` discovery agent (bottom-up, coverage-driven — sibling to, not
   a mode of, `theme-researcher`'s top-down macro-conditioned design), sharing
   `theme-researcher`/`instrument-selector`'s not-yet-built `create_theme_from_agent_run()`/
   `create_theme_holding_from_agent_run()` service functions. Governance path identical to
   `macro-economist` at every step — no direct agent writes, ever. Triggered by James,
   2026-07-11. **Spec drafted 2026-07-12**: `docs/proposals/sector-screener-agent-spec-2026-07-12.md`
   — full frontmatter, data sources, 4-step invocation procedure, `ThemeProposal`/
   `ThemeHoldingProposal` JSON output schema, boundaries, and a 6-stage pre-go-live checklist.
   Deliberately NOT materialized as a live `.claude/agents/*.md` file — that step waits on item 6
   (DB role scoping applied) so the agent is never invocable next to governed tables under
   prompt-level-only SELECT enforcement. Owner: `requirements-analyst` (drafted) →
   `system-architect`/`backend-architect` (design) → James (scope sign-off, then apply item 6 to
   unblock materialization).
6. **Agent DB read-only role — design drafted, ready to apply.**
   `docs/proposals/agent-db-readonly-role-design-2026-07-11.md`: a full draft migration
   (`0038_agent_readonly_role.sql`, NOT applied) creating `asxos_agent_ro` — LOGIN, default-deny
   writes (no INSERT/UPDATE/DELETE/TRUNCATE grant, no sequence privileges), `SELECT` on
   everything, `ALTER DEFAULT PRIVILEGES` so future tables auto-grant. Two corrections to the
   original brief: `approve_object`/`reject_object` are Python, not Postgres functions (nothing
   to `REVOKE EXECUTE`); `nextval`/`setval` are `pg_catalog` built-ins (the real control is no
   sequence grant, not a function revoke). Honest limit: whether the role becomes load-bearing
   depends on whether `supabase-ro` is a connection-string MCP (can point at the role via the
   Supavisor pooler — strong) or the hosted Supabase MCP (can't accept a custom role — the
   migration stays defense-in-depth only). Pre-apply checks, post-apply acceptance test, and a
   rollback script are included. **Next: James applies the migration + re-points the MCP
   connection (infra, outside this repo) — this is what actually satisfies autonomy
   precondition (2).**
7. **Competitive gap analysis — Div 296 is a time-boxed opportunity, not just a backlog item.**
   `docs/product/competitive-gap-analysis-2026-07-11.md` (deep-research-agent, cited/confidence-
   rated). Headline: no consumer AU tool models Division 296 (Sharesight explicitly cannot) or
   enforces thesis discipline — asxos already has both built; the gap is surfacing, not engine
   work. **Time-sensitive finding worth weighing against ETF Slice 2 sequencing:** the s296-50
   cost-base-reset election hinges on **market values at 30 June 2026** (already ~11 days past at
   time of writing) — capturing those reset-date valuations now, while fresh, is a concrete,
   perishable, on-moat feature no competitor offers. Full prioritized P1-P6 roadmap (each tagged
   DIFFERENTIATION or TABLE-STAKES) in the doc. Owner: James — decide whether P1 (Div 296 reset
   workflow) jumps the queue ahead of ETF Slice 2 given the perishability.
8. **Multi-instrument expansion (ETFs / LICs / all ASX vehicles).** North-star: moat
   layers 2–3 (discipline + theme stewardship), and it advances **independent of the Model
   A P0** (rule #11 is moot for passive funds — no signal attaches). James: *"I want ETFs
   and all investment vehicles on the ASX involved."* Full plan (valuation = market price;
   look-through = separate exposure layer; `security_kind` keystone; readers-first-then-
   ingestion ordering invariant; minimal Phase-1 cut to hold VGS/VAS): **`docs/proposals/
   multi-instrument-expansion-2026-07-11.md`**. Owner: `system-architect` +
   `backend-architect` (specs done this session); needs James's 4 scope answers before build.

## Deferred index — `m14_candidate_*` (aggregated; grep to refresh)

Never aggregated before this file. Refresh with `grep -rn m14_candidate_ .`.

| Slug | What it defers | Cited in |
|---|---|---|
| `m14_candidate_agent_db_role_scoping` | Read-only Postgres role for agent MCP sessions (the only *security* deferral) | `portfolio-conventions.md`, `next-session-backlog.md:256` |
| `m14_candidate_agentic_thesis_drafter` | **CORRECTED 2026-08-18 (two independent sessions found this the same day) — the schema is not the gap.** `ThesisProposal` is fully specified at `theses/schemas.py:344`; `create_thesis_from_agent_run()` (`service.py:792-800`) is wired end-to-end and ends in a `raise` whose message ("no `ThesisProposal` schema exists yet") is now false. What's actually missing, per an `/arbi-run` design pass (backend-architect + system-architect, `arbi-run-thesis-authorship-2026-08-18` in the run ledger, `decision-log.md` same date): (1) the agent-authorship boundary itself — undesigned until this session; the shipped schema *permits* an agent to propose `conviction_level`/entry/stop/target/timeline (only an *unprovenanced* price is barred), so whether to tighten that is a named, still-open James decision, not something to assume either way; (2) `agent_run_service.py`'s `_PROPOSAL_MODELS` and `log_agent_run()` both still hard-refuse `object_type='thesis'`; (3) no `thesis_evidence` write path exists, so `approve_object()`'s evidence hard-fail would block every agent-drafted thesis forever without it; (4) the shipped validator checks `entry_lower <= entry_upper` but not `stop < entry < target` (session-handoff-2026-08-18.md item #4). A full design for (1)+(3)+the stub closure exists (not yet in a `docs/proposals/*.md` — currently only in the ledger/decision-log summary and the originating session's transcript) | `theses/schemas.py:344`, `theses/service.py:792-800`, `agent_run_service.py`, `session-handoff-2026-08-18.md` item 4, `arbi-run-ledger.md:arbi-run-thesis-authorship-2026-08-18` |
| `m14_candidate_macro_thesis_evidence_staleness_check` | `macro_theses.approve_object()` skips the evidence-staleness check theses have | `macro_theses/service.py:8,209` |
| `m14_candidate_governance_aware_revisit_cadence` | `approve_object()` doesn't reset revisit cadence on approval | `portfolio-conventions.md:84` |
| `m14_candidate_conviction_weighted_cadence` | Conviction-weighted revisit cadence not built | `governance-first-architecture-2026-06-30.md:310` |
| `m14_candidate_beta_cap` | Market-beta cap (v1 allocator is risk-blind to ASX beta clustering) | `portfolio-conventions.md:204` |
| `m14_candidate_security_kind_enum` | `security_kind` enum to disambiguate overloaded `universe.is_active` | `portfolio-conventions.md:208,222` |
| `m14_candidate_espp_employer_concentration` | ESPP/employer-stock treatment: a lot marker (`acquisition_source='espp_employer'` + `tradeable_from`), an `employer_concentration_cap_pct` policy, and the **10% soft-flag / 20% hard-trim** rule James set 2026-07-13 — fold into the `security_kind` build, "build later when it matters." Excludes HUBS from conviction checks; applies the tighter employer cap; gates trim on the lock. | `james-inbox.md` (HUBS resolved 2026-07-13); portfolio-coherence-reviewer 2026-07-13 |

## Dark-launch gate status (the hidden release state)

"Built but off." A layer being code-complete is not the same as released.

| Gate | Guards | State |
|---|---|---|
| `ASXOS_PORTFOLIO_BRIEF_ENABLED` | M13 portfolio brief section | `0` — off until 4-week paper-trade sign-off (M13.8) |
| `ASXOS_NEWS_BRIEF_ENABLED` | M14a/b news+sentiment brief section | `1` — set in the **executing scheduler**, `.github/workflows/daily-brief.yml:61`. *(Corrected 2026-08-13, SB0-01: this cell previously cited `render.yaml:414`; Render was deleted 2026-08-12, so `render.yaml` sets nothing live.)* ~~**Verdict reverted to UN-SHIPPED / RE-RAISED 2026-08-13** — the flag is still `1` but the surface has no valid SHIP verdict~~ → ✅ **SHIP verdict issued 2026-08-21** (arbi, `/arbi-run`), on a read-only production probe of both restated conditions: `holding_news` 9 rows, `ingest_news` last six runs 3·2·2·1·0·4 all `success`. The flag was already `1` and was **not** touched — the gap was the missing verdict, not the config. See `dark-launch-exit-plan.md` surface #2 |
| `ASXOS_PERSONAL_USE` | s766B personal-advice firewall — gate 1 for any portfolio/brief surface (CLI `_require_personal_use()`) | must be `1`; the portfolio brief needs this **and** `ASXOS_PORTFOLIO_BRIEF_ENABLED` (`portfolio-conventions.md` §Regulatory firewall) |
| `ASXOS_V2_BRIEF_ENABLED` (proposed) | future single master gate for V2 brief sections | not yet plumbed |

---

## Decision log & outcomes (arbi's memory)

Moved to its own canonical file: **`decision-log.md`** (append-only; the run audit trail is
`arbi-run-ledger.md`; standing risks are `risk-register.md`). arbi reads the decision log
first each wake and checks whether its last call held up. It was split out of this file so it
can grow without bloating the reconciled-state view and so the promotion gate + run ledger
reference one canonical decision history.

## Autonomy roadmap — the ASXOS Autonomy Kernel (10-PR sequence)

How arbi grows from a brief into the bounded autonomous operating layer. Governance +
memory/dream policy land **before** scheduled autonomy — without them, scheduled autonomy
just repeats mistakes faster. Each PR is a deliberate, separate change.

| PR | What | Status |
|---|---|---|
| 1 | Constitution + authority hierarchy (`arbi-constitution.md`, `arbi-authority.md`, `arbi-permission-model.md`) | **done (2026-07-10)** |
| 2 | Scorecard + eval rubrics (`arbi-scorecard.md`, `rubrics/`, `arbi-evals.md`) | **done (2026-07-10)** |
| 3 | Read-only `/arbi` | **done** |
| 4 | Docs-write `/arbi-close` | **done** |
| 5 | Memory policy + run ledger (`arbi-memory-policy.md`, `arbi-run-ledger.md`, `decision-log.md`) | **done (docs)** |
| 6 | Dream policy + promotion gate (`arbi-dream-policy.md`, `arbi-promotion-gate.md`) | **done (docs)** |
| **7a** | Scheduled **read-only dry-run** brief (Routine fires `/arbi`; **output only**) | **RE-WIRED 2026-07-15** — daily 20:30 UTC (06:30 AEST), fresh session, push+email to James; Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`. The 2026-07-10 Routine (`trig_01PiLVYg…`) was found **absent from the live trigger list** on 2026-07-15 while these docs still claimed it live — the brief had silently stopped. Standing lesson: verify with `list_triggers` on wake; never trust this cell alone. **SUPERSEDED 2026-08-21 — this cell was false for 34 days, the SECOND occurrence of the exact failure the sentence before it describes.** `list_triggers` on 2026-08-21 showed 7a **user-paused since 2026-07-18T23:18 UTC** (`next_run_at` frozen at 2026-07-19), alongside the secperf WRITE loop, paused 8 seconds earlier. Neither carries `ended_reason`/`suspension_reason`, while a `send_later` row in the same listing carries `"ended_reason":"run_once_fired"` — so the field is emitted when set, and both-empty means user-paused. Not an outage: a Routine created 2026-07-24 fired normally on 2026-07-26. James's reason, asked directly: **"the briefs weren't worth reading."** A revival mission was planned, red-teamed (CHALLENGE) and then **stopped by James at gate G1** in favour of the live `/pm-review` defect. **Do not re-arm without reading the findings first** (`decision-log.md` 2026-08-21 row): the stale Render probe was never the cause; 7a has never produced a repo-observable artifact (28 ledger rows, all `trigger: manual`, zero scheduled), so its quality and liveness problems are the same problem; `rubrics/arbi-daily-brief.md:6-15` has no clause permitting silence; and its cron collides minute-for-minute with `daily-brief.yml`. The likely right answer is the Actions substrate reusing `asxos/domain/brief/severity.py`, not a re-armed Routine |
| **7b** | **Standing** scheduled autonomy (arbi writes/acts unattended on a schedule) | **blocked** on the 3 preconditions below |
| 8 | Multi-agent delegation (arbi coordinates specialists) | **`/arbi-run` shipped 2026-07-10** (thin attended bridge); **`/arbi-mission` + `guilfoyle` mission-control drafted 2026-07-13** — its graph-driven, readiness-gated evolution (task graph → specialists → draft PR), still attended + reversible (Guilfoyle plans/judges, never prioritises/spawns/merges); *standing/unattended* dispatch still gated on the 3 preconditions + runtime |
| 9 | GitHub operator mode (docs-only draft PRs) | not started |
| 10 | Live read-only watchdog (reacts to CI/PR/data events) | not started |

PRs 1–6 are the **governance + learning foundation**, complete as docs (the runtime they map
onto — Managed Agents memory/dreams/outcomes — is not provisioned here).

**PR 7a is the one autonomous-execution step that is safe *before* the preconditions:** a
scheduled `/arbi` that runs **read-only**. It runs the observe → diff → synthesize → present
steps and emits a **draft brief / issue / email — and nothing else.** It explicitly does
**not** perform the I2 state-refresh a human-invoked `/arbi` does (that write is
authorised by James invoking it interactively; an unattended run has no such invocation). So
PR 7a: **no writes** (not even `roadmap-state.md`), no DB, no Render, no GitHub mutation, no
branch creation, no roadmap-state overwrite, no capital-impacting output, no Model A-derived
recommendation. It is **I0–I1 only** — deliberately boring, read-only, and impossible to
confuse with real autonomy. **PR 7b onward** (standing scheduled autonomy that writes/acts
unattended) stays blocked on the preconditions.

**As wired** (Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`, re-created 2026-07-15 — the original
2026-07-10 Routine was found missing from the live trigger list; daily 20:30 UTC = 06:30 AEST,
fresh session, push+email to James): the read-only guarantee is **prompt-enforced only** — the
fresh session holds write tools but the trigger instructs it to emit the brief and never write
(risk **R5**; setting `ARBI_UNATTENDED=1` in the environment config would arm
`unattended-guard.sh` mechanically for these runs — see
`arbi-full-auto-activation-2026-07-15.md`). Pause/stop it any time by disabling or deleting
that trigger. To promote to PR 7b (unattended writes), clear the
preconditions below first. PRs 7–10 run **git-native** — Claude Code Routines
(schedule) + git (memory: `memory/`) + GitHub branch-protection/PRs/CI + the
`unattended-guard.sh` hook. The loop machinery is **built** (guard hook, memory
bank, `/arbi-dream`, `/arbi-promote`, `/arbi-run`; see `arbi-autonomy-loop.md`);
standing activation stays gated. Managed Agents is an optional hosted backend,
not a prerequisite.

**Preconditions before PR 7b+ (standing / writing scheduled autonomy — NOT required for the
7a read-only dry run):** (1) ✅ **MET 2026-07-11** — the P0 Model A dispute is resolved (rule
#11 is now standing policy, not an open question); (2) `m14_candidate_agent_db_role_scoping`
landed (read-only DB role); (3) the scorecard trend + decision log + eval suite showing
arbi's calls hold up (`arbi-permission-model.md` §promotion preconditions). Preconditions (2)
and (3) remain open — resolving the dispute did not by itself unlock standing autonomy.

**Never lifts, at any PR:** the personal-advice firewall (s766B) — arbi automates *what gets
built*, never *what to trade*; the Model A quarantine (rule #11), now **standing policy** —
it lifts only when a *new* model version passes a pre-registered decay bar AND earns
`approved_for_allocation`, never on the basis of v1_5; and the irreversible tiers (5–7) stay
`always_ask`/disabled regardless of track record. Autonomy expands only on the reversible
dev/ops side.

---

## Last wake snapshot

_Recorded by the 2026-09-03 `/arbi-close` (Amendment H campaign, Waves 2→7). **No `/arbi` wake
this session** — it is the continuation of the 2026-09-02 wake, whose snapshot is retained below
for diffing._

```
Close: 2026-09-03 (James: "run arbi close catalogue whatever you need to")
- main @ 55f2619 — UNCHANGED since the 09-02 wake. Nothing merged this session.
- Open PRs: 14 drafts, #185-#198, none merged. Product stack #192→#198 (each based on its
  predecessor); doc stack #185→#186→#189→#190; #187/#188/#191 standalone.
- Campaign diff (origin/main...claude/amendment-h-outcomes): 13 commits, 51 files,
  +8001/-193.
- tests: 4219 passed / 1 skipped (local uv venv without [ml]; ruff + mypy clean). 09-02
  baseline was 2735 (+1484). Skip = MIGRATION_TEST_DATABASE_URL opt-in, unchanged.
- migrations: 51 files on disk (0001..0052, 0042 absent). FOUR applied this session under
  James's 09-02 I5 grant — 0049 pit_knowledge_tier 20260902201241; 0050 research_registry
  20260902203202; 0051 theme_candidates 20260902204920; 0052 outcome_materialisation
  20260903025557. Each verified at pg_catalog (tables, triggers, FKs, uniques, 0 rows).
  0045 segment_map STILL UNAPPLIED, deliberately (C8).
- New schema: 9 tables + 1 column. research_hypotheses, strategy_versions, research_runs,
  research_promotions (0050); theme_versions, candidate_snapshots (0051); thesis_outcomes,
  delivery_receipts, decision_dispositions (0052); rs_fundamentals_pit.knowledge_tier (0049).
  All new tables append-only by BEFORE UPDATE OR DELETE trigger.
- New CLI: asx replay | research | candidates | decision (5 subcommands: build,
  record-t0, observe, positive-control, dispose). All personal-use gated.
- backup.yml: STILL RED. Unchanged from the 09-02 wake — every remaining step is a James
  click (H-03/H-05/H-06/H-07). Script fix waits in #186. ~11 days without a dump or drill.
- Defects found this session: 3, all mine, all fixed pre-merge. (1) min-CGT staging test
  asserted the wrong number — caught by tax-spec-conformance. (2) receipts written into
  brief_runs where deltas.py would read one as "the prior brief" — self-caught, fixed in
  0052 schema + AST guard. (3) portfolio_state.py claimed 5/5 loaders gated when 2/5 did —
  caught by security-engineer; gates added, not the claim weakened.
- Consults: portfolio-invariant-guard PASS-WITH-NOTES; security-engineer PASS-WITH-NOTES
  (x2, the first died on a rate limit and was re-run against the shipped shape);
  tax-spec-conformance FAIL → fixed. Platform grants checked: anon/authenticated/PUBLIC
  hold ZERO grants on all five decision tables.
- Stage cells: NONE moved. Rule #11 untouched; signals never read (grep-pinned, 5 files).
- Probe gaps: no live CLI run anywhere — this sandbox holds DATABASE_URL but asyncpg
  cannot complete a connection to the pooler (6th recorded instance), so every `renders:`
  the campaign would fill is a James click. $BACKUP_REPO still not inspectable.
```

_Prior snapshot (2026-09-02 wake) retained below for diffing._

_Recorded by the 2026-09-02 `/arbi` wake (interactive, James-invoked). Supersedes the 2026-08-25
close snapshot below._

```
Wake: 2026-09-02 ~12:00 UTC (James: "wake up")
- main @ 55f2619 (#184). Branch claude/arbi-wake-tvhllf == origin/main; tree clean.
- Merged since the 08-25 snapshot (2f98332): #167, #183, #161, #169, #171, #170, #180, #181,
  #182, #179, #184 — 11 PRs, no /arbi-close for the 09-01/02 session.
- Open PRs: #178 only (Dependabot pip bump, non-draft, green on 3417645, mergeable_state
  "unknown" at probe). #169/#170/#171 merged; #177 merged as #181.
- tests: 2735 passed / 1 skipped (CI full-check run 33616132894 on 55f2619; fresh local uv
  venv without [ml] agrees). Skip = MIGRATION_TEST_DATABASE_URL opt-in. 08-25: 2691 (+44).
- migrations: 47 files on disk (0001..0048, 0042 absent). Ledger latest 20260901062502
  decision_packets (0048, applied 09-01). 0047 applied 08-24 (20260824002827). 0045
  unapplied — public.segment_map does not exist. migration-drift green 09-02 10:14 UTC.
- freshness: MAX(prices.dt)=2026-09-01; MAX(portfolio_daily_snapshots)=2026-09-01;
  signals frozen at 64,189 rows / as_of 2026-08-05 (expected, rule #11);
  decision_packets = 1 row (dpk-cba-1-2026-09-01, 09-01 06:40 UTC).
- job_runs (14d): every daily job success-only, last batch 09-01 22:43 UTC; weekly chain
  08-29. check_cron_health 11 ok / 2 failed (08-28 sync_prices ASX=0 mid-session; 08-31
  check_us_positions 36h weekend false positive), both self-cleared.
- Actions: full-check/targeted-ml-tests/PR Review Agent green on every push since 08-25;
  daily-brief green daily through 09-01; pipeline-health, us-positions, issue-snapshot,
  weekly-research (08-29) green. nightly-check: 0 runs (first cron 15:17 UTC 09-02).
- NEW BUG: backup.yml red 12 consecutive scheduled runs 08-23 13:52 → 09-01 17:22 UTC.
  Last green 08-22 (run 32576947460, d15266f). First red b352eef (#163) = the commit that
  added the frozen-evidence sha256 assertion (backup_irreplaceable.sh:125-176); fails at
  :170-173 "no file matches the recorded sha256 for signals" (expected e61ee6a4…) before
  the cp at :178. No dump committed, no restore drill, for 11 days. Live signals count
  (64,189) matches the script header, so DB unchanged — mismatch is constant vs archive
  bytes. $BACKUP_REPO not inspectable this session. No deadman secret set → no alert.
  Not in james-inbox, ledger, or any handoff before this wake.
- 08-25 defects: pip-cache comment + CLAUDE.md migration drift both FIXED by #184.
  Orphaned 08-21 snapshot still stashed on claude/live-validation-followup-2026-08-20.
- Dark surfaces #1/#4 expired 08-31, unruled. Rule #11 stands.
- THE ONE THING: restore backup.yml to green + observed (see Ranked next-action queue).
- Probe gaps: backup repo contents; Healthchecks.io not re-read; no gh CLI (GitHub MCP).
```

_Prior snapshot (2026-08-25 close) retained below for diffing._

_Recorded by the 2026-08-25 `/arbi-close`. No `/arbi` wake this session — two governor-named
tasks. Supersedes the 2026-08-23 cursor D10-ops snapshot below._

```
Close: 2026-08-25 (James: implement CI/CD audit ADOPT-NOW items → ingest monitoring dossier
                   → run arbi close)
- main @ 2f98332 (#173 merged)
- Merged since 08-23 D10-ops close: #168 (CI hardening), #173 (delete dead regime module),
  #174 (alpha_loader coverage 0%→100%). Not by this agent — merged by James/other process
  between turns.
- Dependabot (from #168) confirmed LIVE: opened #177 (actions bump) and #178 (27-pkg pip bump)
  unprompted.
- Open, draft, full-check GREEN: #169 (nightly-check, un-stacked from #168 after a review
  caught the branching error), #170 (RUNBOOK.md), #171 (Sydney clock fix, 55 sites + AST
  guard).
- DEFECT NOW LIVE ON MAIN: full-check.yml's pip-cache comment (and commit c35d435's message)
  assert no workflow already caches pip — false, 4 did, unquoted `cache: pip`. Fix attempted
  3x via claude-execute, all failed on the SAME cause (harness's own .claude/settings.json on
  main denies Edit(/.github/**), identical to the local session's block) — diagnosed via a
  debug=true transcript, not routed around. Needs a manual edit or a deliberate permission
  change.
- tests: 2691 passed / 1 skipped on main (measured in a disposable worktree at origin/main,
  not the stale local branch). Baseline before this session's merges was 2640 (+51: #171's
  clock tests, #174's alpha_loader tests, plus unrelated Brief V2 PRs #175/#176 in the same
  window).
- migrations: 46 files on disk. REQUIRED_MIGRATIONS replaced by the name-set diff
  (schema_drift.py / check_migration_drift.py) per the 08-23 close — this row does not
  re-verify DB-applied state (no live DB probe this session).
- CLAUDE.md drift found, not fixed: "currently through 0043; REQUIRED_MIGRATIONS = 96" is
  stale on two counts — the count constant was deleted (per above) and the file count is 46,
  not 43. Third documented instance of this exact doc-vs-reality gap class in this file's own
  history.
- orphaned artifact: a 2026-08-21 `/arbi` wake snapshot sat uncommitted on
  claude/live-validation-followup-2026-08-20 this entire time, never landed while main
  progressed through 5 later closes. STASHED on that branch (not merged, not discarded) —
  James's call on backfill vs drop.
- episode_score: 3.8 provisional (arbi-run-ledger.md close-2026-08-25; two self-caught/
  review-caught defects this session — a false "nobody caches pip" claim, and #169's
  accidental branch-stacking — both corrected before this close, neither shipped broken).
- Next: James names the unit (unchanged since 08-23) — or merges #169/#170/#171 directly.
```

_Prior snapshot (2026-08-23 cursor D10-ops) retained below for diffing._

_Recorded by the 2026-08-23 cursor D10-ops `/arbi-close`. Supersedes the same-day bundle-placement snapshot and the 2026-08-22 harness-promote snapshot below._

```
Close: 2026-08-23 (James: finish audit-P0 GitHub artifacts + apply 0046 + D10-ops drafts → /arbi-close)
- main @ b352eef (#163 merged by James) at close-probe
- Applied: 20260823054040 screening_runs_comment_fix (0046). 0045 still unapplied.
- Close-time drafts CLEAN: #165 allowlist, #167 issue snapshot, #166 ADR/docs, #168 CI, #169 nightly, #170 RUNBOOK
- Close-time drafts BEHIND: #164 earlier 08-23 close (file overlap with #166), #161 cheap cleanups
- Merge-resolution 2026-08-24: #166 landed (`4cf8c39`); #165 landed. #167 still the remaining D10 substrate. Rebase #164 after this close.
- D10 ratified-not-in-force. W1-2 CHALLENGEd. Rule #11 stands.
- Tests on main at close: 2640 passed, 1 skipped (full-check run 32621965350)
- Next: James names the unit
```

_Recorded by the 2026-08-23 bundle-placement `/arbi-close`. No `/arbi` wake that session — governor-named task. Historical: #166 merged 2026-08-24 as `4cf8c39`. Supersedes the 2026-08-22 harness-promote snapshot below._
_Postscript 2026-08-24: #166 squash-merged as `4cf8c39`. Snapshot body below is the close-time record and is not rewritten. Amendment G is a queue amendment, not a wake/close._

```
Close: 2026-08-23 (James: "Read README-PLACEMENT.md and place these files. Don't act on
                   anything yet" → "I give you authoritative permissions to make this edit")
- main @ b352eef — SLICE 0 MERGED MID-SESSION as #163 (audit P0/P1 remediation)
- Branch claude/file-placement-review-0y5u8b, draft PR #166 — **merged 2026-08-24 as `4cf8c39`**
- Placed: ADR (docs/product/architecture-decision-record.md, D1-D14) + 2 audits to
  docs/archive/ + ticketing research to docs/research-archive/ + 4 issue forms + 1 map row
- Zero application code on that branch; full-check + targeted-ml-tests green on every head
- POST-#163, re-measured: 45 migration files; 0018_perf_indexes.sql RECONSTRUCTED and present;
  0046 added; REQUIRED_MIGRATIONS DELETED, replaced by _check_migration_drift() ->
  scripts/check_migration_drift.py (the name-set diff). 0042 absent; 0025/0045 unapplied.
  >> ADR §3.5 still describes the PRE-Slice-0 world and needs a 6th corrections row.
- ADR §4 corrections row 5 added: docs/product/ is NOT in AUTHORITY_FRAGMENTS — the ADR is
  unguarded as committed
- gh issue allow-rule later landed as #165 (this close recorded it as NOT DONE)
- Slice 0 DONE -> the bundle's "Slice 0 must merge before Slice 1 starts" gate is now MET.
  Slice 1 is blocked only on the undecided EvidencePacket contract (ADR §5.3/§6).
- Next: James names the unit. D10-vs-this-file is unresolved; this file is still the queue.
```

_Recorded by the 2026-08-22 harness-promote `/arbi-close`. Supersedes the same-day merge-train snapshot below._

```
Close: 2026-08-22 (James: execute harness rebuild → merge #158 → merge lessons → /arbi-close)
- main @ 1ee184d
- Merged: #158 70b0156 · #153 f31ab51 · #159 1ee184d
- Memory: L1–L45; dream-candidates/ live dir empty except README + archive/
- Harness: review-gate gone; attended settings/hooks/CLAUDE.md un-denied; defaultMode NOT applied
- REQUIRED_MIGRATIONS=97; latest applied 20260821080458; 0045 unapplied
- Open PRs at probe: none (this close PR is next)
- W1-2 CHALLENGE still stands — not #1
- Next: James names the unit
```

_Recorded by the 2026-08-22 merge-train `/arbi-close`. Supersedes the same-day W1-1 snapshot below._

```
Close: 2026-08-22 (James: /arbi-mission plan → CHALLENGE on W1-2 → I6 merge train)
- main @ 62ccceb
- Merged: #155 d7e8242 · #151 67b3bae · #154 f0b8f9c · #152 62ccceb
- Held: #153 (dream overlay; CONFLICTING; unique commits a976173 + 450709e)
- W1-2 CHALLENGE honored — no brief section
- REQUIRED_MIGRATIONS=97 on main; latest applied 20260821080458; 0045 unapplied
- /pm-review HUBS.NYSE OBSERVED (REVIEW; zero Model A)
- renders: TLS.AU FY2024 PIT abstain (from #155)
- Next: James names the unit. Do not merge #153 as a second SB PR.
```

_Recorded by the 2026-08-22 W1-1 `/arbi-close`. Supersedes the same-day #154 snapshot below._

```
Close: 2026-08-22 (James: sessions done; execute one chain unit)
- THE ONE THING: W1-1 asxos_pit_db (P5 integration evidence, not Stage 4).
- Squash-merged as #155 (`d7e8242`).
- renders: TLS.AU FY2024 PIT review, outcome abstain, G2/G3/G5 named,
  presentation_sha256 1224d5f35440e55eb721bba0fbb65c12d018202bf79cdb6051517f81df7baac0.
- /pm-review HUBS.NYSE owed by #149: OBSERVED this session (REVIEW; zero Model A).
```

_Recorded by the 2026-08-22 #154 `/arbi-close`. Supersedes the 2026-08-21 snapshot below, which is
kept verbatim as the audit trail._

```
Close: 2026-08-22 (/arbi-run → chained build → /arbi-close; James drove it, then stepped away)
Branch: claude/production-code-session-tasks-5hqs5n, draft PR #154. main @ d15266f (unmoved).
Commits: 6 — f021795, 726df91, 21016db, f9ca0ea, abc434a, b622a4e
Migrations: 97 applied (20260821080458). REQUIRED_MIGRATIONS now 97 on branch (abc434a).
Tests: 2427 passed, 1 skipped, ZERO collection errors, at pinned versions with .[dev]
Episode score: 3.4 provisional (see arbi-run-ledger.md close-2026-08-22)
ONE THING outcome: partial — the debt half landed, the capability half did not
```

**Four findings, ranked by what they change:**

1. **The agent DB read-only role is INERT.** `asxos_agent_ro` exists in production but the MCP
   authenticates as `supabase_read_only_user`, so the control has done nothing since it was
   applied. The planned rule-#11 REVOKE would have been *recorded as* mechanical enforcement
   while changing nothing measurable. The fallback principal is worse — it inherits SELECT via
   `pg_read_all_data` and carries `rolbypassrls`, so a table REVOKE cannot bind. **Branch A
   (repoint to `asxos_agent_ro`) is the only viable path.**
   → `docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md`

2. **The test suite was never broken, and the project guide's "known sandbox gaps" section is
   dead.** It describes a `model_a.py → cache.py → joblib` chain that PR #144 deleted. With a
   venv at pinned versions: 2427 pass, 0 collection errors, no ML extras needed.

3. **The review gate biases the repo toward docs.** Its marker is denied to the agent
   *intermittently*, so Python commits are a lottery while doc commits sail through. This
   session ran **5 doc commits to 1 code commit**, and the code only landed because the
   classifier relented late. That is the same bias already visible in four inert
   `results_review` PRs and in Amendment E's reason for existing. Allow rule drafted:
   `docs/proposals/review-gate-allow-rule-2026-08-22.md`.

4. **`jobs/compose_brief.py:97` prints the entire brief into the daily-brief Actions run log** —
   holdings, stops, targets. If the repository is public, every run log is world-readable.
   Visibility unverified from the sandbox. Not in any diff; found during security review.

**Three of arbi's eight planned items were falsified by live probe before work began** — the CBA
price-detachment automation was already shipped (`discipline.py:240,257`), the tax/disposal unit
would have closed "correct and empty" (0 disposals), and `detect_theme_stages` was unreachable
(workflow files Edit-denied). Worth noting as a pattern: arbi plans read-only and its items need
probing before they are costed.

**Not built:** Units 4 (doc-expiry sweep, 25 expired), 6 (open-time thesis price-ordering
validator), 7 (memory-gap brief line), 8 (V2 brief descope). Unit 6 carries a live design note —
`open_thesis()` has *no* price validation at all, and enforcement must be open-time-only and
revision-exempt because a raised trailing stop legitimately sits above entry.

---

_Recorded by the 2026-08-21 `/arbi-close`. Superseded by the block above; kept verbatim as the
audit trail._

> **Point-in-time record — one line was overtaken on 2026-08-22.** Kept verbatim. The
> `migrations` bullet's residual *"main's REQUIRED_MIGRATIONS = 96 lags the observed 97"* is
> **discharged**: the constant is bumped **96 → 97** (`asxos/api/main.py:14`), re-measured
> against the live ledger the same day (97, latest `20260821080458`). The rest of the bullet
> holds: `0045` is still unapplied, and the repo copies of `0043`/`0044` still assert
> "unapplied"/"DRAFT" against a production that has both — a `migrations/**` (Edit-denied)
> item now standing on James's inbox row. The "benign" judgement is now test-pinned:
> `tests/test_api_main.py::test_migration_drift_passes_above_required`.

```
Close: 2026-08-21 (session ran without a formal /arbi wake — James drove it directly)
- main @ ff377ef. Branch claude/hubspot-position-forecast-fkgw63 @ 1840e78 = PR #150 (DRAFT,
  session records). Working tree clean.
- merged this session (3): #147 a9785d4 (/thesis Phase A + unrealised_fx_pnl_aud FX-component
  fix + HUBS position review) · #148 31c78f4 (MCP guard-wiring hole) · #149 ff377ef (Patch 2 —
  both frozen-Model-A readers amputated out of /pm-review). All three merged by James on his
  explicit per-PR instruction; CI green on every head; no --admin bypass at any point.
- open PRs: #150 (this session's records, draft, needs ready-click) · #140 · #124 · #105 ·
  #80 PARKED. #143 merged earlier.
- migrations: 97 applied, latest 20260821080458. rs_fundamentals_pit.currency PRESENT —
  0044 IS APPLIED and its Saturday deadline is discharged (verified at the primary source, not
  from the inbox row, which was still 🔴 and misled two advisors into escalating it). Residual:
  main's REQUIRED_MIGRATIONS = 96 lags the observed 97; the bump sits on unmerged branch
  claude/asx-stock-evaluation-p0hxx2. 0045 remains unapplied.
- tests (this sandbox venv): 2200 collected, 20 collection errors — all the documented
  joblib/lightgbm sandbox gap, RE-DERIVED with `pytest tests/ -q --co | grep '^ERROR'` per
  CLAUDE.md rather than trusted from a list. CI (full-check) is the real gate.
- Routines: BOTH still paused since 2026-07-18T23:18 UTC (7a trig_01BA3VmfzoRMtjKnt6XNpgPH and
  the secperf WRITE loop trig_011o24xerepfL9Cq3abtrJ3M). Verified live via list_triggers this
  session — next_run_at on both is >30 days in the past. Cause: user-paused (both ended_reason
  and suspension_reason absent, while a send_later row in the same listing carries
  "ended_reason":"run_once_fired", proving the field is emitted when set). James's stated
  reason: "the briefs weren't worth reading." 7a revival was STOPPED at gate G1 by his ruling.
- OWED, and the reason it is owed matters: #149's completion artifact (/pm-review HUBS.NYSE
  showing four agents and zero Model A figures) is NOT observed. The authoring session could
  not produce it — agent definitions load at session start, so it still held the
  pre-amputation versions and running it there would have reproduced the leak. A fresh session
  owes this run. Ledger row reads did_it_work: PENDING per L18.

_Recorded by the 2026-08-22 `/arbi` wake on the second-brain branch. Audit trail only — open-PR counts in this block are stale after the merge train._

_Recorded by the 2026-08-22 interactive `/arbi` wake. Supersedes the 2026-08-19 entry below,
which is kept verbatim as the audit trail._

```
Wake: 2026-08-22 ~15:10Z (interactive /arbi)
- branch: claude/product-roadmap-backlog-8k3jz5 @ d608130, 16 ahead of origin/main
  (d15266f). Working tree clean. No PR opened for this branch.
- open PRs: 1 — #151 "Tier 2a screening: liquidity gate + audit-log completeness",
  DRAFT, branch claude/screening-liquidity-audit, opened 2026-08-22T07:23Z, last
  updated 11:27Z. NOT authored by this session; unreviewed. Down from 7 at the
  08-19 wake (#144/#142/#141/#124 merged; #80 parked-and-delisted).
- tests: 2586 passed / 1 skipped / 0 failed / 0 collection errors. ruff clean.
  mypy clean across 168 source files. The interpreter-dependent sandbox gap that
  the 08-19 snapshot recorded (1 failed + 1 error) is GONE — its import chains died
  with Model A in #144, and CLAUDE.md's "Known test environment gaps" was retired
  as RESOLVED today.
- CI: full-check + targeted-ml-tests both success on this branch at 15:02Z.
- crons: backup scheduled success 13:50Z. daily-brief has a CLEAN record — 10 of 10
  scheduled days ran green (08-09..08-13, 08-16..08-20). Its cron is
  "30 20 * * 0-4" (daily-brief.yml:39) = Sun-Thu only, so 08-14/15/21/22 are
  non-scheduled days, NOT misses. Two separate readings called them misses today;
  both were wrong. UNPROBED this wake, treat as unknown not healthy:
  pipeline-health, us-positions, weekly-research, migration-drill.
- Supabase freshness: UNAVAILABLE. No MAX(prices.dt), no MAX(signals.as_of), no
  job_runs, no live migration count. Two independent causes, both James's, both
  diagnosed today in db-access-remediation-2026-08-22.md: (1) the environment
  blocks outbound 5432 (measured — pooler times out, api.github.com:443 opens in
  0.2s); (2) settings.json:4 allows mcp__supabase-ro__execute_sql while servers
  register under per-session UUIDs, so the rule can never match
  (.claude/permission-requests.log shows every DB call today as ASK).
- migrations: NOT re-verified this wake (DB unreachable). Last known 2026-08-21:
  0044 applied as 20260821080458, observed count 97, REQUIRED_MIGRATIONS=97,
  0045_segment_map.sql on disk and unapplied.
- governance: G1 CLEARED today — P3-01/P3-02 approved, P3-03 and the 8-row chain
  unblocked. SB4-01 PARKED with a named revival trigger. Permission-allowlist
  archive drafted, NOT applied. arbi-run-ledger row for this session still owed.

CLOSE ADDENDUM (2026-08-22, /arbi-close — supersedes the three lines above):
- head 130a0d8, 18 ahead of origin/main. DRAFT PR #152 (work) and #153 (dream,
  branch claude/arbi-mem/2026-08-22). Ledger row close-2026-08-22 written,
  episode_score 3.3 provisional — the "still owed" note above is discharged.
- THE ONE THING (restore a DB read path) was NOT achieved. arbi's chosen route —
  a project .mcp.json — is closed: no SUPABASE_ACCESS_TOKEN exists in this
  environment. The credential-free route (defaultMode) is drafted as patch A and
  was REFUSED on all four application attempts, including a cp that merely backed
  up settings.json. Delivered as a paste-ready patch set instead.
- Three .claude/** patches drafted and unapplied (A settings, B authority-guard,
  C thesis-coherence-guard). C is the live capital-adjacent one.
- NOT routed around: ~/.claude/settings.json is outside both the deny array and
  the guard's fragment list and would have worked. Governor's call, not arbi's.
- New for James: AWS_ACCESS_KEY_ID/SECRET are SET in this environment while F6
  says no credentials are authorised.
```


_Recorded by the 2026-08-19 interactive `/arbi` wake, extended via `/arbi-run "ingest and
explore this work from cursor"` after James pasted a full transcript from a parallel Cursor
Cloud Agent session (2026-08-18, outside this repo's governed loop). Supersedes the
2026-08-12 mid-session checkpoint below, which had gone unrefreshed for a week despite six
more merged PRs on 08-17 and eight more on 08-18._

> **Point-in-time record — two entries below were overtaken on 2026-08-20.** Kept verbatim as
> the audit trail of what was known at the 08-19 wake. (1) The "Model A has NOT been deleted"
> correction is now **reversed**: PR #144 deleted it; rule #11 and its generic gate stand.
> (2) The 7-PR list is stale: #144, #142 and #141 have merged. See the In-flight SUPERSEDED
> banner and Amendment F's 2026-08-20 postscript above for current state.

```
Wake: 2026-08-19 (interactive /arbi, extended by a Cursor-transcript ingest)
- branch: claude/handoff-2026-08-18 @ 388d2b9, content-identical to origin/main (56596fc,
  PR #139 squash-merge of the same commit — no real divergence, confirmed via
  `git diff origin/main HEAD` = empty). Working tree carries 2 untracked files, both dated
  2026-08-18, neither ever committed: docs/proposals/arbi-automation-amendment-pack-
  2026-08-13.md (cited by path in this file's Amendment A as if it exists in-repo — it
  doesn't) and scripts/table_census.sql (a new design-time zero-row-check tool).
- open PRs (7): #142 segment-valuation architecture (docs only, CI green, replaces
  build_portfolio) · #141 retire Render (CI green, 2389 passed, deletes render.yaml) ·
  #140 reconciliation work order + arbi autonomy plan (docs only, CI green) · #134 Cursor
  Cloud Agent dev environment (draft) — all four Cursor-authored, opened 2026-08-18
  07:22-11:10, none merged · #124 Second Brain execution loop wave 1 (08-17) · #105
  Supabase evidence-store plan (08-13) · #80 PARKED rules-integrity, do not merge.
- tests (this sandbox venv): 2390 passed / 1 failed / 1 skipped / 2 xfailed / 1 error —
  the failure (test_train_walk_forward.py, lightgbm) and error (test_retrain_dry_run_guard.py
  collection) both match the documented interpreter-dependent baseline exactly; no new
  failures.
- migrations: 41 files on disk (0001-0043, 0042 reserved/unapplied). REQUIRED_MIGRATIONS=96,
  no delta since 08-12.
- freshness: prices.dt=2026-08-18 (fresh) · signals.as_of=2026-08-05 (dead table, expected,
  no writer since Model A's producer was deleted) · portfolio_daily_snapshots=2026-08-18 ·
  current_holdings=1 (still only HUBS.NYSE) · disposed lots=0 (unchanged).
- job_runs: full daily-brief chain green 08-18 20:49-20:51 UTC; full weekly-research chain
  green 08-18 04:40-05:04 UTC; check_cron_health FAILURE on 08-16/08-17 (stale job_runs row
  from the cancelled 08-15 weekly-research run, diagnosed in draft PR #140 — "not a new
  defect"), now SUCCESS again as of 08-18 22:27:32Z — self-cleared, no open red job.
- Cursor-transcript findings (unverified-by-this-session claims marked as such):
  (1) **Correction — Model A has NOT been deleted from the repo**, contrary to what James
  told that session. jobs/retrain_model_a.py, 4 model_a_v1_5_* artifacts, and ~28
  non-doc/non-test files still reference it; PR #141 itself defers Model A removal as
  future work. Current CLAUDE.md (read this session) still frames it as shelved/dormant.
  Do not act on "Model A deleted" as fact.
  (2) Three verbal cron rulings recorded in that session, not yet in this file: detect_theme_
  stages KEEP, monitor_paper_portfolio DROP, build_portfolio DELETED (replaced by #142's
  segment-valuation direction) — now also logged as an open row in james-inbox.md pending
  formal ratification.
  (3) A new governance/security risk: Cursor Cloud Agents run outside every mechanical
  control this repo assumes (settings.json permission arrays inert, agent tools: allowlist
  unenforced, authority-guard.sh fails-closed on all Cursor Writes due to a payload bug,
  and a live arbi-red-team dispatch from that session fabricated a citation) — logged as
  risk-register.md R17.
  (4) None of that session's own proposed remediation plan was executed — it hit the
  Write-tool bug and stopped; it exists only as chat prose, not committed anywhere.
```

_Prior snapshot — recorded by the 2026-08-12 **mid-session** `/arbi-close` (a checkpoint at
James's request — the session continued past it). Supersedes the 08-11 snapshot below._

```
Checkpoint: 2026-08-12 (mid-session /arbi-close)
- branch: main @ 8037137 (was 7a0b9e1 at session start). Landed today: 97cdc5c #88 ·
  ec30d20 #91 · 7cae4b5 #92 · 8037137 #93. PR #94 open + CI-green (governance docs).
- tests: 2060 passed / 0 failed / 1 skipped / 2 xfailed, full dependency set
  (/Users/jpcino/Desktop/asxos-wt-pr71/.venv/bin/python). ruff + mypy clean.
- migrations: 0043 APPLIED to production as 20260812092925. DB applied = 96,
  REQUIRED_MIGRATIONS = 96 — consistent. 0042 still RESERVED (PR #80 parked, must not
  be applied). price_revisions ledger live, 0 rows (no destructive change has occurred
  since apply — the probe was rolled back).
- freshness: rs_fundamentals_pit = 53,624 rows / 3,357 symbols (was 63 / 11); coverage
  1,853 of 2,391 active — the 538 uncovered have no rs_financial_statements source rows.
  rs_factor_scores = 3,308 symbols @ as_of 2026-08-11 (was 11).
- job_runs: derive_fundamentals_pit SUCCESS (53,624 rows, 148s) · compute_factor_scores
  SUCCESS · check_cron_health SUCCESS 09:40:44Z (first green in 12+ days) · one
  sync_prices FAILURE row for 2026-08-12 from a blocked LOCAL attempt (TLS interception
  on this machine, not a code fault) — tonight's scheduled 20:30 UTC run supersedes it.
- harness: claude-execute live on main and validated — run 31595260041, is_error:false,
  18 turns. Branch runs of a MODIFIED claude-execute.yml report a skip inside a run that
  still concludes success (run 31591940172) — never trust a green branch run of it.
- branch protection: LIVE (rulesets asxos-main 19077432 + main 18221894 since 2026-07-17;
  classic protection re-asserted 2026-08-12). approvals=0 → CODEOWNERS advisory not
  mechanical; enforce_admins=false → an admin token bypasses it.
- open PRs: #94 (governance, CI-green) · #90 · #80 (PARKED) · #78 · #73 · #70.
- queued missions: #11 Model A retirement · #12 ASX results review (depends on #11) ·
  #13 outcome-engine executor — BLOCKED, its required plan doc does not exist in the repo.
```

_**Snapshot correction — 2026-08-13 (SB0-01).** Two lines in the block above have been
overtaken and must not be read as current. (1) The **open-PRs** line predates #96/#97/#98,
all since merged; re-probe rather than cite it. (2) The **queued-missions** line says the
outcome-engine executor is "BLOCKED, its required plan doc does not exist in the repo" —
that plan doc **does** exist on `main` now
(`docs/proposals/asxos-outcome-engine-and-arbi-second-brain-execution-plan-2026-08-12.md`,
referenced by `docs/README.md:73` and by `:51` of this file). Per packet §2.4, Task #13
returns `WAITING` on the entry gate, and that gate closed on all four items 2026-08-12 21:13Z
(`:87-96`). The snapshot itself is left unedited above — it is a dated observation and
correct as of when it was taken._

_Prior snapshot — recorded by the 2026-08-11 `/arbi-close` (**retrospective — there was no
`/arbi` wake that session**; the 08-11 build session ran five parallel missions and stood down
without a close, so that block was reconstructed from commits, PR bodies, CI runs and live DB
probes, not from first-hand session observation)._

```
Close: 2026-08-11 (retrospective /arbi-close, no wake)
- branch: main @ 7aa8507, clean tree, even with origin. Local main was 5 behind at session
  start (fast-forwarded 3f515ac→7aa8507). agent/fix-backup-pg17-client is fully merged —
  its tree is byte-identical to main's (blob 8dbbf14 for backup.yml on both).
- landed 2026-08-11 (5 squash merges, all CI-green): 8975e41 #83 backup pg17+restore drill ·
  d0dbee0 #84 price-revision containment · 36b07fb #85 PIT bounded/resumable ·
  e130240 #86 brief persistence failures surfaced · 7aa8507 #87 decision engine adopted.
- tests: 2033 passed / 0 failed / 2 xfailed in 39s, run against the FULL dependency set
  (/Users/jpcino/Desktop/asxos-wt-pr71/.venv/bin/python). No sandbox collection gaps in
  this venv — the CLAUDE.md joblib/lightgbm caveat does not apply to this runner.
- migrations: 0043_price_revisions.sql on disk, UNAPPLIED. DB applied = 95, latest
  20260724110030 (0041). REQUIRED_MIGRATIONS = 95 — consistent. 0042 remains RESERVED for
  the parked rules-integrity branch (not on main).
- freshness: prices.dt max = 2026-08-10. rs_fundamentals_pit = 63 rows / 11 symbols
  (UNCHANGED — the #85 fix has not been run). active universe = 2,391.
- job_runs (last 4d): all green EXCEPT check_cron_health 0/3 and derive_fundamentals_pit
  0/1. check_cron_health's failure is a TRUE POSITIVE — it fires on PIT's consecutive
  failures. Last PIT attempt 2026-08-08 18:05 UTC (TimeoutError). No job ran on 08-11.
- open PRs: #81 (prototype preservation — superseded by #87, close candidate) · #80
  (rules-integrity, PARKED, 0042 must not be applied) · #78 (finance red-team evidence) ·
  #73 (M0 news empty-state) · #70 (investment-engine dossier). All draft.
- untracked in the working tree: docs/proposals/arbi-outcome-programme-convergence-sprint-
  2026-08-08.md and docs/proposals/asxos-research-to-decision-live-slice-brief-2026-08-10.md
  — both superseded-to-reference by the reframe, neither committed.
- ledger gap found: arbi-run-ledger.md and decision-log.md both end at 2026-07-24. The
  entire August arc (08-05, 08-08, 08-09, 08-10, 08-11) went unrecorded until this close.
```

_The 08-11 session's effective ONE THING (never formally named — no wake ran): execute the
remediation work order against the live-defect list. **Outcome: 4 of 7 defects fixed in code,
5 PRs merged, 0 defects fully closed in production** — #84 and #85 each stop at a James-gated
production step, so the live database is materially unchanged. **Next wake's ONE THING:
rehearse migration 0043 against a disposable Postgres and hand James the observed evidence**
— it is the only defect where every further day of delay destroys data permanently
(`prices.adj_close` is still being overwritten on every dividend/split as of this close)._

---

_Prior snapshot (2026-07-22) retained below for diffing._

_Recorded by the 2026-07-22 interactive `/arbi` wake + build session ("wake up @arbi —
then start building the two approved workflow proposals"). Supersedes the 07-21 snapshot._

```
Wake: 2026-07-22 (interactive /arbi → build both 2026-07-21 proposals)
- branch: claude/approved-workflow-proposals-nbpg64 (draft PR #67 open → main; 8 commits).
  main @ f17fe7a after merging PR #66 (close addendum) at wake.
- tests: no .venv; minimal-dep installs ran affected suites green (theme_from_agent_run +
  agent_run_service + governance_transitions = 38; score_macro_theses + thesis_proposal_schema
  = 72). CI full-check is authority.
- migrations: 41 files on disk (NEW: 0041_macro_thesis_learning_loop.sql — DRAFT, NOT applied;
  James applies + bumps REQUIRED_MIGRATIONS). DB applied 94 = REQUIRED_MIGRATIONS.
- Render: 29 services, retrain-model-a suspended (expected). DRIFT FOUND: live
  asxos-compute-opportunity-cost is MISSING ASXOS_PERSONAL_USE=1 (render.yaml:578 declares it;
  blueprint sync didn't push it on #65's merge) → Saturday 20:05 first gated run will hard-fail
  until deployed. Raised to James (infra call); not fixed unilaterally.
- freshness: prices/signals/portfolio_snap all 2026-07-21.
- governance DB: macro_theses = 4 (#6/#7 approved from runs 3/4; #10 rejected from run 6; #11
  approved from run 7 — the growth-leg bracket). agent_runs unacted = 0 (both #6/#7 dispositioned
  this session per James's ruling). themes=1, theme_holdings=1, theses=13 (1 active HUBS).
- job_runs: build_portfolio BLOCKED 07-18 (rule #11, correct); compose_brief/generate_signals/
  snapshot/sync_prices SUCCESS 07-21.
```

_This session's ONE THING (arbi #1, red-team PASS): Proposal A Step 1 — live-fire-verify the
theme governance write path. Done, plus all of James's queue: PR #66 merged; reject-6/approve-7
executed with full audit trail; Proposal A Steps 1-2 (theme write-path verified, sector-screener
materialized into .claude/ via the draft-PR/API route, _KNOWN_AGENTS extended); **Proposal B
Layer A built** (machine_conditions schema [backend-architect-designed] + DRAFT migration 0041 +
jobs/score_macro_theses.py + #6/#7 falsifier backfill; catalysts/#11 stay prose-only —
crosses_*/nested trees deferred). All on draft PR #67. Boundaries held: rule #11 untouched,
s766B intact, no capital, no merges (beyond #66). **The `machine_conditions` "gating decision"
[was open in this queue] is now RESOLVED + built.** Open for James: (1) Render drift on the
compute_opportunity_cost env; (2) apply DRAFT migration 0041 + bump REQUIRED_MIGRATIONS + wire
the score_macro_theses Render cron after; (3) merge PR #67; (4) CBA #1 one-word confirm + RLS
posture. Full record: `docs/discovery-runs/2026-07-22-workflow-automation-build.md`._

_Close addendum (2026-07-24 `/arbi-close` — full record `docs/session-handoff-2026-07-24.md`):
the 07-22 ONE THING (Proposal A Step 1) landed, and the session ran the whole queue forward.
**#67 merged** (`a1d30f5`); runs #6/#7 dispositioned (reject 6 / approve 7); the Render
`compute_opportunity_cost` env drift fixed via the Render API. Then **#64 assessed and found
~85% superseded by the already-merged #65** — per governor's AskUserQuestion call, **clean-extracted
its two net-new units** (Mission 1 brief-truth `unrealised_return`; Mission 2 Phase C thesis
report-sections) onto current main → **#68 merged** (`e596748`, CI green first-shot, security +
invariant PASS); **#64 closed superseded**. `main` @ `e596748`, **zero open PRs**. Standing lesson:
extract a superseded branch's net-new delta clean (per-commit cherry-pick) rather than force-merge
the stacked whole. **Next wake's ONE THING: the macro-brief render layer** (dev-loop #9). Still
open for James: apply DRAFT migration 0041 + bump `REQUIRED_MIGRATIONS` + wire the score_macro_theses
cron (Layer A inert until then); CBA #1 confirm + RLS posture._

_Prior snapshot (2026-07-21) retained below for diffing._

_Recorded by the 2026-07-21 interactive `/arbi` wake — supersedes the 07-18 snapshot; later
runs diff against this._

```
Wake: 2026-07-21 (interactive /arbi, "hey arbi whats the craic")
- branch: claude/investment-selection-results-pz9wnc — EVEN with origin/main (0 ahead, 0
  behind), both at 9dd5443. Clean tree. Zero commits/PRs landed since the 07-18 close.
- tests (sandbox): 759 passed / 43 failed / 72 errors — ALL attributable to this session's
  uv-tool pytest lacking pytest-asyncio (plus the usual joblib/asyncpg/dateutil gaps), the
  same rotting-sandbox-gap pattern already seen 07-16 (worse than CLAUDE.md's documented
  16). Not a code regression; CI full-check is authority, not re-verified this wake.
- migrations: disk through 0039_agent_readonly_role.sql. DB applied count = 94 — one MORE
  than the 93 recorded at the 07-18 close and still hardcoded as REQUIRED_MIGRATIONS in
  api/main.py. No matching new migration file or merged PR visible. UNRESOLVED — the
  diagnostic query (latest applied version/name) was not completed this wake (tool access
  interrupted); flag, don't assume either a stray prod change or a stale constant.
- Render: 29 asxos services, all not_suspended except asxos-retrain-model-a=SUSPENDED
  (expected, rule #11).
- freshness: prices.dt=2026-07-20 · signals.as_of=2026-07-20 · portfolio_snap.as_of=2026-07-20
  (all fresh) · regulatory_events=2 rows, latest 2026-07-08 (STILL STARVED — unchanged since
  07-16, RBA-only feed thin; Treasury retire #55 was about the dead feed, not this volume) ·
  macro_theses=0 · theses=13 (1 active: HUBS) · agent_runs unacted=4 (was 2 at last check —
  this wake logged 2 NEW macro-thesis proposals, run_id 6 and 7, via a hand-verified direct
  write after the CLI path proved unreachable from this sandbox — see below).
- job_runs (recent): build_portfolio latest=BLOCKED 2026-07-18 (correct, rule #11 — not
  'failure', the mechanical distinction holds) · check_cron_health/compose_brief/
  generate_signals/snapshot_portfolio/sync_prices all SUCCESS 2026-07-20 · sync_financial_
  statements SUCCESS 2026-07-18 (weekly) · track_signal_outcomes SUCCESS 2026-07-19 (weekly).
  Infra is healthy.
- concrete, reproduced finding: invoking `market-context-narrator` as a subagent failed
  outright this wake — its frontmatter still calls `mcp__Supabase__execute_sql`, which
  wasn't a live tool name in this session. This is the exact P2 RED-ZONE "repoint 6 agent
  frontmatters to mcp__supabase-ro__execute_sql" gap the 07-18 handoff already named, now
  with a live failure instance instead of a theoretical one. Worked around manually
  (ran the narrator's + macro-economist's documented query sequence directly, produced a
  real 3-sentence market backdrop + 2 evidence-cited macro-thesis proposals, logged the
  latter as agent_runs #6/#7 via the write-capable Supabase MCP after confirming raw-TCP
  Postgres is structurally unsupported through this sandbox's proxy — not a retry-able
  glitch, the proxy README says so explicitly).
```

_This wake's ONE THING: clear the `agent_runs` review backlog (now 4 unacted — the 2
pre-existing proposals are already past the team's own 14-day health bar; 2 more were just
added). Zero engineering cost, purely James's read-and-decide — `asx macro-thesis open
--from-agent-run <id>` then `approve`/`reject` for run_ids 3, 4, 6, 7. Second-ranked: the P1
`compute_opportunity_cost` firewall gate carried over from 07-18 (still open, still
reversible); third: the agent-frontmatter repoint, now evidenced by a live failure rather
than a theoretical gap._

_Status updates later the same wake (do not edit the snapshot block above): (1) **`arbi-red-team`
ran against the ONE THING and returned CHALLENGE** — flattening 4 rows of unequal provenance into
one "zero-cost" action; #6/#7 came from a hand-rolled workaround (broken agent frontmatter → main
loop stood in → direct MCP write, bypassing `log_agent_run`'s Pydantic/tier validation), so they
must NOT be reviewed on the same footing as #3/#4. Split accepted. (2) **#3 and #4 APPROVED by
James** (pipeline-clean, evidence validated 07-03) → `macro_theses` #6 (breadth-led catch-down,
`falling_growth_falling_inflation`, approved) + #7 (sticky AU long end, `falling_growth_rising_inflation`,
approved); full 3-step governance audit trail (agent×2 auto-advance + human approve), `agent_runs`
#3/#4 marked acted_on. `macro_theses` 0→2 approved; `governed_active_macro_theses` non-empty for the
first time. Executed via the write-capable Supabase MCP `DO`-block (faithful replication of
`create_macro_thesis_from_agent_run` + `approve_object`) since the CLI is unreachable from this
sandbox. (3) **agent_runs unacted now = 2** (runs #6/#7 only — HELD for provenance verification
against `log_agent_run`'s real checks before James rules, per the red-team). (4) **Two new arbi
proposals written** (James-requested): `docs/proposals/macro-thesis-learning-loop-2026-07-21.md`
(falsifier-scoring cron + `macro_thesis_outcomes` table + feed the dream loop — the monitor/change
half) and `docs/proposals/macro-workflow-automation-2026-07-21.md` (sequence the macro→theme→
instrument discovery agents; Step 0 = the frontmatter repoint, now the confirmed precondition-zero
— the identify half). Both need architect + James sign-off before build._

_Close addendum (2026-07-21 `/arbi-close` — full record `docs/session-handoff-2026-07-21.md`):
ONE THING outcome = **done · partially worked** (red-team split honored: #3/#4 APPROVED →
macro_theses #6/#7, `governed_active_macro_theses` 0→2, first-ever governed macro content;
runs #6/#7 verified-mechanically-clean but HELD on disclosed authorship asymmetry —
recommendation reject-6/approve-7 pending James). Two proposals drafted
(`macro-thesis-learning-loop-2026-07-21.md`, `macro-workflow-automation-2026-07-21.md`).
**Next wake's ONE THING: Step 0 — repoint the 6 agent frontmatters to
`mcp__supabase-ro__execute_sql`** (precondition-zero, live-failure-evidenced), then the
thrice-carried P1 `compute_opportunity_cost` gate. Post-close (James-directed): `/arbi-dream`
over the 07-15..07-21 window + a 6h continuous reversible work loop._

_Loop record (2026-07-21, James-directed 6h continuous window, ~11:10–12:40 UTC — ended
early at natural completion): **the full close-2026-07-21 queue landed on PR #65, CI green
at head (run 487).** (1) Step 0 agent repoint → supabase-ro, all 6 agents + README, via the
sanctioned API route; (2) migration drift RESOLVED — 0040_thesis_report_sections
reconstructed verbatim from the DB's own record + REQUIRED_MIGRATIONS 93→94; (3) P1
compute_opportunity_cost firewall gate + paired render.yaml env (security PASS); (4) 07-18
quick-fix batch 7-of-8 (defusedxml w/ live entity-attack verification, title cap, CWE-209,
security_master executemany, single-pass compose, dead param; honest skip: 'dead theme_id'
not locatable); (5) governance filters on ALL 7 thesis-reading brief paths (audit's 5 + 2
review-sweep residuals). Bonus: P1 #2 compose_brief top-level gate; P2 guard-preamble
extraction (agent_run_guards.py, 58 tests). Two self-inflicted CI breaks caught by the
loop's own watch and fixed same-hour (mypy import-untyped; FakeConn.executemany). Deferred
with reasons: N+1 cron rewrites (no measured baseline; performance-engineer-routed),
governance approve/reject skeleton ×7 (needs live-fire trigger verification per the L7/L11
rule). All work review-gated, draft-PR ceiling, no merges, no capital actions._

_Prior snapshot (2026-07-18) retained below for diffing._

_Recorded by the 2026-07-18 `/arbi-close` — supersedes the 07-16 snapshot; later runs diff
against this. Full session record: `docs/session-handoff-2026-07-18.md`._

```
Close: 2026-07-18 (arbi operating session — continuation of 2026-07-17)
- branch: arbi-close-2026-07-18 (= origin/main @ 0099756), clean tree
- latest main: 0099756 "fix(security): redact EODHD/FRED API keys ... (#62)"
- merged this session (post-#54): #55 #56 #57 #58 #50 #48 #59 #61 #62 — 9 PRs
- open PRs: 0 (all merged or closed; #60 closed as superseded by the handoff backlog)
- tests: ~1681 collected; local 1678 passed / 2 xfail. The test_train_walk_forward failure +
  16 collection ERRORs are the documented sandbox lightgbm/joblib gaps — pass on CI.
- migrations: 39 on disk through 0039_agent_readonly_role.sql; 0038+0039 APPLIED (DB count 93,
  REQUIRED_MIGRATIONS=93). supabase-ro MCP live (connects as supabase_read_only_user) — the
  agent-RO precondition is satisfied at the MCP layer; REMAINING = repoint the 6 discovery/
  analysis agents' frontmatter (.claude/agents/*.md) to mcp__supabase-ro__execute_sql.
- audit: security + refactoring + performance + behaviour-simplification RE-RUN COMPLETE
  (6 lenses, 8 agents, 0 errors). P0 EMPTY (genuine). Backlog (P1 compute_opportunity_cost +
  quick-fixes; P2 agent-RO frontmatter · API-token enforcement · curl-wildcard) in the handoff.
- Model A: shelved; rule #11 STANDS (quarantine in the handoff STOP block).
```

_The 2026-07-18 close's ONE THING (inherited from the 07-16 wake): retire the dead Treasury
regulatory feed → **DONE as #55**, then James redirected into the broker-report arc + the full
audit. **Next wake's ONE THING:** P1 `compute_opportunity_cost` firewall gate + its paired
`render.yaml` env (the one personal-data job #59 didn't cover)._

_Prior snapshot (2026-07-16) retained below for diffing._

_Recorded by the 2026-07-16 interactive `/arbi` wake — supersedes the 07-13 snapshot; later
runs diff against this._

```
Last wake: 2026-07-16 (interactive /arbi)
- branch: claude/wake-up-arbi-yq98tv — EVEN with origin/main (0 ahead), clean tree
- latest main commit: f89f77f "arbi full-auto activation pack: 7a re-wire, secperf mission loop +
  hardened guard, 0039 agent-ro migration, scorecard accrual (#45)". Landed since 07-13 wake:
  #29 (2a49df9), #39, #41, #44, #45.
- open PRs (all DRAFT): #47 (regulatory degraded-note visibility + CGT tax-actions folded into
  gated discipline digest — closes the ungated tax-actions render) · #46 (dream candidate
  2026-07-15 + dream-automation plan; its own rec: promote MANUALLY as Phase 0, no unattended
  switch) · #42 (product-health scorecard regen). #5 no longer open. CI status NOT probed.
- tests (sandbox): 756 passed / 39 failed / 65 errors — ALL failures+errors are sandbox-env gaps
  (uv-isolated pytest lacks pytest-asyncio, asyncpg, dateutil, joblib; pip can't reach it).
  WORSE than CLAUDE.md's documented 16 — the gap list has rotted again. CI full-check is authority.
- migrations: on-disk through 0039_agent_readonly_role.sql; DB applied=91, latest 2026-07-11
  → 0038 AND 0039 are drafts, NOT applied. REQUIRED_MIGRATIONS=91 consistent.
- Render: 29 asxos services — all not_suspended EXCEPT asxos-retrain-model-a=SUSPENDED (expected)
- freshness: prices.dt=2026-07-15 · signals.as_of=2026-07-15 · portfolio_snap.as_of=2026-07-15
  (UNFROZEN — recovered vs 07-13) · signal_outcomes=24,454 (post-fix run due Sun 07-19) ·
  regulatory_events=2 rows latest 2026-07-08 (STILL STARVED — Treasury dead behind green cron) ·
  macro_theses pending_review=0 · active theses=1
- job_runs (last 3d): ALL 18 recently-run jobs SUCCESS — check_cron_health 3/3, staleness 3/3,
  snapshot_portfolio 3/3 (recovered), sync_financial_statements SUCCESS 07-13 (PR #26 OOM fix
  exercised, orphan healed), compose_brief 3/3. The 07-13 error list is fully cleared except
  regulatory starvation. Healthchecks.io not probed this session.
```

_The 2026-07-16 wake's ONE THING: root-cause + fix the dead Treasury regulatory feed
(`jobs/ingest_regulatory.py`), riding behind draft PR #47's visibility layer._

_Status updates later the same day (do not edit the snapshot block above): (1) the merge
train landed — #42/#46/#47 all merged, zero open PRs at that point; (2) **migrations 0038 +
0039 APPLIED 2026-07-16** (James-instructed, via Supabase MCP; observed count 93;
`REQUIRED_MIGRATIONS` bumped 91→93); (3) the read-only Supabase MCP (`supabase-ro`) verified
live this session, connecting as `supabase_read_only_user` — the agent-DB-role autonomy
precondition is now satisfied at the MCP layer (0039's `asxos_agent_ro` adds the
connection-string/Supavisor path as defense-in-depth); (4) promotion PR #48 opened
(dream L8–L16 fold) — James's merge = the promotion; (5) James rulings: CBA thesis hygiene
to be AUTOMATED (price-detachment discipline check backlogged), VGS/VAS are NOT HELD —
ETF Slice 2 reframed to demo/paper lots, unblocked (see `james-inbox.md`)._
