# Model A decay analysis — the P0, resolved (2026-07-11)

**Status:** **RESOLVED — against Model A.** The signal-reliability dispute that gated rule #11
and Phase 2c is answered with direct evidence: **Model A (`model_a_ml`, v1_5) has no usable
edge over the 5-day and 21-day horizons this system holds positions for.** The quarantine
(rule #11) is **vindicated and stands.**
**Supersedes:** the provisional `docs/model-a-decay-analysis-2026-07-10.md` (which had to
reconstruct outcomes from prices and could not test 21d — "5d weak/unstable, 21d untestable").
**Method:** direct read of `signal_outcomes` (now populated — 24,454 rows; surfaced by the
first product-health scorecard run). Read-only. This is Model A *investigation*, not action —
no capital decision is derived from Model A here.

---

## The evidence (19,032 matured `model_a_ml` signals, 2025-12-08 → 2026-03-25)

Every one of the 19,032 signals has matured at both 5d and 21d (`actual_return_5d`,
`actual_return_21d` materialised in `signal_outcomes`).

**Pooled correlation of the signal vs realised forward return:**
| | 5-day | 21-day |
|---|---|---|
| `corr(ml_prob, actual_return)` | **+0.032** | **−0.030** |
| `corr(ml_expected_return, actual_return_21d)` | — | **−0.0003** |

Both ≈ 0; the 21d correlation is marginally **negative**. The signal's probability carries no
linear information about the return over either horizon.

**The killer test — does conviction map to realised return? (by label, 21d):**
| label | n | avg `ml_prob` | avg 5d | avg **21d** | dir. acc |
|---|---|---|---|---|---|
| STRONG_BUY | 1,491 | 0.712 | −0.82% | **−0.09%** | 0.52 |
| BUY | 2,879 | 0.599 | −0.70% | **+1.24%** | 0.56 |
| HOLD | 14,588 | 0.331 | −1.70% | **+5.07%** | 0.30* |
| SELL | 38 | 0.357 | −1.38% | −3.34% | 0.61 |
| STRONG_SELL | 36 | 0.090 | −1.36% | −2.25% | 0.17 |

**The long side is inverted at the top:** STRONG_BUY (+conviction) returned **−0.09%** at 21d
while HOLD (neutral) returned **+5.07%** and plain BUY returned +1.24%. The model's *strongest*
ideas underperformed its *neutral* ones by ~5 percentage points. A working stock-picker's
highest-conviction longs should out-return its holds; Model A's do the opposite.

\* HOLD "direction accuracy" (0.30) is a metric artifact — "correct direction" is ill-defined
for a no-view label — so ignore it. The load-bearing facts are the ≈0/negative correlations
and the **non-monotonic, top-inverted conviction→return ranking**, which are regime-independent.

## Honest caveats (stated so the conclusion isn't over-read)

- **5d is uniformly negative** (−0.7% to −1.7% across all labels) — that's a market-regime
  effect over Dec–Mar (everything fell short-term), not a model signal. The *relative* ranking
  (STRONG_BUY < BUY < HOLD at 21d) is what indicts the model, and relative ranking is
  regime-independent.
- **The sell side is tiny** (SELL 38 + STRONG_SELL 36 = 74 signals) — directionally "correct"
  (negative) but too small to lean on. The model almost never issues a sell (77% of signals are
  HOLD).
- **Coverage window ends 2026-03-25.** `signal_outcomes` has not been refreshed since ~April
  (a `track_signal_outcomes` staleness issue — see cleanup), so this is Dec–Mar signals. 19k
  matured signals over 3.5 months is a robust sample for "does this model version have edge";
  it does not cover Apr–Jun.
- Direction accuracy on *actual buy signals* is marginally above 50% (0.52–0.56) — so the model
  is **not** pure inverse-noise; it just has no *usable, monotonic* edge, and its magnitude/
  conviction signal is inverted at the top.
- **Model-name check (verify):** `signal_outcomes.model = 'model_a_ml'`; the live `signals`
  table and rule #11 say `model_a`/v1_5. Treated as the same production ML model here; confirm
  the naming maps 1:1 before any irreversible action.

## Verdict

**Keep rule #11. The dispute is resolved in the direction of James's original distrust:** Model
A v1_5's signal does not provide a usable edge over the weeks-to-months horizon the theses hold
for, and its highest-conviction longs underperform its neutral holds. Do **not** use Model A
output — signals, allocator, candidate scans, opportunity-cost — as a basis for real capital.
The quarantine is no longer "temporary pending investigation"; it is the **standing, evidenced
policy for this model version.**

This also **vindicates the whole session's direction**: build the model-independent product
(discipline, tax, theme stewardship, ETFs) — the moat layers that were always authoritative —
rather than waiting on a signal engine that this analysis shows isn't carrying alpha.

## Recommended actions (arbi does the doc side; the strategic call is James's)

1. **Reframe rule #11** from "temporary, pending resolution" → "resolved: v1_5 shown to lack
   usable edge; quarantine stands." (Done in this change: `CLAUDE.md`, `north-star.md`,
   `risk-register.md` R1, `decision-log.md`, `roadmap-state.md`.) The rule is **not removed** —
   removal would mean "Model A is fine," which the evidence refutes.
2. **Fix `track_signal_outcomes`** so `signal_outcomes` refreshes past 2026-03-25 (cleanup) —
   this analysis becomes a one-query standing check, not a manual dig.
3. **James's strategic call (not arbi's):** what to do about Model A now — (a) retrain a new
   version and hold it to a pre-registered decay bar (e.g. positive, monotonic conviction→21d
   return + `corr ≥ ~0.05`) before it can ever earn `approved_for_allocation`; (b) shelve the
   ML engine and lean fully into the model-independent discipline/ETF product; or (c) both, in
   parallel. This unblocks Phase 2c one way or the other.
