# 07 — ASXOS Benchmark Ladder (L0 → L5, modern acceptance criteria)

ASXOS is solidly **L0**, partially **L1**, reaches into **L5** on plumbing — but the **L2/L3/L4 evidence core is missing**. Acceptance criteria are upgraded to the 2021–2026 bar (rank IC, Deflated Sharpe, PBO, CPCV, net-of-cost, Open-Source-Asset-Pricing baselines).

## L0 — Operational — ✅ MET
*Evidence:* jobs run, data fresh, signals written, brief honest. *Status:* recovery GREEN; deadman + backup; recency gate (`a719b3c`). *Accept:* green `job_runs`, healthy deadman.

## L1 — Data-trust — 🟡 PARTIAL
*Evidence:* adjusted prices, complete-day anchor, PIT universe, no partial/stale gen. *Status:* anchor + recency done; **raw close + survivorship remain.** *Next:* adopt `adj_close`; `universe_history`; liquidity floor. *Accept:* features/target on `adj_close`; backtests include delisted names; ex-date artefacts gone.

## L2 — Baseline-beating — ❌ NOT MET
*Evidence:* beats equal-weight, **12-1 momentum**, trend, naive value/quality, prior-signal persistence — measured by **rank IC + net-of-cost decile spread**, benchmarked against the **Chen-Zimmermann Open Source Asset Pricing** library. *Status:* no baselines, no IC. *Next:* baseline suite + IC/decile metrics (`08` P1–P2). *Accept:* signal's rank IC and net-of-cost decile spread **exceed every baseline** over a multi-year sample.

## L3 — Research-grade — ❌ NOT MET
*Evidence:* OOS, **purge/embargo → CPCV**, costs, turnover, liquidity, regime/sector/size splits, survivorship controls, **Deflated-Sharpe-significant** for the trial count, **PBO < ~0.2–0.5**. *Status:* 5-fold no purge; no costs; survivorship-biased. *Next:* backtest framework (`08` P3). *Accept:* positive net-of-cost IC/spread OOS, deflated-significant, stable across regimes/sectors, FDR-controlled.

## L4 — Portfolio-useful — ❌ NOT MET
*Evidence:* improves a paper portfolio's after-cost, after-tax risk-adjusted return / drawdown / TE; handles liquidity (ADV cap) and CGT; stable for decision support; ideally **uncertainty-gated deployment**. *Status:* `build_portfolio` exists (inverse-vol) but unproven; `paper_trade.py` "not a backtester." *Next:* denoised-covariance HRP/Schur sizing + paper book + attribution (`08` P4). *Accept:* shadow book beats equal-weight/momentum paper books on **after-cost, after-tax IR or drawdown** OOS.

## L5 — Production-governed — 🟡 PARTIAL
*Evidence:* monitored (drift + rolling IC), outcome-tracked, kill criteria, promotion/demotion gates, human-approval boundaries. *Status:* statistical promotion gates + JobMonitor + personal-use firewall; **but `signal_outcomes` unread, no kill criteria, ungated activation.** *Next:* read-back + Evidently drift + IC/cost promotion gate + kill rules + re-validate on `model activate` (`08` P5). *Accept:* rolling rank IC tracked + alarmed; economic promotion gate; documented kill criteria; activation re-validates.

---

**Ladder principle (reinforced by modern evidence):** **L5 governance over an unmeasured signal is theatre.** The 2021–2026 literature is unanimous that the binding constraints are *evaluation discipline* (purge/CPCV, rank IC, net-of-cost, deflated significance) and *data trust* (adjusted prices, survivorship, liquidity) — exactly L1–L3. Climb the evidence levels; keep the strong L0/L5 plumbing.
