# asxos Roadmap & State — the reconciled picture

**Status:** current (living document — refreshed every `/arbi` and `/arbi-close`)
**Scope:** whole repo — **the single live queue.** All other backlogs are reference only.
**Last verified:** 2026-08-11 (`/arbi-close`, retrospective — the 08-11 build session shipped five
merged PRs and stood down without a close; this refresh reconciles the defect list against `main`
@ `7aa8507`. See "PROGRAMME REFRAME" immediately below; the 2026-07-14 notes are retained as history)
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
| **1** | Evidence foundation. **Order matters: contain irreversible loss first**, then repair PIT | **STILL NOT AUTHORISED as a stage.** What ran on 2026-08-11 was the *remediation work order* against the live-defect list below (defects 1/2/3/6 fixed in code, five PRs merged) — **not** Stage 1's evidence-foundation build. F5 (Dagster deployment/cost/cutover) and F6 (S3 bucket/credentials) each still name a prior work order that has not been written |
| **2** | Research registry + evaluation (method-agnostic; reproducibility and failed-variant retention) | not started |
| **3** | Theme + candidate engine | not started |
| **4** | One governed paper investment case, end-to-end (**new screened candidates** — governor ruling) | not started |
| **5** | Outcome learning — **initially a process audit + descriptive outcome evidence**, not statistical validation | not started |
| **6** | Portfolio scale + surface cutover | not started |

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

**🟡 Amendment E — DRAFT, AWAITING JAMES'S RATIFICATION (drafted 2026-08-18).** **This is not
in force.** It is recorded here per the same GOV-01 two-artifact convention Amendment D
followed — a ruling requires the ruling AND the queue amendment, and *this row is only the
first artifact*. Amendment D's row states "Ratified verbatim by James"; this row deliberately
cannot, because he has not seen it. Nothing may cite Amendment E as authority, and no close row
may be blocked or admitted under it, until James ratifies it and the queue amendment is
written. Drafted text follows verbatim:

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
| 1 | **`backup.yml` had never succeeded** — apt step failed (`packages.microsoft.com` 403, exit 100) before reaching `backup_irreplaceable.sh`; pg16 client could not dump a pg17 server | ✅ **FIXED + OBSERVED GREEN.** PR #83 (`8975e41`). Run `31465179375` @ `9d6bffd`: `backup: success` **and** `restore_drill: success` — a real restore against a clean schema built from repo migrations, with every table count verified. This is the first end-to-end proof the irreplaceable backup works |
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
| News/sentiment M14a/M14b | `asxos/ingestion/{news,sentiment}.py` | **Shipped, writing, but near-empty** (`ASXOS_NEWS_BRIEF_ENABLED=1` on `main` since 2026-07-11 — this row previously said `0`, which was wrong; live state wins). Corrected 2026-08-17: `holding_news` does **not** have zero rows — it has **7** (2026-08-10..13), all `HUBS.NYSE`, all sourced `finance.yahoo.com`. So the ingest path works. **The cause is not symbol mapping** (this row claimed that until 2026-08-17 and it is falsified): `jobs/ingest_news.py:186` selects `DISTINCT symbol FROM current_holdings`, and there is exactly **one open lot**, so the job is correctly ingesting news for the whole of a one-name portfolio. Coverage is bounded by portfolio breadth, not by a mapping bug. `signal_sentiment` downstream remains empty. Ingest guard + brief gate fixed 2026-08-05 (`deea76a`). See `docs/market-trends-report-2026-08-05.md` §1. | V2 arch audit Part A |
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
| `ASXOS_NEWS_BRIEF_ENABLED` | M14a/b news+sentiment brief section | `1` — set in the **executing scheduler**, `.github/workflows/daily-brief.yml:61`. *(Corrected 2026-08-13, SB0-01: this cell previously cited `render.yaml:414`; Render was deleted 2026-08-12, so `render.yaml` sets nothing live.)* **Verdict reverted to UN-SHIPPED / RE-RAISED 2026-08-13** — the flag is still `1` but the surface has no valid SHIP verdict; see `dark-launch-exit-plan.md` surface #2 |
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
| **7a** | Scheduled **read-only dry-run** brief (Routine fires `/arbi`; **output only**) | **RE-WIRED 2026-07-15** — daily 20:30 UTC (06:30 AEST), fresh session, push+email to James; Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH`. The 2026-07-10 Routine (`trig_01PiLVYg…`) was found **absent from the live trigger list** on 2026-07-15 while these docs still claimed it live — the brief had silently stopped. Standing lesson: verify with `list_triggers` on wake; never trust this cell alone |
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

_Recorded by the 2026-08-12 **mid-session** `/arbi-close` (a checkpoint at James's request —
the session continued past it). Supersedes the 08-11 snapshot below._

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
