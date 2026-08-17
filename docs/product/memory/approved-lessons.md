# arbi approved-lessons — the second brain (promoted memory)

**Status:** current (read-only during runs; changed only via a reviewed PR to `main`)
**Scope:** durable, promoted lessons arbi carries into every wake — its long-term memory
**Owner:** promoted via PR review (merge = promotion, `arbi-promotion-gate.md`); never
written by an unattended run
**Superseded by:** N/A

This is arbi's **mind bank**: lessons that survived the promotion gate and are now
authoritative (authority-ladder level 6). A dream (`/arbi-dream`) proposes *candidates*;
only a reviewed merge to `main` lands one here. Each lesson is dated, sourced, and
actionable. **Never deleted** — a superseded lesson is struck through with a note, not
removed. arbi reads this every wake, after the repo docs (levels 3–4) and before raw
transcript (level 8).

---

## L1 — Verify a blocker's blast radius against code, not a doc's framing (2026-07-10)
The "Model A is the platform / everything's blocked" framing was **wrong**. A multi-agent
scan (`wf_f54323f5-d7d`, verdict *supported*) proved the tax engine, thesis/discipline
scaffolding, theme stewardship, and governance are authoritative **today, independent of
Model A** — the quarantine gates only the allocator path + `compute_opportunity_cost`.
**Lesson:** when a doc says "X blocks everything," trace X's real consumers in code before
repeating it. Repo + live state outrank a doc's tone (authority ladder).
Source: `north-star.md:73-81`, `decision-log.md` row 1. *Extended by L12 (2026-07-16).*

## L2 — Don't over-credit external platforms; GitHub + git *is* the runtime (2026-07-10)
I over-stated that autonomy "needs Anthropic Managed Agents." For a single-user, git-backed
project, **Routines (schedule) + git (memory) + GitHub branch-protection/PRs/CI + hooks
(mechanical enforcement)** replace it — and are *more* auditable (every decision is a diff).
Managed Agents is an optional later upgrade, not a prerequisite.
**Lesson:** prefer the repo-native, auditable mechanism; reach for a managed platform only
when the native one demonstrably can't do the job.

## L3 — Pin dev tooling to CI's exact version before claiming green (2026-07-10)
R9's first CI run failed on a single `ruff` F401 (an `import pytest` left unused after
flipping two tests). My **local ruff was 0.15.8; CI pins 0.7.0** — the newer version both
missed the F401 context and reported 4 unrelated false-positives. **Lesson:** run the
CI-pinned tool version (and `ruff check .` over the *whole* repo, not just changed files)
before pushing. A venv with the pinned tool lives at
`scratchpad/venv312` (rebuild per `pyproject.toml`).
Source: `run-ledger` R9 CI round-trip.

## L4 — The highest-leverage move is often a "cleanup," not a feature (2026-07-10)
R9 looked like a cosmetic decoupling but was actually the **mechanical enabler of rule #11**:
until it landed, revoking `approved_for_allocation` to honor the quarantine would hard-fail
the whole brief and hide every (Model-A-independent) thesis card. arbi's ladder + circuit
breakers surfaced this; a surface read would have ranked a feature first.
**Lesson:** rank by *what unblocks*, not by what looks substantial. Check whether the
"cleanup" is the prerequisite to enforcing a boundary.

## L5 — Merge to `main` = prod deploy (I6) — always the governor's call (2026-07-10)
On asxos, pushing to `main` auto-deploys Render across 9 services. Every merge this session
was held for James's explicit go. **Lesson:** never auto-merge to `main` unattended; the
irreversible tiers (5–7) stay human-approved regardless of track record.

