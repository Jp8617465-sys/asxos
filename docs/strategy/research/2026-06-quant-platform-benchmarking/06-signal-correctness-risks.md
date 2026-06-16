# 06 — Signal Correctness Risks

Each risk classified **CONFIRMED / LIKELY / POSSIBLE / REFUTED / UNKNOWN** with evidence, severity, affected outputs, whether current outputs are misleading, build_portfolio impact, and next action. Verification is **read-only**; no fix is applied here.

---

## Risk 1 — `expected_return` units mismatch — **LIKELY · CRITICAL**

- **Evidence:** training target is basis points — `y_reg = df["forward_return"].to_numpy() * 10_000.0  # in basis points` (`train.py:134`). Inference returns it **unscaled** — `expected_return = model.regressor.predict(X)` (`model_a.py:43`). Thresholds compare to **fractions** — `expected_return > 0.05` etc. (`thresholds.py`). The three are mutually inconsistent if the live `v1_5` regressor was trained on this path.
- **Why LIKELY not CONFIRMED:** it depends on the scale of the *persisted* `model_a_v1_5` regressor artefact, which requires inspecting the artefact or `signals.expected_return` magnitudes (DB) — not done here.
- **Severity:** CRITICAL. If `expected_return` is in bps (~tens/hundreds), `> 0.05` is satisfied by essentially any positive prediction, so the magnitude arm of every label **degenerates to a sign check**; labels become `prob_up`-driven and the "expected return > 5%" semantics in the spec are false.
- **Affected outputs:** `signal_label` (all labels), the brief's implied "two-signal agreement" framing.
- **Misleading now?** Potentially yes — STRONG_BUY may not require a 5% expected move at all.
- **build_portfolio impact:** **ranking is NOT affected** — `allocator.rank_candidates` z-scores `expected_return` (`allocator.py`), and z-scoring is scale-invariant. Only the **label filter** (`signal_label ∈ {STRONG_BUY,BUY}`) and the brief are affected.
- **Next action:** read-only verify — `SELECT` percentile distribution of `signals.expected_return` for `v1_5`; inspect `models/model_a_v1_5_metrics.json` RMSE scale; confirm the artefact's training path. **Do not change thresholds or code** until classified CONFIRMED/REFUTED. (Prompt A.)

---

## Risk 2 — Raw `close` vs `adj_close` — **CONFIRMED · MED–HIGH**

- **Evidence:** the panel loader selects raw `p.close` (and open/high/low/volume) at `loader.py:119` and `:134`; `adj_close` exists in `prices` (migration `0001`) but is **never referenced** by the feature/loader code. The training target also uses raw `close` (`train.py:73`).
- **Severity:** MED–HIGH. Corporate-action days (splits, rights, special/bonus dividends — frequent on ASX) inject spurious returns into momentum/vol/trend features **and** the target. Because both use raw close, train/serve are *consistent* (no skew) but both are *noisy*.
- **Affected outputs:** all price features; the 5-day forward target → indirectly every label.
- **Misleading now?** Subtly — momentum signals around ex-dates are contaminated; magnitude unknown without measurement.
- **build_portfolio impact:** indirect (via feature/label quality), not a direct break.
- **Next action:** read-only — sample known-corporate-action symbols, compare raw vs `adj_close` return spikes on ex-dates, quantify contamination. Recommend adopting `adj_close` in features + target (research first, then a scoped change with retrain). (Prompt A.)

---

## Risk 3 — `latest_complete_trading_day` / recency — **REFUTED (largely fixed) · LOW residual**

- **Evidence:** `generate_signals` anchors on `latest_complete_trading_day` (`dcb0461`), with a no-complete-day gate and a recency gate that blocks when the complete day is > 5 calendar days stale (`a719b3c`). `sync_prices` logs completeness (`fe406d8`). Residue (12/14-row days) is classified, not trusted.
- **Severity:** LOW residual. The original stale-date risk is closed.
- **Residual:** staleness is **calendar-day**, not trading-day; a rare > 5-calendar-day market closure could block legitimately-latest data (mitigated by `--as-of` / `--allow-stale-upstream`). Documented v1 limitation.
- **Next action:** none required now; revisit when an ASX trading calendar source exists.

---

## Risk 4 — Survivorship / universe — **CONFIRMED · HIGH (for research/backtest)**

- **Evidence:** both training (`retrain_model_a.py:104`, `SELECT symbol FROM universe WHERE is_active = TRUE`) and the panel loader (`loader.py:132-143`, `... AND u.is_active = TRUE`) apply the **current** active flag to **all historical rows**. Delisted/failed symbols are excluded from history.
- **Severity:** HIGH for any backtest/evaluation; the model is trained on survivors.
- **Affected outputs:** training data, the claimed AUC, and any future backtest IC/return — all inflated.
- **Misleading now?** The headline AUC is optimistic by an unknown margin (a phase-2 doc estimates ~2-5%/yr inflation for backtests generally; not quantified for ASXOS).
- **build_portfolio impact:** indirect (model quality).
- **Next action:** a `universe_history` (point-in-time membership) table, or retain delisted rows as `is_active=FALSE` and join as-of. Required before L3 (research-grade). (Prompt D/E.)

---

## Risk 5 — `signal_outcomes` / outcome tracking — **CONFIRMED dead-end · MED**

- **Evidence:** `track_signal_outcomes.py` computes `actual_return_5d`, `actual_return_21d`, `was_direction_correct` (`= (close_21d > signal_close) == (prob_up > 0.5)`) and writes `signal_outcomes` idempotently. **No production code reads `signal_outcomes`** (grep finds only the writer) — no IC, hit-rate, calibration, or brief footnote consumes it.
- **Severity:** MED. The data needed to answer "do the signals work?" is being recorded and discarded.
- **Provenance/contamination risk:** outcome rows depend on the same raw-close prices (Risk 2) and survivorship universe (Risk 4); the entry/exit close selection and horizon must be re-verified before trusting it as ground truth.
- **Next action:** provenance review of `track_signal_outcomes` math + PIT safety, then read it back into a rolling IC/hit-rate monitor and a brief footnote. (Prompt E.)

---

## Summary

| Risk | Class | Severity | Misleading now? | build_portfolio? | First action |
|---|---|---|---|---|---|
| 1 `expected_return` units | LIKELY | CRITICAL | possibly (labels) | no (z-scored) | verify distribution (Prompt A) |
| 2 raw vs adj close | CONFIRMED | MED–HIGH | subtly | indirect | adopt adj_close (research) |
| 3 stale-date | REFUTED | LOW | no | no | none (revisit calendar) |
| 4 survivorship | CONFIRMED | HIGH (research) | optimistic AUC | indirect | universe_history |
| 5 outcomes unread | CONFIRMED | MED | omits accuracy | no | read-back monitor |

**Order of operations:** Risk 1 first (cheapest, highest-leverage, gates label trust), then Risk 2, then Risks 4-5 as part of the evaluation harness. Risk 3 is effectively done.
