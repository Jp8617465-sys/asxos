-- 0004_tax_alpha.sql
-- M8: tax-alpha settings + per-security corporate tax rate.
--
-- Per docs/foundation/spec/tax-alpha.md §3: corporate_tax_rate is an input
-- per security, not a global constant. Default 0.30; BREs are 0.25.
--
-- tax_settings holds the per-year, per-account knobs the spec calls out as
-- user-supplied inputs (§2 SMSF fields, §4.1 marginal rate, §5.2 carry-forward
-- losses, §7 medicare thresholds proxy).
--
-- Applied via: mcp__supabase__apply_migration

ALTER TABLE universe
    ADD COLUMN IF NOT EXISTS corporate_tax_rate NUMERIC(4,3) NOT NULL DEFAULT 0.30;

CREATE TABLE IF NOT EXISTS tax_settings (
    financial_year                 INTEGER     NOT NULL,                 -- e.g. 2027 for FY 2026-27
    account_type                   TEXT        NOT NULL,                 -- 'individual' | 'smsf'

    -- Individual (NULL for smsf rows)
    marginal_rate                  NUMERIC(5,4),                         -- e.g. 0.37
    medicare_levy_rate             NUMERIC(5,4)   DEFAULT 0.02,          -- spec §7

    -- SMSF (NULL for individual rows)
    fund_pension_proportion        NUMERIC(5,4),                         -- spec §2; [0.0, 1.0]
    fund_segregated_eligible       BOOLEAN        NOT NULL DEFAULT FALSE,
    div296_election_made           BOOLEAN        NOT NULL DEFAULT FALSE, -- spec §6.4
    div296_reset_date              DATE,                                 -- spec §6.4 (30-Jun-2026)

    -- Shared
    carried_forward_capital_loss   NUMERIC(18,6)  NOT NULL DEFAULT 0,    -- spec §5.2 scalar input
    franking_refundable            BOOLEAN        NOT NULL DEFAULT TRUE, -- spec §4.1 / s 67-25
    notes                          TEXT           NOT NULL DEFAULT '',

    PRIMARY KEY (financial_year, account_type)
);

-- Division 296 indexed thresholds (spec §6.1). Provisional rows carry the
-- `is_provisional` flag so any output that depends on them can surface it.
CREATE TABLE IF NOT EXISTS div296_thresholds (
    financial_year   INTEGER       PRIMARY KEY,
    lsbt             NUMERIC(18,6) NOT NULL,    -- $3M at commencement
    vlsbt            NUMERIC(18,6) NOT NULL,    -- $10M at commencement
    is_provisional   BOOLEAN       NOT NULL DEFAULT FALSE,
    source_note      TEXT          NOT NULL DEFAULT ''
);

INSERT INTO div296_thresholds (financial_year, lsbt, vlsbt, is_provisional, source_note)
VALUES (2027, 3000000, 10000000, FALSE, 'FY 2026-27 commencement values per Imposition Act 2026')
ON CONFLICT (financial_year) DO NOTHING;