## ~~L6 — Model A decay, first pass: keep the quarantine (2026-07-10)~~ [SUPERSEDED → L14, promoted 2026-07-16]
**Struck in place per the append-only rule (never deleted). Superseded by L14 below:** the
2026-07-11 re-run on the *populated* `signal_outcomes` (24,454 rows — the "empty" premise
recorded here was already stale; the product-health scorecard's discovery of that is itself
the surviving instrumentation lesson) resolved the P0 **against Model A**. The "not yet
testable / resolves ~late Aug" framing and the "fix `track_signal_outcomes`" open action are
both closed (PR #26 init-pool + PR #30 `::varchar` cast).
~~Read-only SQL over live `signals`+`prices` (`signal_outcomes` is **empty** — the
`track_signal_outcomes` cron hasn't populated it): the 5-day `prob_up`→return edge is weak
and **sign-flips across dates** (per-date corr −0.075..+0.146; pooled ≈0); the 21-day claim
is **not yet testable** (~2 matured dates; resolves ~late Aug 2026). **Lesson:** rule #11
stays; the fuller study (per-date Spearman rank-IC, benchmark-relative, re-run late Aug) is
the real resolution. **Open action:** fix `track_signal_outcomes` so `signal_outcomes`
populates and the next decay check is one query.~~
Source: `docs/model-a-decay-analysis-2026-07-10.md`.

## L7 — Live-verify the exact emitted statement sequence, not hand-written SQL (carried)
Governance transitions must INSERT the `governance_events` row **before** the
`governance_status` UPDATE (the BEFORE-UPDATE triggers check same-`xact_id`). Mocked tests
and hand-replicated SQL both passed while the real Python-emitted order was wrong.
**Lesson:** any `governance_status` transition must have its *emitted* order live-verified
against the real triggers (rolled-back transaction) at least once.
Source: `.claude/rules/portfolio-conventions.md` Phase-2a verification lesson.
*Extended by L11 (2026-07-16).*

---

## Promotion 2026-07-16 — from dream candidate 2026-07-15

_Provenance: `dream-candidates/archive/2026-07-15-dream.md` (input SHAs pinned in its
frontmatter: 2a49df9 · 91495a4 · fffa2db · 47fb21e · 2d14120 · b59985c · eff3732 · 90f2f54 ·
8848fc2 · 70fd1ad · 1af76e4 · 1208ab8). Gate: fresh-context grader (grader ≠ producer)
returned PROMOTE-PARTIAL — L8–L16 promoted; **L17 (differentiation ≠ validated value) NOT
folded** (single-instance, discretionary — James may add it in review); boundary-adjacent
second review by `security-engineer`: L9 CLEAR, L14 CLEAR. Promotion-log row appended.
James's merge of this PR = the promotion (arbi never self-approves)._

## L8 — Finish before you chase the next thread (2026-07-15 dream)
When a more interesting product thread appears mid-task, do exactly one of: (1) record it
for later, (2) run it in parallel via **explicit** multi-agent orchestration, or (3) stop and
ask James if the priority genuinely changed — **never a silent solo pivot that leaves the
original half-done.** Finish → split → review → merge → *then* build the next thing. This is
a memory-integrity concern, not tidiness: a branch merged in a hurry pollutes the docs arbi
reads each wake.
Evidence: `memory/working/2026-07-11-branch-closeout.md:29-57`.

## L9 — Reversible work is inside arbi's standing authority: scope it, and open the draft PR, without asking (2026-07-15 dream)
When arbi has found the structural cause behind a complaint and the next step is a
**reversible** artifact (proposal / design / docs / scoped plan): (a) **produce it
immediately** — do not end with "want me to scope this?"; (b) when it's ready on an
authorised `claude/**` branch, **open a draft PR** — that is the durable stopping point;
branch-only state is itself the visibility failure the work often exists to fix. Stop and
ask James **only** when the *next* step crosses a reserved boundary: capital, broker
execution, migration/DB write, deploy, merge, secret, Render/infra mutation, governed-thesis
write, policy/conviction change, gate flip, or a red safety-hook denial.
**Do-not-overgeneralise:** this is NOT "act without asking" — the boundary set is unchanged
and hard. ("Standing authority" here = the reversible-work principle; it does not promote
any permission-model tier.)
Evidence: two direct James corrections 2026-07-12
(`memory/working/2026-07-12-scope-reversible-without-asking.md:22-27,64-68`).

## L10 — PR transaction discipline; log every slip honestly and gate continuation on verified-safe state (2026-07-15 dream)
On any branch that backs a PR: (1) chain **commit && push && PR-state read** as one
transaction — never let a push run after a failed commit; (2) avoid force-pushing a reviewed
branch unless the mission explicitly requires reconstruction; (3) after any force-push/
rebase, immediately verify PR head/base/open-closed/diff-count via **live reads, not
memory**; (4) if GitHub auto-closes a PR on head==base, reopen and report immediately;
(5) **never smooth over a slip** — log it in the ledger and the session report even when
fully recovered; (6) prefer fresh branches for unrelated work. On any discovered slip: stop
new work, verify the affected refs, log it, continue **only** if state is verified safe.
Honest logging is what keeps autonomy expandable.
Evidence: the #29 auto-close incident,
`memory/working/2026-07-14-pr-transaction-discipline.md:9-18`; James's verdict.

## L11 — A green suite, a mocked connection, or hand-written SQL is not proof against the live constraint (2026-07-15 dream; extends L7)
Mocked DB connections don't enforce constraints or triggers; a 1264-passing suite proves
nothing about what the DB rejects. Before considering a DB-touching change done, **replay
the exact emitted statement against the real schema** (a rolled-back txn is fine). For an
additive `NOT NULL`-no-default column: update **every INSERT writer** (not just readers) in
the same change that applies the migration, or ship nullable + backfill + writers first,
THEN set `NOT NULL`. Never paper over it with a `DEFAULT` that would silently misclassify a
future write.
Evidence: `memory/working/2026-07-11-etf-phase1-build.md:14-45` (0037 applied while
`refresh_universe` still omitted `security_kind`; `ON CONFLICT DO NOTHING` does not suppress
a `23502`). Third instance of the L7 pattern.
*Amended 2026-08-14 — seven instances; see the amendment at the end of this file. Extended by
L19 (control) and L17.*

## L12 — A framing is a hypothesis, not truth: verify against the primary source before acting on it or writing it as fact (2026-07-15 dream; extends L1)
The source of a claim does not make it true — not a doc's tone, not a **WebFetch
summarizer's** result, not a backlog item's premise, not a majority of agents. Verify
against the primary artifact (raw docs / code / a direct query / the owner) before you act
on it **or write it into a hook header, a permission-model doc, or a memo as fact.** A
summarizer's *silence* on a question is not the docs being silent.
Evidence: decision-log `permission-friction-pack-2026-07-14` correction row;
`memory/working/2026-07-11-pmreview-hubs-cba.md:58-75` (2 of 5 "bugs" were stale premises).

## L13 — Reconcile a cross-agent disagreement on a capital-relevant number AT THE SOURCE; the majority can be wrong together (2026-07-15 dream)
Before writing any figure into a capital-relevant memo, look for a cross-agent disagreement
on a capital number and resolve it with a **direct query**, not by majority — independent
agents can share the *same* misread of an ambiguous input. **Do-not-overgeneralise:** the
lesson is reconciliation discipline on **shared, ambiguous inputs**, not "agents are
unreliable."
Evidence: `memory/working/2026-07-11-pmreview-hubs-cba.md:13-42` — 2 of 5 agents read
`cost_base_normal` (6978.23 **AUD** tax base) as USD÷24 → "HUBS −29%/stop-violated"; source
check: 6978.23 × 0.6450 ÷ 24 = 187.54 = `actual_entry_price`; position ≈ flat. Now
`risk-register.md` R10.

## L14 — Model A decay is RESOLVED *against* Model A; rule #11 is standing policy, not an open question (2026-07-15 dream; supersedes L6)
On 19,032 matured `signal_outcomes`, `corr(ml_prob, 21d) = −0.03` and STRONG_BUY returned
−0.09% at 21d vs HOLD's +5.07% (conviction inverted at the top) — **no usable edge** over
the held horizon. James **shelved the ML engine**; the product is the model-independent
moat. Rule #11 is now **standing/vindicated**, mechanically enforced
(`approved_for_allocation=FALSE` → allocator hard-fails). **Do NOT re-run the decay check**
(recency overfit, per `arbi-red-team`); it lifts only when a *new* model version passes a
**pre-registered decay bar (positive, monotonic conviction→21d return)** AND earns
`approved_for_allocation` — never on the basis of v1_5. The L6 open action
(`track_signal_outcomes`) is closed (PR #26 + PR #30).
Evidence: decision-log `decay-2026-07-11`; `risk-register.md` R1 (resolved);
`docs/model-a-decay-analysis-2026-07-11.md`. **Safety item — verbatim block below.**

## L15 — Merge order: harden the safety gate before the machinery that leans on it (2026-07-15 dream)
When a train contains both a safety-gate hardening and machinery that depends on that gate,
merge the hardening first. James ordered #35 (review-gate hardening) slotted **before** #31
(mission-control) for exactly this reason, and called the adjustment "the right standing
pattern."
Evidence: decision-log `merge-2026-07-14`.

## L16 — An authority-path deny rule must account for its OWN operational files before it ships (2026-07-15 dream)
A deny rule that guards `.claude/**` will, if unscoped, also deny the review-gate's own
marker (`.claude/.review-passed-*`) and `settings.json` itself — deadlocking every future
`.py` commit **and** the fix to the rule via any tool path. Before shipping an
authority-path deny, enumerate the review-gate's and the permission system's own operational
files and carve them out.
Evidence: run-ledger `permission-friction-pack-2026-07-14-lockout`; `risk-register.md` R5.

---

## Safety carried verbatim (2026-07-16 promotion — never summarised, `arbi-dream-policy.md`)

> **Rule #11 (CLAUDE.md, Non-negotiable rules):** STANDING (resolved 2026-07-11): do not use
> Model A output — signals, candidate scans, allocator runs, or new thesis proposals derived
> from it — as a basis for real capital decisions. … Keep this rule until a **new** model
> version passes a pre-registered decay bar (positive, monotonic conviction→21d return) AND
> earns `approved_for_allocation` — do not remove it on the basis of v1_5.

> **s766B personal-advice firewall (`.claude/rules/portfolio-conventions.md`):** Every CLI
> entry point and every job that touches portfolio data MUST call `_require_personal_use()`
> (CLI) or check `os.environ.get("ASXOS_PERSONAL_USE") == "1"` (jobs). This is the
> architectural firewall preventing personal-advice outputs (s766B Corporations Act 2001 /
> Westpac v ASIC) from being surfaced in a multi-user context.

> **Never lifts, at any autonomy PR (`roadmap-state.md`):** the personal-advice firewall
> (s766B) — arbi automates *what gets built*, never *what to trade*; the Model A quarantine
> (rule #11), now standing policy; and the irreversible tiers (5–7) stay
> `always_ask`/disabled regardless of track record. Autonomy expands only on the reversible
> dev/ops side.

> **Permission tiers (`arbi-permission-model.md`, via risk-register R5):** I5–I6 / P5–P6 are
> never standing. P6 (execution) is enforced by no execution tool ever being mounted. Every
> arbi-executed I5 write and I6 merge is **per-action** governor-instructed, not standing
> authority.

---

## Promotion 2026-08-14 — from dream candidates 2026-07-21, 2026-08-05, 2026-08-14

_Provenance: three candidates cleared in one batch after a month-long stall (last promotion
2026-07-16). Input SHAs pinned in each candidate's frontmatter —
`dream-candidates/2026-07-21-dream.md` (ef1d473 · d90e986 · 2184ea2);
`dream-candidates/2026-08-05-dream.md` (9d442de · d90e986 · d549688 · 2184ea2 · deea76a ·
5e33727 · 002b6c9 · c2a7f76 · a255537); `dream-candidates/2026-08-14-dream.md` (fad6215 ·
5c67fe0 · 65966d7 · 6360dbb · 657ae8b · 6fa2b21 · 3dbcaee · ee3ab4c · 6327a61 · 14b5cb7).
Gate: fresh-context grader (grader ≠ producer), tree `5ef9a71`, verdict PROMOTE-PARTIAL ×3;
boundary-adjacent `security-engineer` second review, fresh context, PASS-WITH-AMENDMENT on L23
and L25 (both BLOCK unamended — amendments A1–A3 / B1–B4 folded in below). Holdout evals and
`episode_score` trend **not run** — no ledger rows exist for this window (see L26). Rejected →
`rejected-candidates.md` RC5–RC8. James's merge is the promotion; arbi never self-approves._

## L17 — Recorded state is a hypothesis: re-derive "is live / is applied / is green" from a probe at the moment you rely on it (2026-07-21 + 2026-08-14 dreams; extends L12)
Seven independent instances of a document asserting state the live system contradicted: the 7a
Routine absent from the live trigger list while `roadmap-state.md` and `arbi-autonomy-loop.md`
both claimed it WIRED; DB migration count 94 against `REQUIRED_MIGRATIONS = 93`; CLAUDE.md's
enumerated sandbox test-gap list rotting 4→14→16 against 39/65 then 43/72 observed;
`target-architecture.md` asserting for a full day that `types.py` was "not on main" and the
prototype "not adopted" — falsified by `7aa8507` merged the day before; the Model A manifest's
`ACTIVE_REMOVE` heading claiming 25 rows deleted when a filesystem check found 10 removed and
11 present; `migrations/0039_agent_readonly_role.sql:1` still headed "DRAFT — NOT APPLIED"
though applied 2026-07-16; and `risk-register.md` R16 asserting hooks match on `".*"` when
`.claude/settings.json` carries five exact per-tool matchers.
**Lesson:** any "is live / is applied / is green / was removed" sentence must be re-derived
from a probe — a trigger list, a DB count, a test run, a filesystem check — at the moment it
is relied on. Its presence in a state doc, a manifest heading, or a PR description is a
hypothesis. **The fix shape matters:** annotate the false passage as superseded with its
date and superseding commit; never silently rewrite it (`target-architecture.md:1344-1353`
is the model).
**Do-not-overgeneralise:** this is about *ratified artifacts that instruct*, not about dated
records — a dated record is correct precisely because it is dated.
Evidence: run-ledger `full-auto-2026-07-15`; `decision-log.md:63` (governor ruling (c));
`model-a-reference-manifest.md:489-540`.

## L18 — Provenance is part of a record's identity: bypass-produced output never shares review footing with pipeline-produced output, and a fabricated record is worse than an absent one (2026-07-21 + 2026-08-14 dreams)
`agent_runs` #6/#7 were hand-logged via a direct MCP write after the `macro-economist` subagent
failed on dead frontmatter — mechanically valid on every post-hoc check, yet correctly HELD and
disclosed rather than reviewed alongside pipeline-clean #3/#4, because the validation a pipeline
runs *at write time* cannot be reconstructed afterwards (`macro_theses/service.py:124-129`
explicitly trusts log-time validation it never repeats). The same principle, inverted: SB0-01
**refused** to backfill the missing ledger rows — *"inventing an `episode_score` for an
unobserved run corrupts the exact series the promotion gate trends over"* (`risk-register.md:28`,
R6 reward-hacking).
**Lesson, three clauses:** (1) a "zero-cost review batch" that flattens unequal provenance is a
category error — disclose the bypass and review it separately; (2) a fabricated or backfilled
record is a **worse** defect than an absent one, because it corrupts a series rather than
leaving a visible hole; (3) when a broken pipe forces a bypass, rank **repointing the pipe**
above consuming its output — otherwise the bypass becomes the pattern.
**Live status at promotion (do not assume fixed):** the discovery-agent pipe is broken again.
Eleven files under `.claude/` pin `mcp__supabase-ro__execute_sql` while the connector resolves
in-session as `mcp__claude_ai_supabase-ro__*`, so all eight data-backed agents' declared DB tool
does not resolve. Fixing the *name* is not the fix — the connector has been renamed across
sessions before; the fix is a project-owned binding that survives reconnects. (Checked at
promotion: `unattended-guard.sh` is unaffected in the dangerous direction — its catch-all
`mcp__*` deny still swallows every renamed server, so the rename over-blocks rather than
under-blocks.)
Evidence: run-ledger `close-2026-07-21` (red-team CHALLENGE); decision-log 2026-07-21 standing
rule; `arbi-run-ledger.md:13-32`.

## L19 — A coverage claim requires an observed failure: mutation-test any test named regression / pins / guard before writing the claim (2026-08-05 dream; control for L11)
Six guards were mutation-tested by reintroducing each bug and checking whether the named test
failed. **Five were genuine; one was hollow** — and a separate pre-existing test proved hollow
too, having passed green for the entire life of the defect because its fake *raised* while the
real `_fetch_and_upsert` catches everything and returns a value. Neither was detectable by
reading; both were detectable in seconds by running. In the same session an eight-line comment
asserted a CWE-117 security property that nothing verified, and a request-side fix shipped with
zero coverage (reverting `eodhd_symbol()` left all 52 news tests green).
**Lesson:** any test whose name or docstring contains *regression*, *pins*, or *guard* must have
been **observed failing against the un-fixed code** before that claim may be written. Comment the
observation, not the intention. The adopted form to copy is
`tests/test_ingestion_news.py:487-491` — *"Mutation-verified gap: before this test, removing the
scrub entirely left all 57 tests green."*
**Not yet mechanical.** `docs/proposals/mutation-coverage-gate-2026-08-05.md` remains a draft
proposal; the review-gate hook has no mutation check. This lesson is prose until James rules on
that gate — which is itself the point of the L11 amendment below.
Evidence: `c2a7f76` (mutation results table); `002b6c9`.

## L20 — A gate must assert on the artifact, not on a job's status (2026-08-05 dream)
A ship condition, a runtime freshness gate, and a deadman all keyed off
`job_runs.status='success'`. One defect cleared all three, and a surface was marked SHIPPED while
rendering nothing for a month. **Two checks reading the same field are one check.** Corollary: a
job's success predicate must be able to return **False** — `is_ok=lambda r: isinstance(r, int)
and r >= 0` accepts every int, so 22 consecutive fully-failing runs each scored 100% healthy
(now fixed, with the anti-regression note at `jobs/ingest_news.py:234-239`).
**Do-not-overgeneralise — this is the amended form.** The candidate's blanket prescription
("require `rows_written > 0`") was **tried and rejected** for the news freshness gate with
reasoning at `asxos/brief/compose.py:528-532`: a row count on the *writer* is not a health
signal for a *reader* querying a different window. The durable rule is therefore: **the gate must
assert a property of the artifact that the defect in question would break** — a row count, a
join onto the populated table (as the portfolio gate joins `rebalance_runs`), or a degradation
sentinel — and *which* property is a per-gate design question, not a constant.
Evidence: `deea76a`; `d549688`; `docs/product/dark-launch-exit-plan.md:166-171`.

## L21 — Any fan-out whose agents mutate files must use worktree isolation or serialise (2026-07-21 + 2026-08-05 dreams)
Six mutation agents sharing one worktree contaminated each other's measurements: two wrote
backups to the same filename, two recorded a mid-mutation snapshot as the "pristine" hash, and
one produced a **false escalation** about a branch defect that did not exist. The per-mutation
isolated cycles were authoritative and all agreed; the shared-tree observations were not. The
converse worked: #59's test-break fix was verified in an isolated worktree so a concurrently
running audit's tree stayed clean.
**Lesson:** mutating fan-outs use `isolation: 'worktree'` or run serially, and use unique backup
filenames. Treat any measurement taken from a shared tree during concurrent mutation as
unreliable — including an escalation it produces.
Evidence: `docs/session-review-2026-08-05.md:236`; run-ledger `close-2026-07-18`.

## L22 — A pre-registered success criterion is what makes a null result interpretable (2026-08-14 dream)
The 0043 runbook committed **in advance** that *"revision growth may be zero when the provider
returns byte-equivalent rows"* and that what must be observed is that ingestion succeeds. So when
the scheduled `sync_prices` wrote 2,366 rows with the capture trigger live and `price_revisions`
stayed at **0**, the empty ledger read as **confirmation**. Without the pre-registration the same
observation supports both "the trigger works and nothing needed capturing" and "the trigger is
silently broken" — and the tiebreak is whichever the reader wanted.
**Lesson:** for any deadman, tripwire, drill, or containment whose healthy state is an empty
result, write down what success looks like **before** the observation. An unpre-registered null
result is not evidence in either direction.
Evidence: `docs/product/runbooks/price-revisions-0043.md:145-146`; `decision-log.md:67`;
mechanism at `migrations/0043_price_revisions.sql:194-196`.

## L23 — A permission delta is reviewed by enumerating the production side effects it newly reaches, by name — and enumeration is necessary, never sufficient (2026-08-14 dream)
arbi's own proposal justified a `Bash(gh run rerun:*)` allow-rule as **"read-triggering only."**
It is not: it re-executes any run up to 30 days old **with all secrets re-injected**. The review
that caught it did so by listing the live runs the grant could re-fire — `daily-brief` (prod DB
writes + email), `us-positions` (alert email), `weekly-research` (prod writes + EODHD quota) —
rather than reasoning about the verb's name. A second finding in the same pass: `$(...)` is not a
segment separator, so `gh workflow run backup.yml $(gh workflow run daily-brief.yml)` fired the
*denied* workflow and prefix-matched the settings rule with no prompt at all.
**Lesson:** for any permission delta, list the concrete production side effects it newly reaches,
by name, **before** writing the rationale. A rationale written from the verb is not a review.
**Enumeration is necessary and never sufficient:** a grant is judged by the widest capability it
confers, not by the runs that happen to exist on the day the list is written. `gh run rerun`
reaches every run inside its window **including ones not yet created**, so no enumeration could
have made it safe. A review that ends in a better rationale rather than a narrower grant has not
discharged the finding.
**An allow-rule is a convenience, never a boundary.** The boundary is the deny layer, the
always-on hooks, and branch protection (`arbi-permission-model.md` §Runtime enforcement honesty,
and its asymmetric-risk rule that hooks are deny-only). Denying the command-substitution shape
closed one bypass of a prefix-matched rule — it did **not** convert prefix matching into a
boundary, and nothing here licenses a wider prefix grant.
**Do-not-overgeneralise:** this changes no tier and grants nothing. It is a review procedure. The
permission model is unchanged: I5–I6 and P5–P6 remain never-standing.
Evidence: discharged by removing the rule from `.claude/settings.json` **and** hard-denying the
shape at `.claude/hooks/push-guard.sh:169-177`, with tests, before merge;
`tests/test_push_guard_hook.py:120-132`; `tests/test_claude_execute_harness.py:63-66`;
`decision-log.md:61`.

## L24 — Do not mint an identifier for work that existing identifiers already own (2026-08-14 dream)
`arbi-red-team` blocked `RENDER-RETIRE` as a canonical work-order ID: it had no route, no
dependency edge and no completion proof, which makes it a queue entry that can neither be
executed nor closed. Recorded instead as a **scope label** owned by existing orders `P1-03` and
`P3-01` — and `P1-03` then actually discharged it. The same pass blocked a subtler duplicate
queue: session task numbers written as canonical order when they are execution aliases (now an
explicit alias→work-order map at `roadmap-state.md:129-134`). Third instance, found at
promotion: the 2026-08-14 candidate itself cites a task `#16` that exists nowhere in the repo.
**Lesson:** a new identifier is justified only if it has a route, a dependency edge, and a
definition of done. Otherwise it is a scope label on an existing order — and a reference to an
identifier you have not verified exists is a fabricated dependency.
Evidence: `decision-log.md:65` corrections (a) and (c); `roadmap-state.md:125,165`.

## L25 — For a "remove all references to X" campaign the denominator is claim-driven, never name-driven — and the tripwire must be allowlist-difference, never count (2026-08-14 dream)
**(a) False negatives — the enforcer is invisible to the search.** Rule #11's mechanical
enforcement point (`asxos/domain/portfolio/build.py:209-214`, the
`is_active AND approved_for_allocation` fetch) contains **zero** Model A tokens in the gate
block, while its test file contains several. A token-driven retirement therefore deletes the
*test* and keeps the *enforcer* — or deletes the enforcer as "Model A plumbing" and leaves rule
#11 with no teeth and no failing test to announce it. Seven of the most load-bearing sites were
token-blind, and five further sites are **inverse-polarity bans** (E5–E8 in
`decision_engine/types.py`, E12 in `decision_engine/demo.py`) — code whose entire purpose is to
forbid Model A, which a "delete Model A references" pass deletes.
**Precision, re-derive before citing:** the *gate block* carries zero Model A tokens; the *file*
carries **8** matching lines at `d1b8420` — including one inside the `DO NOT DELETE` comment
that exists to protect it — and `tests/test_portfolio_build.py` carries **5**. The protective
paperwork moves the denominator it protects, so every number in this lesson is dated, not
current. Limb (b) eats limb (a).
**Correction to the cascade claim:** the E12→E8 cascade is real and reproduces — deleting both
`ConstraintResult(name="model_a_quarantine", …)` blocks makes `build_demo_brief()` raise
`ValueError: the blocking Model A quarantine constraint must pass exactly once` from
`types.py:635`. But *"nothing announces it"* is too strong: every quarantine test in
`tests/test_decision_engine_prototype.py` calls `build_demo_brief()`, so deleting E7/E8 to green
the demo also turns `test_explicit_model_independence_and_quarantine_gate_are_mandatory`
(`:380-400`) red. The ban survives **three** deletions, not two — and this lesson must not be
cited as evidence that the quarantine is undefended.
**(b) False positives — the count rises while the retirement succeeds.** The corpus went
989 → 1,166 → **1,278** matching lines (207 → 210 → 212 files) *because* the retirement's own
documentation writes about the thing removed. **A CI tripwire whose trip condition is "the token
count rose" would fire on the retirement's own paperwork**, and the cheapest way to make it green
is to disarm it. The assertion must be **allowlist-difference** based (a new unallowlisted file
appeared), never count-based — and the allowlist must cover the campaign's own artifacts.
**Scoping on (b):** "never count-based" is a design constraint on a *new* removal-campaign
tripwire, not a licence to disarm an existing check. **No tripwire may be deleted, weakened, or
left unbuilt before its allowlist-difference replacement is landed and observed firing on a real
violation.** A noisy check is a defect; no check is a regression.
**(c) A classification is not a plan.** An `ACTIVE_REMOVE` list is *what may be removed*; the
plan is the removal **order** plus the same-commit couplings, and only an execution pass produces
it — e.g. `models/*.pkl` and `tests/test_model_artifact_contract.py` are a same-commit constraint
(that test reads the real `models/` directory with pure stdlib, so `make check` goes red between
the two commits).
**The rule:** derive the denominator from the import and call graph and from *what asserts X is
live*, never from X's name. Grep produces the **seed set**, never the boundary. Treat any claim
that the seed set is complete as unsupported.
**Boundary note — this protects rule #11 and changes nothing about it.** *"Removing the code is
a superset of refusing to use it"* holds **only for Model A *consumers*** (`ACTIVE_REMOVE`). **It
is false for the `ENFORCEMENT_KEEP` set — E1, E5–E8, E12, E13–E15 and their tests — where removal
does not strengthen the quarantine, it destroys it.** No phase of the retirement may cite this
lesson as a reason to delete a site whose purpose is to forbid Model A; those sites are retired
only by a governor decision that retires rule #11 itself (ladder level 0).
Evidence: `model-a-reference-manifest.md:103-132, 167-193, 354-361, 366-377, 405-431,
489-540, 1406-1453, 1470-1477`; `production_gate.py:57-60`.

## L26 — Ledger rows are produced by a closing ritual and nothing else; a campaign that merges without `/arbi-close` breaks the audit trail by construction (2026-08-14 dream)
Second recorded occurrence, and the wider one. The first: both `arbi-run-ledger.md` and
`decision-log.md` *"ran dry after 2026-07-24 — the whole August arc went unrecorded, so the
compounding loop was broken for five sessions before anyone noticed."* The second: at promotion
the ledger's stated invariant — *"Every arbi run leaves a row here"* — **is false.** Last ledger
row `gov-01-2026-08-12`; last decision-log row `close-gov01-2026-08-12`; **both books stop at the
same commit**, with at least nine merged, CI-green, PR-bounded missions owed.
**The mechanism, named:** nothing but the closing ritual produces a ledger row. So *any* campaign
structure that merges work without running `/arbi-close` per unit breaks the trail by
construction — and stacked-successor branches (Amendment A) make this **more** likely, not less,
because successors proceed before predecessors merge. The failure is in execution, not in the
ruling, whose text preserves the obligation.
**Why it is urgent rather than tidy:** autonomy precondition (3) *is* a scorecard track record,
and the promotion gate trends `episode_score` over these rows. A holed ledger does not merely
lose history — it **blocks the promotion path.** This promotion batch was graded with holdout
evals and score trend recorded as *not run*, for exactly this reason.
**Do not fix it by backfilling** — see L18 clause (2). Fix it forward, and build the check: flag
any merged `claude/**` PR with no matching ledger row. Third manual rediscovery is the predicted
outcome otherwise; this promotion was the second.
Evidence: `decision-log.md:57`; `arbi-run-ledger.md:9, 13-32, 98`; `risk-register.md:28` (R6).

---

## Amendment to L11 (2026-08-14 promotion) — the pattern is not about Postgres, and it has reached seven instances

L11 records itself as *"Third instance of the L7 pattern."* Four more have landed, none of them
involving a DB constraint — which is the point. The family is **accepting a proxy for evidence**:

| # | Instance | The proxy accepted as evidence |
|---|---|---|
| 1 | Phase 1 governance transition (L7) | a mocked connection |
| 2 | hand-replicated SQL (L7) | hand-written statement order |
| 3 | migration 0037 / `refresh_universe` (L11) | a 1264-passing suite |
| 4 | `tests/test_ingest_news_job.py` threshold tests | a 57-passing suite whose fakes patched out the worker they claimed to test |
| 5 | `docs/market-trends-report-2026-08-05.md` §1, twice | reading the code, and probing the *parser* with synthetic input |
| 6 | GitHub run `31591940172` | a workflow run that concluded `success` — `claude-code-action` refuses to execute a modified workflow from a non-default ref and reports that refusal as a **SKIP inside a run that still concludes `success`**. For a workflow-file change, verify *step* conclusions and turn count, never the run's top-level conclusion |
| 7 | the 2026-08-05 dream's own `supabase-ro` claim | the absence of a repo file, treated as proof of non-provisioning — falsified by `docs/pr2a-supabase-ro-provisioning-plan-2026-07-05.md:31-38`, which records the connector provisioned in the claude.ai connector layer with live-fire Groups 1–2 **PASSED** |

**The recursive finding, preserved because it is the actual signal and must not be softened:** the
defect under investigation in instances 4–5 was *`job_runs.status` says a job ran; it does not say
work happened.* The investigator then committed the identical fallacy in prose — *reading says the
code would work; it does not say it did* — four times, **while writing standing rules against it.**
Instance 7 is the same fallacy committed by the dream that named it. A lesson can be correct,
specific, promoted, and auto-attaching, and still not bind, because **advisory memory does not gate
behaviour.** The open question that follows — whether L11/L19 get a mechanical gate or a fifth prose
copy — is a hook-and-settings change and is **James's alone**
(`docs/proposals/mutation-coverage-gate-2026-08-05.md`).

---

## Safety carried verbatim (2026-08-14 promotion — never summarised, `arbi-dream-policy.md`)

_Carried in full, unelided. The 2026-07-16 block abbreviated rule #11's evidence sentence with an
ellipsis and two of the three candidates in this batch paraphrased it; both are defects under
`arbi-dream-policy.md` ("It does not compress away safety"), corrected here._

> **Rule #11 (`CLAUDE.md`, Non-negotiable rules), quoted in full:**
> **STANDING (resolved 2026-07-11): do not use Model A output — signals, candidate scans,
> allocator runs, or new thesis proposals derived from it — as a basis for real capital
> decisions.** No longer "temporary/disputed": the decay analysis
> (`docs/model-a-decay-analysis-2026-07-11.md`) shows on 19,032 matured signals that v1_5 has
> **no usable edge** over the 5d/21d horizons this system holds for (`corr(ml_prob, 21d) =
> −0.03`; STRONG_BUY 21d −0.09% vs HOLD +5.07% — conviction inverted at the top). Keep this rule
> until a **new** model version passes a pre-registered decay bar (positive, monotonic
> conviction→21d return) AND earns `approved_for_allocation` — do not remove it on the basis of
> v1_5.

> **s766B personal-advice firewall (`.claude/rules/portfolio-conventions.md`, quoted in full):**
> Every CLI entry point and every job that touches portfolio data MUST call
> `_require_personal_use()` (CLI) or check `os.environ.get("ASXOS_PERSONAL_USE") == "1"` (jobs).
> This is the architectural firewall preventing personal-advice outputs (under s766B Corporations
> Act 2001 / the Westpac v ASIC boundary) from being surfaced in a multi-user context.

> **Permission tiers (`arbi-permission-model.md`):** "I5–I6 are irreversible → always
> human-approved, never standing, regardless of track record." "**I5–I6 and P5–P6 are never
> promoted to standing** — they are permanently `always_ask`/disabled/not-held by design."
> "**Never promotable:** I5–I6 (irreversible infra), P5 (capital-policy change — draft-only
> forever), P6 (execution — not a tool arbi holds). No track record unlocks these."

> **Nothing in this promotion lifts, weakens, or reopens any of the above.** L25 documents how a
> retirement campaign could *accidentally* delete rule #11's enforcer; it exists to prevent that,
> and its boundary note explicitly forbids citing it to delete an `ENFORCEMENT_KEEP` site. L23 is
> a review procedure and grants no tier. The P1 Model A retirement **strengthens** the quarantine
> and does not lift it.
