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
