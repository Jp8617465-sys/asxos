# 06 — Signal Correctness Risks (with modern ASX evidence)

Each risk classified **CONFIRMED / LIKELY / POSSIBLE / REFUTED / UNKNOWN**. Verification is read-only; no fix applied. Modern (2021–2026) sources strengthen Risks 2 and 4.

---

## Risk 1 — `expected_return` units mismatch — **LIKELY · CRITICAL**
- **Evidence:** target trained in basis points — `y_reg = forward_return * 10_000.0` (`train.py:134`); inference returns it unscaled (`model_a.py:43`); thresholds compare to fractions (`expected_return > 0.05`, `thresholds.py`).
- **Why LIKELY:** depends on the persisted `v1_5` regressor scale — needs the artefact or `signals.expected_return` distribution (DB) to confirm.
- **Severity:** CRITICAL — if bps, `> 0.05` is trivially true and the magnitude arm of every label **degenerates to a sign check**; labels become `prob_up`-driven.
- **Affected:** all `signal_label`; the brief's implied "two-signal agreement."
- **Misleading now?** Possibly — STRONG_BUY may not require a 5% expected move.
- **build_portfolio?** Ranking **not** affected (allocator z-scores `expected_return`, scale-invariant); only the label filter + brief.
- **Next action:** SELECT percentile distribution of `signals.expected_return`; inspect `metrics.json` RMSE scale. **Do not change code.** (Prompt A.)

## Risk 2 — Raw `close` vs `adj_close` — **CONFIRMED · HIGH (ASX-elevated)**
- **Evidence:** loader selects raw `p.close` (`loader.py:119,134`); `adj_close` exists, unused; target also raw (`train.py:73`).
- **Modern ASX evidence:** fully-franked ex-dates, rights/bonus issues, consolidations are frequent on the ASX and manufacture spurious 1–5 day returns into a 5-day model — best practice is unambiguous: **generate on the adjusted series** (EODHD academy; backtest-practice literature 2023). This raises the v1 severity from MED–HIGH to **HIGH** for an ASX system.
- **Affected:** all price features + the 5-day target → every label.
- **build_portfolio?** Indirect (feature/label quality).
- **Next action:** sample known-corporate-action ASX symbols, compare raw vs `adj_close` ex-date spikes; recommend adopting `adj_close` (research first, then scoped change + retrain). **#1 ASX fix.** (Prompt A.)

## Risk 3 — `latest_complete_trading_day` / recency — **REFUTED (largely fixed) · LOW residual**
- **Evidence:** anchor (`dcb0461`) + recency gate (`a719b3c`) + completeness logging (`fe406d8`). Residual: calendar-day (not trading-day) staleness; rare >5-day closures mitigated by `--as-of`/`--allow-stale-upstream`.
- **Modern note:** the Dec-2024 CHESS batch-settlement failure (RBA 2025) shows ASX data plumbing can fail — the existing kill-switch/deadman discipline is the right posture.
- **Next action:** none now; revisit with a trading calendar.

## Risk 4 — Survivorship / universe — **CONFIRMED · HIGH (research)**
- **Evidence:** `is_active=TRUE` applied to historical rows in training (`retrain_model_a.py:104`) and the loader (`loader.py:132-143`).
- **Modern evidence:** Hou-Xue-Zhang / Novy-Marx-Velikov show anomaly alpha concentrates in small/illiquid names and vanishes value-weighted, net-of-cost; **and there is no Australian small-cap premium** (Small Ords lagged ASX 100 since ~2000). So survivorship bias compounds with an *uncompensated* small-cap tilt — doubly inflating any backtest.
- **Affected:** training data, the claimed AUC, future backtest IC/return.
- **build_portfolio?** Indirect (model quality).
- **Next action:** `universe_history` / as-of membership + delisting returns; liquidity-filter the universe. Required before L3. (Prompt D/E.)

## Risk 5 — `signal_outcomes` unread — **CONFIRMED dead-end · MED**
- **Evidence:** `track_signal_outcomes.py` writes `actual_return_5d/21d`, `was_direction_correct`; **no code reads `signal_outcomes`.**
- **Contamination risk:** outcomes depend on raw-close prices (Risk 2) and survivorship universe (Risk 4); entry/exit close selection + horizon must be re-verified before trusting them.
- **Next action:** provenance review + read-back into a rolling rank-IC/hit-rate brief footnote. (Prompt E.)

---

## Summary
| Risk | Class | Severity | Misleading now? | build_portfolio? | First action |
|---|---|---|---|---|---|
| 1 `expected_return` units | LIKELY | CRITICAL | possibly (labels) | no (z-scored) | verify distribution |
| 2 raw vs adj close | CONFIRMED | HIGH (ASX) | subtly | indirect | adopt adj_close |
| 3 stale-date | REFUTED | LOW | no | no | none |
| 4 survivorship | CONFIRMED | HIGH | optimistic AUC | indirect | universe_history + liquidity filter |
| 5 outcomes unread | CONFIRMED | MED | omits accuracy | no | read-back monitor |

**Order:** Risk 1 (cheapest, gates label trust) → Risk 2 (#1 ASX fix) → Risks 4–5 inside the evaluation harness. Risk 3 is effectively done.
