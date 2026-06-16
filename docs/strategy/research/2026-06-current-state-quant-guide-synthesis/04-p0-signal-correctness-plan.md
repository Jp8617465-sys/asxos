# 04 — P0 Signal-Correctness Plan (both risks CONFIRMED from data)

*Crown jewel of this pack. Category-1 (production data) + Category-2 (repo `file:line`). The quant guide flagged these as LIKELY/CONFIRMED-by-code; this pack upgrades both to **CONFIRMED by production data**.*

---

## Risk 1 — `expected_return` units mismatch — **CONFIRMED · severity HIGH (label mis-specification)**

### Code mechanism (Category-2)
- Training target is basis points: `y_reg = forward_return * 10_000.0` (`asxos/domain/models/train.py:134`).
- Inference returns it **unscaled**: `expected_return = regressor.predict(X)` (`asxos/domain/models/model_a.py:43`).
- Thresholds compare to **fractions**: `expected_return > 0.05` / `> 0` / `< -0.05` (`asxos/domain/signals/thresholds.py`), documented intent "5% expected move".

### Production-data proof (Category-1)
`expected_return` distribution (signals, 2026-06-15): **min −31.9, p01 −20.6, p50 1.72, p95 16.7, p99 31.2, max 94.4.** A fractional return with median 1.72 would mean +172% — impossible. **Units are NOT fractional** (basis-point-scale, consistent with the `×10_000` target, though heavily shrunk by regularization — max ≈ 94 bps ≈ 0.94%).

Label sensitivity at 2026-06-15:
| label | n | median prob_up | min er | median er | max er |
|---|---|---|---|---|---|
| STRONG_BUY | 163 | 0.708 | **0.0755** | 5.27 | 55.7 |
| BUY | 244 | 0.596 | 0.00178 | 4.82 | 84.9 |
| HOLD | 1053 | 0.431 | −22.7 | 1.64 | 94.4 |
| SELL | 85 | 0.398 | −18.0 | −1.26 | −0.042 |
| STRONG_SELL | 158 | 0.247 | −31.9 | −3.59 | −0.055 |

### Interpretation
The `0.05` cutoff sits in the **extreme left tail** of the positive distribution (median er = 1.72 ≫ 0.05). STRONG_BUY's `min er = 0.0755` confirms the cutoff is *technically* binding but **operationally near-inert** — virtually every positive prediction clears 0.05, so STRONG_BUY ≈ `prob_up ≥ 0.65 AND er > 0`. The documented "5% expected move" intent (= 500 bps) is **not enforced**. **Labels are prob_up-dominated; the expected_return magnitude arm is largely degenerate.**

### Blast radius
- **Labels / brief: affected** — STRONG_BUY/SELL mean something different from their documented definition.
- **build_portfolio ranking: NOT affected** — the allocator z-scores `expected_return` (scale-invariant); composite ranking and inverse-vol sizing are unchanged.
- Misleading to the user: yes (brief shows hard labels implying a calibrated 5% conviction that does not exist).

### Classification: **CONFIRMED.** Remaining UNKNOWN: 100% certainty that the *persisted* `v1_5` artefact used the `×10_000` line (vs an older artefact) — strongly inferred from the distribution; close with one code/artefact read.

### Fix is NOT a one-line rescale (important)
Naive `÷10_000` at inference would make `expected_return` ≈ ±0.003 → **no row ever clears `er > 0.05`** → zero STRONG_BUY (opposite degeneration). Because the regressor is heavily shrunk (max ≈ 0.94%), **the thresholds must be re-derived from the empirical `expected_return` distribution** (e.g. percentile-based), or the regressor recalibrated. That is a deliberate **threshold change requiring research + explicit approval** — not a quick fix.

---

## Risk 2 — raw `close` vs `adj_close` — **CONFIRMED · severity HIGH (ASX)**

### Code mechanism (Category-2)
Feature panel selects raw `p.close` (`asxos/domain/signals/loader.py:119,134`); target uses raw `close` (`train.py:73`). `adj_close` exists in `prices` but is unused.

### Production-data proof (Category-1)
- `adj_close` is **100% populated**: 646,015 / 646,015 rows non-null.
- **25.38%** of rows (163,962) have `adj_close ≠ close` — a quarter of all price history is adjustment-affected.
- Extreme cases real: e.g. **OSL.AU adj_ratio = 400×** (close 0.007 vs adj_close 2.80 — a consolidation). Using raw close, the consolidation date manufactures a catastrophic spurious return into both features and the 5-day target.

### Interpretation
The corrected series is **already in the table** and materially different. Raw-close features/targets inject corporate-action noise on ~25% of rows — exactly the ASX trap the quant guide flags (frequent franked ex-dates, rights/bonus issues, consolidations).

### Blast radius
Features **and** target → every label and the model's learned mapping. Train/serve are *consistently* wrong (both raw close), so it is signal-quality degradation rather than train/serve skew.

### Classification: **CONFIRMED.**

### Fix requires retraining
Switching the loader to `adj_close` changes the feature/target basis → the live `v1_5` model (trained on raw close) would face train/serve skew unless **retrained** on adj_close. Retraining is gated. So this is a **larger, sequential workstream**: change loader → retrain → re-validate → promote.

---

## Recommended P0 sequence (read-only research → approved implementation)

1. **(read-only, ~done here)** Verification — both CONFIRMED. Close the one residual: confirm the persisted `v1_5` regressor used the `×10_000` target (artefact/code read).
2. **(small, model-preserving, APPROVAL-GATED)** `expected_return`/threshold scale fix: re-derive label cutoffs from the empirical distribution (or recalibrate regressor output) so STRONG/BUY/SELL mean what they claim. Ship with a **brief honesty caveat** (display `prob_up`/`confidence` + "research-stage, magnitude not calibrated") as a same-PR safety rider. **This changes labels by design → requires explicit human sign-off** (threshold change).
3. **(larger, sequential, retrain-gated)** `adj_close` adoption: switch loader + target to `adj_close`, retrain `v1_6`, re-validate (with purge/embargo + rank-IC, per the v2 guide), compare to `v1_5`, promote only on a gated improvement.
4. **(parallel, read-only)** Begin baseline/rank-IC research (`08`, Prompt D) — but do not promote any fix on AUC alone; use net-of-cost rank IC.

## Meanwhile (protective, until step 2 ships)
The brief should **not** present STRONG_BUY/SELL as precise conviction. Smallest safe mitigation: a brief caveat (research-stage, labels prob_up-driven, magnitude not calibrated). This is candidate action **E** and is the recommended same-change rider on step 2.
