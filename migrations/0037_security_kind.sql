-- 0037_security_kind.sql
--
-- Multi-instrument expansion Phase 1, the KEYSTONE
-- (docs/proposals/multi-instrument-expansion-2026-07-11.md).
--
-- Adds `security_kind` to `universe` so ETFs / LICs / REITs / hybrids can be held, valued and
-- taxed WITHOUT entering Model A's training/prediction universe. Today `universe.is_active` is
-- triple-overloaded (price-fetching + ML-universe membership + delisting); this column gives
-- "what kind of instrument" its own axis so `is_active` can shrink back to "currently listed."
--
-- BEHAVIOR-PRESERVING: the backfill sets every existing row to the kind its suffix already
-- implies, and the `au_equity` set is exactly today's active ASX-equity universe. So the paired
-- reader change (WHERE is_active AND security_kind = 'au_equity') is a NO-OP on current data.
--
-- ORDERING INVARIANT (proposal §3 — load-bearing, do not invert):
--   1. Apply THIS migration (column + backfill). Readers still use bare `is_active` -> unchanged.
--   2. Deploy the ML/screening reader edits (add `AND security_kind = 'au_equity'`). Still a
--      no-op today, but now structurally kind-scoped.
--   3. ONLY THEN change refresh_universe to ingest ETF/FUND types (a later migration/PR).
-- If an ETF lands as is_active=TRUE while any reader still says bare `WHERE is_active`, it
-- silently enters Model A's fundamentals-zero-filled universe and emits garbage signals —
-- corrupting a model whose reliability is already under the rule #11 dispute.
--
-- Backfill counts verified against live `universe` (2026-07-11):
--   1894 `%.AU`   -> au_equity  (incl. 59 A-REITs — kept as equity to preserve their existing
--                                 Model A coverage + single-name thesis eligibility)
--      1 `%.INDX` -> index      (AXJO.INDX)
--      1 foreign  -> us_equity  (HUBS.NYSE)
-- No ETF/LIC/hybrid rows exist yet; they populate when refresh_universe starts ingesting them
-- (step 3 above) and via targeted reclassification. Anything unclassified stays au_equity —
-- the safe default that keeps the ML universe identical to today.
--
-- TEXT + CHECK (not a native ENUM), matching `underlyings.category` (migration 0014): avoids the
-- non-transactional, un-droppable `ALTER TYPE ... ADD VALUE` when the kind list grows.
--
-- Applied via: mcp__supabase__apply_migration
-- After applying: bump REQUIRED_MIGRATIONS in asxos/api/main.py to the observed
-- SELECT count(*) FROM supabase_migrations.schema_migrations.

BEGIN;

ALTER TABLE universe ADD COLUMN security_kind TEXT;

-- Default everything to the safe kind, then override by exchange suffix (suffixes are disjoint).
UPDATE universe SET security_kind = 'au_equity';

UPDATE universe SET security_kind = 'index'
  WHERE symbol LIKE '%.INDX';

UPDATE universe SET security_kind = 'us_equity'
  WHERE symbol LIKE '%.US'
     OR symbol LIKE '%.NYSE'
     OR symbol LIKE '%.NASDAQ'
     OR symbol LIKE '%.AMEX';

ALTER TABLE universe
  ALTER COLUMN security_kind SET NOT NULL,
  ADD CONSTRAINT universe_security_kind_chk
    CHECK (security_kind IN
      ('au_equity', 'us_equity', 'index', 'etf', 'lic', 'reit', 'hybrid'));

-- The kind-scoped reads (ML filters on 'au_equity'; price/allocator select by kind) hit
-- (security_kind, is_active) together — index it.
CREATE INDEX universe_kind_active_idx ON universe (security_kind, is_active);

COMMIT;
