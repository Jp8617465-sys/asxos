-- migration_drill_0043.sql
--
-- Observed rehearsal of migration 0043 (price-history containment) against a
-- DISPOSABLE PostgreSQL 17 instance. Never run this against production.
--
-- Why this file exists: tests/test_price_revision_migration.py asserts the
-- migration's TEXT with regex and never executes it — the file says so itself
-- ("The migration is intentionally not applied in CI"). That is precisely the
-- Phase-2a live-fire lesson in .claude/rules/portfolio-conventions.md: mocked or
-- text-level tests do not enforce trigger semantics. PR #84 therefore names an
-- observed rehearsal as its own production gate:
--
--     "Before production application, run migration 0043 against a disposable
--      PostgreSQL database and observe update, delete, no-op, and immutability
--      behaviour end to end."
--
-- This script is that observation. It runs under ON_ERROR_STOP=1, so ANY
-- deviation aborts the run non-zero. Every scenario prints what it observed, so
-- a green run is evidence rather than an assertion of faith.
--
-- Preconditions: 0001_initial.sql then 0043_price_revisions.sql already applied.

\set ON_ERROR_STOP on
\set VERBOSITY default
SET client_min_messages = notice;

\echo '=== 0043 DRILL — observed behaviour against disposable PostgreSQL ==='
\echo ''

-- ---------------------------------------------------------------------------
-- S0 — fixture
-- ---------------------------------------------------------------------------
INSERT INTO universe (symbol, sector, currency, is_active)
VALUES ('DRILL.AX', 'Materials', 'AUD', TRUE);

INSERT INTO prices (symbol, dt, open, high, low, close, volume, adj_close)
VALUES ('DRILL.AX', DATE '2026-08-10', 10.0, 10.5, 9.8, 10.2, 1000, 10.2);

\echo 'S0  fixture inserted (1 universe row, 1 prices row)'

DO $$
BEGIN
    IF (SELECT count(*) FROM price_revisions) <> 0 THEN
        RAISE EXCEPTION 'S0 FAILED: plain INSERT into prices manufactured a revision';
    END IF;
    RAISE NOTICE 'S0  OBSERVED: INSERT produces no revision row (correct — only UPDATE/DELETE are destructive)';
END $$;

-- ---------------------------------------------------------------------------
-- S1 — material UPDATE captures complete OLD and NEW, in the same transaction
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_txid  BIGINT;
    v_rev   price_revisions;
BEGIN
    v_txid := pg_current_xact_id()::text::bigint;

    UPDATE prices
       SET close = 5.10, adj_close = 5.10
     WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10';

    SELECT * INTO v_rev FROM price_revisions ORDER BY revision_id DESC LIMIT 1;

    IF (SELECT count(*) FROM price_revisions) <> 1 THEN
        RAISE EXCEPTION 'S1 FAILED: expected exactly 1 revision, got %',
            (SELECT count(*) FROM price_revisions);
    END IF;
    IF v_rev.operation <> 'update' THEN
        RAISE EXCEPTION 'S1 FAILED: operation=% expected update', v_rev.operation;
    END IF;
    IF v_rev.prior_close <> 10.2 OR v_rev.prior_adj_close <> 10.2 THEN
        RAISE EXCEPTION 'S1 FAILED: prior values not captured (close=% adj=%)',
            v_rev.prior_close, v_rev.prior_adj_close;
    END IF;
    IF v_rev.replacement_close <> 5.10 OR v_rev.replacement_adj_close <> 5.10 THEN
        RAISE EXCEPTION 'S1 FAILED: replacement values not captured (close=% adj=%)',
            v_rev.replacement_close, v_rev.replacement_adj_close;
    END IF;
    -- Untouched columns must still be carried on both sides, not left NULL.
    IF v_rev.prior_open <> 10.0 OR v_rev.replacement_open <> 10.0
       OR v_rev.prior_volume <> 1000 OR v_rev.replacement_volume <> 1000 THEN
        RAISE EXCEPTION 'S1 FAILED: untouched columns not carried on both sides';
    END IF;
    -- The load-bearing atomicity proof: the ledger row carries the xid of the
    -- transaction that performed the price mutation, so capture cannot be a
    -- separate later write that could be lost independently.
    IF v_rev.transaction_id <> v_txid THEN
        RAISE EXCEPTION 'S1 FAILED: capture xid % <> mutation xid % — NOT same-transaction',
            v_rev.transaction_id, v_txid;
    END IF;

    RAISE NOTICE 'S1  OBSERVED: destructive UPDATE captured prior close=% adj=% -> replacement close=% adj=%, xid=% (same transaction)',
        v_rev.prior_close, v_rev.prior_adj_close,
        v_rev.replacement_close, v_rev.replacement_adj_close, v_rev.transaction_id;
