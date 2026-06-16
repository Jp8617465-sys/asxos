# bibliography.md — Modern Source Matrix (2021–2026)

Sources gathered via web research on 2026-06-16, **restricted to ~2021–2026**. Findings paraphrased, never quoted at length. **Access caveat:** many publisher/vendor PDFs returned HTTP 403 to automated fetch; those are marked **"not accessed — corroborated via multiple independent search results"** and any load-bearing figure from them is flagged **[verify]** before external citation. Foundational pre-2021 works appear only where a modern source builds on them, and are labelled *(foundational)*.

## A. Factor investing & anomaly caution (2021–2026)

| Title | Author/Org | Year | Type | Link | Key concept | ASXOS relevance | Conf. | Accessed |
|---|---|---|---|---|---|---|---|---|
| Is There a Replication Crisis in Finance? | Jensen, Kelly, Pedersen (*J. Finance*) | 2023 | Journal | onlinelibrary.wiley.com/doi/full/10.1111/jofi.13249 | Bayesian hierarchical model; **~82% of 153 factors replicate** [verify]; more factors *strengthen* evidence | Defends the value/momentum/quality/low-vol families ASXOS uses; supports theme-clustering over single signals | High | No — corroborated |
| Replicating Anomalies | Hou, Xue, Zhang (*RFS*) | 2020 *(anchor, still central)* | Journal | global-q.org | **~65% of 452 anomalies fail t>1.96** once microcaps de-weighted, value-weighted | The #1 ASX trap: small/illiquid names inflate signals | High | No — corroborated |
| Do t-Statistic Hurdles Need to be Raised? | A. Y. Chen (*Mgmt Sci*) | 2023 | Journal | arxiv.org/abs/2204.10275 | **t>3 bar is weakly identified**; use FDR/empirical-Bayes | Don't impose t>3; use FDR + shrinkage | High | No — corroborated |
| Most Claimed Findings… Are Likely True | A. Y. Chen | 2022 | WP | arxiv.org/abs/2206.15365 | **FDR ≤ ~9–25%** [verify]; most predictors real | Factor exposures aren't mostly noise | High | No — corroborated |
| Open Source Cross-Sectional Asset Pricing | Chen, Zimmermann | 2022 | Journal + open data | openassetpricing.com | ~98% of clear predictors replicate; **free factor library** | Ready-made baseline suite for ASXOS L2 | High | Partial |
| Factor Momentum and the Momentum Factor | Ehsani, Linnainmaa (*J. Finance*) | 2022 | Journal | (Wiley) | Factors are positively autocorrelated; momentum ≈ factor timing | Validates momentum features; factor-momentum overlay idea | High | No — corroborated |
| Model Comparison with Transaction Costs | Detzel, Novy-Marx, Velikov (*J. Finance*) | 2023 | Journal | (Wiley) | Net-of-cost spanning; **gross Sharpe ≠ net Sharpe** | ASXOS has no cost model — close this first | High | No — corroborated |
| Assaying Anomalies (toolkit) | Novy-Marx, Velikov | 2023 | Method + code | github.com/velikov-mihail/AssayingAnomalies | NYSE-breakpoint, value-weighted, net-of-cost protocol | Template for ASXOS anomaly vetting | High | Yes (GitHub) |
| Not All Factors Crowd Equally | (arXiv) | 2025 | WP | arxiv.org/abs/2512.11913 | Mechanical factors (momentum/reversal) crowd & decay hyperbolically post-2015 | Momentum capacity/crowding caution | Med | No — corroborated |
| Anomalies and Their Short-Sale Costs | Muravyev et al. (*J. Finance*) | 2025 | Journal | (Wiley) | Short-leg costs erode anomaly alpha | ASXOS is long-only → can't capture short-leg premia | Med | No — corroborated |
| Contrarian Factor Timing is Deceptively Difficult | Asness et al. (AQR) | 2017 *(foundational)* | Practitioner | ssrn.com/abstract=2928945 | Timing rarely beats diversification | Don't add factor-valuation timing in v1 | Med | No — corroborated |

## B. ML for return prediction (2021–2026)

