-- 0058_risk_free_pit.sql
-- Issue #301: the risk-free rate becomes a point-in-time series.
--
-- WHY THIS EXISTS. `ke = risk_free + beta * erp` (domain/valuation/capm.py), and
-- `ke` is the DISCOUNT RATE in a residual-income model — one of the two or three
-- inputs the output is most sensitive to. Until now the only source for it was
-- `market_context_current`, which is a daily-forward ingest and not a series:
-- 55 rows, all from 2026-07-03, carrying 3 distinct values of aus_10y_yield.
--
-- The consequence was not a slow backtest, it was no backtest. The valuation
-- model could not be replayed at ANY historical cutoff, so it could not be
-- validated against a realised return at all — which is how it came to be live
-- on 2026-09-16, emitting target prices for 23 named securities, with
-- `research_runs` still empty. The sealed value-to-price test hard-failed on
-- exactly this (run 35135765565) rather than substituting today's rate, which
-- would have injected look-ahead bias into a pre-registered test.
--
-- WHAT IT IS. One row per (series, as_of) observation, as published. FRED
-- IRLTLT01AUM156N (Australia 10-year government bond yield) is monthly, which
-- is sufficient for quarterly cutoffs; `series` is stored per row rather than
-- assumed, so a later daily series can land beside the monthly one without a
-- second table or a rewrite of these rows.
--
-- A reader takes the latest `as_of` AT OR BEFORE the date it needs and derives
-- staleness itself. Staleness is never stored, for the reason 0056 gives: a
-- stored validity window is a second thing that can be wrong.
--
-- WHAT IT IS NOT. Not a replacement for `market_context` — that table carries
-- breadth, regime and the other indicators, and keeps doing so. This table
-- owns ONE quantity. The valuation read path moves to it as its SINGLE source
-- in a follow-up PR, once a backfill has been run and verified, so the live
-- sweep never reads an empty table. It is deliberately NOT a second source
-- standing beside `market_context_current`: PR #298 has just finished
-- documenting what a duplicated policy value costs (profiles.cash_floor_pct = 0
-- against CASH_FLOOR_PCT = 7.5), and repeating that shape in the data layer
-- would be learning nothing.
--
-- NOT append-only by trigger, unlike 0043/0048/0050-0057. Those tables hold
-- evidence, assertions and decisions — things whose value depends on not being
-- editable after the fact. This one holds a published third-party observation
-- that is periodically REVISED by its publisher; a revision must overwrite, or
-- the series silently keeps a stale print forever. `ingested_at` records when
-- each value was last written so a revision is visible. Nothing here is
-- evidence of a decision, so nothing here needs to be immutable.
--
-- Re-derivable from FRED, so NOT added to scripts/backup_irreplaceable.sh.
--
-- Consumers (each its own PR, none in this migration):
--   jobs/backfill_risk_free.py       writes rows from FRED (this PR)
--   valuation/universe.py            load_market_inputs reads it (follow-up PR)

CREATE TABLE risk_free_rates (
    -- The series as published, so a later daily series coexists with the
    -- monthly one rather than silently overwriting it.
    series      VARCHAR(60)   NOT NULL CHECK (series <> ''),
    -- The observation date FRED publishes, never the date we fetched it.
    as_of       DATE          NOT NULL,
    -- Percent, as published (4.99 means 4.99%), NOT a decimal fraction. The
    -- reader divides by 100 — matching what load_market_inputs already does
    -- with market_context_current.aus_10y_yield, so the conversion does not
    -- move and then have to be found in two places.
    yield_pct   NUMERIC(18,6) NOT NULL,
    -- Where it came from, so a hand-entered value can never be mistaken for a
    -- published one.
    source      VARCHAR(40)   NOT NULL DEFAULT 'fred'
                CHECK (source IN ('fred', 'manual_entry')),
    -- When this row was last written. A FRED revision updates yield_pct and
    -- moves this forward; the pair is how a revision is detected.
    ingested_at TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    PRIMARY KEY (series, as_of)
);

-- The only access pattern: "the latest observation at or before this cutoff",
-- once per cutoff per replay.
CREATE INDEX idx_risk_free_rates_series_as_of_desc
    ON risk_free_rates (series, as_of DESC);

COMMENT ON TABLE risk_free_rates IS
    'Point-in-time risk-free rate observations as published (issue #301). '
    'yield_pct is percent, not a fraction. Readers take the latest as_of at or '
    'before the date they need and derive staleness themselves. Overwritable by '
    'design: FRED revises published values, and a series that cannot take a '
    'revision keeps a stale print forever.';
