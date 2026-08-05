# Market trends report — month & week to 2026-08-04

Generated 2026-08-05 from the asxos data pipelines. Anchors: month = 2026-07-03,
week = 2026-07-28, latest = 2026-08-04.

**Scope.** Descriptive market and pipeline analysis. No Model A output is used
anywhere (CLAUDE.md rule #11 — the ML engine is shelved and quarantined). Nothing
here is a buy, sell, or hold recommendation.

Rendered version: published as a Claude artifact (HTML source at
`docs/assets/market-trends-report-2026-08-05.html`).

---

## 1. CRITICAL — `ingest_news` reports success while writing zero rows

`holding_news` contains **zero rows**. Every `ingest_news` run from 2026-07-06 to
2026-08-04 (22 runs) recorded `status='success'` with `rows_written = 0`. There is
no article-level news in this system for the past month, the past week, or at all.

**Root cause** — `jobs/ingest_news.py:156`:

```python
is_ok=lambda r: isinstance(r, int) and r >= 0,
```

`_fetch_and_upsert()` catches every exception and `return 0` (line 70). Because
`0 >= 0` is true, a run in which *every symbol fails* scores 100% healthy and
passes the `threshold=0.75` gate in `assert_partial_success`. **The job cannot
fail.** This is the failure mode CLAUDE.md non-negotiable #10 exists to prevent.

### Consequence: the news brief was signed off on this green

`docs/product/dark-launch-exit-plan.md` ships surface #2 on ship condition (a):
*"`job_runs` shows `ingest_news` status='success' every scheduled business day for
3+ weeks … zero failures."* That is precisely the signal the bug fabricates.
`render.yaml:414` now carries `ASXOS_NEWS_BRIEF_ENABLED = "1"`. The verification
checked job status; it never checked row count. When the flag takes effect the
news section renders empty.

### Related, but expected — not bugs

- `signal_sentiment` is empty because it aggregates from `holding_news` (empty),
  and EODHD `/sentiments` has no ASX coverage on the current plan tier
  (documented REV-K pivot, 2026-05-24).
- `rs_factor_scores` covers 11 symbols with every factor scoring 0.000 — no factor
  lens is available. Excluded from this report rather than reported as noise.

---

## 2. Relevant news: two RBA items in six weeks

The only working news-type ingest is `ingest_regulatory` (RBA RSS; Treasury and
ATO removed as dead feeds). Two items total, neither inside the past week:

| Published | Source | Item |
|---|---|---|
| 2026-07-08 | RBA | A2A Payments Roundtable releases vision for account-to-account payments in Australia |
| 2026-06-25 | RBA | Review of Payments System Regulation commences |

Both are payments-infrastructure regulation — directionally relevant to the one
theme the system has an approved view on (Big 4 Banks), but two RSS headlines are
not a news signal and neither mentions a held symbol. **There is no evidentiary
basis in this system for a news-driven narrative this month.** Everything below is
derived from prices and market context, which are healthy.

---

## 3. The shape of the move: narrow bank-led month, broad growth-led week

| | Month (3 Jul → 4 Aug) | Week (28 Jul → 4 Aug) |
|---|---|---|
| ASX 200 (cap-weighted) | **+3.41%** (8,844 → 9,146) | **+2.21%** |
| Median liquid stock (n=515) | **+0.53%** | **+1.65%** |
| Breadth (% advancing) | 53% | 69% |

Over the month the index gained **6.4×** what the median liquid stock did, with
barely half of names advancing — a narrow, top-heavy grind. The industry table
identifies the engine precisely: **Banks +8.5%**, the heaviest index weights.

In the last week the gap closes hard: the median stock captures three-quarters of
the index move and breadth jumps to 69%. Participation broadened materially, and
into different sectors than led the month.

**Breadth caveat.** Long-horizon breadth did *not* repair. `pct_above_200d_ma`
moved only 25.9% → 26.8% and never crossed its 40% threshold on any of 24 days.
`pct_above_50d_ma` improved sharply (30.4% → 40.2%). The rally is broad on a
one-quarter lookback and still narrow on a one-year lookback — 73% of the market
remains below its 200-day average.

---

## 4. Sector performance — the leadership table inverted in five sessions

Median return of liquid names per sector (≥ A$250k average daily turnover,
close > $0.02). Median, not mean, so no single outlier carries a sector.

| Sector | n | Month | Week | Breadth 1M | Breadth 1W |
|---|---|---|---|---|---|
| Consumer Cyclical | 41 | **+6.24%** | +2.60% | 76% | 73% |
| Communication Services | 16 | +4.74% | +2.19% | 81% | 88% |
| Consumer Defensive | 17 | +3.70% | +0.88% | 88% | 53% |
| Real Estate | 36 | +2.59% | +1.70% | 72% | 72% |
| Technology | 34 | +1.93% | **+5.80%** | 62% | 88% |
| Utilities | 8 | +1.79% | −0.26% | 63% | 38% |
| Financial Services | 83 | +1.45% | +0.97% | 64% | 70% |
| Healthcare | 39 | +0.97% | +2.82% | 56% | 77% |
| Energy | 26 | −0.48% | +0.75% | 50% | 50% |
| Industrials | 55 | −1.40% | +1.22% | 42% | 65% |
| Basic Materials | 151 | **−5.17%** | +1.85% | 30% | 65% |

**Technology went from 5th to 1st and Healthcare from 8th to 2nd.** Both moves are
broad, not single-name: Tech breadth 88% (n=34), Healthcare 77% (n=39). Utilities
is the only negative sector on the week and the only one below 50% breadth (38%).

**Basic Materials is the swing factor** — worst sector of the month (−5.17%, 30%
breadth), then positive on the week (+1.85%) with breadth more than doubling to
65%. A genuine participation reversal, not a dead-cat print in a few large caps.

---

## 5. Industry detail (GICS, ≥ A$1m ADT)

| Industry | n | Month | Week |
|---|---|---|---|
| Banks | 12 | **+8.5%** | +1.6% |
| Professional Services | 5 | +8.3% | +2.4% |
| Hotels, Restaurants & Leisure | 9 | +6.2% | +4.2% |
| Specialty Retail | 6 | +6.0% | +5.3% |
| Food Products | 9 | +5.3% | −2.6% |
| IT Services | 4 | +4.8% | +6.2% |
| Software | 10 | +4.4% | **+8.5%** |
| Health Care Providers & Services | 7 | +4.2% | +1.2% |
| Diversified REITs | 17 | +4.1% | +2.1% |
| Insurance | 9 | +3.7% | −0.5% |
| Retail REITs | 7 | +2.9% | +1.0% |
| Oil, Gas & Consumable Fuels | 18 | +1.8% | +1.6% |
| Diversified Telecom Services | 8 | +1.6% | +1.1% |
| Biotechnology | 7 | +1.0% | +2.4% |
| Health Care Equipment & Supplies | 7 | +0.7% | +4.6% |
| Commercial Services & Supplies | 6 | +0.1% | +1.6% |
| Electronic Equipment & Components | 4 | −0.2% | +1.8% |
| Capital Markets | 21 | −0.3% | +1.9% |
| Construction & Engineering | 7 | −1.0% | +1.5% |
| Metals & Mining | 82 | **−5.6%** | +2.0% |

**Banks +8.5% is the month** — it reconciles the whole picture. Note the
deceleration: Banks contributed only +1.6% in the final week, *below* the +1.65%
median stock. The engine that drove the month stopped leading in the week.

**Software +8.5% on the week** (vs +4.4% month) is the sharpest acceleration in
the table, with IT Services +6.2% behind it.

### Metals & Mining — the median hides everything that matters

Month-return distribution across 82 liquid names:

| p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|
| −22.7% | −14.0% | −5.6% | −0.4% | +12.5% |

A **35-point spread** between the 10th and 90th percentile inside one industry.
"Avoid resources" and "buy the dip in resources" are both wrong framings —
dispersion this wide means the sector call is nearly worthless and the name-level
call is nearly everything.

---

## 6. Movers (≥ A$2m ADT)

**Week leaders:** APX.AU +52.0% (Tech, +42.2% month), 4DX.AU +32.3% (Health),
PYC.AU +22.8% (Health), VMM.AU +21.1% (Materials), CU6.AU +18.9% (Health),
SKS.AU +18.7% (Industrials), DMP.AU +16.8% (Cons Cyc), BMN.AU +16.5% (Energy),
ELS.AU +15.7% (Tech), DRO.AU +15.2% (Industrials).

**Month laggards:** WBT.AU −44.3% (Tech), LTR.AU −39.6% (Materials),
AYA.AU −34.4% (Health), ELV.AU −27.9%, ARU.AU −26.0%, EOS.AU −25.5%,
IPX.AU −24.6%, DVP.AU −22.7%, KCN.AU −21.9%, CNI.AU −20.6%.

Six of the ten worst month performers are Basic Materials — and the sector's
biggest month gainers (BNZ +48.8%, CNB +27.5%, MLX +25.9%) sit in the same
industry. The 35-point dispersion made concrete.

> APX.AU +52.0% in a week and +42.2% over the month means the entire month's gain
> arrived in the last five sessions. A move that size is normally an announcement
> — and this system has no news row to explain it. That is the cost of §1.

---

## 7. Macro backdrop — regime says risk-off, tape says otherwise

The classifier reads `risk_off_orderly` on all 24 days, but on a **single firing
rule**: `breadth_200_thin` (26.8% vs 40% threshold). Every other rule stayed
quiet, and two cannot fire at all.

**Unit bug — the credit-stress rules are dead switches.** `hy_oas_elevated` and
`hy_oas_stress` compare `us_hy_oas`, stored in **percent** (2.78), against
thresholds in **basis points** (450 / 600). Spreads would need to reach 450
*percent* to trip. "No credit stress signal" therefore carries no information.

| Metric | 3 Jul | 28 Jul | 4 Aug | Month Δ | Confidence |
|---|---|---|---|---|---|
| ASX 200 | 8,844.40 | 8,947.80 | 9,145.80 | +3.41% | good |
| % above 50d MA | 30.36% | 35.66% | 40.21% | +9.85pp | good |
| % above 200d MA | 25.88% | 25.28% | 26.81% | +0.93pp | good |
| AVIX | 11.191 | 11.162 | 11.546 | +0.36 | good |
| AUD/USD | 0.6940 | 0.6977 | 0.7044 | +1.50% | good |
| US 10y–2y | 0.35 | 0.34 | 0.45 | +10bp | good |
| VIX | — | 18.21 | 16.50 | n/a | partial (NULL to 07-09) |
| AU 10y yield | 4.990 | 4.831 | 4.831 | −15.9bp | **frozen 14 sessions** |
| RBA cash rate | — | 4.350 | 4.350 | n/a | **suspect (4bp step)** |
| Iron ore 62% Fe | — | — | — | n/a | **dead (0/24)** |

- **Iron ore has never had a value** — `IRON.COMM` returned HTTP 404 on all 24
  days. Any iron-ore narrative about the Materials drawdown would be unsourced.
- **AU 10y frozen** at 4.831 for 14 consecutive sessions; the −15.9bp move is one
  step, not a trend.
- **RBA cash rate stepped 4.310 → 4.350 on 2026-07-16** — a 4bp move the RBA does
  not make. Both series stepped on the same date and pinned afterwards: source
  swap or backfill, not two market events.
- **Cadence defects** — every Friday missing (07-10, 07-17, 07-24, 07-31), five
  phantom Sunday rows, at least two verbatim carry-forwards. 24 rows cover ~19
  distinct sessions.

---

## 8. Scoring our own macro theses against the tape

| # | Claim | Status |
|---|---|---|
| 6 | Breadth-led catch-down — index converges *down* toward its median constituent | **Going against.** Not falsified (needs breadth ≥50% for 10 days; it is 26.8%), but the index moved the opposite way: +3.41% to a period high of 9,146 vs the ≤8,400 its catalyst wanted. |
| 7 | Sticky ~5% AU long end keeps duration pressure on ASX | **Untestable.** Catalyst reads as met (4.831 ≥ 4.75, breadth <40%) — but the yield series is frozen for 14 sessions. Confirmed by a dead feed. Do not score. |
| 11 | Un-inverted US curve + benign credit — no near-term recession signal | **Tracking.** Spread positive and steepening (+0.35 → +0.45). Caveat: its falsifier ("HY OAS above 450") can never fire — same percent-vs-bps unit bug. |

(Thesis 10 is `rejected`, excluded.)

One thesis is contradicted by the tape, one is unscoreable because its input is
stale, one is tracking but carries an unfalsifiable leg. Thesis #6's core
observation holds — 73% of the market is below its 200-day average and the median
stock did +0.53% — but its directional call has not happened. Its September
deadline is the moment of truth.

---

## 9. Which segments deserve attention

- **Technology, on breadth rather than price.** The +5.80% weekly median matters
  less than the 88% breadth behind it, up from 62% over the month. Software
  (+8.5%) and IT Services (+6.2%) are the engine. Caution: one month is not a
  trend, and WBT.AU at −44.3% shows the sector still carries violent single-name
  risk.
- **Consumer Cyclical is the only sector in the top three of both windows**
  (+6.24% month, +2.60% week) with breadth in the 70s throughout — the most
  persistent, least reversal-dependent trend in the data. Specialty Retail
  (+6.0%/+5.3%) and Hotels & Leisure (+6.2%/+4.2%) sit consistently underneath.
- **Healthcare deserves a look precisely because it was ignored** — 8th on the
  month, 2nd on the week, breadth 56% → 77%. Health Care Equipment +0.7% → +4.6%.
  An early rotation candidate on one week of evidence only.
- **Basic Materials is a stock-selection question, not a sector call.** The
  breadth reversal (30% → 65%) is real, but 35-point dispersion means the median
  tells you almost nothing — and the work is handicapped by iron ore having no
  price in the system.
- **Watch Banks for the rotation-out.** The month's engine (+8.5%) trailed the
  median stock last week (+1.6% vs +1.65%). If that persists, the index's
  cap-weighted advantage closes — which is also the mechanism thesis #6 awaits.

---

## 10. Positioning — the portfolio owns none of this

| | |
|---|---|
| Positions | **1** (target 20 under the balanced profile — 19 short) |
| Sole holding | **HUBS.NYSE** — 24 sh, Technology, USD, **100% weight** |
| Value | A$8,480.07 (US$248.89 close × 24 ÷ AUDUSD 0.7044, 2026-08-04) |
| Return | **+32.7% USD**, +21.5% AUD after FX |
| Cash | A$0.00 · ASX exposure 0.0% · no franking credits |

100% of capital in one name, one sector, one currency, unhedged. Against the
active *balanced* profile that is a 10× breach of the 10% per-name cap and a 70pp
breach of the 30% sector cap.

**This is not a discipline failure.** `thesis_revisions.revision_id=13` records the
position as sitting in a locked employee-share-scheme window — non-disposable,
with the 2026-07-03 stop breach explicitly logged as monitor-only. The
concentration is involuntary and documented. What is missing is any funded
expression of anything else.

### The theme layer describes 0% of invested capital

- The one approved theme, `big-4-banks` (medium conviction), maps to **CBA.AU,
  which is not held** — thesis 1 is `watching`, and its 42.00–45.00 entry band sits
  ~300% below the 180.72 close, so the band is stale and unusable. Its
  `theme_holdings` row is still `draft`, never promoted.
- HUBS carries theme tags `us-saas-ai` and `us-equities`, and **neither exists as
  a row in `themes`**.

So the segment the system has an opinion about is unowned, and the segment holding
100% of the capital is undeclared. The irony runs both ways: **Banks — the theme
with an approved view but no ownership — was the best industry of the month
(+8.5%). Technology — holding all the capital by accident of an ESPP — was the
best sector of the week (+5.80%).** Both calls were right; neither was expressed
on purpose.

Of the three approved macro theses, two have no expression, and #7 (sticky long
end, pressure on long-duration assets) is arguably *inverted* by the book — a
high-multiple US SaaS name is the most duration-sensitive equity type available.
Only #11 is directionally consistent. The eleven remaining theses are `research`
stubs auto-seeded from paper-build run 1 with degenerate entry bands and no
stop/target — **no thesis is currently in-band**, so zero cash is not what blocks
deployment; the absence of a governed candidate set is.

