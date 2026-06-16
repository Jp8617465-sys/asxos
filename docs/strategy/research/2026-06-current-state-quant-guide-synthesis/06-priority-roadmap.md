# 06 — Priority Roadmap (what to build / defer / not build)

*Category-5. Ordering reflects: production loop GREEN, both P0 risks CONFIRMED, data-completeness YELLOW.*

## Build next (in order)
1. **P0 units fix** (model-preserving, APPROVAL-GATED). Re-derive label cutoffs from the empirical `expected_return` distribution (or recalibrate regressor output) so STRONG/BUY/SELL match their documented intent. Ship with the **brief honesty caveat** (action E) as a same-PR safety rider. *Why first:* confirmed defect in the labels the user reads; small; no retrain; one branch.
2. **adj_close adoption + retrain `v1_6`** (sequential, retrain-gated). Switch loader+target to `adj_close`; retrain; re-validate with purge/embargo + rank-IC; promote only on a gated improvement. *Why second:* confirmed 25%-contamination, but requires the retrain pipeline.
3. **Baseline + rank-IC / decile-spread evaluation harness** (read-only research; can start now in parallel). OSAP + 12-1 momentum baselines; net-of-cost rank IC; purge/embargo. *Why:* the only way to answer "useful or coin flip"; gates everything past L2.
4. **Durable `price_coverage` metadata + gap detector** (design now, implement after P0). Persist the completeness verdict; auto-flag missing trading days (06-04/05/11/12).
5. **`signal_outcomes` read-back** into a rolling rank-IC brief footnote (after P0 + adj_close, so outcomes aren't computed on contaminated prices).

## Defer (until after L2 rank-IC verdict)
- Backtest CPCV (purge/embargo first), Deflated Sharpe, PBO.
- Paper portfolio / decision ledger + attribution.
- Denoised-covariance HRP/Schur sizing (`skfolio`); keep inverse-vol meanwhile.
- MLflow / Evidently / experiment-tracking machinery.
- Production governance gates (economic promotion + kill criteria).

## Do NOT build yet
- **Threshold *optimization*** (distinct from the one-off scale correction) — no tuning until evaluation exists.
- **Performance retraining / new model classes** (the only sanctioned retrain is the adj_close-correctness `v1_6`).
- **New signals / signal families.**
- **Portfolio automation / live execution.**
- **V2 / parallel-engine, env groups, cron redesign, migration recovery** (out of scope).

## Single immediate next action
**A — P0 signal correctness.** Verification is complete (both CONFIRMED); the next concrete step is the **scoped, approved units fix + brief caveat** (item 1). Justification: it is the smallest change that repairs a confirmed, user-facing label defect, requires no retrain, and unblocks honest signal display. Items 3 and the `price_coverage` design run **in parallel as read-only**.

## Why not the alternatives
- **B/C (price_coverage):** valuable but the recency gate already makes gaps *safe*; it's observability, not a correctness fix. Design in parallel; implement after P0.
- **D (baselines):** essential and starts now *in parallel*, but it measures a signal whose labels are currently mis-specified — correctness should lead the *implementation* path.
- **E (brief caveat):** correct and important — folded into item 1 as the safety rider, not a standalone strategic step.
- **F (do nothing):** wrong — we have confirmed defects.
