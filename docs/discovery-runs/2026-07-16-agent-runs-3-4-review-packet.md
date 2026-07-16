# Review packet — agent_runs #3 & #4 (macro theses) — for James

**Why this exists:** the red-team's sharpest finding on the idea-generation
lane was that **review throughput, not generation, is the bottleneck** — two
`macro-economist` proposals have sat `acted_on=false` since **2026-07-03
(13 days)** with no resolution. Adding a producer (sector-screener) to a queue
nothing is draining just grows the backlog. So before shipping more generation,
here is the packet to clear these two, one way or the other.

**Your decision, per run:** `open + approve` · `open + reject` · `re-run the
agent now that more data exists` · `leave pending`. Nothing here is auto-acted.

Both are `object_type=macro_thesis`, 0 speculative claims (10 verified /
3 inferred each), evidence intact. Both were built on the **first-ever market
snapshot (2026-07-03)** with single-day history and, at the time, several dead
feeds — a caveat the agent stated in both.

---

## The 13-day check: have the theses' own catalysts/falsifiers moved?

I re-pulled `market_context_current` (2026-07-15) against the 2026-07-03 values
each thesis hinges on. **Neither has been falsified; both core conditions still
hold — and the feed both flagged as broken is now live.**

| Signal | 2026-07-03 (thesis basis) | 2026-07-15 (now) | Bearing |
|---|---|---|---|
| regime_label | risk_off_orderly | risk_off_orderly | unchanged |
| asx200_close | 8,844.40 | 8,841.10 | flat (−0.04%) |
| pct_above_200d_ma | 0.259 | 0.264 | **still < 0.40** — both catalysts' shared condition holds |
| pct_above_50d_ma | 0.304 | 0.363 | modest breadth repair (watch vs Thesis 1 falsifier: needs ≥0.50 × 10 days) |
| avix | 11.19 | 11.15 | still calm; nowhere near the 22 elevated trigger |
| aus_10y_yield | 4.99 | 4.99 | **unchanged — Thesis 2's "sticky ~5% long end" is holding at the level** |
| rba_cash_rate | **NULL (broken ticker)** | **4.31** | **now live** — Thesis 2's "curve slope unverifiable" caveat is now resolvable: 10y−cash = +68bps |
| us_hy_oas | ~275bps | 272bps | tight, consistent |

**The material change:** Thesis 2 explicitly rested on `rba_cash_rate` being
NULL ("the AU curve slope versus cash is unverifiable from the data"). That feed
is now populated (4.31%), so the slope IS now verifiable (+0.68% positive). That
is a reason to consider **re-running** rather than approving as-written — the
thesis's own stated data gap has closed, and a fresh run would evaluate the
slope it couldn't.

---

## Run #3 — "Breadth-led catch-down" (falling_growth_falling_inflation, 6mo)

- **Claim:** the ASX 200's strength is narrow (25.9% above 200d MA); over 6
  months the cap-weighted index de-rates toward its median constituent in an
  orderly disinflationary risk-off, vol repricing up from a complacent base.
- **Catalyst:** breadth stays < 0.40 through 2026-09-30 AND (index < 8,400 OR
  avix ≥ 22). **Status:** breadth still < 0.40 ✓; index 8,841 (not yet < 8,400);
  avix 11.1 (not ≥ 22). Catalyst partially progressing, not triggered.
- **Falsifier:** breadth ≥ 0.50 on 10 consecutive rows with index > 8,600.
  **Status:** breadth 0.264 — not close to falsified.
- **Evidence:** 13 claims (10 verified / 3 inferred), citation IDs [5,6,7,8,9,12,16].
- **Agent's own caveat:** all trend claims inferred from one day's
  cross-section; no time series; inflation leg is the weakest (no CPI field).
- **arbi read:** internally coherent, falsifiable, evidence-cited, and not
  contradicted 13 days on. Weakness is the single-snapshot basis, not the logic.

## Run #4 — "Sticky ~5% AU long end" (falling_growth_rising_inflation, 9mo)

- **Claim:** a ~5% nominal 10y coexisting with weak equity breadth and tight US
  credit is term-premium/inflation-compensation, not growth optimism; the long
  end stays restrictive for 9 months, pressuring long-duration ASX (REITs, tech,
  infra), favouring short-duration cash flow.
- **Catalyst:** 10y ≥ 4.75 through 2026-09-30 (or ≥ 5.25 at any point) with
  breadth < 0.40. **Status:** 10y 4.99 ✓, breadth 0.264 ✓ — **both legs
  currently satisfied.**
- **Falsifier:** 10y closes < 4.25 on 5 consecutive rows. **Status:** 4.99 —
  not close.
- **Evidence:** 13 claims (10 verified / 3 inferred), citation IDs [19,23,24,26,29].
- **Agent's own caveat:** persistence rests on one yield reading; `rba_cash_rate`
  NULL made the slope-vs-cash unverifiable. **← now resolved (4.31%).**
- **arbi read:** the stronger of the two on current data (both catalyst legs
  live), but the one most improved by a re-run — its central data gap has closed.

---

## arbi recommendation (advisory — you decide)

1. **Both are governance-valid** (0 speculative, evidence intact, falsifiable,
   uncontradicted). Neither should just keep sitting at `pending`.
2. **Cleanest path: re-run `macro-economist` now**, then compare. 13 days of
   history plus the now-live cash-rate feed mean a fresh run can evaluate what
   these two explicitly couldn't (a trend, a curve slope). Approving a thesis
   built on a single-day snapshot with a since-fixed data hole is the weaker
   move when a better-grounded version is one command away.
3. **If you'd rather clear the backlog directly:** #4 is the stronger approve
   candidate (both catalyst legs live today); #3 is a reasonable reject-or-hold
   (catalyst only partially progressing, single-day basis).

**Commands (attended, your call — not run here):**
```
# Re-run, then review the fresh proposals:
/discover-macro

# Or act on the existing ones:
asx macro-thesis open --from-agent-run 3   # then: asx macro-thesis approve <id> --reason "..."
asx macro-thesis open --from-agent-run 4
# (reject path: asx macro-thesis open then the reject verb, with a reason)
```

Firewall note: this packet summarises the agent's evidence and the data's
movement. It is not a market call or capital recommendation (s766B) — the
approve/reject/re-run decision, and any capital that ever follows, is yours.
