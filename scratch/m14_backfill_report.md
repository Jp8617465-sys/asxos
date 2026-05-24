# M14b Backfill Spike Report

**Generated:** 2026-05-24  
**Lookback:** 24 months  
**Signal source:** EODHD /news polarity (not /sentiments — no ASX coverage on plan tier)  
**Symbols analysed:** 30  

## ⚠️  Architecture Finding

EODHD `/sentiments` endpoint returns **empty for all ASX symbols** on the current
Fundamentals Data Feed plan. `/news` items include a numeric `polarity` score
(`{'polarity': float, 'neg': float, 'neu': float, 'pos': float}`) on every article.

**Recommendation (plan amendment M14b-REV-K):**
- Add `sentiment_polarity NUMERIC(8,6)` column to `holding_news`
- Store the raw numeric polarity at ingest time (already available in news items)
- Nightly aggregation query: `INSERT INTO signal_sentiment` from daily mean polarity
  grouped from `holding_news` (replaces the `/sentiments` API call in `ingest_sentiment.py`)
- `ingest_sentiment.py` can be repurposed or replaced with a post-ingest aggregation step

## Aggregate Verdict

✅ H1_PASS — proceed with M14c (full composite score integration)

| Metric | Value |
|---|---|
| Max abs IC (any horizon) | 0.4364 |
| Avg hit rate | 54.0% |
| H1_PASS symbols | 25 |
| H1_MARGINAL symbols | 0 |
| H1_NULL symbols | 2 |
| Insufficient data | 3 |

## Per-Symbol Results

| Symbol | IC 5d | IC 10d | IC 21d | Hit 5d | Hit 10d | Hit 21d | n | Verdict |
|---|---|---|---|---|---|---|---|---|
| ALL.AU | -0.0073 | -0.1823 | +0.0182 | 72.7% | 81.0% | 85.7% | 21 | H1_PASS |
| AMP.AU | +0.2591 | +0.4364 | +0.2128 | 62.5% | 75.0% | 75.0% | 16 | H1_PASS |
| ANZ.AU | -0.0836 | -0.0484 | +0.1348 | 45.9% | 44.7% | 46.4% | 84 | H1_PASS |
| APX.AU | — | — | — | — | — | — | 1 | INSUFFICIENT_DATA |
| ASX.AU | +0.0372 | +0.0995 | +0.2827 | 33.3% | 33.3% | 45.0% | 20 | H1_PASS |
| BHP.AU | -0.0958 | -0.1040 | -0.0443 | 38.0% | 60.3% | 41.3% | 179 | H1_PASS |
| CBA.AU | -0.2248 | -0.1534 | -0.1130 | 58.0% | 61.2% | 59.3% | 81 | H1_PASS |
| COL.AU | +0.1164 | +0.2685 | -0.0375 | 54.2% | 62.5% | 66.7% | 24 | H1_PASS |
| CSL.AU | +0.0060 | -0.0096 | -0.0198 | 65.0% | 25.4% | 14.3% | 56 | H1_NULL |
| FMG.AU | +0.0199 | -0.0072 | -0.0564 | 30.0% | 75.0% | 40.7% | 59 | H1_PASS |
| GMG.AU | -0.0707 | +0.1564 | +0.1439 | 70.0% | 60.0% | 13.3% | 15 | H1_PASS |
| IAG.AU | +0.1057 | +0.0116 | +0.1014 | 88.0% | 83.3% | 73.9% | 23 | H1_PASS |
| JHX.AU | +0.2544 | +0.3160 | +0.1333 | 47.2% | 54.7% | 50.9% | 53 | H1_PASS |
| MIN.AU | -0.1872 | +0.1423 | -0.1643 | 12.3% | 83.1% | 13.9% | 65 | H1_PASS |
| MPL.AU | +0.3077 | +0.3223 | +0.2878 | 70.6% | 41.2% | 88.2% | 17 | H1_PASS |
| MQG.AU | -0.0483 | -0.1041 | -0.1029 | 58.5% | 59.8% | 55.6% | 90 | H1_PASS |
| NAB.AU | -0.0085 | -0.0073 | -0.0168 | 55.3% | 59.8% | 50.6% | 79 | H1_NULL |
| NCM.AU | — | — | — | — | — | — | 0 | NO_DATA |
| QBE.AU | -0.1664 | +0.0244 | -0.0060 | 65.1% | 62.8% | 66.7% | 42 | H1_PASS |
| REA.AU | +0.0911 | +0.1693 | +0.0663 | 80.0% | 78.5% | 72.3% | 65 | H1_PASS |
| RIO.AU | -0.0183 | +0.1359 | +0.0449 | 28.7% | 77.6% | 32.2% | 143 | H1_PASS |
| S32.AU | -0.0082 | -0.1183 | -0.0694 | 39.2% | 54.0% | 47.9% | 48 | H1_PASS |
| SHL.AU | +0.0172 | +0.2655 | +0.2452 | 55.6% | 55.6% | 41.2% | 17 | H1_PASS |
| TCL.AU | -0.0809 | +0.1123 | +0.1875 | 63.6% | 68.2% | 27.3% | 22 | H1_PASS |
| TLS.AU | -0.2052 | +0.0589 | +0.1731 | 80.0% | 40.0% | 42.5% | 40 | H1_PASS |
| TWE.AU | -0.0979 | -0.1686 | -0.0628 | 20.8% | 13.2% | 9.6% | 52 | H1_PASS |
| WBC.AU | +0.0934 | -0.0686 | -0.0683 | 61.4% | 58.6% | 57.7% | 97 | H1_PASS |
| WDS.AU | -0.1102 | -0.0830 | -0.1602 | 70.9% | 69.1% | 29.1% | 110 | H1_PASS |
| WES.AU | +0.0962 | +0.0323 | +0.0429 | 51.8% | 42.3% | 68.0% | 25 | H1_PASS |
| WPL.AU | — | — | — | — | — | — | 0 | NO_DATA |

## Gate Thresholds (plan Step B7)

| IC | Outcome |
|---|---|
| ≥ 0.05 at any horizon | H1_PASS → proceed with M14c |
| 0.02–0.05 | H1_MARGINAL → proceed with conservative weighting |
| < 0.02 all horizons AND hit < 53% | H1_NULL → halt M14c |

## Next Steps

1. Implement M14b-REV-K: add `sentiment_polarity` to `holding_news` + nightly aggregation.
2. Run `asx sentiment backtest-signoff` once M14b-REV-K is live and re-validated.
3. Wait for `m13_paper_signoff` + `m14_news_signoff` before running `asx allocator-news signoff`.