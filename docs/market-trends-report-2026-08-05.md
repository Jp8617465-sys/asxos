# Market trends report — month & week to 2026-08-04

Generated 2026-08-05 from the asxos data pipelines. Anchors: month = 2026-07-03,
week = 2026-07-28, latest = 2026-08-04.

**Scope.** Descriptive market and pipeline analysis. No Model A output is used
anywhere (CLAUDE.md rule #11 — the ML engine is shelved and quarantined). Nothing
here is a buy, sell, or hold recommendation.

Rendered version: published as a Claude artifact (HTML source at
`docs/assets/market-trends-report-2026-08-05.html`).

**Revision 2 (same day)** adds a live market/news layer fetched from outside the
system, and a live test of PR #70's impact.

---

## 0. LIVE TEST — run 2026-08-05, outside the system

| | |
|---|---|
| ASX 200 — live | **9,227.80**, +0.9%, record close 5 Aug (intraday 9,230) |
| ASX 200 — our DB | 9,145.80, stops 4 Aug — 82 points behind |
| Our regime label | `risk_off_orderly`, 24/24 days |
| Rules firing | **1 of 5** (`breadth_200_thin` only) |

**The regime label is now visibly contradicted by the tape.** The market printed an
all-time high while our classifier read `risk_off_orderly` for the 24th straight
day. That label was never a risk assessment — it is one rule firing alone, with two
of the other four structurally unable to fire (§7). The underlying observation is
still true and useful (73% of the market is below its 200-day average), but
**"risk_off_orderly" is the wrong label for it**, and anything downstream consuming
that string is being misled.

---

## 0b. LIVE NEWS — what the pipeline should have captured

Queried live to fill the gap. Every item is news our system had no row for, and
each independently corroborates a finding the price data produced blind.

**Past month**

- **Financials +5.85% in July, "the majority of the ASX 200's gains."** Derived
  independently from prices: Banks +8.5%, index +3.41% vs median stock +0.53%.
- **The lithium/battery-metals cycle reset** — lithium prices down, Chinese
  conversion capacity expanding, EV demand normalising. Liontown (LTR) fell 9.28%
  on 30 July as the materials index dropped 1.36%, driven by a steady-rates Fed
  decision and a firmer USD. Our data has LTR.AU at **−39.6%** for the month.
- **"Base and precious metals wipeout"** is the recurring wrap language for the
  month — matching Basic Materials −5.17% at 30% breadth.

**Past week**

- **APX.AU — the answer to §6's open question.** Appen released its **Q2 FY26
  quarterly report on 29 July**: revenue US$65.1m (+26% pcp), Appen China US$41.3m
  (+75%), FY26 guidance reaffirmed at US$270–300m. That is the announcement behind
  the +52.0% week. This is precisely the article the dead pipeline was supposed to
  deliver.
- **Tech ran six-to-seven consecutive sessions**, one at +3.9% for the IT index —
  Life360 +11.4%, Appen +6.0%, Catapult +6.0%, Megaport +5.7%. Our data: Technology
  +5.80% week, 88% breadth; 360.AU +13.2%.
- **Healthcare +2.4% in a session**, Neuren +17% on record quarterly DAYBUE sales
  and raised royalty guidance. Our data: Healthcare 8th → 2nd, +2.82%, breadth
  56% → 77%.
- **CBA fell 2.6% in a session** as traders cut exposure ahead of results —
  consistent with Banks decelerating to +1.6%, below the median stock.

**Forward catalysts — none of these exist anywhere in our data**

- **RBA decision Tuesday 11 August, 2:30pm AEST.** Consensus hold at 4.35%; CBA,
  NAB, ANZ and Westpac all moved to hold after June CPI printed 3.8% headline /
  3.6% trimmed mean. Westpac is the outlier, calling +25bp in August and September.
- **CBA FY26 full-year results Wednesday 12 August, 10:30am AEST.** Directly
  material to `big-4-banks` — the one theme the system has an approved view on and
  owns none of.
- **August reporting season is underway**, the mechanism behind most of §6's
  single-name dispersion.

The live cross-check also settles one data question: the real RBA cash rate is
4.35% and has been, so the stored 4.350 is the correct *value* but the 4.310 →
4.350 step on 2026-07-16 was definitively an ingestion artifact, not a policy move.

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

**The same fabricated field defeats a second, independent guard.** `compose.py`
documents three-layer gating on the news section, and layer 3 is a freshness check
— `_news_ingest_fresh()` (`compose.py:514-525`) queries `job_runs WHERE
job_name='ingest_news' AND status='success'`. That is the identical field the bug
forges. The ship condition and the runtime freshness gate are not two checks; they
are the same check twice, and one bug clears both.

### Consequence: the news brief was signed off on this green

`docs/product/dark-launch-exit-plan.md` ships surface #2 on ship condition (a):
*"`job_runs` shows `ingest_news` status='success' every scheduled business day for
3+ weeks … zero failures."* That is precisely the signal the bug fabricates.
`render.yaml:414` now carries `ASXOS_NEWS_BRIEF_ENABLED = "1"`. The verification
checked job status; it never checked row count.

**This is not pending — it is already live.** `ASXOS_NEWS_BRIEF_ENABLED = "1"` is
on `origin/main`, and `compose_brief` has run successfully 22 times in the last 30
days. `compose.py:507` gates the section on that flag, then calls `_holding_news()`
against an empty table. The daily brief has been shipping an **empty news section**
every day since the redeploy — a surface marked SHIPPED, rendering nothing.

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

**One genuinely open data-integrity item:** `profiles.capital_aud` (6,666.98) is
stale against the snapshot's 8,224.65 — weights computed off the profile would show
the position at ~127% of capital. The lot's 0.6450 acquisition FX, raised by the
coherence check against the 0.7171 vendor rate, is **already ruled and not open**:
both `.claude/rules/portfolio-conventions.md` and `docs/product/james-inbox.md:31`
record it as confirmed against the brokerage statement — an ESPP fill rate that
legitimately differs from spot. Not worth reopening.

---

## 10b. LIVE TEST — what changes if PR #70 merges

PR #70 — *"docs: add investment-engine implementation dossier"* — open as a
**draft** since 2026-07-25: 157 files, +39,974/−88, `mergeable_state: clean`, one
commit, base `main`. I read the full changed-file list across both pages (100 + 57
= 157 of 157).

| | |
|---|---|
| Doc files | 155 (143 under `docs/programs`) |
| Non-doc files | **2** — `scripts/validate_investment_program.py`, `tests/test_investment_program_dossier.py` |
| Broken pipelines touched | **0 of 6 checked** |
| Report findings changed | **0 of 11** |

**Answer: none of this report's findings change.** The PR touches none of
`jobs/ingest_news.py`, `asxos/ingestion/news.py`, `jobs/ingest_market_context.py`,
`asxos/jobs/_helpers.py`, `migrations/0013`, or `render.yaml`. Every finding here is
a runtime-data finding; a docs PR cannot move any of them.

**The one thing that does change: the false ship condition gets carried forward.**
PR #70 *does* edit `docs/product/dark-launch-exit-plan.md`, and substantially
rewrites **three of the four surfaces** — the portfolio brief's gate becomes the
S01–S12 acceptance chain, the V2 brief tree is re-scoped, and the paper-trade
evaluator is demoted to *"LEGACY PROTOTYPE · do not start its four-week promotion
clock."*

**Surface #2 — the news brief — is left verbatim.** Ship condition (a) still reads
*"status='success' every scheduled business day for 3+ weeks … zero failures,"* and
the summary table still carries **SHIPPED 2026-07-11 · both conditions verified**.
The merge would promote the false verification, untouched, into the new canonical
programme doc set. The document does flag its own limit in the header it adds
(*"individual legacy-surface facts still require live refresh"*) — honest, and
exactly the refresh this report performs — but that does not stop the SHIPPED
verdict propagating.

**The one code-risk, checked and cleared.** If `validate_investment_program.py`
asserted on the exit plan's text, merging would convert a wrong verdict into a green
test defending it. It does not: searching the full validator for `dark-launch`,
`NEWS_BRIEF`, `ingest_news` and `SHIPPED` returns **zero matches**. The five
`docs/product/*.md` files it references are `investment-engine-roadmap.md`,
`north-star.md`, `portfolio-manager-charter.md`, `portfolio-policy.md`,
`recommendation-schema.md` and `arbi-permission-model.md`. (Scope note: targeted
search of the whole file, not a full read of its ~223k characters.) The merge-order
dependency is lifted.

**On priority:** the dossier's programme raises the stakes on `ingest_news` rather
than lowering them. A *model-independent* PM review with Model A retired removes the
signal engine as an input and leaves news, market context and price as the surviving
evidence layer. Fix #1 gets *more* load-bearing under this programme, not less.

Merge approval is James's call, not arbi's. Nothing here argues against merging —
only against letting surface #2 ride along unamended.

---

## 11. Pipeline fixes, in priority order

**Re-ranked — the honest case for fixing this is integrity, not news coverage.**
`ingest_news.py:106` fetches for `SELECT DISTINCT symbol FROM current_holdings` —
which is **one symbol, HUBS.NYSE**: non-ASX, involuntary, locked, non-disposable.
Repairing the feed today restores article news for exactly one position that cannot
be acted on, so the *evidential* value right now is near zero. The *integrity* value
is very high: a job that structurally cannot fail, fabricated the evidence for a
ship decision, and fools the runtime freshness gate. Fixes #1 and #2 hold the top
slots for that reason — not because the news is needed this week.

| # | Fix | Location | Why |
|---|---|---|---|
| 1 | **Make `ingest_news` able to fail, and un-ship the surface** — one change, not two | `jobs/ingest_news.py:70,156` + `render.yaml:414` | Predicate `r >= 0` accepts total failure. Use `r > 0`, or return `None`/re-raise from `_fetch_and_upsert` so a genuine zero-news day stays distinguishable. Split them and you either leave the trap armed for the next ship check or keep shipping an empty section. |
| 2 | **Audit every `assert_partial_success` predicate for the accepts-zero class** | repo-wide + `check_cron_health` | Promoted out of a footnote: this is the class fix and the news bug is one instance. Add `rows_written > 0` to the deadman — it watches job status, and status is exactly what was forged. |
| 3 | Correct the HY OAS unit mismatch | `migrations/0013_market_context.sql` | **Promoted above the EODHD diagnosis.** §8 shows two of three approved, governed macro theses are unscoreable or unfalsifiable. That corrupts the Layer A falsifier-scoring loop (`jobs/score_macro_theses.py`) — the model-independent product's only learning mechanism. A governance loop scoring itself against dead inputs is worse than one not running. |
| 4 | Diagnose the actual EODHD `/news` failure | `asxos/ingestion/news.py` | Fix #1 makes the failure visible; it does not explain it. Budget for the answer being "no ASX coverage on this plan tier" — the same REV-K wall as `/sentiments`. If so, **retire the feed** as Treasury and ATO were, don't patch it. |
| 5 | Repair or drop the `IRON.COMM` feed | `jobs/ingest_market_context.py` | 404 on 24/24 days; most consequential missing input for a Materials-heavy universe. |
| 6 | Investigate frozen AU 10y + 4bp cash-rate step | `jobs/ingest_market_context.py` | Both pinned since 2026-07-16. Live check confirms the true cash rate is 4.35%, so the value is right and the step is an artifact. Thesis #7 is scored against a dead series. |
| 7 | Reconcile the four documents that disagree about this flag | see below | New. `roadmap-state.md:121` and `:404` say `ASXOS_NEWS_BRIEF_ENABLED=0`; `product-health-scorecard.md:101` and `dark-launch-exit-plan.md` say shipped/1; `render.yaml` says `"1"`. Four docs, two states — live state wins, so `roadmap-state.md` is stale. |
| 8 | Fix missing-Friday / phantom-Sunday cadence | `jobs/ingest_market_context.py` | Friday sessions appear stamped with a Sunday `as_of`; 24 rows cover ~19 sessions. |

**Governance gap underneath all of this.** The exit plan's own rules cover expired
KEEP-DARK surfaces and never counting dark as delivered, but **there is no rule for
a SHIPPED surface whose ship condition later proves false** — exactly the state
here, and nothing forces a re-raise. Worth adding alongside fix #1.

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