| Title | Author/Org | Year | Type | Link | Key concept | ASXOS relevance | Conf. | Accessed |
|---|---|---|---|---|---|---|---|---|
| Machine Learning vs. Economic Restrictions | Avramov, Cheng, Metzker (*Mgmt Sci*) | 2023 | Journal | pubsonline.informs.org/doi/abs/10.1287/mnsc.2022.4449 | **ML alpha concentrates in microcap/distressed/high-vol; dies after costs+restrictions** [verify] | Long-only large-cap ASX captures a fraction of headline edge | High | No — corroborated |
| Virtue of Complexity in Return Prediction | Kelly, Malamud, Zhou (*J. Finance*) | 2024 | Journal | onlinelibrary.wiley.com/doi/10.1111/jofi.13298 | Complex models beat simple **only with ridge shrinkage** | Regularization is mandatory, not optional | High | No — corroborated |
| Empirical Asset Pricing via Machine Learning | Gu, Kelly, Xiu (*RFS*) | 2020 *(anchor)* | Journal | (Oxford) | Trees/NNs beat linear; baseline the field builds on | Frames ASXOS LightGBM choice | High | No — corroborated |
| The Expected Returns of ML Strategies | (AFA/SSRN) | 2023–24 | Journal/WP | afajof.org | Net ~1.4%/mo can survive with turnover control [verify] | Disciplined ML *can* work net of costs | Med | No — corroborated |
| ML & the cross-section of emerging-market returns | Hanauer, Kalsbach | 2023 | Journal | sciencedirect.com (S1566014123000274) | Trees > linear; net positive in large caps | Confirms tree choice; large-cap caveat | High | No — corroborated |
| Can ChatGPT Forecast Stock Price Movements? | Lopez-Lira, Tang | 2023–24 | WP | arxiv.org/abs/2304.07619 | LLM news-sentiment predicts returns; **decays with adoption** | Benchmark/caution for any LLM-news feature | High | No — corroborated |
| BloombergGPT / FinGPT | Bloomberg / AI4Finance | 2023 | Tech report / OSS | arxiv.org/abs/2303.17564 ; arxiv.org/pdf/2307.10485 | Big internal FinLLM vs cheap open FinLLM | Don't build your own; use open models if at all | High | No — corroborated |
| LambdaRankIC | Lin et al. | 2026 | WP | arxiv.org/abs/2605.00501 | Directly optimize rank-IC; beats regression at low SNR | Use rank-IC objective/eval for signals | Med | No — corroborated |
| Look-Ahead-Bench / Agentic Trading survey | (arXiv) | 2026 | Benchmark/survey | arxiv.org/pdf/2601.13770 ; arxiv.org/html/2605.19337v1 | Point-in-time leakage & memorization in LLM finance | Skepticism toward LLM/agentic alpha | Med | No — corroborated |
| Classifier Calibration (empirical) | (arXiv) | 2026 | Empirical | arxiv.org/pdf/2601.19944 | Post-hoc isotonic/Platt comparison | Calibrate `prob_up` before sizing | Med | No — corroborated |

## C. Backtest validation & overfitting (2021–2026)