END $$;

-- ---------------------------------------------------------------------------
-- S2 — no-op UPDATE writes nothing
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_before BIGINT; v_after BIGINT;
BEGIN
    SELECT count(*) INTO v_before FROM price_revisions;

    UPDATE prices
       SET close = 5.10, adj_close = 5.10
     WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10';

    SELECT count(*) INTO v_after FROM price_revisions;
    IF v_after <> v_before THEN
        RAISE EXCEPTION 'S2 FAILED: no-op UPDATE manufactured % revision(s)', v_after - v_before;
    END IF;
    RAISE NOTICE 'S2  OBSERVED: no-op UPDATE (identical values) produced no revision — ledger count still %', v_after;
END $$;

-- ---------------------------------------------------------------------------
-- S3 — the REAL ingestion path: ON CONFLICT DO UPDATE with identical values.
--      asxos/ingestion/prices.py upserts every row on every run; without the
--      no-op guard this would manufacture a revision per symbol per run.
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_before BIGINT; v_after BIGINT;
BEGIN
    SELECT count(*) INTO v_before FROM price_revisions;

    INSERT INTO prices (symbol, dt, open, high, low, close, volume, adj_close)
    VALUES ('DRILL.AX', DATE '2026-08-10', 10.0, 10.5, 9.8, 5.10, 1000, 5.10)
    ON CONFLICT (symbol, dt) DO UPDATE SET
        open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
        close = EXCLUDED.close, volume = EXCLUDED.volume,
        adj_close = EXCLUDED.adj_close;

    SELECT count(*) INTO v_after FROM price_revisions;
    IF v_after <> v_before THEN
        RAISE EXCEPTION 'S3 FAILED: idempotent re-upsert manufactured % revision(s)', v_after - v_before;
    END IF;
    RAISE NOTICE 'S3  OBSERVED: re-running the production upsert with unchanged values produced no revision (no per-run ledger noise)';
END $$;

-- ---------------------------------------------------------------------------
-- S4 — the DEFECT ITSELF: an upsert that silently rewrites adj_close.
--      This is what defect #3 has been doing on every dividend/split.
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_rev price_revisions;
BEGIN
    INSERT INTO prices (symbol, dt, open, high, low, close, volume, adj_close)
    VALUES ('DRILL.AX', DATE '2026-08-10', 10.0, 10.5, 9.8, 5.10, 1000, 4.87)
    ON CONFLICT (symbol, dt) DO UPDATE SET
        adj_close = EXCLUDED.adj_close;

    SELECT * INTO v_rev FROM price_revisions ORDER BY revision_id DESC LIMIT 1;

    IF v_rev.operation <> 'update' OR v_rev.prior_adj_close <> 5.10
       OR v_rev.replacement_adj_close <> 4.87 THEN
        RAISE EXCEPTION 'S4 FAILED: dividend-style adj_close rewrite not captured (prior=% replacement=%)',
            v_rev.prior_adj_close, v_rev.replacement_adj_close;
    END IF;
    RAISE NOTICE 'S4  OBSERVED: the exact defect-#3 write path (upsert rewriting adj_close %% -> %%) is now recoverable from the ledger';
    RAISE NOTICE '        prior_adj_close=% replacement_adj_close=%', v_rev.prior_adj_close, v_rev.replacement_adj_close;
END $$;

-- ---------------------------------------------------------------------------
-- S5 — DELETE writes a tombstone with NULL replacement
-- ---------------------------------------------------------------------------
INSERT INTO prices (symbol, dt, open, high, low, close, volume, adj_close)
VALUES ('DRILL.AX', DATE '2026-08-11', 1.0, 2.0, 0.5, 1.5, 77, 1.5);

