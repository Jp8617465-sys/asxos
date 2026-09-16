-- 0056_cash_balance_assertions.sql
-- #228 PR 3 (F-E2E r2 M1): the authoritative cash source — dated, sourced,
-- append-only balance assertions.
--
-- WHAT IT IS. One row per time somebody (James from a statement, or arbi for
-- the paper book's mirror — never a job inferring from policy) ASSERTS the live
-- account's AUD cash balance as at a date. A reader takes the latest as_of at
-- or before the date it needs and derives staleness itself ("this balance is
-- N days old"); staleness is never stored, because a stored validity window is
-- a second thing that can be wrong.
--
-- WHAT IT IS NOT. Not a cash ledger: no flows, no reconciliation arithmetic.
-- Dividends, fees and fills move cash on every day; a flow model that was ever
-- one entry short would be silently wrong forever, whereas an assertion is
-- either the balance the statement shows or it is not. The ledger is a later
-- decision, on evidence that assertions are too coarse.
--
-- Append-only by trigger, like the 13 decision/research tables (0043, 0048,
-- 0050-0054): a balance that can be edited after a challenge was sized against
-- it is not evidence of anything. A wrong assertion is corrected by a NEW row
-- for the same as_of with a later recorded_at, which the read order prefers.
--
-- Irreplaceable (hand-recorded): added to scripts/backup_irreplaceable.sh in
-- the same PR, conditionally, so the script stays green against a database
-- where this migration is not yet applied (restore-drill schema, forks).
--
-- Consumers (each its own PR, none in this migration):
--   jobs/snapshot_portfolio.py       write cash_aud from the latest assertion,
--                                    NULL (with capital_aud, 0055) when none
--   decision_engine/portfolio_state  cash_pct measured only from this table
--   asx cash assert <amount> ...     the CLI that writes a row

CREATE TABLE cash_balance_assertions (
    assertion_id  BIGSERIAL     PRIMARY KEY,
    as_of         DATE          NOT NULL,
    cash_aud      NUMERIC(18,6) NOT NULL CHECK (cash_aud >= 0),
    -- Where the number came from. 'manual_entry' is James typing a figure he
    -- read; the statement kinds carry the document they were read from.
    source        VARCHAR(40)   NOT NULL
                  CHECK (source IN ('broker_statement', 'bank_statement', 'manual_entry')),
    asserted_by   VARCHAR(10)   NOT NULL CHECK (asserted_by IN ('human', 'agent')),
    evidence_uri  TEXT          CHECK (evidence_uri IS NULL OR evidence_uri <> ''),
    note          TEXT,
    recorded_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- A statement-sourced assertion names its statement.
    CONSTRAINT cash_balance_assertions_statement_names_evidence
        CHECK (source = 'manual_entry' OR evidence_uri IS NOT NULL),
    -- An agent never asserts the live balance from a statement it cannot read;
    -- an agent row is a manual entry of a figure a human gave it, and says so.
    CONSTRAINT cash_balance_assertions_agent_is_manual
        CHECK (asserted_by = 'human' OR source = 'manual_entry')
);

COMMENT ON TABLE cash_balance_assertions IS
    'Dated, sourced, append-only assertions of the live account AUD cash balance '
    '(#228). Readers take the latest as_of <= their date, latest recorded_at '
    'first, and derive staleness at read time. Never inferred from policy.';

-- The read path: latest assertion at or before a date.
CREATE INDEX idx_cash_balance_assertions_asof
    ON cash_balance_assertions (as_of DESC, recorded_at DESC);

CREATE OR REPLACE FUNCTION _cash_balance_assertions_forbid_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'cash_balance_assertions is append-only: % on assertion_id=% is refused -- '
        'record a new assertion for the same as_of instead',
        TG_OP, OLD.assertion_id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cash_balance_assertions_forbid_mutation
    BEFORE UPDATE OR DELETE ON cash_balance_assertions
    FOR EACH ROW EXECUTE FUNCTION _cash_balance_assertions_forbid_mutation();
