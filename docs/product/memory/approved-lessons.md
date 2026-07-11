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
Source: `north-star.md:73-81`, `decision-log.md` row 1.

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

## L6 — Model A decay, first pass: keep the quarantine (2026-07-10)
Read-only SQL over live `signals`+`prices` (`signal_outcomes` is **empty** — the
`track_signal_outcomes` cron hasn't populated it): the 5-day `prob_up`→return edge is weak
and **sign-flips across dates** (per-date corr −0.075..+0.146; pooled ≈0); the 21-day claim
is **not yet testable** (~2 matured dates; resolves ~late Aug 2026). **Lesson:** rule #11
stays; the fuller study (per-date Spearman rank-IC, benchmark-relative, re-run late Aug) is
the real resolution. **Open action:** fix `track_signal_outcomes` so `signal_outcomes`
populates and the next decay check is one query.
Source: `docs/model-a-decay-analysis-2026-07-10.md`.

## L7 — Live-verify the exact emitted statement sequence, not hand-written SQL (carried)
Governance transitions must INSERT the `governance_events` row **before** the
`governance_status` UPDATE (the BEFORE-UPDATE triggers check same-`xact_id`). Mocked tests
and hand-replicated SQL both passed while the real Python-emitted order was wrong.
**Lesson:** any `governance_status` transition must have its *emitted* order live-verified
against the real triggers (rolled-back transaction) at least once.
Source: `.claude/rules/portfolio-conventions.md` Phase-2a verification lesson.