| Title | Author/Org | Year | Type | Link | Key concept | ASXOS relevance | Conf. | Accessed |
|---|---|---|---|---|---|---|---|---|
| Backtest Overfitting in the ML Era (synthetic controlled comparison) | Arian, Norouzi, Seco | 2024 | Journal (*Knowledge-Based Systems*) | papers.ssrn.com/sol3/papers.cfm?abstract_id=4686376 | **CPCV dominates walk-forward/K-fold** on PBO & DSR; WF weakest | Indicts ASXOS's TimeSeriesSplit directly | High | No — corroborated |
| Leakage & the Reproducibility Crisis in ML-based Science | Kapoor, Narayanan (*Patterns*) | 2023 | Journal | arxiv.org/pdf/2207.07048 | **8-type leakage taxonomy**; model info sheets | ASXOS 5-day overlap = temporal leakage; audit checklist | High | Partial (arXiv) |
| False (and Missed) Discoveries in Financial Economics | Harvey, Liu | 2021 | Journal/WP | arxiv.org/pdf/2006.04269 | FDR control across the anomaly zoo | How many trials before significance dies | High | Partial (arXiv) |
| The Deflated Sharpe Ratio | Bailey, López de Prado | 2014 *(foundational, std. 2021–26)* | Journal | papers.ssrn.com/.../2460551 | Correct Sharpe for trials/skew/kurtosis | Replace raw Sharpe with DSR | High | Yes (PDF) |
| The Probability of Backtest Overfitting | Bailey, Borwein, LdP, Zhu | 2017 *(foundational)* | Journal | davidhbailey.com/.../backtest-prob.pdf | CSCV → PBO; model-free | Cheap PBO computable solo | High | Yes (PDF) |
| Advances in Financial Machine Learning | López de Prado | 2018 *(anchor)* | Book | wiley.com (9781119482086) | Purging, embargo, CPCV, triple-barrier, meta-labeling | The discipline ASXOS validation lacks | High | No — corroborated |
| When Alpha Breaks (uncertainty-gated deployment) | (arXiv) | 2026 | Preprint | arxiv.org/pdf/2603.13252 | Two-level uncertainty gating of rank models | Confidence-gated signal deployment | Med | No — recommended |
| Chain-of-Alpha / modern factor-eval stack | (arXiv) | 2025 | Preprint | arxiv.org/pdf/2508.06312 | IC/RankIC/ICIR/decile spread as the standard eval set | Defines ASXOS evaluation metrics | Med | Partial |

## D. Portfolio construction & risk (2021–2026)

| Title | Author/Org | Year | Type | Link | Key concept | ASXOS relevance | Conf. | Accessed |
|---|---|---|---|---|---|---|---|---|
| Schur Complementary Allocation (unifies HRP & MVP) | P. Cotton | 2024 | arXiv | arxiv.org/abs/2411.05807 | One γ dial interpolates HRP↔min-variance | Tunable upgrade from inverse-vol | High | No — corroborated |
| skfolio: Portfolio Optimization in Python | Delatte et al. | 2025 | arXiv / library | arxiv.org/abs/2507.04176 | sklearn-API HRP/NCO/denoising/Schur | The lean tool to adopt | High | No — corroborated |
| Overcoming Markowitz Instability with HRP | Antonov, Lipton, López de Prado | 2024 | SSRN | papers.ssrn.com/.../4748151 | Analytic proof HRP < Markowitz noise | Justifies hierarchical over MVO | High | No — corroborated |
| Covariance filtering: Average Oracle vs NLS | Bongiorno, Bouchaud et al. | 2023 | arXiv | arxiv.org/pdf/2309.17219 | Denoise (RMT/NLS) before optimizing | Denoise covariance first | High | Partial |
| Tax-Aware Long-Short Factor Strategies | AQR | 2024 | Practitioner | aqr.com | Defer gains, harvest losses | Validates ASXOS CGT/loss-harvest overlay | Med | No — corroborated |
| Tax-Aware Active Management | Goldman Sachs AM | 2024/25 | Practitioner | am.gs.com | ~+0.35%/yr after-tax (high bracket) [verify] | Value of tax overlay | Med | No — corroborated |
| Tax-Loss Harvesting: Personalized Approach | Vanguard Research | 2024 | White paper | corporate.vanguard.com | Personalized > blanket TLH | Single-user TLH design | Med | No — corroborated |
| Next-Generation Equity Factor Models | MSCI Barra | 2022 | Vendor | msci.com | +Sustainability/Crowding/ML factors | Reference for factor-risk gap | High | No — corroborated |

## E. Platform engineering / MLOps (2021–2026)

