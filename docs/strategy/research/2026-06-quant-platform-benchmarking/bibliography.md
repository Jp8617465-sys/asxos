# bibliography.md — Source Matrix

Public, primary/authoritative sources used in this guide. Web-accessed 2026-06-16. Concepts are **paraphrased and cited**, never quoted at length. Confidence reflects how directly the source was verified.

| # | Title | Author / Org | Type | Link | Key concept | ASXOS relevance | Confidence |
|---|---|---|---|---|---|---|---|
| 1 | Portfolio Selection (1952), *J. Finance* 7(1):77-91 | Harry Markowitz | Paper | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1952.tb01525.x | Mean-variance optimisation; risk-return trade-off; diversification | Portfolio construction & risk budgeting beyond inverse-vol | High |
| 2 | Capital Asset Prices (1964) | William Sharpe | Paper | (canonical) | CAPM; market beta as the first factor | Beta baseline; excess-return framing | High |
| 3 | The Sharpe Ratio (1966/1994) | William Sharpe | Paper/encyclopaedia | https://en.wikipedia.org/wiki/Sharpe_ratio | Risk-adjusted return | Portfolio metric for paper book | High |
| 4 | Information Ratio | (industry standard) | Reference | https://en.wikipedia.org/wiki/Information_ratio | Active return / tracking error | Primary scorecard for an active signal | High |
| 5 | Returns to Buying Winners and Selling Losers (1993), *J. Finance* 48:65-91 | Jegadeesh & Titman | Paper | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x | Cross-sectional momentum (3-12m) | The single hardest baseline ASXOS must beat | High |
| 6 | Common Risk Factors… (1993); A Five-Factor Asset Pricing Model (2015), *JFE* 116:1-22 | Fama & French | Papers | https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002323 | Market, size, value (+profitability, investment) | Factor baselines + residualisation target | High |
| 7 | On Persistence in Mutual Fund Performance (1997), *J. Finance* 52:57-82 | Mark Carhart | Paper | https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1997.tb03808.x | Four-factor model (+momentum); **survivorship-bias-free sample** | Momentum factor; survivorship discipline | High |
| 8 | Active Portfolio Management (1995/2000); Fundamental Law | Grinold & Kahn | Book | https://www.mheducation.com/highered/mhp/product/advances-active-portfolio-management-new-developments-quantitative-investing.html | **IR ≈ IC × √Breadth × TC** | Why measuring IC matters more than AUC for a high-breadth weekly signal | High |
| 9 | Value and Momentum Everywhere (2013), *J. Finance* 68(3):929-985 | Asness, Moskowitz, Pedersen | Paper | https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12021 | Value & momentum premia across markets; negative value-momentum correlation | Combining value + momentum features; diversification of styles | High |
| 10 | Quality Minus Junk (2014/2019) | Asness, Frazzini, Pedersen | Paper | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2312432 | Quality/profitability premium | Quality factor baseline | High |
| 11 | Betting Against Beta (2014), *JFE* | Frazzini & Pedersen | Paper | (canonical) | Low-risk / low-beta anomaly | Low-vol factor; leverage-constraint intuition | Med |
| 12 | …and the Cross-Section of Expected Returns (2016), *RFS* 29(1):5 | Harvey, Liu, Zhu | Paper | https://academic.oup.com/rfs/article/29/1/5/1843824 | **Factor zoo; multiple testing; t > 3.0**; ~half of published factors likely false | The central caution for ASXOS feature/signal discovery | High |
| 13 | Replicating Anomalies (NBER w23394) | Hou, Xue, Zhang | Paper | https://www.nber.org/system/files/working_papers/w23394/w23394.pdf | ~64% of 447 anomalies insignificant once microcaps controlled & value-weighted | Small/illiquid bias; ASX micro-cap caution | High |
| 14 | The Deflated Sharpe Ratio (2014) | Bailey & López de Prado | Paper | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 | Correct Sharpe for selection bias / multiple trials / non-normality | Deflated significance for any ASXOS backtest | High |
| 15 | The Probability of Backtest Overfitting (2017) | Bailey, Borwein, López de Prado, Zhu | Paper | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 | PBO via combinatorially symmetric CV | Guards ASXOS against over-tuned backtests | High |
| 16 | Advances in Financial Machine Learning (2018), Wiley | Marcos López de Prado | Book | https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086 | **Purging, embargo, walk-forward, leakage, triple-barrier, meta-labeling, fractional differentiation** | The ML-for-finance discipline ASXOS validation lacks | High |
| 17 | Purged cross-validation | (community / AFML) | Reference | https://en.wikipedia.org/wiki/Purged_cross-validation | Purge + embargo to stop label-window leakage | Direct fix for ASXOS's overlapping 5-fold | High |
| 18 | Barra US Equity Model (USE4); GEM3 methodology | MSCI / Barra | Official methodology | https://www.msci.com/documents/10199/242721/Barra_Global_Equity_Model_GEM3.pdf | Fundamental factor risk model; country/industry/style factors; data-quality emphasis | Lean factor-covariance risk model target | Med |
| 19 | MSCI Equity Factor Models | MSCI | Official page | https://www.msci.com/our-solutions/factor-investing/factor-models | Style factors: size, value, momentum, volatility, growth | Maps ASXOS features to recognised styles | Med |

**Recommended-reading (not relied upon for specific claims here):**
- AQR style-premia public research library (aqr.com/insights) — practitioner factor framing.
- FTSE Russell factor index methodology — alternative public factor construction.
- Quantopian post-mortems / open quant lessons — practical backtest-overfitting cautions.
- ASX market microstructure / small-cap liquidity & corporate-action notes (ASX official, broker research) — ASX-specific constraints; **listed as to-read, no specific claims asserted from un-accessed pages.**

**Notes on standard.** Canonical works (CAPM, FF, Carhart, Jegadeesh-Titman, Markowitz, Sharpe, Grinold-Kahn, AMP, QMJ, Harvey-Liu-Zhu, López de Prado, Barra) are cited by title/author/year with primary links where retrieved. No proprietary hedge-fund internals are claimed. No long excerpts copied. Where a page was not directly accessed, it is listed as recommended reading rather than cited for specifics.
