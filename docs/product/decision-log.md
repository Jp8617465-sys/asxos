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

## How arbi uses it

- **Read first each wake.** Before ranking NEXT ACTIONS, check whether the last "one thing"
  was done and whether it worked. A repeated failure is *data*, not a prompt to re-issue the
  same call verbatim (`arbi-scorecard.md` §Calibration; `arbi-evals.md` G6).
- **Feeds the promotion gate.** Sustained good calls are part of the Tier-promotion track
  record; a pattern of reversed calls blocks promotion.
- **Never rewritten by a dream.** A dream may *summarise* this log into a lesson, but the log
  rows themselves are immutable and outrank the dream's summary (ladder level 5 > 7).
