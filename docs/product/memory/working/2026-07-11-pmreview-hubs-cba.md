# Working memory — 2026-07-11 · run `pmreview-hubs-cba`

**Layer:** untrusted working scratch (ladder 8) — advisory only, not authoritative until it
survives a dream + the promotion gate into `../approved-lessons.md`. Do not cite as approved.

**Run:** first live P2 portfolio review under the new Portfolio ladder — `/pm-review` HUBS.NYSE
+ CBA.AU, 5 model-independent analysis agents fanned out from the main loop, adversarially
reconciled. Attended (James invoked). Model-independent (rule #11): HUBS has 0 Model A signals;
no SHAP read for CBA. Execution untouched (HUBS is ESPP-locked; CBA not held).

---

## Candidate lesson L-cand-1 — fan-out + adversarial reconciliation catches correlated agent error

**Status:** candidate (proposed; needs a second instance or a dream to promote)
**Type:** process / verification
**Source:** `/pm-review` 2026-07-11 (this run)
**Applies-when:** synthesizing multiple agents' outputs into a capital-relevant memo where a
shared input can be misread the same way by more than one agent.
**Behaviour-change:** before writing any figure into a memo, look for a **cross-agent
disagreement on a capital-relevant number** and resolve it *at the source* (a direct query),
not by majority — the majority can be wrong together.

**What happened.** 2 of 5 agents (thesis-milestone-monitor, benchmark-performance-analyst)
independently reported HUBS.NYSE **−29% underwater / stop-violated / −28pp vs XJO**. Both made
the *same* error: they read `cost_base_normal` (6978.23, the **AUD tax base**) as a USD cost
total and divided by 24 → "US$290.76/share." The 3rd agent (portfolio-coherence-reviewer),
which read `thesis_revisions #13` and the active profile, flagged it. Source verification then
closed it decisively: `6978.23 × 0.6450 ÷ 24 = 187.54` = `actual_entry_price` to the cent. The
position is ≈ flat (+9.8% USD / ~+2% AUD), not −29%.

**Why it matters.** A single-agent review — or a naive "2 of 3 agree" synthesis — would have
shipped "HUBS −29%, stop violated, EXIT-CANDIDATE" into a capital memo. Wrong, and (had the
shares not been ESPP-locked and non-disposable) potentially loss-causing. This is the concrete
case *for* the multi-agent fan-out + the schema's "every figure traces to a cited source" rule
+ reconcile-at-source. It also mirrors the existing portfolio-conventions "verification lesson"
(mocked/replicated checks pass while the real thing fails) — same shape, capital side.

**Do-not-overgeneralise:** this is not "agents are unreliable." Each agent was internally
rigorous and cited its data; the failure was a genuinely ambiguous schema (`cost_base_normal`
currency — now risk R10). The lesson is about *reconciliation discipline on shared inputs*, not
distrust of agents.

## Secondary observations (for the dream to fold or drop)

- The Portfolio ladder's P2 path worked end-to-end on first real use: model-independent by
  construction (HUBS has no Model A signal), execution physically impossible (ESPP lock / not
  held), memo → outcome-ledger row pending James. The firewall held with zero friction.
- `/pm-review`'s own template features a Model A signal in its FOR example — under rule #11 the
  run had to *deliberately exclude* `thesis-coherence-guard`. Candidate: update the command to
  make model-independence the default framing while the quarantine stands (a doc/command edit,
  [REV]).
- Data-integrity is the theme of the run, not performance: cost-base currency (R10), CBA ladder
  broken (RC2), conviction NULL everywhere (R11), market_context feed gaps (RC3), `.NYSE`
  discipline-coverage hole (RC5, confirms existing R7). The product's discipline layer is only
  as good as the data under it — and the data has real holes.
