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

---

## Promotion 2026-08-22 — from dream candidates 2026-08-17, 2026-08-18, 2026-08-22

_Provenance: three completed candidates (`completed: true`) graded in a context that did
not produce them. Input SHAs are pinned in each candidate frontmatter. Gate:
`rubrics/arbi-dream-promotion.md` — improve-one ✓ (state accuracy, repeated-mistake
reduction, blocker prioritisation, scope control, handoff quality); regress-none ✓
after the security-engineer amendments below. Boundary-adjacent second review
(`security-engineer`, fresh context): PROMOTE-WITH-AMENDMENT on 17.2, 17.6, 17.10,
17.12, 22.1, 22.2 (four would BLOCK unamended — amendments folded in). 18.3 PROMOTE.
Holdout evals and `episode_score` trend **not run** (same honesty as the 2026-08-14
batch; L26). 18.4 lands here, not in `project-facts.md` (that file is a pointer index
with no original content). 17.3 → L19 amendment; 17.4 + 18.6 → L17 amendment;
17.8 → L22 amendment; 17.10 → L23 amendment; 17.11 → L26 amendment; 18.5 → L11
amendment. James's merge is the promotion; arbi never self-approves._

## L27 — A destructive cleanup derives its targets from an enumeration, never from a class pattern; a flag whose only job is to defeat a safety interlock does not belong in the command (2026-08-17 dream)
A cleanup written to remove **one** stopped agent's worktree matched every `agent-*`
worktree and force-removed a **live, locked** builder worktree with `--force --force`.
The second `--force` exists only to override the lock; the lock exists only to stop
removal of an in-use worktree. Recovery happened because the builder had been told to
commit incrementally — luck, not a control in the cleanup path.
**Three defects, separable:** (a) the denominator was a name pattern, not an identity
(L25's seed-vs-boundary rule, in a *destructive* context); (b) the interlock was
pre-overridden, not reached after a refusal; (c) there was no pre-flight print of
what would be removed.
**Lesson:** a destructive command derives its target list from an explicit enumeration
of identifiers, prints that list before acting, and carries no flag whose sole
function is to defeat a safety interlock. If the interlock fires, that is the answer.
**With L21:** worktree isolation creates a new destructive lifecycle. Promote them
aware of each other.
**Provenance:** session evidence, not in the 2026-08-17 handoff or ledger. A dream
cannot amend a level-5 row.
Evidence: `dream-candidates/archive/2026-08-17-dream.md` L-cand-17.1.

## L28 — "Independent review" is a property of the reviewer's relationship to the work, not of how many passes were run (2026-08-17 dream)
P2-04's `arbi-red-team` vet ruled that a builder's own extra review passes cannot
satisfy `independent_of_author: Literal[True]`. A fresh zero-ownership reviewer
returned PASS-WITH-FIXES and found a real gap: the advice-vocabulary grep omitted
`allocate` and missed plurals.
**Lesson:** a contract field that asserts a *relationship* (grader ≠ producer,
arms-length, `independent_of_author`) is satisfied only by **changing who does the
work**. Extra author-passes increase confidence and leave the asserted property false.
The 2026-08-17 note that P2-02 "preserved independent review in separate documented
passes" is a record of a deviation, not precedent.
**Boundary note:** the s766B firewall is `_require_personal_use()` /
`ASXOS_PERSONAL_USE=1` and `ASXOS_PORTFOLIO_BRIEF_ENABLED` (portfolio-conventions
Part 0 Q1). The advice-vocabulary grep is a **template tripwire**, not "the one
control guarding the s766B boundary." This lesson is only about who satisfies
independence. It does not promote the grep to firewall status and does not license
weakening, deleting, or relying solely on either control. P5–P6 stay never-standing.
Evidence: `decision-log.md` 2026-08-17; `session-handoff-2026-08-17.md`.

## L29 — Merge-train mechanics: `ready` re-triggers CI, a stacked PR is not auto-retargeted, and a strict up-to-date rule costs N rebuilds (2026-08-17 dream)
Three platform facts, none guessable from the verb: (a) `gh pr ready` re-triggers CI,
so `ready && merge` races its own checks — `--admin` bypasses staleness, not a check
that has never run; (b) GitHub does not auto-retarget a stacked PR when its parent
squash-merges unless the parent branch is deleted — flip `--base main` first or the
merge lands in the parent; (c) a strict up-to-date ruleset makes every merge re-stale
every other open PR.
**Procedure:** flip every stacked PR to `main` first; then oldest-first
`ready → wait-for-green → merge`; budget N rebuild rounds.
Evidence: `session-handoff-2026-08-17.md`; ledger `campaign-2026-08-17` cost_efficiency 3.

## L30 — A positive hook result is evidence about the one guard observed; authority-guard matches command text, and #158 is the authorized false-positive cut (2026-08-17 + 2026-08-22 dreams)
`(a)` `authority-guard.sh` holds inside an isolated worktree because it canonicalises
payload `.cwd`. That is **not** "the hook layer holds in a worktree." The other
path/branch-anchored hooks were later found failing open in exactly that fan-out and
were fixed separately (`tests/test_hook_worktree_scope.py`).
`(b)` The same mechanism is text-based, so it false-positives on read-only commands
whose *text* names a guarded file. Task #18 ended 2 of 11 drafts applied, 9 DENIED —
those write denials are the product. The `grep`/`cat` denials are friction.
**Live deny after #158:** deny iff (redirect target is authority) OR (`util_verb` ∧
`authority_ref` on the command after scrubbing `/dev/null` and `/dev/stderr`). Bare
`>>?` is not a `util_verb`. This lesson licenses **that split and no further
write-path narrowing.** `unattended-guard.sh` is unchanged and remains the I5–I6
unattended floor. The attended un-deny of `settings.json` / `hooks/` / `CLAUDE.md` is
not standing and does not apply under `ARBI_UNATTENDED=1`.
**Do not cite "grep/cat denials are friction" to strip `util_verb`∧`authority_ref`.**
`cp`/`mv`/`tee` of an authority path is not a false positive. Text matching is not
replaced by intent analysis.
Evidence: `#112`; `#158`; `.claude/hooks/authority-guard.sh`; `tests/test_cursor_i56_hooks.py`.