**Data-integrity items surfaced here.** `profiles.capital_aud` (6,666.98) is stale
against the snapshot's 8,224.65 — weights computed off the profile would show the
position at ~127% of capital. And the lot's 0.6450 acquisition FX is still flagged
in `thesis_revisions.revision_id=13` as conflicting with the vendor rate for
2026-05-31 (0.7171); CLAUDE.md records it as confirmed against the brokerage
statement. At the vendor rate the AUD return would be +35.1% rather than +21.5%.
The USD leg is unaffected.

---

## 11. Pipeline fixes, in priority order

| # | Fix | Location | Why |
|---|---|---|---|
| 1 | Make `ingest_news` able to fail | `jobs/ingest_news.py:70,156` | Predicate `r >= 0` accepts total failure. Use `r > 0`, or return `None`/re-raise from `_fetch_and_upsert` so failures are distinguishable from genuine zero-news days. |
| 2 | Re-check the news-brief ship decision | `render.yaml:414` | `ASXOS_NEWS_BRIEF_ENABLED="1"` was approved on the green fix #1 exposes as false. Revert to "0" or gate the flip on a row-count assertion. |
| 3 | Diagnose the actual EODHD `/news` failure | `asxos/ingestion/news.py` | Fix #1 makes the failure visible; it does not explain it. Plan-tier coverage is the likely candidate given the known `/sentiments` ASX gap. |
| 4 | Correct the HY OAS unit mismatch | `migrations/0013_market_context.sql` | Percent-vs-bps comparison makes two regime rules and one thesis falsifier permanently unfirable. |
| 5 | Repair or drop the `IRON.COMM` feed | `jobs/ingest_market_context.py` | 404 on 24/24 days; most consequential missing input for a Materials-heavy universe. |
| 6 | Investigate frozen AU 10y + 4bp cash-rate step | `jobs/ingest_market_context.py` | Both pinned since 2026-07-16. Thesis #7 is scored against a dead series. |
| 7 | Fix missing-Friday / phantom-Sunday cadence | `jobs/ingest_market_context.py` | Friday sessions appear stamped with a Sunday `as_of`; 24 rows cover ~19 sessions. |

**General guard.** Add a `rows_written > 0` assertion to the deadman pattern.
`check_cron_health` watches job *status*, and status is exactly what was fabricated
here — the same class of bug can hide in any job whose success predicate accepts
zero.

---

## Sources

All figures computed from `prices` (733,719 rows to 2026-08-04), `universe`,
`rs_security_master` (GICS industry), `market_context` (24 rows),
`regulatory_events`, `job_runs`, `themes`, `theme_holdings`, `macro_theses`,
`theses`, `holding_lots`/`current_holdings`, `fx_rates`, `profiles`.

Sector and industry figures are **medians of liquid names, not cap-weighted index
returns** — they will not reconcile to published sector indices and are not
intended to.

Agents used: `market-context-narrator` (§7 backdrop and feed reliability),
`portfolio-coherence-reviewer` (§10 exposure and theme coherence).
