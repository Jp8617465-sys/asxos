# 11 — Independent Red-Team & Accepted Revisions

An independent read-only review of this v2 guide was run after drafting (the "second-opinion stream"). It independently **re-confirmed the three load-bearing repo facts** — `train.py:134` scales the regressor target to basis points (`*10_000.0`), `model_a.py:43` returns it unscaled, `thresholds.py` compares to fractional cutoffs (`> 0.05`) — so the central units-mismatch finding is real, not speculative.

## Verdict
**GREEN-leaning-YELLOW.** Analytically sound, verifiable claims confirmed, honest about its gaps. Downgraded from full GREEN by (a) `[verify]` figures stated too declaratively in prose and (b) a 90-day plan heavier than a solo operator should attempt.

## Strongest parts (per review)
- `06` correctness risks — correctly notes the units bug degrades the *label* magnitude arm but **not** the allocator ranking (z-scored).
- `07` — "L5 governance over an unmeasured signal is theatre."
- `08`/`09` phase gating + the honest-null exit ("quarantine as research-only").
- README separation of predictive quality vs portfolio usefulness, with the Avramov net-edge caution genuinely load-bearing.

## Accepted revisions (this addendum overrides the relevant parts of `09`)

1. **Prose-caveat policy (integrity).** `[verify]` figures — "no Australian small-cap premium" (rests on a single Morningstar AU note), ASX sector weights (~28–30% / ~20%), franking ~40% gross-up, JKP 82%, Chen FDR 9–25%, Avramov microcap concentration, GS +0.35%/yr — are **claims pending primary-source confirmation, not facts.** They must not appear in code comments or spec until the primary PDF is re-fetched and read. (README updated.)

2. **Defer the machinery behind the L2 verdict (scope).** The 61–90 day items in `09` (CPCV ≥100 paths, Schur/HRP via `skfolio`, MLflow, Evidently, `review_queue`/agentic layer) are **precision instruments on a signal not yet shown to beat momentum.** They are explicitly **deferred until the signal clears L2** (net-of-cost rank IC > 12-1 momentum and equal-weight). If it never clears, all Phase 4 construction/MLOps work is wasted. The "skip the institutional kit" guidance in `03` governs over the body's enthusiasm.

3. **Compressed near-term plan (replaces the front of `09`):**
   - **Move 1 —** `expected_return` units + `adj_close` memo (Prompt A). First, read-only.
   - **Move 2 —** `research/baselines.py` + rank-IC / decile-spread with a **one-bps cost stub and purge+embargo** (skip CPCV for now) → get the "useful or coin flip" answer cheaply.
   - **Move 3 — stop and re-decide.** Do **not** pre-commit to skfolio/MLflow/Evidently/CPCV. Defer all construction + MLOps behind the L2 verdict. Replace "denoised HRP/Schur" in the 90-day plan with a simple **equal-weight vs inverse-vol A/B** first.

4. **State the uncomfortable prior loudly (honesty).** Avramov-Cheng-Metzker implies a **long-only, large-cap, weekly ASX book may capture *near-zero* of ML's net edge** — not merely "a fraction." The realistic base case is a small-or-null net edge; the harness exists to find out, not to confirm.

5. **Add three missing checks before trusting any backtest:**
   - **Cost/turnover sizing for *this* book** — estimate ASX spreads + turnover for a ~20-name weekly rebalance; the cost model was named but never sized.
   - **Baseline the existing allocator** — equal-weight vs inverse-vol, before assuming HRP/Schur is needed.
   - **Breadth sanity check (Grinold IR≈IC·√Breadth)** — a ~20-name weekly book has limited *independent* breadth; verify there is enough for an ML edge to matter at all before building modelling machinery.

## Five ways this guide could let ASXOS fool itself (+ guards)
1. **In-sample rank IC mistaken for skill** → report only purged/embargoed OOS IC with a Deflated-Sharpe haircut; never quote an in-sample number.
2. **`[verify]` figures hardening into "facts" by repetition** → ban un-refetched `[verify]` numbers from prose conclusions and code comments.
3. **Beating a strawman baseline** → baseline must be value-weighted, net-of-cost, survivorship-controlled (Novy-Marx-Velikov protocol), not equal-weight gross.
4. **Building portfolio/MLOps machinery as displacement activity** → hard gate: no Phase 4+ code until L2 net-of-cost IC > momentum.
5. **Survivorship + no-size-premium double-count inflating a "good"-looking backtest** → require delisted returns *and* a liquidity floor before any IC is trusted.

## Net effect on the guide's recommendation
The diagnosis and the **first two roadmap moves stand verbatim.** Everything past the L2 rank-IC verdict is demoted to "conditional, build only if the signal proves out." The guide's own governing sentence, reinforced: **measure — net, purged, deflated — before you model, and before you build the machinery to model.**
