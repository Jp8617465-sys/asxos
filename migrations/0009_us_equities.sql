-- M15: US equities support — FX rates table + holding_lots FX tracking columns.
-- Applied via: mcp__supabase__apply_migration
--
-- fx_rates: daily AUD/USD spot rate from EODHD AUDUSD.FOREX.
--   rate = USD per 1 AUD (e.g. 0.640000 means 1 AUD = 0.64 USD)
--   Source is always 'eodhd' in Phase 1; extensible via source column.
--
-- holding_lots FX columns (all nullable — NULL for all ASX lots):
--   cost_base_usd:         original USD cost (ESPP grant price × shares)
--   disposal_proceeds_usd: USD proceeds on disposal (filled at disposal time)
--   acquisition_fx_rate:   AUDUSD rate on acquired_at date (for Div 775 calc)
--   disposal_fx_rate:      AUDUSD rate on disposed_at date (filled at disposal time)
--
-- NULL means the lot is ASX-denominated — no FX event on disposal.
-- Non-NULL means an FX translation is required per ATO TR 2019/1.

CREATE TABLE IF NOT EXISTS fx_rates (
    pair   TEXT          NOT NULL,              -- 'AUDUSD'
    dt     DATE          NOT NULL,
    rate   NUMERIC(18,6) NOT NULL,              -- USD per 1 AUD
    source TEXT          NOT NULL DEFAULT 'eodhd',
    PRIMARY KEY (pair, dt)
);

COMMENT ON TABLE fx_rates IS
    'Daily exchange rates sourced from EODHD FOREX endpoint. '
    'Rate is expressed as units of the quote currency per 1 unit of the base currency '
    '(e.g. AUDUSD rate=0.640000 means 1 AUD = 0.64 USD).';

CREATE INDEX IF NOT EXISTS fx_rates_dt_idx ON fx_rates (dt DESC);

ALTER TABLE holding_lots
    ADD COLUMN IF NOT EXISTS cost_base_usd         NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS disposal_proceeds_usd  NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS acquisition_fx_rate    NUMERIC(18,6) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS disposal_fx_rate       NUMERIC(18,6) DEFAULT NULL;

COMMENT ON COLUMN holding_lots.cost_base_usd IS
    'Original USD cost base (ESPP grant price × shares). NULL for ASX lots.';
COMMENT ON COLUMN holding_lots.disposal_proceeds_usd IS
    'USD proceeds at disposal. NULL until disposed or for ASX lots.';
COMMENT ON COLUMN holding_lots.acquisition_fx_rate IS
    'AUDUSD rate on acquired_at (USD per 1 AUD). NULL for ASX lots. '
    'Required for Div 775 FX gain/loss calc per ATO TR 2019/1.';
COMMENT ON COLUMN holding_lots.disposal_fx_rate IS
    'AUDUSD rate on disposed_at (USD per 1 AUD). NULL until disposed or for ASX lots.';