DO $$
DECLARE v_rev price_revisions;
BEGIN
    DELETE FROM prices WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-11';

    SELECT * INTO v_rev FROM price_revisions ORDER BY revision_id DESC LIMIT 1;

    IF v_rev.operation <> 'delete' THEN
        RAISE EXCEPTION 'S5 FAILED: operation=% expected delete', v_rev.operation;
    END IF;
    IF v_rev.prior_close <> 1.5 OR v_rev.prior_volume <> 77 THEN
        RAISE EXCEPTION 'S5 FAILED: deleted row values not captured';
    END IF;
    IF v_rev.replacement_symbol IS NOT NULL OR v_rev.replacement_dt IS NOT NULL
       OR v_rev.replacement_close IS NOT NULL OR v_rev.replacement_adj_close IS NOT NULL
       OR v_rev.replacement_open IS NOT NULL OR v_rev.replacement_high IS NOT NULL
       OR v_rev.replacement_low IS NOT NULL OR v_rev.replacement_volume IS NOT NULL THEN
        RAISE EXCEPTION 'S5 FAILED: delete tombstone carries non-NULL replacement values';
    END IF;
    RAISE NOTICE 'S5  OBSERVED: DELETE recorded as tombstone (prior close=% volume=%, every replacement column NULL)',
        v_rev.prior_close, v_rev.prior_volume;
END $$;