## L31 — Three verdict vocabularies coexist; each names a different object, and a new one ships with a negative test (2026-08-17 dream)
B.3 decision-state answers *what James might do about a position*. P1-04 review
states answer *whether the evidence is sayable*. Results-review
(`complete|revise|abstain`) answers *whether the artifact is finished*. B.6 forbids
a conversion function between the first two; the third is a third altitude, not a
rival. `complete` is the most authorising-sounding English word in its set and still
authorises nothing.
**Lesson:** any new verdict vocabulary ships, in the same change, with the negative
test that pins it away from every existing one. Prose cannot enforce
non-promotability into an action vocabulary.
Evidence: `contracts.ResultsReviewOutcome`; `test_authored_presentation_uses_neither_ruled_vocabulary`.

## L32 — A repeatedly-surfaced trivial action that never lands is a routing defect, not a diligence defect (2026-08-17 dream)
Two dark-launch expiries were carried by five consecutive `arbi-red-team` vets and
still needed their own PR (`#120`) to become a `james-inbox.md` row. A vet's
carried-forward observation has no owner, no queue entry, and no definition of done.
Re-surfacing is detection; the row landing is remediation.
**Lesson:** an observation a vet carries forward must terminate in a durable row
before the mission it was raised in can close — the mission writes the row, or the
finding is not discharged. Being trivial is exactly what keeps it off a code-mission
task graph.
Evidence: `james-inbox.md` via `#120`; five vets 2026-08-13 → 2026-08-17.

## L33 — Deleting a writer changes the backup classification of everything it wrote, in the same change (2026-08-17 dream)
`P1-02` (`#100`) deleted the `signal_outcomes` writer and the maturation job. From
that commit, 60,072 `signal_outcomes` rows and 64,189 `signals` rows were no longer
re-derivable, while `backup_irreplaceable.sh` still called `signals` "re-derivable"
and never named `signal_outcomes`. The exposure ran until the 2026-08-17 archive.
**Lesson:** "re-derivable" is a claim about a **live pipeline** and expires when that
pipeline is deleted. Same-change question: *what did the deleted code write, and does
anything still claim it can be regenerated?*
**Boundary note:** this is backup classification of rule #11's *evidence*, not a
change to rule #11. The quarantine stays standing. It does not license restoring a
`signals` / `signal_outcomes` writer, re-running v1_5 decay, or using the archive as
a live signal source for any capital decision (reading that archive is reading Model A
output).
Evidence: `#100` (`6fa2b21`); `#112`; `session-handoff-2026-08-17.md`.

## L34 — An un-enacted lesson is not a control: the promotion backlog is itself a risk surface (2026-08-17 dream)
L17–L26 sat drafted, graded, and security-reviewed in `#110` / `#125` while
`approved-lessons.md` still ended at L16. In that window the same session minted
"Amendment B" while an un-enacted Amendment B already existed — the exact defect L24
names, with L24 written and waiting. A payload is a document awaiting a merge;
`approved-lessons.md` is what a session actually reads.
**Lesson:** the cost of a stalled promotion is not lateness — the lesson provides
**zero protection** while it waits, and only James's merge ends the wait. The correct
response to a stalled promotion is to close it, not to consolidate more on top of it.
If the batch is too large to review in one sitting, the fix is a smaller unit, not a
weaker gate.
**Live status at this promotion:** L17–L26 *are* enacted (`#125`, 2026-08-18). This
batch is the remaining 17.x / 18.x / 22.x backlog that 17.13 predicted. The gate
stays; latency was the defect.
Evidence: `#110`; `#125`; L-cand-17.13.

## L35 — Run the path against production before you build on it; a review loop cannot see absent data (2026-08-18 dream)
One live SQL query killed work order F5a after it had survived planning as the
largest buildable item: `holding_lots` has **zero disposed rows**, and **nothing in
the repository writes `disposed_at`** (many readers, zero writers — 26 non-test
mentions, 0 assignments outside test fixtures). Six earlier units had passed full
review loops and shipped inert. Review-after-build audits correctness; only running
the path audits whether there is anything to be correct about.
**Lesson:** before a work order is sized, run its actual read path against production
and record the row count in the work order. This is the input-side twin of the
output-side standing condition that a finished feature must render something.
Evidence: `migrations/0001_initial.sql`; `asxos/domain/tax/positions.py`; F5a kill.

