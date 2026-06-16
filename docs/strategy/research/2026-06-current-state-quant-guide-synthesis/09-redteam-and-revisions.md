# 09 — Independent Red-Team & Accepted Revisions (authoritative override)

An independent read-only red-team reviewed this pack and **re-confirmed the four load-bearing code facts** (`train.py:134` `* 10_000.0`; `model_a.py:43` unscaled `predict`; `thresholds.py:27` `> 0.05`; `loader.py:119/134` raw `p.close`). Diagnosis and citations: solid. **Trustworthiness: YELLOW-GREEN** — diagnosis GREEN; sequencing/prioritisation and two framings YELLOW. **Where this file conflicts with `04`/`06`, this file wins.**

## Accepted corrections

1. **Production is GREEN-*provisional*, not "proven recovery."** Two windows (one with a known `ingest_regulatory` failure) means "no longer broken," not "recovered." Bar: ~4 clean weekly cycles. (Revises `01`/README wording.)

2. **P0-1 framing tightened.** The expected_return magnitude arm is **genuinely inert at the BUY/SELL tier** (`er > 0`; median er ≈ 1.72 so ~every positive row passes) but **still excludes a band at the STRONG tier** (`STRONG_BUY min er = 0.0755` vs cutoff 0.05). Correct statement: **the cutoff is mis-scaled by ≈100×**, so labels are prob_up-dominated *at the BUY/SELL tier* and the STRONG cutoff is near-but-not-fully inert — NOT "magnitude is meaningless." Still a confirmed mis-specification.

3. **The artefact-scale UNKNOWN is upstream of the fix.** "Did the persisted `v1_5` regressor actually use the `×10_000` line?" must be closed **before** any threshold re-derivation. `06` listed "P0 units fix" as build-next as if verification were closed — it is not.

4. **Re-derive thresholds ONCE, on clean data.** Fixing units/thresholds now (on raw-close-based `expected_return`) and then retraining on `adj_close` later would force **deriving thresholds twice** (the distribution changes after retrain) — wasted, error-prone work this pack failed to flag. Therefore **adj_close+retrain should lead the threshold track**; derive label cutoffs once from the clean `v1_6` distribution.

5. **The 4 missing trading days (06-04/05/11/12) may be an ACTIVE leak**, not static observability debt — recurring Thu/Fri pattern, root cause UNKNOWN, one hole in the current week, feeding a 450-day lookback. Raise the GAP diagnostic (`08` Prompt GAP) from "nice-to-have" to "do soon."

## REVISED single immediate next action (supersedes README/`06`)

**E — ship the brief honesty caveat, as a standalone, decoupled from any label change.** It is the only **zero-risk, reversible, no-approval-needed-for-labels** step that removes the real user-facing harm *now* (the brief presenting STRONG_BUY/SELL as calibrated 5%-conviction signals that the data shows they are not). It does **not** change labels, thresholds, or the model.

**Then, in this order:**
1. **P0-A (read-only):** close the artefact-scale verification (confirm `v1_5` regressor trained with `×10_000`).
2. **adj_close adoption + retrain `v1_6`** (the deeper data fix; regenerates `expected_return` on clean prices). Run the adj_close design in parallel read-only now.
3. **Derive label thresholds ONCE** from the clean `v1_6` `expected_return` distribution (the units/threshold fix — done correctly, once).
4. **Baseline + rank-IC research** in parallel read-only throughout; **GAP diagnostic** soon.

## Smallest next step vs most-damaging wrong step
- **Smallest useful step:** the standalone brief caveat (E) — zero risk, removes harm today.
- **Most damaging wrong step:** re-deriving percentile thresholds and re-labelling **before** confirming the persisted artefact's scale — a silent, user-facing, approval-stamped label change against a possibly-misread distribution.

## Net
Accept all of `04`'s empirical findings. **Reorder to: caveat (E) → verify artefact scale → adj_close+retrain → derive thresholds once.** Downgrade production to GREEN-provisional. Treat the price gaps as a possible active leak.