| Title | Author/Org | Year | Type | Link | Key concept | ASXOS relevance | Conf. | Accessed |
|---|---|---|---|---|---|---|---|---|
| Feast docs / Feast joins PyTorch Ecosystem | Feast / PyTorch | 2025 | Official docs/blog | docs.feast.dev ; pytorch.org/blog/feast-joins-the-pytorch-ecosystem/ | Point-in-time correctness; train/serve skew | Lean equivalent = shared feature module + `as_of` joins | High | Yes (search) |
| MLflow alternatives / 2025 MLOps landscape | ZenML / Uplatz | 2025 | Comparison | zenml.io/blog/mlflow-alternatives | MLflow = OSS default registry+tracking | Add experiment tracking (biggest platform gap) | Med | Yes (search) |
| Evidently — drift & ML observability | Evidently AI | 2024–25 | Official | evidentlyai.com | 20+ drift tests (KS/PSI/JS) | Wire feature/prediction drift into cron | High | Partial (403) |
| DVC data pipelines / lineage with MLflow | DVC (Iterative) / AWS | 2025 | Docs/guide | dvc.org ; aws.amazon.com (blog) | DAG pipelines; model→data commit-hash lineage | Lineage-as-a-column in `model_versions` | High | Yes (search) |
| The Big Book of Generative AI | Databricks | 2024 | Report | databricks.com/resources/ebook/big-book-generative-ai | Production GenAI/LLMOps patterns | Platform context for agentic review layer | Med | Yes (search) |
| State of Agent Engineering | LangChain | 2025 | Industry report | langchain.com/state-of-agent-engineering | Evals (~52%) lag observability (~89%) [verify] | Agentic review needs evals-in-CI + tracing | Med | No (403) |
| CI Practices in ML Projects | (arXiv) | 2025 | Peer research | arxiv.org/pdf/2502.17378 | Non-determinism, data deps, metric gates in CI | Research/prod separation + ML CI gates | High | Partial |

## F. ASX-specific market structure (2021–2026)

| Title | Author/Org | Year | Type | Link | Key concept | ASXOS relevance | Conf. | Accessed |
|---|---|---|---|---|---|---|---|---|
| Considerations for accelerating cash equities settlement to T+1 (whitepaper) | ASX | 2024 | Exchange WP | asx.com.au (t1-whitepaper-042024.pdf) | T+1 follows CHESS replacement (~2030) | Future FX/settlement leg timing | High | No — recommended |
| CHESS Replacement Project & T+1 | Boardroom Ltd | 2024 | Industry | boardroomlimited.com.au | TCS BaNCS; Release 1 ~2026 | Infra instability → kill-switch | Med-High | Yes (search) |
| Developments in C&S Industry — PSB Annual Report 2025 | RBA | 2025 | Regulator | rba.gov.au/publications/annual-reports/psb/2025/ | **Dec-2024 CHESS batch-settlement failure** | Operational-risk hazard | High | No (403) — corroborated |
| Adjusted vs Unadjusted Price Data (backtest practice) | Palmarium / EODHD | 2023 | Practitioner/vendor | eodhd.com (academy) | Raw close → spurious returns at ex-date/split | **Adopt `adj_close`** (#1 ASX fix) | Med | Yes (search) |
| Understanding Australian Franking Credits | Vanguard Australia | 2023–24 | Asset-mgr edu | vanguard.com.au | Imputation grosses yield ~40%+ [verify] | Franking ∈ expected return; after-tax overlay | High | Yes (search) |
| S&P/ASX Australian Indices Methodology (franking-adjusted TR) | S&P DJI | 2024 | Index methodology | spglobal.com/spdji | Franking-adjusted total-return indices | Total-return benchmark definition | High | No — recommended |
| Should you invest in small caps? (no AU size premium) | Morningstar Australia | 2024 | Analyst | morningstar.com.au | **Small Ords has lagged ASX 100 since ~2000** | No AU small-cap premium → liquidity-filter universe | Med-High | Yes (search) |
| Avoid growing concentration risk in the ASX 200 | VanEck Australia | 2024–25 | Asset-mgr | vaneck.com.au | **Financials ~28–30%, Materials ~20%** [verify] | Sector co-movement caps; risk-blindness | Med-High | No (403) — corroborated |

---

**Recommended reading not relied on for specifics:** AQR style-premia library; FTSE Russell factor methodology; MSCI Australia Momentum Index factsheet; NBER w28432; "Publication Bias in Asset Pricing Research" (arXiv 2209.13623); Haddad-Kozak-Santosh "Factor Timing" (NBER w26708). Listed for follow-up, **no specific claims asserted** from un-accessed pages.

**Verification protocol before any of these numbers becomes load-bearing in code or spec:** re-fetch the primary PDF (many were 403 to automation) and confirm the figure. The **[verify]** tags mark the specific quantities to re-check (JKP 82%, Chen FDR 9–25%, Avramov microcap concentration, GS +0.35%/yr, ASX sector weights, franking ~40% gross-up, LangChain eval/observability %).
