# 10 — Future Pasteable Prompts (A–L, modernised)

Each: scope · hard constraints · tasks · deliverable · stop. All read-only/design except L (implements after approval). Methods reflect 2021–2026 standards.

**Prompt A — Signal correctness: `expected_return` units & price basis**
- *Scope:* read-only verification (`06` R1 & R2). *Constraints:* no edits/commits/migrations/jobs/Render; SELECT-only DB; no threshold/code change.
- *Tasks:* trace `train.py:134` → `model_a.py:43` → `thresholds.py`; SELECT percentile distribution of `signals.expected_return`; inspect `metrics.json` RMSE scale; sample known-corporate-action ASX symbols comparing raw `close` vs `adj_close` returns around ex-dates.
- *Deliverable:* memo classifying units (bps/fraction) + adj_close contamination estimate + recommended fix path.
- *Stop:* after the memo.

**Prompt B — Factor baseline suite design**
- *Scope:* design `research/baselines.py` (read-only). *Constraints:* research-only.
- *Tasks:* specify equal-weight, 12-1 momentum (skip-month), 200-day trend, naive value, naive quality, persistence, random; define adj_close forward-return convention (5/21-day); integrate the **Chen-Zimmermann Open Source Asset Pricing** library as the benchmark.
- *Deliverable:* design doc + signatures + acceptance tests. *Stop:* after design.

**Prompt C — Rank IC / decile evaluation plan**
- *Scope:* design + test plan. *Tasks:* define rank IC (Spearman/date), ICIR, **net-of-cost** decile spread + monotonicity, hit rate; survivorship-safe `signals`↔forward-return join; trial counter for FDR.
- *Deliverable:* plan + acceptance (reproduce one month's IC by hand). *Stop:* after plan.

**Prompt D — Backtest harness audit & design (CPCV)**
- *Scope:* audit current validation + design research harness. *Tasks:* prove the leakage in the no-purge 5-fold split (Kapoor-Narayanan taxonomy); design **purge+embargo → CPCV** (Arian-Norouzi-Seco), as-of universe, liquidity floor, cost model, **Deflated Sharpe + PBO**, FDR.
- *Deliverable:* harness design + leakage proof + acceptance (PBO < ~0.2–0.5). *Stop:* after design.

**Prompt E — `signal_outcomes` provenance review**
- *Scope:* read-only. *Tasks:* audit `track_signal_outcomes.py` math/PIT safety; assess raw-close (R2) + survivorship (R4) contamination; design safe read-back for a brief footnote.
- *Deliverable:* provenance report + read-back design. *Stop:* after report.

**Prompt F — Paper portfolio / decision ledger design**
- *Scope:* design (research-only, no orders). *Tasks:* decision-ledger table for would-be `build_portfolio` trades, with cost/tax/CGT/franking assumptions + factor-vs-selection attribution + optional uncertainty-gated deployment.
- *Deliverable:* schema + attribution method + acceptance. *Stop:* after design.

**Prompt G — Risk model / liquidity overlay design (modern)**
- *Scope:* design. *Tasks:* specify **RMT/Ledoit-Wolf denoised covariance** → **HRP/Schur via `skfolio`** + **L1 turnover penalty** + ADV liquidity cap, integrating with sector/cash caps and CGT-defer; sector co-movement caps given ASX concentration.
- *Deliverable:* design doc + numerical-stability notes (weekly cadence). *Stop:* after design.

**Prompt H — Model calibration audit**
- *Scope:* read-only. *Tasks:* `prob_up` reliability diagram + Brier on a time-ordered held-out fold; quantify label shift at 0.55/0.65; post-units-fix `expected_return` scale check; isotonic vs Platt options.
- *Deliverable:* calibration verdict + recalibration options (no change). *Stop:* after verdict.

**Prompt I — Brief signal-display truthfulness QA**
- *Scope:* read-only review of `compose.py` + `brief.html.j2`. *Tasks:* enumerate founder-facing signal claims; flag missing `prob_up`/`confidence`/regime/caveat; propose truthful copy + realised-accuracy footnote.
- *Deliverable:* QA report + caveat strings (no edits). *Stop:* after report.

**Prompt J — Opus red-team of the v2 roadmap**
- *Scope:* adversarial review. *Tasks:* attack the ladder, phase ordering, "useful vs coin flip"; find self-deceptions (in-sample IC, survivorship + no-AU-size-premium, cost optimism, multiple testing, source-access caveats); challenge whether modern sources were applied correctly.
- *Deliverable:* red-team memo — top 5 self-deceptions + guards. *Stop:* after memo.

**Prompt K — ASXOS quant operating manual docs pack**
- *Scope:* documentation only under `docs/strategy/`. *Constraints:* docs-only branch; no production change.
- *Tasks:* consolidate this v2 guide + acceptance criteria into living runbooks (verification, evaluation, promotion, kill).
- *Deliverable:* docs pack + commit + push (no merge). *Stop:* after push.

**Prompt L — Implement first baseline/evaluation module (AFTER APPROVAL)**
- *Scope:* implement `research/baselines.py` + `research/metrics.py` (rank IC, net-of-cost decile spreads) read-only against production tables, writing only research artefacts.
- *Hard constraints:* must not write `signals`/`portfolio_*`/any production table; no migrations; no threshold/model change; behind a `research/` package; full unit tests; **requires explicit human approval before starting.**
- *Tasks:* implement per B & C; reproduce one month's IC; compare signal to Open-Source-Asset-Pricing baselines + 12-1 momentum; commit on a feature branch.
- *Deliverable:* tested module + evaluation report. *Stop:* after tests pass + report; do not merge.
