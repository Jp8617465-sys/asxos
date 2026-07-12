# arbi decision log — the "one thing" calls and their outcomes

**Status:** current
**Scope:** arbi's durable memory of prioritisation decisions and whether they held up
**Last verified:** 2026-07-10
**Owner:** arbi appends (I2, command-invoked); James audits
**Superseded by:** N/A

This is where arbi *learns*. Every `/arbi-close` appends the wake's "one thing," what was
actually done, and whether it worked. Every `/arbi` reads this **first** (per
`arbi-authority.md`, memory sits below repo truth but is still read before ranking) and lets a
call that didn't pan out reshape the next one. **Append-only — never delete a row;** it is the
record of the project's real trajectory and the only place the system checks its own past
calls against outcomes.

(Previously this log lived inline in `roadmap-state.md`; it is split out here so it can grow
without bloating the state file, and so the promotion gate + run ledger can reference one
canonical decision history. `roadmap-state.md` now points here.)

---

## Log (append below; newest at bottom)

| Date | arbi's "one thing" | What was done | Outcome (done/partial/deferred/superseded · did it work?) | Run ref |
|---|---|---|---|---|
| 2026-07-10 | Scope Model A's real blast radius (governor challenged the "Model A is the platform" framing) | Ran arbi multi-agent scan→verify→synth (6/7 agents); adversarial verifier returned **verdict: supported** with file-cited evidence | **done · worked** — corrected north-star + roadmap-state (quarantine is narrow: only the allocator path + opportunity-cost); logged 2 bugs (R8 behavioral-only quarantine, R9 brief↔approval coupling). Next: run the decay check (the sole P0 unlock) | `wf_f54323f5-d7d` |
| 2026-07-10 | Run the Model A decay check (THE ONE THING — resolve the P0) | Read-only SQL over live `signals`+`prices` (`signal_outcomes` empty): pooled + per-date corr of `prob_up` vs 5d/21d forward return, label buckets | **done · partial** — 5-day edge is weak + sign-flipping across dates (−0.075→+0.146, pooled ≈0), supporting James's distrust; 21-day claim **not yet testable** (only ~2 matured dates — resolves ~late Aug). **Rule #11 stays.** Full findings: `docs/model-a-decay-analysis-2026-07-10.md` | decay-2026-07-10 |
| 2026-07-11 | Re-run the decay check directly on `signal_outcomes` — surfaced *populated* (24,454 rows) by the first product-health scorecard run, when it had been recorded empty on 07-10 — to resolve the P0 | Read-only decay analysis on **19,032 matured signals** (5d+21d realised returns materialised): pooled corr + per-label conviction→return ranking | **done · RESOLVED against Model A** — `corr(ml_prob,21d)=−0.03`; STRONG_BUY 21d −0.09% vs HOLD +5.07% (conviction inverted at the top); no usable edge over the held horizon. Rule #11 → **standing/vindicated**. P0 closed; retrain-vs-shelve strategic call is James's. Full: `docs/model-a-decay-analysis-2026-07-11.md`. Lesson: the scorecard caught an "assumed-empty" table that unblocked the P0 — instrumentation earns its place | decay-2026-07-11 |
| 2026-07-11 | Governor granted an 8-hour reversible-work autonomy window (improve product/code/roadmap/backlog/risks + competition/gap research) | Recorded the grant; stood up hourly autonomy Routine `trig_01M5mWFrgZBmqbinLK12F6iU` (fresh session, ~8 cycles to 20:08Z, **draft-PR-only**, self-bounded at 20:18Z via STEP-0 clock check) + stand-down `trig_01Qg9BPG3KYvAeKQRxmYAMPA`; front-loaded attended dev work onto branch `claude/wake-up-arbi-jeww8p` / PR #26 | **in progress** — held every hard line (no merge/deploy/DB-write/Render/capital/Model-A/self-edit-of-boundaries); all output reversible + reviewable as draft PRs. A formal `arbi-permission-model.md` amendment to *standing* reversible autonomy is **drafted-for-James, not self-enacted** (constitution §reserved) | autonomy-2026-07-11 |
| 2026-07-11 | R8 — make rule #11 mechanically enforced, not behavioral-only (found `model_a v1_5` still `approved_for_allocation=TRUE` while shelved) | Revoked with James's explicit I5 approval (AskUserQuestion): `UPDATE model_versions SET approved_for_allocation=FALSE WHERE model='model_a' AND version='v1_5'` — RETURNING confirmed 1 row; it is the only model_versions row → 0 approved-and-active. Safe because R9 (brief best-effort on 0-approved) landed 2026-07-10 first | **done · worked** — the allocator gate now resolves 0 approved → `build()` hard-fails (intended dormant state) instead of passing the shelved no-edge model to the allocator. First arbi-executed I5 write, gated per-action by James. risk-register R8 → resolved | autonomy-2026-07-11 |
| 2026-07-11 | Merge PR #26 to main "if CI green" (governor instruction) | Verified CI green (full-check + targeted-ml-tests + automated-review all `success` on head 034b77d) and `mergeable_state=clean`, not draft; squash-merged → main (338194a); reset the branch to merged main for follow-up work | **done · worked** — monitoring-lane + OOM fixes + R8 docs on main; Render auto-deploys crons from main. **First arbi-executed I6 (merge/deploy)**, gated per-action by James's explicit instruction (not standing autonomy). **Risk surfaced:** the merge succeeded via API with no required-review block (`mergeable_state=clean`), confirming **branch protection on `main` is NOT configured** — the autonomy-loop layer-2 backstop is still open; recommend configuring it before any *standing* (unattended) merge authority | autonomy-2026-07-11 |
| 2026-07-11 | **Calibration lesson (governor correction, not a "one thing" call):** "Just because we have something built that no one else does, doesn't mean this is right — never take what we have as an advantage." Triggered by the just-landed `competitive-gap-analysis-2026-07-11.md`, whose Q2/roadmap sections tag six items `[DIFFERENTIATION]` on "no competitor does this" alone | Added a calibration note directly into `competitive-gap-analysis-2026-07-11.md` (top of doc): every `[DIFFERENTIATION]` tag there is competitive *absence*, not validated user *value* — read as "investigate," never as a build-priority signal by itself | **standing lesson, applies going forward** — any future competitive/gap analysis, or any argument of the form "we're the only ones who do X," must be treated as a flag to verify X is actually right for James, not evidence it should be prioritized. Feeds `arbi-scorecard.md` calibration; should inform how `deep-research-agent` competitive-gap tasks are briefed next time (ask it to separately rate "is this validated as wanted," not just "is this rare") | calibration-2026-07-11 |

## How arbi uses it

- **Read first each wake.** Before ranking NEXT ACTIONS, check whether the last "one thing"
  was done and whether it worked. A repeated failure is *data*, not a prompt to re-issue the
  same call verbatim (`arbi-scorecard.md` §Calibration; `arbi-evals.md` G6).
- **Feeds the promotion gate.** Sustained good calls are part of the Tier-promotion track
  record; a pattern of reversed calls blocks promotion.
- **Never rewritten by a dream.** A dream may *summarise* this log into a lesson, but the log
  rows themselves are immutable and outrank the dream's summary (ladder level 5 > 7).
