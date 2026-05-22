-- 0005_portfolio.sql
-- M13: portfolio construction (profile, target allocations, proposed trades).
--
-- All monetary columns NUMERIC(18,6) per CLAUDE.md non-negotiable #5.
-- Bounded weight columns NUMERIC(8,6) for byte efficiency on [0, 1] ranges.
-- No user_id (CLAUDE.md non-negotiable #4 — single user).
--
-- Schema additions from the M13 plan amendments:
--   profiles.score_weights_json (Part I.3) with precision-tolerant CHECK
--   profiles.defer_near_boundary_sells (Part I.4) — §5.1 deferral opt-in
--   set_active_profile() function (Part I.8) — atomic activate + invariant
--
-- Applied via: mcp__supabase__apply_migration

-- ============================================================
-- profiles: one named investment profile per row
-- ============================================================
CREATE TABLE IF NOT EXISTS profiles (
    profile_id                BIGSERIAL    PRIMARY KEY,
    name                      TEXT         NOT NULL UNIQUE,
    is_active                 BOOLEAN      NOT NULL DEFAULT FALSE,

    account_type              TEXT         NOT NULL,                          -- individual | smsf
    risk_tolerance            TEXT         NOT NULL,                          -- conservative|balanced|growth|aggressive
    risk_tolerance_scalar     NUMERIC(5,4) NOT NULL,                          -- [0, 1]
    capital_aud               NUMERIC(18,6) NOT NULL,
    cash_floor_pct            NUMERIC(5,4) NOT NULL DEFAULT 0.05,
    leverage_cap              NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    per_name_cap_pct          NUMERIC(5,4) NOT NULL DEFAULT 0.10,
    sector_cap_pct            NUMERIC(5,4) NOT NULL DEFAULT 0.30,

    excluded_sectors          TEXT[]       NOT NULL DEFAULT '{}',
    excluded_symbols          TEXT[]       NOT NULL DEFAULT '{}',
    min_position_aud          NUMERIC(18,6) NOT NULL DEFAULT 1000,
    horizon_years             INTEGER      NOT NULL DEFAULT 10,

    -- M13 plan I.4: defer sells of lots within 30 days of CGT discount
    -- eligibility (spec §5.1). Default TRUE because the canonical James
    -- profile is conservative on realised gains.
    defer_near_boundary_sells BOOLEAN      NOT NULL DEFAULT TRUE,

    -- M13 plan I.3: composite-score weighting. Default 60/40 on
    -- prob_up / expected_return. CHECK enforces "valid weight pair"
    -- with a tolerance band on the sum (Decimal-precision inputs like
    -- 0.333333 + 0.666667 = 0.999999 should not violate). Application
    -- code (asxos/domain/portfolio/profile.py:load_active) normalises
    -- to exact Decimal("1") on read.
    score_weights_json        JSONB        NOT NULL DEFAULT
        '{"prob_up": 0.6, "expected_return": 0.4}'::jsonb,

    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT profiles_account_type_chk
        CHECK (account_type IN ('individual', 'smsf')),
    CONSTRAINT profiles_risk_chk
        CHECK (risk_tolerance IN ('conservative', 'balanced', 'growth', 'aggressive')),
    CONSTRAINT profiles_risk_scalar_chk
        CHECK (risk_tolerance_scalar >= 0 AND risk_tolerance_scalar <= 1),
    CONSTRAINT profiles_capital_chk
        CHECK (capital_aud >= 0),
    CONSTRAINT profiles_cash_floor_chk
        CHECK (cash_floor_pct >= 0 AND cash_floor_pct <= 1),
    CONSTRAINT profiles_leverage_chk
        CHECK (leverage_cap >= 1 AND leverage_cap <= 3),
    CONSTRAINT profiles_per_name_cap_chk
        CHECK (per_name_cap_pct > 0 AND per_name_cap_pct <= 0.5),
    CONSTRAINT profiles_sector_cap_chk
        CHECK (sector_cap_pct > 0 AND sector_cap_pct <= 1),
    CONSTRAINT profiles_min_position_chk
        CHECK (min_position_aud >= 0),
    CONSTRAINT profiles_horizon_chk
        CHECK (horizon_years >= 0),
    CONSTRAINT profiles_score_weights_chk
        CHECK (
            (score_weights_json->>'prob_up')         IS NOT NULL
            AND (score_weights_json->>'expected_return') IS NOT NULL
            AND (score_weights_json->>'prob_up')::numeric         BETWEEN 0 AND 1
            AND (score_weights_json->>'expected_return')::numeric BETWEEN 0 AND 1
            AND (
                (score_weights_json->>'prob_up')::numeric
                + (score_weights_json->>'expected_return')::numeric
            ) BETWEEN 0.999 AND 1.001
        )
);

-- At most one active profile (partial unique index — the standard pattern).
CREATE UNIQUE INDEX IF NOT EXISTS profiles_one_active
    ON profiles ((is_active)) WHERE is_active = TRUE;

-- ============================================================
-- set_active_profile(name) — atomic activate with invariant assertion
-- ============================================================
-- M13 plan I.8: the partial unique index enforces *at most* one active.
-- This function adds the "exactly one" assertion and rolls back if violated.
-- CLI calls this; never raw UPDATEs.
CREATE OR REPLACE FUNCTION set_active_profile(p_name TEXT) RETURNS BIGINT AS $$
DECLARE
    target_id BIGINT;
    active_count INTEGER;
BEGIN
    SELECT profile_id INTO target_id FROM profiles WHERE name = p_name;
    IF target_id IS NULL THEN
        RAISE EXCEPTION 'profile % not found', p_name;
    END IF;

    UPDATE profiles SET is_active = FALSE WHERE is_active = TRUE;
    UPDATE profiles
       SET is_active = TRUE,
           updated_at = NOW()
     WHERE profile_id = target_id;

    SELECT COUNT(*) INTO active_count FROM profiles WHERE is_active = TRUE;
    IF active_count != 1 THEN
        RAISE EXCEPTION 'set_active_profile invariant violated: % active rows', active_count;
    END IF;

    RETURN target_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- rebalance_runs: one row per `asx build-portfolio` invocation
-- ============================================================
CREATE TABLE IF NOT EXISTS rebalance_runs (
    run_id        BIGSERIAL    PRIMARY KEY,
    profile_id    BIGINT       NOT NULL REFERENCES profiles(profile_id),
    as_of         DATE         NOT NULL,
    signals_as_of DATE         NOT NULL,
    -- M13 plan H.1 CRITICAL-4: pin the model version that produced the
    -- signals. Two runs 90s apart can read different versions via the
    -- 60s model-cache TTL; this captures which.
    model_version TEXT         NOT NULL,
    capital_aud   NUMERIC(18,6) NOT NULL,
    notes         TEXT         NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (profile_id, as_of)
);

CREATE INDEX IF NOT EXISTS idx_rebalance_runs_as_of
    ON rebalance_runs(as_of DESC);

-- ============================================================
-- target_allocations: target weight per symbol for one run
-- ============================================================
CREATE TABLE IF NOT EXISTS target_allocations (
    run_id          BIGINT       NOT NULL REFERENCES rebalance_runs(run_id) ON DELETE CASCADE,
    symbol          TEXT         NOT NULL REFERENCES universe(symbol),
    target_weight   NUMERIC(8,6) NOT NULL,
    target_aud      NUMERIC(18,6) NOT NULL,
    sector          TEXT,
    signal_label    TEXT,
    prob_up         NUMERIC(8,6),
    expected_return NUMERIC(10,6),
    inv_vol_score   NUMERIC(18,6),
    constraint_log  JSONB        NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_target_alloc_symbol
    ON target_allocations(symbol);

-- ============================================================
-- proposed_trades: delta vs current_holdings for one run
-- ============================================================
CREATE TABLE IF NOT EXISTS proposed_trades (
    trade_id        BIGSERIAL    PRIMARY KEY,
    run_id          BIGINT       NOT NULL REFERENCES rebalance_runs(run_id) ON DELETE CASCADE,
    symbol          TEXT         NOT NULL REFERENCES universe(symbol),
    side            TEXT         NOT NULL,
    delta_qty       NUMERIC(18,6) NOT NULL,
    delta_aud       NUMERIC(18,6) NOT NULL,
    target_qty      NUMERIC(18,6) NOT NULL,
    current_qty     NUMERIC(18,6) NOT NULL,
    reference_price NUMERIC(18,6) NOT NULL,
    rationale_tags  JSONB        NOT NULL DEFAULT '{}'::jsonb,
    lot_hints       JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT proposed_trades_side_chk
        CHECK (side IN ('buy', 'sell', 'hold'))
);

CREATE INDEX IF NOT EXISTS idx_proposed_trades_run
    ON proposed_trades(run_id, side);
CREATE INDEX IF NOT EXISTS idx_proposed_trades_symbol
    ON proposed_trades(symbol, created_at DESC);
