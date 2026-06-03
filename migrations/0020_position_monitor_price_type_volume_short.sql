-- 0020: position_monitor_runs extensions
-- Gap 1: price_type — intraday vs close flag
-- Gap 4: volume_vs_avg_pct and short_interest_pct — manual context prompts

ALTER TABLE position_monitor_runs
    ADD COLUMN IF NOT EXISTS price_type          TEXT          NOT NULL DEFAULT 'close'
        CHECK (price_type IN ('intraday', 'close')),
    ADD COLUMN IF NOT EXISTS volume_vs_avg_pct   NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS short_interest_pct  NUMERIC(18,6) DEFAULT NULL;
