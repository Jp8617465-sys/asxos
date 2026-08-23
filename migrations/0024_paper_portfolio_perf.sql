-- 0024_paper_portfolio_perf.sql
-- M13.8+: paper-portfolio performance scoreboard.
-- Records the realised-performance evaluation of persisted build-portfolio runs
-- (rebalance_runs / target_allocations / proposed_trades) against subsequent
-- prices. This is a strategy-incubation tracker, NOT proof of alpha.
--
-- Applied via: mcp__supabase__apply_migration (project gxjqezqndltaelmyctnl).
--
-- All writes are idempotent UPSERTs keyed on (run_id, eval_as_of[, symbol|dt]);
-- re-running the monitor for a later eval date extends, never overwrites,
-- history. Existing runs/holdings are never modified by the monitor.

-- Per-eval summary metrics for one run (one row per run_id × eval_as_of).
CREATE TABLE IF NOT EXISTS paper_portfolio_run_metrics (
    run_id                  BIGINT        NOT NULL REFERENCES rebalance_runs(run_id) ON DELETE CASCADE,
    eval_as_of              DATE          NOT NULL,
    run_as_of               DATE          NOT NULL,
    signals_as_of           DATE          NOT NULL,
    model_version           TEXT          NOT NULL,
    n_positions             INTEGER       NOT NULL,
    measurable              BOOLEAN       NOT NULL,
    n_forward_days          INTEGER       NOT NULL,
    measurability_note      TEXT          NOT NULL DEFAULT '',
    capital_aud             NUMERIC(18,6) NOT NULL,
    cash_aud                NUMERIC(18,6) NOT NULL,
    total_nav_aud           NUMERIC(18,6),
    price_return_pct        NUMERIC(18,6),
    total_return_pct        NUMERIC(18,6),
    benchmark_available     BOOLEAN       NOT NULL DEFAULT FALSE,
    benchmark_source        TEXT          NOT NULL DEFAULT '',
    benchmark_return_pct    NUMERIC(18,6),
    benchmark_relative_pct  NUMERIC(18,6),
    equal_weight_return_pct NUMERIC(18,6),
    model_weight_return_pct NUMERIC(18,6),
    hit_rate_pct            NUMERIC(18,6),
    avg_winner_pct          NUMERIC(18,6),
    avg_loser_pct           NUMERIC(18,6),
    payoff_ratio            NUMERIC(18,6),
    max_drawdown_pct        NUMERIC(18,6),
    realised_vol_pct        NUMERIC(18,6),
    turnover_pct            NUMERIC(18,6)  NOT NULL,
    est_cost_aud            NUMERIC(18,6)  NOT NULL,
    est_cost_bps_of_capital NUMERIC(18,6)  NOT NULL,
    n_missing_events        INTEGER        NOT NULL DEFAULT 0,
    computed_at             TIMESTAMPTZ    NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, eval_as_of)
);

-- Daily NAV path for a run (one row per run_id × dt). The series is a function
-- of dt only; later evals extend it. computed_at records last refresh.
CREATE TABLE IF NOT EXISTS paper_portfolio_nav (
    run_id            BIGINT        NOT NULL REFERENCES rebalance_runs(run_id) ON DELETE CASCADE,
    dt                DATE          NOT NULL,
    invested_mv_aud   NUMERIC(18,6) NOT NULL,
    cash_aud          NUMERIC(18,6) NOT NULL,
    total_nav_aud     NUMERIC(18,6) NOT NULL,
    cum_return_pct    NUMERIC(18,6) NOT NULL,
    daily_return_pct  NUMERIC(18,6),
    n_priced          INTEGER       NOT NULL,
    n_missing         INTEGER       NOT NULL,
    forward_filled    BOOLEAN       NOT NULL DEFAULT FALSE,
    benchmark_level   NUMERIC(18,6),
    benchmark_cum_return_pct NUMERIC(18,6),
    computed_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, dt)
);

-- Per-position attribution at a given eval (one row per run_id × eval_as_of × symbol).
CREATE TABLE IF NOT EXISTS paper_portfolio_position_perf (
    run_id            BIGINT        NOT NULL REFERENCES rebalance_runs(run_id) ON DELETE CASCADE,
    eval_as_of        DATE          NOT NULL,
    symbol            TEXT          NOT NULL,
    sector            TEXT,
    weight            NUMERIC(18,6) NOT NULL,
    entry_close       NUMERIC(18,6) NOT NULL,
    last_close        NUMERIC(18,6),
    last_dt           DATE,
    price_return_pct  NUMERIC(18,6),
    total_return_pct  NUMERIC(18,6),
    pnl_aud           NUMERIC(18,6),
    contribution_pct  NUMERIC(18,6),
    signal_label      TEXT          NOT NULL,
    prob_up           NUMERIC(18,6) NOT NULL,
    expected_return   NUMERIC(18,6) NOT NULL,
    used_adj_close    BOOLEAN       NOT NULL DEFAULT FALSE,
    priced            BOOLEAN       NOT NULL DEFAULT FALSE,
    computed_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, eval_as_of, symbol)
);

CREATE INDEX IF NOT EXISTS idx_paper_perf_metrics_eval
    ON paper_portfolio_run_metrics(eval_as_of);
CREATE INDEX IF NOT EXISTS idx_paper_perf_nav_run
    ON paper_portfolio_nav(run_id);
CREATE INDEX IF NOT EXISTS idx_paper_perf_pos_run_eval
    ON paper_portfolio_position_perf(run_id, eval_as_of);
