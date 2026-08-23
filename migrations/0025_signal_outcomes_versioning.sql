-- 0025_signal_outcomes_versioning.sql
-- Versions the pre-existing `signal_outcomes` table (created ad-hoc by
-- jobs/track_signal_outcomes.py and never captured in migrations/ — audit gap).
--
-- Every statement is IF NOT EXISTS, so this is a no-op against any database that
-- already carries the table. It exists so a fresh/dev database reproduces it and
-- so the shape is reviewable in repo. Whether it has been applied is a question
-- for scripts/check_migration_drift.py, which reads the ledger; it is
-- deliberately not asserted here.
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

-- Added 2026-08-23: found by diffing production's indexes against this repo and
-- declared by nothing until now. It belongs here rather than in the
-- reconstructed 0018 for a mechanical reason — files replay in filename order
-- and signal_outcomes does not exist until this file.
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_model_date ON signal_outcomes(model, signal_date);
