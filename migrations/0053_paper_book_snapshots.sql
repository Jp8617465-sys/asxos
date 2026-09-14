-- 0053_paper_book_snapshots.sql
-- C1: the paper book (James's ruling, 2026-09-07) — ADR D15.
--
-- 25,000.000000 AUD at 100% cash, its own snapshot id, flagged paper so that
-- no live-book query can read it.
--
-- WHY A SEPARATE TABLE, NOT A `book` COLUMN ON portfolio_daily_snapshots.
-- The ruling is that the paper book is invisible to live-book aggregation.
-- A flag column makes that a property of every SELECT ever written against
-- the table: one forgotten `WHERE book = 'live'` silently mixes paper money
-- into the live cash floor, the sizer's headroom and the brief. Separating
-- the tables makes the invariant structural — an existing live query cannot
-- read this table because it does not name it, and a new one has to name it
-- deliberately. The cost is a second loader; the benefit is that the failure
-- mode requires an act of commission rather than an omission.
--
-- Live readers of portfolio_daily_snapshots are unchanged by this migration
-- and continue to see only the live book:
--   asxos/domain/decision_engine/portfolio_state.py::load_portfolio_state
--   jobs/snapshot_portfolio.py
--   asxos/brief/compose.py
--
-- Append-only, like the 13 decision/research tables (0043, 0048, 0050-0052):
-- a paper book that can be edited after a case was challenged against it is
-- not evidence of anything.

CREATE TABLE paper_book_snapshots (
    snapshot_id      VARCHAR(200)  PRIMARY KEY
                     CHECK (char_length(snapshot_id) >= 1),
    -- Present so a reader of one row can see what it is without joining
    -- anything. Pinned by CHECK: this table cannot hold a live book.
    book             VARCHAR(5)    NOT NULL DEFAULT 'paper'
                     CHECK (book = 'paper'),
    as_of            DATE          NOT NULL,
    label            TEXT          NOT NULL CHECK (label <> ''),
    capital_aud      NUMERIC(18,6) NOT NULL CHECK (capital_aud > 0),
    holdings_mv_aud  NUMERIC(18,6) NOT NULL CHECK (holdings_mv_aud >= 0),
    cash_aud         NUMERIC(18,6) NOT NULL CHECK (cash_aud >= 0),
    holdings_count   INTEGER       NOT NULL CHECK (holdings_count >= 0),
    ingested_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    -- The book must balance. A paper book whose parts do not sum to its
    -- capital would produce a cash_pct the sizer would act on.
    CONSTRAINT paper_book_balances
        CHECK (capital_aud = holdings_mv_aud + cash_aud),
    -- A book with no holdings holds only cash. Pins the C1 shape.
    CONSTRAINT paper_book_empty_is_all_cash
        CHECK (holdings_count > 0 OR holdings_mv_aud = 0)
);

CREATE INDEX idx_paper_book_snapshots_asof ON paper_book_snapshots (as_of DESC);

CREATE OR REPLACE FUNCTION _paper_book_forbid_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'paper_book_snapshots is append-only: % on snapshot_id=% is refused',
        TG_OP, OLD.snapshot_id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER paper_book_snapshots_forbid_mutation
    BEFORE UPDATE OR DELETE ON paper_book_snapshots
    FOR EACH ROW EXECUTE FUNCTION _paper_book_forbid_mutation();

-- The ruled C1 book. 25,000.000000 AUD, 100% cash, no holdings.
INSERT INTO paper_book_snapshots (
    snapshot_id, as_of, label, capital_aud, holdings_mv_aud, cash_aud, holdings_count
) VALUES (
    'paper-c1-2026-09-07',
    DATE '2026-09-07',
    'C1 paper book — James''s ruling 2026-09-07, ADR D15',
    25000.000000,
    0.000000,
    25000.000000,
    0
);
