-- 0022: FX P&L split columns in portfolio_daily_snapshots
-- Gap 6: isolate equity P&L from FX movement on US positions

ALTER TABLE portfolio_daily_snapshots
    ADD COLUMN IF NOT EXISTS us_holdings_mv_aud    NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS us_holdings_cost_aud  NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS fx_rate_audusd         NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS unrealised_fx_pnl_aud  NUMERIC(18,6) DEFAULT NULL;
