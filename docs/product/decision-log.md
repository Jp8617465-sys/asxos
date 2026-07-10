# arbi decision log — the "one thing" calls and their outcomes

**Status:** current
**Scope:** arbi's durable memory of prioritisation decisions and whether they held up
**Last verified:** 2026-07-10
**Owner:** arbi appends (Tier 2, command-invoked); James audits
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

## How arbi uses it

- **Read first each wake.** Before ranking NEXT ACTIONS, check whether the last "one thing"
  was done and whether it worked. A repeated failure is *data*, not a prompt to re-issue the
  same call verbatim (`arbi-scorecard.md` §Calibration; `arbi-evals.md` G6).
- **Feeds the promotion gate.** Sustained good calls are part of the Tier-promotion track
  record; a pattern of reversed calls blocks promotion.
- **Never rewritten by a dream.** A dream may *summarise* this log into a lesson, but the log
  rows themselves are immutable and outrank the dream's summary (ladder level 5 > 7).