## L36 — A fix is not safe because the defect it targets is real (2026-08-18 dream)
Repairing a broken control **changes the threat model of everything downstream**,
because the broken control was load-bearing as a *suppressor*. The R1 job-failure
banner fix was aimed at a real defect and still carried: (a) a 27-hour Friday hole
in a Sun–Thu brief that would have dropped `backup_irreplaceable` failures; (b) an
egress path (`fallback_email.py`) that was survivable only because the broken filter
never matched — widening the window made a bearer-token-shaped `error_message`
email-reachable. Both fixed pre-merge in `#132` (redaction before truncation).
**Lesson:** the review question is not "is this fix correct?" but **"what was
protected by this thing being broken?"**
Evidence: `#132`; `asxos/brief/compose.py` `_job_failures`; `fallback_email.py`.

## L37 — An agent that cannot verify must name the failure and stop; a plausible zero is worse than a refusal (2026-08-18 dream)
`sector-screener` twice declined to emit an honest-looking zero when it could not
reach the database. Those refusals surfaced a harness defect (stale
`mcp__supabase-ro__execute_sql` vs live `mcp__claude_ai_supabase-ro__execute_sql`)
that a zero would have laundered into a claim about the ASX.
**Lesson:** an agent that cannot verify its own inputs must name the failure and
stop, and must not emit a value whose shape is indistinguishable from a real result.
**"0" and "could not measure" must never render the same way.** This does not license
opening a write-capable SQL path or substituting recollection / Model A for the
missing probe.
Evidence: eight discovery/analysis agents' frontmatter vs live connector name.

## L38 — "No writer anywhere" is a different failure class from "no data yet" (2026-08-18 dream)
`disposed_at` has readers and no writer. "No data yet" means the recording path
exists and a person has not used it. "No writer anywhere" means a decision may
already have been taken and nothing could have written it — that routes to **code**,
not to another ask. The probe that separates them is one grep for a write site.
**Lands here, not in `project-facts.md`:** that file is a pointer index with no
original content; this is a durable distinction without a better home.
Evidence: L-cand-18.1 box (0 write sites for `disposed_at`).

## L39 — An authorisation changes intent; only a config change alters capability (2026-08-22 dream)
James granted permission three times in one session (blanket override, then a named
file, then "this one time"). All four subsequent attempts were refused — twice by
`permissions.deny` before the hook, twice by `authority-guard.sh`, including a `cp`
that only *backed up* `.claude/settings.json`. A sentence in a conversation does not
edit configuration.
**Lesson:** a spoken grant is Level 0 *intent*, not a config write and not a window
grant. It never edits `permissions.deny`, hooks, or settings; never promotes I5–I6
or P5–P6 to standing; never lifts s766B, rule #11, or migration 0042. After a grant,
probe the **already-configured** capability on the narrowest *reversible* action,
then stop and report. It does not license attempting a reserved surface, a merge, or
treating a refusal as a defect to bypass. `#158`'s attended un-deny is a **merged
config change**, not a verbal grant taking effect.
Evidence: `docs/proposals/claude-config-patches-2026-08-22/README.md`; `#158`.

## L40 — A text-matching guard generates false positives; #158 is the authorized cut, not a licence to keep cutting (2026-08-22 dream)
Pre-#158, `authority-guard.sh` treated any redirect as a write verb and blocked
commands that wrote nothing to an authority path. `#158` Fix A+B is the authorized
false-positive reduction.
**Live rule (do not promote the pre-#158 mechanism):** deny = (redirect-target is
authority) OR (`util_verb` ∧ `authority_ref`) after scrubbing `/dev/null` /
`/dev/stderr`; no bare `>>?` in `util_verb`. Remaining false positives are friction;
the write denial is the product (same split as L30). This does not license dropping
`util_verb`∧`authority_ref`, treating `cp`/`mv`/`tee` of an authority path as a
false positive, replacing text matching with intent/effect analysis, or changing
`unattended-guard.sh`. FN-avoidance is not replaced by intent analysis.
Evidence: `#158`; `tests/test_authority_guard_hook.py` Fix A+B cases.

## L41 — Attack your own validator before trusting it; reading it is not the same test (2026-08-22 dream)
`scripts/roquery.py`'s SQL screen looked right when read. Attacking it found four
bypasses, including `SELECT * INTO` (leading verb still `select`) and `nextval()` /
`setval()` (Postgres read-only transactions **permit** sequence advancement — the
docstring's "convenience over a server guarantee" layering is inverted for that
case), plus `pg_read_file` / `lo_export`. Same pass: psycopg2's default cursor
materialises the whole result before `fetchmany`, so `--max-rows` was decorative.
**Lesson:** a screen whose claim is "rejects writes" must be mutation-tested with
adversarial statements, not reviewed by eye. Same family as L11/L19, different
mechanism: here the human reads their own regex and sees what they intended.
Evidence: `tests/test_roquery.py::test_bypasses_found_by_adversarial_testing_are_refused`.

