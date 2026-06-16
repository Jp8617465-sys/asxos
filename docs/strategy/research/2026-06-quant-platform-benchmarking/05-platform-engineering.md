# 05 — Computer Science & Platform Engineering to Apply

For each: *why it matters · ASXOS current state · recommended improvement.* ASXOS already has unusually strong ops plumbing for a solo project; the gaps are in **evaluation, lineage, and research/production separation**.

| Concept | Why it matters | ASXOS current state | Recommended improvement |
|---|---|---|---|
| **Data contracts** | catch bad inputs at the boundary | NUMERIC(18,6) discipline; no explicit column/row contracts at panel load | assert expected columns + non-null + row-count contract in `load_panel` (research copy) |
| **Schema versioning** | safe migration | numbered SQL migrations, `REQUIRED_MIGRATIONS` count | keep; add a `universe_history` migration (research-gated) |
| **Feature contracts** | stop train/serve skew | `MODEL_A_FEATURES` constant + shared `FeatureEngine` (strong) | version the feature list **with** the model artefact (store in `features.json` + registry) |
| **Model registry** | reproducible promotion | `model_versions` table + `models/*_metrics.json` (good) | store baseline-relative metric, data window, git SHA, and feature-contract hash per artefact |
| **Artifact metadata** | know what's live | classifier/regressor/features pickles + metrics | add training window, fold scheme, purge/embargo flags, units flag |
| **Experiment tracking** | don't lose research | none | a lightweight `experiments` table or `docs/strategy/research/experiments/*.md` (params → metrics → window) |
| **Reproducible pipelines** | deterministic results | jobs idempotent; backtest not deterministic | seed + as-of snapshot the research backtest |
| **Idempotent jobs** | safe re-runs | all writes UPSERT, `JobMonitor` (strong) | keep |
| **Event logs** | observability + audit | `job_runs` (status/duration/rows/error) | add `ops_events` (run type, gate decisions) + a `review_queue` for human-in-the-loop |
| **Lineage** | trace a signal to its inputs | implicit | record (data window → feature contract → model version → signal rows → outcomes) lineage IDs |
| **Caching** | latency/cost | 60s model cache; 300-symbol batches (memory-aware) | fine for weekly cadence |
| **Batch vs streaming** | match cadence | batch, weekly/daily | keep batch; no streaming need |
| **Testable pure functions** | unit-testable core | thresholds/coverage/validation pure + tested (strong) | keep; add pure baseline + IC functions |
| **Integration tests** | end-to-end safety | strong unit suite; **no feature-level PIT/leakage test** | add the mandated leakage test (assert T-1-only inputs) |
| **Deterministic backtests** | trustworthy results | none yet | research-only harness, seeded, as-of, never writes production tables |
| **CI quality gates** | block regressions | ruff + mypy + pytest (`make check`) | add a rank-IC regression gate once the harness exists |
| **Observability** | catch silent failure | Healthchecks deadman; honest stale email | add rolling-IC + drift summary to the brief/monitoring |
| **Deployment snapshots** | reproduce prod | `render.yaml`-as-code; `make check-drift` | keep; tag deploys with git SHA |
| **Secret management** | no leaks | env-per-service; secrets never in repo | keep; never print `DATABASE_URL`/`RENDER_API_KEY` |
| **Environment groups** | shared config | per-service env (drift documented) | out of scope for this guide |
| **Run types** | distinguish intent | `--as-of`/`--allow-stale-upstream` overrides exist | tag runs scheduled/manual/recovery/probe in `job_runs` |
| **Research/production separation** | research can't corrupt prod | mixed (`jobs/` vs `scripts/`, `scratch/`) | a dedicated `research/` module that **only reads** production tables and writes research artefacts |

**The single most important platform move:** a **research/production firewall** — a `research/` package that reproduces feature loading and scoring read-only, runs baselines + IC + backtests deterministically, and **never** writes `signals`/`portfolio_*`. Everything in `08-research-program.md` lives there. This lets ASXOS iterate on evaluation without any risk to the GREEN production loop.