-- ---------------------------------------------------------------------------
-- S6 — atomicity in the safe direction: rolling back the price mutation
--      rolls back its capture too. No orphan ledger rows.
-- ---------------------------------------------------------------------------
BEGIN;
UPDATE prices SET close = 999.99 WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10';
ROLLBACK;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM price_revisions WHERE replacement_close = 999.99) THEN
        RAISE EXCEPTION 'S6 FAILED: rolled-back UPDATE left an orphan revision row';
    END IF;
    IF (SELECT close FROM prices WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10') <> 5.10 THEN
        RAISE EXCEPTION 'S6 FAILED: rolled-back UPDATE mutated the served row';
    END IF;
    RAISE NOTICE 'S6  OBSERVED: ROLLBACK discarded both the price change and its ledger row — no orphan capture';
END $$;

-- ---------------------------------------------------------------------------
-- S7 — the ledger is append-only: UPDATE / DELETE / TRUNCATE all rejected
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_state TEXT;
BEGIN
    BEGIN
        UPDATE price_revisions SET prior_close = 0 WHERE revision_id > 0;
        RAISE EXCEPTION 'S7a FAILED: UPDATE on price_revisions was permitted';
    EXCEPTION WHEN sqlstate '55000' THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE;
        RAISE NOTICE 'S7a OBSERVED: UPDATE price_revisions rejected, SQLSTATE %', v_state;
    END;

    BEGIN
        DELETE FROM price_revisions WHERE revision_id > 0;
        RAISE EXCEPTION 'S7b FAILED: DELETE on price_revisions was permitted';
    EXCEPTION WHEN sqlstate '55000' THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE;
        RAISE NOTICE 'S7b OBSERVED: DELETE price_revisions rejected, SQLSTATE %', v_state;
    END;

    BEGIN
        TRUNCATE price_revisions;
        RAISE EXCEPTION 'S7c FAILED: TRUNCATE on price_revisions was permitted';
    EXCEPTION WHEN sqlstate '55000' THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE;
        RAISE NOTICE 'S7c OBSERVED: TRUNCATE price_revisions rejected, SQLSTATE %', v_state;
    END;
END $$;

-- ---------------------------------------------------------------------------
-- S8 — TRUNCATE prices is rejected (row triggers cannot audit it)
-- ---------------------------------------------------------------------------
DO $$
DECLARE v_state TEXT;
BEGIN
    BEGIN
        TRUNCATE prices;
        RAISE EXCEPTION 'S8 FAILED: TRUNCATE prices was permitted — history could vanish unaudited';
    EXCEPTION WHEN sqlstate '55000' THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE;
        RAISE NOTICE 'S8  OBSERVED: TRUNCATE prices rejected, SQLSTATE %', v_state;
    END;
END $$;

-- ---------------------------------------------------------------------------
-- S9 — SECURITY DEFINER does what its comment claims: a prices writer with NO
--      rights on price_revisions still triggers a successful capture.
-- ---------------------------------------------------------------------------
CREATE ROLE drill_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO drill_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON prices TO drill_writer;
-- deliberately NO grant on price_revisions, and no sequence grant

DO $$
DECLARE v_before BIGINT; v_after BIGINT; v_rev price_revisions;
BEGIN
    SELECT count(*) INTO v_before FROM price_revisions;

    SET LOCAL ROLE drill_writer;
    UPDATE prices SET close = 6.25 WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10';
    RESET ROLE;

    SELECT count(*) INTO v_after FROM price_revisions;
    IF v_after <> v_before + 1 THEN
        RAISE EXCEPTION 'S9 FAILED: unprivileged writer produced % captures, expected 1', v_after - v_before;
    END IF;
    SELECT * INTO v_rev FROM price_revisions ORDER BY revision_id DESC LIMIT 1;
    IF v_rev.recorded_by <> 'drill_writer' THEN
        RAISE NOTICE 'S9  NOTE: recorded_by=% (session_user, not the SECURITY DEFINER owner)', v_rev.recorded_by;
    END IF;
    RAISE NOTICE 'S9  OBSERVED: a role with zero rights on price_revisions still triggered capture (SECURITY DEFINER works as documented); recorded_by=%',
        v_rev.recorded_by;
END $$;

-- ---------------------------------------------------------------------------
-- S10 — fail-closed on an unledgered column. The migration claims: "if a future
--       column changes without this ledger being extended, the payload-shape
--       constraint fails closed instead of silently losing that field."
--       This is the subtlest claim in the file and the one most likely to rot.
--       Run last, on a throwaway column, then reverted.
-- ---------------------------------------------------------------------------
ALTER TABLE prices ADD COLUMN drill_future_col TEXT;

DO $$
DECLARE v_state TEXT; v_before BIGINT;
BEGIN
    SELECT count(*) INTO v_before FROM price_revisions;
    BEGIN
        UPDATE prices SET drill_future_col = 'changed'
         WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10';
        RAISE EXCEPTION 'S10 FAILED: a change to an unledgered column was silently accepted — the field would be lost';
    EXCEPTION WHEN check_violation THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE;
        RAISE NOTICE 'S10 OBSERVED: change to an unledgered column FAILED CLOSED, SQLSTATE % (payload-shape constraint)', v_state;
    END;

    IF (SELECT count(*) FROM price_revisions) <> v_before THEN
        RAISE EXCEPTION 'S10 FAILED: fail-closed path still wrote a ledger row';
    END IF;
    IF (SELECT drill_future_col FROM prices
         WHERE symbol = 'DRILL.AX' AND dt = DATE '2026-08-10') IS NOT NULL THEN
        RAISE EXCEPTION 'S10 FAILED: the rejected UPDATE still mutated the row';
    END IF;
END $$;

ALTER TABLE prices DROP COLUMN drill_future_col;

-- ---------------------------------------------------------------------------
-- Summary
-- ---------------------------------------------------------------------------
\echo ''
\echo '=== LEDGER CONTENTS AFTER DRILL ==='
SELECT revision_id, operation, prior_close, prior_adj_close,
       replacement_close, replacement_adj_close, recorded_by
  FROM price_revisions
 ORDER BY revision_id;

\echo ''
\echo '=== SERVED prices AFTER DRILL ==='
SELECT symbol, dt, close, adj_close FROM prices ORDER BY symbol, dt;

DO $$
DECLARE v_updates BIGINT; v_deletes BIGINT;
BEGIN
    SELECT count(*) FILTER (WHERE operation = 'update'),
           count(*) FILTER (WHERE operation = 'delete')
      INTO v_updates, v_deletes
      FROM price_revisions;

    -- S1, S4, S9 are the three material updates; S5 is the sole delete.
    IF v_updates <> 3 OR v_deletes <> 1 THEN
        RAISE EXCEPTION 'DRILL FAILED: expected 3 update + 1 delete revisions, got % + %',
            v_updates, v_deletes;
    END IF;
    RAISE NOTICE 'DRILL PASSED: % update revisions, % delete tombstone, all 10 scenarios observed',
        v_updates, v_deletes;
END $$;

\echo ''
\echo '=== 0043 DRILL COMPLETE — all scenarios observed ==='