## L42 — A run-history gap is not a failure until you have read the schedule (2026-08-22 dream)
Two independent readers invented opposite defects from the same `daily-brief` run
list. The cron is `30 20 * * 0-4` (Sun–Thu). Reconciled against the schedule: all
ten scheduled days ran green; zero misses. Absence of an artifact is evidence only
against a known expectation. The second error happened *during a correction*.
**Lesson:** before calling a gap a miss, open the schedule. A correction is exactly
when your own date arithmetic goes unchecked.
Evidence: `.github/workflows/daily-brief.yml`; `roadmap-state.md` 2026-08-22 wake.

## L43 — Buildable and closeable are different properties (2026-08-22 dream)
`SB4-01` was technically unblocked and was parked: the packet places it in wave 4
while the programme is at wave 3, and Amendment E bars closing a fixture-only row
when zero emitted arbi briefs exist in history. The suite would have been built and
then parked.
**Lesson:** before starting a unit, check not only whether it can be built but
whether its completion condition is reachable with the evidence that exists. A unit
that cannot produce a closeable row is work that will need doing twice.
Evidence: `session-handoff-2026-08-22.md`; Amendment E; `scripts/check_ledger_coverage.sh`.

## L44 — The Nth duplicate is where consolidation happens; a written justification for keeping it is usually wrong on the mechanics (2026-08-22 dream)
`leaves()` had been implemented three times and was consolidated. Hours later,
`context.py` became the fourth byte-identical `ConfigDict(extra="forbid", frozen=True)`
with a docstring justifying the copy — and the justification was wrong (pydantic
resolves `model_config` through the MRO; a subclass may override it).
**Lesson:** when a duplicate carries a written justification, check the justification
against the framework's actual behaviour before accepting it. The cost of N copies is
that a later strengthening must be applied N times, and the missed copy is a silently
weaker freeze.
Evidence: `asxos/secondbrain/_schema.py`; `docs/product/mission-context-schema-freeze-2026-08-22.md` §1.

## L45 — An ahead-count is not a staleness check (2026-08-22 dream)
A session ran `git rev-list --count origin/main..HEAD` (ahead) at least four times
and never `HEAD..origin/main` (behind). Two commits already on `main` before the
session's first commit (`#149` closed the `/pm-review` Model A leak in *two* agents;
`#150` closed two inbox rows) were escalated all day as open, and a drafted patch C
would have **regressed** the better fix.
**Lesson:** a one-directional ahead-count reports a branch as healthy no matter how
far the base has moved. Staleness is `HEAD..origin/main`. Re-read `main` before
escalating a hazard or drafting a fix for it.
Evidence: `#149` (`ff377ef`); `#150` (`d15266f`); L-cand-22.7.

---

## Amendment to L17 (2026-08-22 promotion) — dispatch-time probes, and re-count every "N things do X"

**Dispatch (from 17.4).** L17 is about claims. The cheap application is *dispatch*: a
stacked mission pre-flight-enumerates every assumed artifact (branch, merge state,
document, table, credential), probes each, and writes the probe result into the
report. A failed assumption caught at dispatch costs a re-plan; the same assumption
caught at claim costs the mission.

**Counts (from 18.6).** Any claim of the form "N things do X" is re-counted from the
artifact immediately before it is written — including a count you produced earlier
in the same session. When the count comes from a runtime, name the runtime in the
same sentence. Direction survives; numbers do not. A correct measurement of a
different interpreter is not a property of the code.

---

## Amendment to L19 (2026-08-22 promotion) — mutate the hazard, not a field

L19 requires an observed failure. **17.3:** what you make fail must be the *hazard*
— a mechanism by which two correct-looking runs disagree — not a field value. A hash
test that only proves "change a field, the hash changes" is worthless. P2-05's
mutations (hidden wall-clock read; one Decimal written two ways; mapping insertion
order) found that pydantic's JSON render preserves a Decimal's written exponent:
the presentation digest held while frozen `artifact_sha256` / `case_sha256` moved.
Prove absence of a wall-clock read with an AST walk, not a grep — package docstrings
name `datetime.now(UTC)` in order to say they never call it (L25(b) as test design).

---

## Amendment to L22 (2026-08-22 promotion) — a run on the wrong class of input leaves a prediction untested, not passed

L22 covers the null-result case. **17.8** covers the wrong-population case. When a
pre-registered prediction is about a *class* of input, a run on a different class
neither confirms nor falsifies it — record **"untested"**, never "passed", and state
the mechanical reason the classes cannot be silently conflated. P2-05's synthetic
`hashed_fixture` cannot be `real` (`AcquisitionPath` +
`validate_fixture_never_real`); the matrix prediction about the first *real* results
review therefore stands untested even though the artifact returned `complete`.
Do not launder a fixture result into a capability claim.

---

## Amendment to L23 (2026-08-22 promotion) — the useful answer to a broad loosening is the narrow alternative; lift-and-reinstate is fail-open

