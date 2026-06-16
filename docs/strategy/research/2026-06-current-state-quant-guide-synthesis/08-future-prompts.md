# 08 — Future Pasteable Prompts

*Each: scope · constraints · tasks · deliverable · stop. Read-only/design unless marked IMPLEMENT (which requires explicit approval and one branch).*

## Prompt P0-A — Finalize P0 units verification + fix decision brief (read-only)
- *Scope:* confirm the persisted `model_a_v1_5` regressor was trained with `forward_return * 10_000` (artefact/`metrics.json`/code read); design the fix.
- *Constraints:* read-only; SELECT-only DB; no edits/commits/migrations/jobs/Render; do not change thresholds/code.
- *Tasks:* (1) read `train.py`, `model_a.py`, `thresholds.py`, model `metrics.json`; (2) re-run the `expected_return` percentile + label-sensitivity SELECTs; (3) propose ≥2 fix options (re-derive percentile thresholds vs recalibrate regressor output) with predicted label-distribution impact for each; (4) draft the brief honesty caveat copy.
- *Deliverable:* a decision brief with a recommended option + blast radius + rollback. *Stop:* after the brief.

## Prompt P0-B — Implement P0 units fix + brief caveat (IMPLEMENT — needs approval)
- *Scope:* one branch implementing the approved fix option from P0-A, plus the brief caveat.
- *Constraints:* one implementation branch only; no retrain; no adj_close change in this PR; full unit tests; PR, do not merge without review.
- *Tasks:* apply the scale/threshold correction; add brief caveat display; update threshold tests; verify label-distribution shift matches P0-A prediction.
- *Deliverable:* tested branch + PR + before/after label distribution. *Stop:* after PR.

## Prompt ADJ — adj_close adoption + retrain plan (read-only design)
- *Scope:* plan switching feature loader + target to `adj_close` and retraining `v1_6`.
- *Constraints:* read-only; no retrain executed; preserve train/serve consistency.
- *Tasks:* identify every raw-`close` use in features/target; design the loader change; define the retrain + purge/embargo + rank-IC re-validation + promotion gate; quantify expected feature changes on the 25%-adjusted rows.
- *Deliverable:* adj_close+retrain design + acceptance gate. *Stop:* after design.

## Prompt BASE — Baseline + rank-IC / decile evaluation (read-only research design)
- *Scope:* design `research/baselines.py` + `research/metrics.py` (rank IC, ICIR, net-of-cost decile spread) vs Open Source Asset Pricing + 12-1 momentum; purge/embargo.
- *Constraints:* research-only; reads production tables, writes only research artefacts; survivorship-safe joins.
- *Deliverable:* design + acceptance (reproduce one month's IC by hand). *Stop:* after design.

## Prompt COV — price_coverage metadata + gap detector (read-only design)
- *Scope:* design a durable `price_coverage(dt, au_equity_rows, status, classified_at)` table written by `sync_prices` from the existing completeness verdict, plus a missing-trading-day detector.
- *Constraints:* read-only design; SELECT-only confirmation of gaps; no migration applied.
- *Tasks:* confirm the 06-04/05/11/12 gaps + scan the last 60 trading days; design table + writer + read API for `latest_complete_trading_day`; propose migration (not applied).
- *Deliverable:* design + gap report. *Stop:* after design.

## Prompt GAP — Thu/Fri price-gap root-cause diagnostic (read-only)
- *Scope:* why are 2026-06-04/05 and 06-11/12 missing from `prices`?
- *Constraints:* read-only; SELECT-only + `job_runs`/log inspection; no backfill run.
- *Tasks:* check `job_runs` for sync_prices on those dates; check for partial/residue rows; determine provider vs backfill cause; recommend a (separate, approved) backfill.
- *Deliverable:* root-cause memo. *Stop:* after memo.

## Prompt QA — Brief signal-display truthfulness review (read-only)
- *Scope:* does the brief overstate confidence given confirmed label mis-specification?
- *Constraints:* read-only; no edits.
- *Tasks:* read `compose.py` + templates; enumerate signal claims; confirm `prob_up`/`confidence` not shown; propose caveat copy aligned with P0 findings.
- *Deliverable:* QA report + caveat strings. *Stop:* after report.

## Prompt RT — Red-team this synthesis (read-only)
- *Scope:* adversarially review this pack's conclusions and the recommended single next action.
- *Deliverable:* red-team memo (overclaims, misordering, smallest-next-step, most-damaging-wrong-step). *Stop:* after memo.
