-- 0025_signal_outcomes_versioning.sql
-- Versions the pre-existing `signal_outcomes` table (created ad-hoc by
-- jobs/track_signal_outcomes.py and never captured in migrations/ — audit gap).
--
-- This is IDEMPOTENT and ALREADY SATISFIED in production: the table exists there
-- with this exact shape, so CREATE TABLE IF NOT EXISTS is a no-op in prod. It is
-- NOT applied via MCP and REQUIRED_MIGRATIONS is NOT bumped — the file exists so
-- a fresh/dev database reproduces the table and the schema is reviewable in repo.
--
-- TYPE DEBT (do not silently "fix" in prod): this table uses double precision /
-- varchar rather than the house NUMERIC(18,6) / text convention because the
-- tracking job created it before the convention was enforced. Migrating types is
-- a separate, deliberate change — not bundled here.

CREATE TABLE IF NOT EXISTS signal_outcomes (
    id                       SERIAL PRIMARY KEY,
    symbol                   VARCHAR        NOT NULL,
    signal_date              DATE           NOT NULL,
    model                    VARCHAR,
    ml_prob                  DOUBLE PRECISION,
    ml_expected_return       DOUBLE PRECISION,
    signal_label             VARCHAR,
    actual_return_5d         DOUBLE PRECISION,
    actual_return_21d        DOUBLE PRECISION,
    was_direction_correct    BOOLEAN,
    evaluation_date          DATE,
    evaluated_at             TIMESTAMPTZ    DEFAULT now(),
    regime                   VARCHAR,
    dividends_21d            NUMERIC,
    actual_return_21d_total  NUMERIC,
    price_staleness_days     SMALLINT
);

CREATE INDEX IF NOT EXISTS idx_signal_outcomes_date   ON signal_outcomes(signal_date);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_symbol ON signal_outcomes(symbol);

-- Added 2026-08-23. Live in production and declared by no migration until now;
-- found by diffing every production index against migrations/. It belongs here
-- rather than in the reconstructed 0018 for a mechanical reason: files replay in
-- filename order and signal_outcomes does not exist until this file.
--
-- Production/repo state of the three indexes on this table, measured 2026-08-23,
-- because they disagree and that disagreement is the point:
--   idx_signal_outcomes_date        live AND declared here (created ad-hoc)
--   idx_signal_outcomes_model_date  live, declared NOWHERE until this line
--   idx_signal_outcomes_symbol      declared here, NOT live
-- So this file's own "ALREADY SATISFIED in production" header is two-thirds
-- true: the table matches, one index is missing and one was undeclared.
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_model_date ON signal_outcomes(model, signal_date);
