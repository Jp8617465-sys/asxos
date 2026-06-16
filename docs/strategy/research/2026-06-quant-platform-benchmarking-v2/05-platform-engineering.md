# 05 — Platform Engineering / Lean MLOps (2021–2026)

*The 2021–2026 lesson: **discipline beats tooling.** The enterprise stack (Tecton, Databricks Feature Store, Kubeflow, full W&B) solves team-coordination problems a solo operator does not have. Adopt the *patterns*, not the platforms.*

| Concept | Why it matters (2021–2026) | ASXOS current state | Lean recommended improvement |
|---|---|---|---|
| **Feature store / train-serve skew** | Feast (now in the PyTorch ecosystem, 2025) solves train/serve skew + point-in-time correctness | shared `FeatureEngine` + `as_of` joins already exist (strong) | **Keep the single shared feature module** (delivers Feast's #1 benefit with no Feast); add an explicit lookahead-guard test |
| **Experiment tracking** | MLflow is the OSS default; biggest *missing* layer for solo quants | none | **MLflow with a local SQLite/file backend** — queryable runs (params, data window, metrics), near-zero ops |
| **Model registry** | versioned artefacts + lineage gate promotion | `model_versions` table + `metrics.json` (a minimal registry) | add **baseline-relative metric + data-window hash + git SHA + units flag** per artefact; optionally layer MLflow registry |
| **Data contracts / lineage** | "which exact data produced this model?" | implicit | **lineage as a column** (data-window hash in `model_versions`); skip full DVC unless data outgrows Postgres-as-source-of-truth |
| **Reproducible pipelines** | determinism = trustworthy backtests | idempotent jobs; backtest non-deterministic | seed RNG, pin deps, immutable `as_of` snapshots in the research harness |
| **Drift monitoring** | clearest under-served gap; Evidently (OSS, 20+ tests: KS/PSI/JS) | job liveness only | wire **feature-drift + prediction-drift (PSI/KS)** into the existing cron + `job_runs` + Healthchecks |
| **CI quality gates** | promote models like code | ruff+mypy+pytest (`make check`); no ML metric gate | add a **rank-IC regression gate** once the harness exists; metric-threshold + no-skew + drift-baseline checks |
| **Event logs / review queue** | observability + human-in-loop | `job_runs` (status/duration/rows/error) strong | add `ops_events` (run type, gate decisions) + a `review_queue` for an agentic review layer |
| **Run types** | distinguish intent | `--as-of`/`--allow-stale-upstream` exist | tag runs scheduled/manual/recovery/probe in `job_runs` |
| **LLMOps / agentic context** | Databricks *Big Book of GenAI*, LangChain *State of Agent Engineering* (2024–25): **evals (~52%) lag observability (~89%)** [verify]; quality is the top production blocker | none | if an agentic review layer is built: **versioned prompts + a small eval set in CI + trace logging** — mirror the existing `job_runs`/metrics discipline |
| **Research/production separation** | research must not corrupt prod | mixed (`jobs/` vs `scripts/`, `scratch/`) | **a `research/` package that only reads production tables and writes research artefacts — never `signals`/`portfolio_*`** |
| **Secret management** | no leaks | env-per-service; secrets never in repo | keep; never print `DATABASE_URL`/`RENDER_API_KEY` |

## Lean platform stack recommendation (solo operator)

1. **Feature consistency:** the existing shared feature module + point-in-time `as_of` SQL joins. *(No feature store.)*
2. **Tracking + registry:** MLflow (local backend) layered onto `model_versions`/`metrics.json`.
3. **Reproducibility/lineage:** deterministic pipelines + data-window hash in the registry. *(DVC optional/deferred.)*
4. **Monitoring:** Evidently drift checks inside the existing cron + `job_runs` + Healthchecks deadman.
5. **CI gates:** metric-threshold + no-skew + drift-baseline + rank-IC regression on commit; registry-stage promotion as the prod boundary.
6. **Research firewall:** a read-only `research/` package for baselines, rank-IC, backtests, paper book.
7. **Avoid (enterprise overkill):** Tecton/Databricks Feature Store, Kubeflow, SaaS W&B, standalone lineage platforms.

**The single most important platform move:** the **research/production firewall** — it lets ASXOS iterate on evaluation (everything in `08`) with zero risk to the GREEN production loop, and makes deterministic, leakage-safe backtesting possible.