When the governor asks for a blanket bypass or "unblock and reinstate at end of
session," the useful draft is surgical grants with an L23 by-name enumeration — not
the blanket. Lift-and-reinstate is fail-open: re-arming does not undo what crossed;
the exit depends on the agent the window constrains; the catching layer is off
precisely during peak activity.
**This changes no tier and grants nothing.** I5–I6 and P5–P6 stay never-standing
(`always_ask` / not-held), including inside any window. The un-liftable floor is
that **full never-standing set** plus s766B, rule #11, and migration 0042 — not a
four-item subset. A fail-closed window grant (James-placed, named-stops-only, never
`"all"`, self-expiring, ignored for un-liftable stops) is a *drafted alternative*,
not applied, not standing, and not a reason to honour a spoken bypass.

---

## Amendment to L26 (2026-08-22 promotion) — when an audit control is found broken, measure the downstream consumer first

L26 predicted the third rediscovery. **17.11:** the first question is not "how do we
fix it" but **"what has been consuming its output, and what did that consumer
conclude while it was degraded?"** The ledger gap reached 19 of 22 uncited
`claude/**` PRs and had already forced the 2026-08-14 promotion to record holdout
evals and `episode_score` trend as NOT RUN. `scripts/check_ledger_coverage.sh`
reports and cannot write a row (L18 clause 2). A missing row looks cosmetic; a
promotion gate that silently graded "evals: not run" is not.

---

## Amendment to L11 (2026-08-22 promotion) — instances 8–9

| # | Instance | The proxy accepted as evidence |
|---|---|---|
| 8 | 2026-08-18 hand-transcribed SQL (18.5) | a paraphrase of a query, run against production, treated as verification of the code path. Extract the literal statement from the source (or the composed string logged at runtime). A lesson scoped only to the subsystem where it was found (Phase 2a governance-trigger SQL) gets re-learned in the next subsystem. |
| 9 | 2026-08-22 `/pm-review` hazard restated as open (22.7 / RM-1) | a stale *state* claim that was once true (`#149` had already closed it). A wrong number stays wrong; a stale state claim decays on its own. Re-read `main` (`HEAD..origin/main`) before escalating. |

---

## Safety carried verbatim (2026-08-22 promotion — never summarised, `arbi-dream-policy.md`)

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

> **Nothing in this promotion lifts, weakens, or reopens any of the above.** L28 does not
> promote a grep to firewall status. L30/L40 license only the #158 deny split. L33
> classifies evidence, it does not restore a writer or feed the archive into a capital
> decision. L39 treats a spoken grant as intent, not config. L23's amendment grants
> no window and no standing I5/I6.

---

## L46 — A one-line FYI is not a wake; re-rank before you plan a PR (2026-09-14)
James said "Supabase is now Pro, FYI" and I drafted a PR around it — four doc-line fixes and
a spend-cap recommendation — while the 09-10 handoff's *blocking* residue and a live §7
incident sat untouched, and while James had set the session to read-only. `arbi-red-team`
(on Fable) called it: recency overfit, cleanup dressed as progress, and relitigating a §2
number he had already declined to set. **Lesson:** the last thing said is input to the
ranking, not a substitute for it. Before any PR that did not come from the queue, read
`roadmap-state.md`'s ranked block and the newest handoff's residue list; if the item is not
there, it goes there — not into a branch. And a plan that came from the last chat line is
exactly the plan to red-team first; it cost one agent run and saved a James-blocking PR.
Source: `decision-log.md` 2026-09-14 row 2; `AGENTS.md` §7 "Incidents before features".

