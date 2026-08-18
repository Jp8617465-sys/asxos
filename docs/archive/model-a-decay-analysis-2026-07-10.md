# Model A decay analysis — 2026-07-10 (first pass)

**Status:** current
**Scope:** the P0 decay check prescribed by `session-handoff-2026-07-04.md §2`
**Method:** read-only SQL against live `signals` + `prices` (measuring Model A — outside
rule #11, which gates *acting on* the signal for capital, not *studying* it)
**Verdict:** interim — **keep the quarantine**; the 5-day edge is weak and unstable, the
21-day claim is not yet testable

---

## Data

`model_a`/`v1_5` (the only model): **33,932 signals, 20 dates (2026-05-20 → 07-09), 1,728
symbols.** `signal_outcomes` exists but is **empty** (the `track_signal_outcomes` cron hasn't
populated it), so forward returns were computed directly from `prices` (Jan 2025 → 07-09).
Coverage: **25,387** signal-rows have a 5-trading-day forward price; only **3,333 across ~2
usable dates** have a 21-day forward. The 21-day horizon is thin, exactly as the handoff
warned.

## Results

**Pooled cross-sectional (Pearson corr of signal vs realized forward return):**
| | 5-day | 21-day |
|---|---|---|
| `prob_up` vs forward return | **+0.013** | **−0.008** |
| `expected_return` vs forward return | +0.007 | +0.024 |

Both ≈ **zero** — `prob_up` explains ~0.02% of forward-return variance; the sign flips
negative by 21d but the magnitude is noise.

**Label buckets (raw mean forward return):** BUY/STRONG_BUY +2.33% (5d) / +3.99% (21d);
SELL/STRONG_SELL −0.13% (5d) / −0.09% (21d). Buys outperform sells — **but these are raw,
not benchmark-relative**, so the spread is plausibly market beta over a rising window, not
alpha. Needs a benchmark-relative recheck before it counts as evidence of edge.

**Per-date 5-day edge (`corr(prob_up, ret5)`) — the "swings around" test:**
```
05-20 −0.025 | 06-10 −0.075 | 06-15 −0.017 | 06-16 −0.002 | 06-17 −0.009 | 06-19 −0.017
06-22 +0.040 | 06-23 +0.040 | 06-24 +0.046 | 06-25 +0.043 | 06-26 +0.043
06-29 +0.110 | 06-30 +0.146 | 07-01 +0.065 | 07-02 +0.062
```
The edge **swings from −0.075 to +0.146** across dates — negative through mid-June, positive
from 06-22 (peak +0.146 on 06-30). Unstable and regime/time-dependent; never consistently
strong. Per-date 21-day edge has only 2 usable dates (−0.014, +0.028) — no signal.

## Verdict (interim)

1. **James's concern is supported at the 5-day horizon.** The cross-sectional edge is weak
   and sign-flipping date-to-date; there is no stable, tradeable predictive signal on this
   evidence. Pooled edge ≈ 0.
2. **The "completely swings around at 21 days" claim is NOT yet testable** — only ~2 dates
   have matured 21-day forward returns. It becomes testable ~**late August 2026**, when the
   July signals mature (matches the handoff's "inconclusive until ~late Aug" note).
3. **Rule #11 stays.** Nothing here clears Model A for capital; the evidence supports keeping
   the allocator path quarantined.

## Caveats (why this is a first pass, not the final walk-forward)

Raw returns (not benchmark-relative); pooled Pearson (Simpson's-paradox risk across dates);
no per-date **Spearman rank-IC** aggregation; overlapping forward windows; 21d under-powered.

## Recommended fuller study (the real resolution)

- Fix/run `track_signal_outcomes` so `signal_outcomes` populates (then this is a one-query
  check, not a manual join).
- Per-date **rank IC (Spearman)** with **benchmark-relative** returns (strip market beta).
- Re-run ~late Aug 2026 when July's 21-day outcomes exist.
- If IC stays weak/unstable → this is the `system-architect`/`backend-architect` conversation
  the handoff §3 prescribes (faster cadence / different horizon / different architecture),
  **not** a hyperparameter re-tune.

Governance: measurement only — supports keeping rule #11 in force. See
`docs/product/decision-log.md`.
