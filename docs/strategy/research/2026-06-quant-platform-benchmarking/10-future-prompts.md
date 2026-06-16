# 10 — Future Pasteable Prompts (A–L)

Each prompt: scope · hard constraints · tasks · final deliverable · stop condition. All are **read-only/design** except L, which implements *after explicit approval*.

---

**Prompt A — Signal correctness verification: `expected_return` units & price basis**
- *Scope:* read-only verification of `06` Risks 1 & 2.
- *Hard constraints:* no edits/commits/migrations/jobs/Render; SELECT-only DB; do not change thresholds or code.
- *Tasks:* trace `train.py` target scaling → `model_a.py` inference → `thresholds.py` constants; `SELECT` percentile distribution of `signals.expected_return` for the active version; inspect `models/model_a_v1_5_metrics.json` RMSE scale; sample known-corporate-action symbols comparing raw `close` vs `adj_close` returns.
- *Deliverable:* memo classifying units (bps/fraction) with evidence + recommended fix path (no fix applied).
- *Stop:* after the memo.

**Prompt B — Factor baseline suite design**
- *Scope:* design of `research/baselines.py` (read-only).
- *Constraints:* research-only; no production writes.
- *Tasks:* specify equal-weight, 12-1 momentum (skip-month), 200-day trend, naive value (P/B), naive quality (ROE/EPS), prior-signal persistence, random; define forward-return convention (adj_close, 5/21-day).
- *Deliverable:* design doc + function signatures + acceptance tests.
- *Stop:* after the design.

**Prompt C — Rank IC / quintile evaluation implementation plan**
- *Scope:* design + test plan (read-only).
- *Tasks:* define rank IC (Spearman per date), IC mean/t-stat/IR, decile spread + monotonicity, hit rate, calibration (reliability + Brier); specify survivorship-safe join of `signals` to forward returns.
- *Deliverable:* implementation plan + acceptance criteria (reproduce one month's IC by hand).
- *Stop:* after the plan.

**Prompt D — Backtest harness audit and design**
- *Scope:* audit current validation + design research harness (read-only).
- *Tasks:* document the leakage in the current 5-fold split; design purged + embargoed walk-forward, as-of universe, liquidity floor, cost model, turnover, Deflated Sharpe / PBO.
- *Deliverable:* harness design doc + leakage proof + acceptance criteria.
- *Stop:* after the design.

**Prompt E — Signal outcome tracking table provenance review**
- *Scope:* read-only review of `track_signal_outcomes.py` + `signal_outcomes`.
- *Tasks:* audit entry/exit close selection, `was_direction_correct`, horizons; confirm survivorship/PIT safety; identify why nothing reads it; design a safe read-back for a brief footnote.
- *Deliverable:* provenance report + read-back design.
- *Stop:* after the report.

**Prompt F — Paper portfolio / decision ledger design**
- *Scope:* design only (research-only, no orders).
- *Tasks:* design a decision-ledger table recording would-be trades from `build_portfolio`, with cost/tax/CGT assumptions and attribution (factor vs selection).
- *Deliverable:* schema + attribution method + acceptance criteria.
- *Stop:* after the design.

**Prompt G — Portfolio risk model / liquidity overlay design**
- *Scope:* design only.
- *Tasks:* specify Ledoit-Wolf shrinkage covariance over the candidate set, a turnover penalty, and an ADV-based liquidity/capacity cap, integrating with the existing inverse-vol allocator and CGT-defer logic.
- *Deliverable:* design doc + numerical-stability notes (Decimal/NumPy, weekly cadence).
- *Stop:* after the design.

**Prompt H — Model calibration audit**
- *Scope:* read-only.
- *Tasks:* assess `prob_up` calibration (reliability diagram, Brier); quantify how miscalibration shifts labels at 0.55/0.65; assess `expected_return` scale post-Prompt-A.
- *Deliverable:* calibration verdict + recalibration options (no change applied).
- *Stop:* after the verdict.

**Prompt I — Brief signal-display truthfulness QA**
- *Scope:* read-only review of `compose.py` + `brief.html.j2`.
- *Tasks:* enumerate every founder-facing signal claim; flag where labels show without `prob_up`/`confidence`/regime/caveat; propose truthful display copy.
- *Deliverable:* QA report + proposed caveat strings (no edits).
- *Stop:* after the report.

**Prompt J — Opus red-team of the ASXOS quant roadmap**
- *Scope:* adversarial review of this guide.
- *Tasks:* attack the benchmark ladder, phase ordering, and "useful vs coin flip" classification; find where ASXOS could fool itself (in-sample IC, survivorship, cost optimism, multiple testing).
- *Deliverable:* red-team memo — the 5 most likely self-deceptions and guards.
- *Stop:* after the memo.

**Prompt K — Create ASXOS quant operating manual docs pack**
- *Scope:* documentation only under `docs/strategy/`.
- *Constraints:* docs-only branch; no production change.
- *Tasks:* consolidate this guide + the research-program acceptance criteria into a living "quant operating manual" (runbooks for verification, evaluation, promotion, kill).
- *Deliverable:* docs pack + commit + push (no merge).
- *Stop:* after push.

**Prompt L — Implement first baseline/evaluation module (AFTER APPROVAL)**
- *Scope:* implement `research/baselines.py` + `research/metrics.py` (rank IC, quintile spreads) **read-only against production tables**, writing only research artefacts.
- *Hard constraints:* must not write `signals`/`portfolio_*`/any production table; no migrations; no threshold/model change; behind a `research/` package; full unit tests; **requires explicit human approval before starting.**
- *Tasks:* implement baselines + IC/quintile metrics per Prompts B & C; reproduce one month's IC; commit on a feature branch.
- *Deliverable:* tested module + an evaluation report comparing the live signal to baselines.
- *Stop:* after tests pass and the report is delivered; do not merge.