## L47 — Source per claim, not per paragraph (2026-09-14)
Having been caught fabricating once this session (`decision-log.md` 2026-09-14 row 1), I then
quoted three specifics from the bundled `claude-api` skill and one from my head — in the
same sentence, at the same confidence. The skill-sourced ones held on re-check
(`shared/models.md:73,76`); the head-sourced one ("`claude-opus-5[1m]` silently falls
back") did not survive and was withdrawn. The red team correctly treated all four as
suspect because it could not tell them apart, and neither could James. **Lesson:** every
specific carries its own source or its own hedge. A sourced claim next to an unsourced one
lends the unsourced one credibility it has not earned — that is how a fabrication hides.
`AGENTS.md` §7 "Honest sample" applies to sentences, not just briefs.
Source: `decision-log.md` 2026-09-14 row 2.

## L48 — A carried-forward item is a claim; carrying is not verifying (2026-09-14)
Three items forwarded unchanged for weeks were all wrong at the point of action, in the same
way: a rule that had rotted into a description of a system that no longer existed.
`asxos/backlog.py`'s `DENIED_FILES` was handed over as "three deleted `arbi-*` docs"; measured,
**17 of its 30 entries** named files that do not exist, and the consequence was that the
`backlog-roll` lane had nothing it was permitted to build — which every prior test pin recorded
as `picked == []` and which was read as a property of the backlog rather than of that list.
Dark surfaces #1 and #3 were waiting on, respectively, a job James had ratified DELETED on
2026-08-19 and a gate the doc called "not yet plumbed" that had been plumbed all along.
**Lesson:** the expiry machinery worked — it fired on 2026-08-31 — what failed is that nobody
ruled, and each carry made the claim look more settled. Re-measure a claim that has been
carried more than twice *before* acting on it, not after. The sharpest case this session was
item 10: "the thesis-in-the-same-sitting pairing item named in the 09-10 handoff" is not in the
09-10 handoff, occurs in exactly two places repo-wide, and neither defines it.
Source: `decision-log.md` 2026-09-14 (wake row); `session-handoff-2026-09-14-3.md`.

## L49 — An agent lane's findings age against the session that produced them (2026-09-14)
`#259`, the toolwatch lane's first real report, measured the `claude-code-action` pin at Claude
Code 2.1.251 and recommended a 19-release jump to gain two capabilities. **#214 landed CC
2.1.269 hours later in the same merge-train session**, so both were already in the bundle before
anyone read the report. Adopting it verbatim would have produced a PR whose stated rationale was
false. What actually remained was real and smaller: *using* the flag the bump had already
delivered. **Lesson:** re-probe a lane's premise at the primary source before adopting it,
especially when the lane fired and the change landed on the same day. The lane is not wrong —
it was right when it ran.
Source: `decision-log.md` 2026-09-14 (wake row); PR #263.

## L50 — A test that passes on its first draft, where it was meant to be red, proves nothing (2026-09-14)
Writing the coverage a `security-engineer` review asked for on #228's builder hunks, the first
draft of both tests passed while exercising neither line. One reused an `evidence_id` that the
dedupe guard (itself added by the 2026-09-07 live run) then used to skip the entire branch; the
other used the default CBA fixture, which is 3.5x price-detached, so the assertion never reached
the branch under test. A green run said nothing; **coverage output caught it.**
**Lesson:** for a test written to pin new behaviour, confirm it fails without the change. When
it cannot be run red — because the branch already carries the fix — read the coverage of the
specific lines instead of trusting the pass. This is the same failure class as the Phase 2a
governance finding already recorded in `portfolio-conventions.md`: a test that cannot fail is
not a test.
Source: `decision-log.md` 2026-09-14 (wake row); PR #266 review comment.

## L51 — A scheduler's "succeeded" is not evidence the session did anything (2026-09-15)

Two scheduled fires of a Routine created from an arbi session came back `ROUTINE_RUN_STATUS_SUCCEEDED`
having done nothing: the trigger stored no repository (`sources: []`), so the session woke
empty, wrote a paragraph and went idle. The only thing that showed it was a ledger issue on
which every fire must post a START comment as its first act — absence of START against a
scheduler success is the detector, and it fired on the very first night. Three corollaries
learned at ≈US$1.40 in four sessions: (1) bind routines to what you have already proven
(a repo-attached session with the tools) rather than to a mechanism whose config you have
not read — `sources: []` was visible in the trigger record before the first fire; (2) a
verification prompt that asks for token-shaped actions is refused as injection by the very
rule the preamble carries, so verify with the routine's own prescribed actions only; (3) a
session with no human will stop to ask unless its instructions say there is no one to ask.
Fix the instruction first, then test once — this session tested first and paid for it.

## L52 — A backlog row names a file; the defect may live in an immutable artifact (2026-09-16)

E-11 said "fix the false pip-cache comment in `full-check.yml`". The false sentence was in
commit `c35d435`'s message and PR #168's body — neither editable — while the file comment
only carried the implication ("worth a step here at all"). Three prior attempts and one
roadmap line ("#184 fixed it") had all worked from the row's wording rather than from the
artifact; #184's actual patch to the file was a one-line quote normalisation. Before
building a row whose premise is "X is false", fetch X at the commit the row cites (the
GitHub API can; a shallow clone cannot — `git blame` here bottoms out at the clone root)
and quote the false text. If it is not in the file, the fix is the residue plus an honest
close, not a rewrite. The picker cannot tell the difference, so the row's close note must.

## Authority pointers (folded in from the retired `authority-lessons.md`, 2026-09-10)

This section replaces the old separate pointer index. It holds **no original content** — it
points at the real authority so there is exactly one source of truth. The real files win over
this list.

- **The operating contract — authority, James's domain (§2), reversal-cost classes, landing
  work, delegation, the source-of-truth ladder (§10):** `../../../AGENTS.md`
- **Non-negotiables + rule #11 (Model A quarantine), domain facts, schema:** `../../../CLAUDE.md`
- **The Output / non-negotiable firewall:** `../north-star.md`
- **Portfolio decision-support charter + capital mandate:** `../portfolio-manager-charter.md` + `../portfolio-policy.md`
- **Personal-advice firewall + portfolio invariants:** `../../../.claude/rules/portfolio-conventions.md`
- **Specialist roster and the owner→agent table:** `../../../.claude/agents/README.md`

If a lesson in this file ever conflicts with any file above, the file above wins: flag the
lesson stale and correct it in place with a `decision-log.md` row (`AGENTS.md` §10).

## 2026-09-16 — A pre-registration is only as good as the inputs it can actually reach

The sealed value-to-price test was built carefully: append-only seal, survivorship-correct
membership, a whole-ladder monotonicity test chosen specifically because Model A's failure
was an inverted ladder under a strong top bucket. All of that was right, and none of it
mattered on the first run, which hard-failed at the first cutoff for want of a risk-free
rate.

`market_context_current` had looked like a rate series for as long as anyone had needed one.
It is a daily-forward ingest: 55 rows, all from 2026-07-03, carrying 3 distinct values of a
monthly print it was forward-filling. `ke = risk_free + β·erp` is the discount rate in a
residual-income model, so the model could not be replayed at any historical cutoff — it had
never been testable, and the empty `research_runs` table was a symptom of that rather than of
neglect.

Three things to carry forward.

**The hard-fail earned its keep.** `CLAUDE.md` #10 exists for exactly this. A graceful
warning here would have valued 1,774 securities against today's rate at a 2025 cutoff,
producing a plausible number, a green run, and look-ahead bias inside a pre-registered test.
The loud failure is what made the gap findable.

**Check that a test CAN run before concluding anything from the fact that it hasn't.** #299
correctly established that `research_runs` was 0 while the model emitted target prices for 23
securities, and read that as a governance gap. It was also a capability gap, and the second
reading only appeared when the test was actually dispatched. Running the thing is a different
kind of evidence from reasoning about it.

**Read the constant before designing around it.** When the backfill stopped at 2026-08-01 I
flagged that a six-week-lagging monthly series looked unsuitable as a live discount rate, and
started designing a two-source rule to accommodate it. `capm.RISK_FREE_LABEL` already said
the daily table was "a MONTHLY series carried forward, not a daily 10-year ACGB quote" — the
same series. The concern was wrong, the two-source design was unnecessary, and one paragraph
of existing documentation would have prevented both. Verified rather than assumed: both
sources read 5.015 on 2026-09-16.

The loop's headline result (verdict `null`, demotion) is real and pre-committed. But the
finding that paid for the day was the one that got in the way of producing it.

## L53 — A guard you have not opened is not a guard you know is missing (2026-09-17)

L52 said: verify a backlog row's premise against the artifact before building. One day later I
filed a row that broke the same rule, and only caught it because I opened the code before
starting the build rather than after.

**What happened.** The 2026-09-16 hard-coding audit recorded that `_ASX200_TR_YIELD = 0.04` is
compounded onto the AXJO **price** index and written to a column named `benchmark_tr_level` on
67 of 74 snapshot rows, against governor ruling F1. That is all true. From it I filed A-45
describing a live defect that "corrupts what performance is measured against" and "outranks
cosmetic work", and ranked it #1 in the live queue.

Then I opened the consumers. `outcome.py:26-33` reads the `trailing_div_yield_pct` marker the
writer sets for exactly that path and **reports the measurement as unavailable, naming the proxy
as the reason** — "it never silently substitutes". `compose.py` derives `is_proxy` from the same
marker. `wealth_state.py` selects the columns and uses neither. A test pins the behaviour. The F1
guard was built, and built well, at the same time as the approximation.

**So the severity was mine, not the code's.** The real finding is narrower: a synthetic value is
stored under a total-return column name, which F1 does forbid, and one collector has a dead
select. Worth fixing; nowhere near the top of the queue.

**The rule, and it is not the same as L52's.** L52 was about a row citing the wrong *artifact*.
This is about a row citing the right artifact and the wrong *blast radius*. A writer producing a
questionable value and a consumer trusting it are two separate facts, and finding the first tells
you nothing about the second. **Before ranking a defect by severity, open the readers.** The
distance between "this value is wrong" and "this value is used" is where a whole night can go.

**Why this one cost nothing.** The correction landed before the build, because the first thing I
did on picking the row up was read the code rather than write it. That ordering is the only
reason this is a lesson and not an incident.

## L54 — A negative existence claim needs a probe, exactly like a figure does (2026-09-17)

I opened a 62-hour mission on this sentence, in the plan James approved:

> *"#7 beat the incumbent — a **measured** deterministic baseline to compare against: **none exists**."*

It was false. `factor_scores.py:79` defines `_COMPOSITE_CATEGORIES = ("value", "quality")` and
comments it *"the thing under test"*. `alpha_eval.py` already computes effective non-overlapping
sample size, the effective t it instructs callers to quote, decile spreads with a monotonicity
fraction, a `top_minus_upper_mid` "top decile has no edge" detector, calibration and a liquidity
split. `eval_alpha_factors.py:92` already drives its deciles off `composite_score` — literally the
D4 #7 comparison. Roughly 20 hours of the approved graph re-implemented shipped capability, and
the test it designed measured a single sub-factor rather than the composite D4 actually names.

**`AGENTS.md` §7 says every figure traces to a probe or a doc line, and an unsourced number is
omitted rather than guessed. A "none exists" is a claim of exactly that weight** — arguably more,
because a wrong figure gets checked by the next reader and a wrong absence closes the question.
One `ls asxos/domain/research/` would have cost four seconds.

The tell was available and I walked past it: I cited an ADR line written 2026-08-23 as authority
over code that shipped afterwards. That is the §10 ladder inverted — live state outranks repo
docs — and it is the same shape as L53 the day before.

**The rule: before building the thing that does not exist, run the command that would find it.**

## L55 — Two agents agreeing is not verification (2026-09-17)

`guilfoyle` and `arbi-red-team` were dispatched independently, given different briefs, and
converged on the same finding: the `alpha_eval` stack exists. They were right, and I verified
every claim myself against the code before acting.

The same two agents also told me A-45 was an active nightly corruption of the benchmark series,
ranked #1, incoherent to leave running. **That was false when they said it.** PR #317 had landed
on `main` about three hours earlier and found the F1 guard fully implemented — `outcome.py:26-33`
reports the measurement unavailable and "never silently substitutes". Both agents were reading
`roadmap-state.md` at my branch point and had no way to know. I nearly relayed it to James.

Convergence is not evidence: two agents reading the same stale snapshot converge on the same
stale conclusion. **What separated the true finding from the false one was not agreement — it was
that I re-derived one against live state and had not yet re-derived the other.** A subagent's
report is evidence to check, never a conclusion to carry.

## L56 — Dispatching the thing is a form of reading the code (2026-09-17)

`refresh_factor_scores` wrote its cross-section with `await conn.execute(...)` inside a per-symbol
loop — ~3,300 sequential round-trips to a remote Supabase. It had passed review, had tests, and
looked entirely ordinary. The first real dispatch made it obvious in ninety seconds: one `as_of`
still writing after ~13 minutes, so a 21-date panel meant ~5 hours against a 60-minute timeout.
Batched into one `executemany`, a cross-section takes **7.3 seconds** — measured in `job_runs`.

The latency was the visible half. The half that mattered: row-by-row writes leave a **partially
built cross-section queryable**, and I watched it pass through 1,373 → 1,683 → 2,253 rows for the
same date. An evaluator reading that window computes a rank-IC over whichever names happened to
have landed and reports it as the cross-section's result — a silent wrong answer, which is what
the hard-fail convention exists to prevent.

**The rule: a job's shape only shows up at production scale.** Mocked tests cannot see a
round-trip, and no amount of reading finds a defect whose symptom is wall-clock. This is the same
family as the Phase 2a finding that mocked connections do not enforce trigger semantics — run it
against something real, once, before trusting it.

## L57 — A lane being green is only evidence about the files it applies (2026-09-17)

AGENTS.md §8 step 1 is "`migration-integration.yml` green on the branch." On the A-47 branch it
was green on the first head, and I read that as step 1 satisfied. It was not.
`tests/test_m1_migrations_integration.py` applies an **explicit list** — 0055, 0056, 0057 — on a
scaffold that did not even have the `revision_type` column 0060 alters. The green run had
exercised nothing of the migration I was about to apply to production. The lane's name promised
coverage; its fixture delivered coverage of three other files.

The fix was to open the fixture, add the column in 0021's shape under 0021's constraint **name**
(so `DROP CONSTRAINT IF EXISTS` actually drops it), put 0060 in the list, and pin the exact row
the writeback emits against the real widened CHECK on Postgres 17. Only then was the box ticked.

**The rule: before ticking a gate, read what the gate ran, not what it is called.** A check's
conclusion is evidence about its inputs, and a fixture with an enumerated list has a fixed set of
inputs that does not grow when a new migration file appears. This is the migration-lane sibling of
L53 (open the readers before ranking severity) and L56 (dispatch the thing): the artefact that
looked like verification was a different verification.
## L58 — A runbook written from the domain layer will describe work the scheduler already does (2026-09-17)

**What happened.** James asked for a plan to scan for investment opportunities using
existing infrastructure. I read `asxos/domain/`, the CLI, the contracts and the
migrations, wrote `docs/product/runbooks/opportunity-scan.md`, and pushed it. Its §9
told him to run `asx decision build --context` by hand and its §10 told him to run
`asx decision observe` by hand.

Both already run **nightly** in `daily-brief.yml` — `jobs/build_decision_packets.py`
builds a challenged packet for every approved thesis, and
`jobs/observe_decision_outcomes.py` closes the outcome loop. Worse than redundant: the
nightly builder challenges against the **paper** book (C1/D15, deliberately never the
live one) while `--context` is the **live** book, so following the runbook would have
produced packets that could not be compared to the ones already in the table.

I found this in the `/arbi` wake James asked for afterwards — from `job_runs`, not from
the code. The `build_decision_packets` row was sitting in the freshness probe the whole
time.

**Why it happened.** I searched by capability ("what can produce a broker report?") and
the domain layer answered completely, so I stopped. `jobs/` is not where a *capability*
lives; it is where the decision to **invoke** that capability on a schedule lives. A
capability search finds the former and is blind to the latter.

**The rule.** Before documenting any procedure as manual, grep `jobs/` and
`.github/workflows/` for the thing being described. If a job already calls it, the
procedure is *read the result*, not *run the command* — and the manual verb is an
off-cycle escape hatch, which is a different section with a different warning.

**The sharper form.** L54 said a negative existence claim needs a probe. This is the
same failure one level up: **"the user must do X" is a negative existence claim about
automation** — it asserts nothing already does X. It was made on the same day L54 was
written, about the same subsystem, by me. Two independent probes would have caught it:
`ls jobs/`, or reading the `job_runs` table I queried twice for other reasons.
