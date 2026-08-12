-- 0043_price_revisions.sql
--
-- PRODUCTION-READY — still unapplied. Apply only through the separately approved
-- Supabase migration workflow in docs/product/runbooks/price-revisions-0043.md,
-- then bump REQUIRED_MIGRATIONS to the observed schema_migrations count. Migration
-- number 0042 is deliberately skipped here:
-- it is reserved by the parked rules-integrity PR #80 and must remain unapplied.
--
-- Stage 1 price-history containment. The serving `prices` table remains the
-- current projection, but every UPDATE that actually changes a row and every
-- DELETE now writes the complete prior/replacement values to an append-only
-- ledger in the SAME Postgres transaction. An audit insert failure therefore
-- rolls the price mutation back; there is no application-layer bypass.
--
-- Deliberate limits of this slice:
--   * no historical backfill — the first post-migration change captures the
--     then-current row as its prior value;
--   * no provider raw-payload archive or source-object identity (later Stage 1);
--   * no S3, Dagster, provider, scheduler, or ingestion-code change;
--   * recorded_at is when Postgres observed the replacement, not the vendor's
--     first-publication time. `dt` remains the economic observation date.
--
-- Safety properties:
--   * AFTER-row capture sees the final NEW row after any BEFORE triggers;
--   * trigger work is atomic with the UPDATE/DELETE that caused it;
--   * no-op UPDATEs are idempotent and do not manufacture revisions;
--   * DELETE is retained as an explicit tombstone;
--   * TRUNCATE prices is rejected because row triggers cannot audit it;
--   * UPDATE/DELETE/TRUNCATE price_revisions are rejected by the database.
--
-- Emergency rollback (data preserving): if the trigger causes a confirmed ingestion
-- outage, apply a NEW governed migration that drops only
-- public.prices_revision_capture. Keep public.price_revisions and its append-only
-- trigger intact. Never edit this file after production application and never drop the
-- ledger merely to restore ingestion; doing so would destroy the evidence this migration
-- exists to preserve.

BEGIN;

-- DDL must fail rather than wait indefinitely behind a live price writer. A retry in a
-- confirmed quiet window is safer than an unbounded production lock.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

-- The ledger below is intentionally a complete typed copy of the current prices row.
-- Refuse application if the live table has drifted: otherwise a newly added column could
-- change alongside a captured column and escape revision history.
DO $migration_preflight$
DECLARE
    actual_shape TEXT;
    primary_key_definition TEXT;
    expected_shape CONSTANT TEXT :=
        'symbol:text:true,dt:date:true,open:numeric(18,6):false,'
        'high:numeric(18,6):false,low:numeric(18,6):false,'
        'close:numeric(18,6):true,volume:bigint:false,'
        'adj_close:numeric(18,6):false';
BEGIN
    IF to_regclass('public.prices') IS NULL THEN
        RAISE EXCEPTION '0043 preflight: public.prices does not exist';
    END IF;

    SELECT string_agg(
        attribute.attname || ':'
        || format_type(attribute.atttypid, attribute.atttypmod) || ':'
        || attribute.attnotnull::TEXT,
        ',' ORDER BY attribute.attnum
    )
    INTO actual_shape
    FROM pg_attribute AS attribute
    WHERE attribute.attrelid = 'public.prices'::regclass
      AND attribute.attnum > 0
      AND NOT attribute.attisdropped;

    IF actual_shape IS DISTINCT FROM expected_shape THEN
        RAISE EXCEPTION
            '0043 preflight: public.prices shape mismatch; expected %, observed %',
            expected_shape,
            actual_shape;
    END IF;

    SELECT pg_get_constraintdef(constraint_row.oid)
    INTO primary_key_definition
    FROM pg_constraint AS constraint_row
    WHERE constraint_row.conrelid = 'public.prices'::regclass
      AND constraint_row.contype = 'p';

    IF primary_key_definition IS DISTINCT FROM 'PRIMARY KEY (symbol, dt)' THEN
        RAISE EXCEPTION
            '0043 preflight: public.prices primary key mismatch; observed %',
            primary_key_definition;
    END IF;
END;
$migration_preflight$;

CREATE TABLE public.price_revisions (
    revision_id             BIGSERIAL      PRIMARY KEY,
    operation               TEXT           NOT NULL
        CHECK (operation IN ('update', 'delete')),

    -- Prior row identity and values: exactly what ASXOS previously served.
    prior_symbol            TEXT           NOT NULL,
    prior_dt                DATE           NOT NULL,
    prior_open              NUMERIC(18,6),
    prior_high              NUMERIC(18,6),
    prior_low               NUMERIC(18,6),
    prior_close             NUMERIC(18,6)  NOT NULL,
    prior_volume            BIGINT,
    prior_adj_close         NUMERIC(18,6),

    -- Replacement identity and values. NULL throughout for a delete tombstone.
    replacement_symbol      TEXT,
    replacement_dt          DATE,
    replacement_open        NUMERIC(18,6),
    replacement_high        NUMERIC(18,6),
    replacement_low         NUMERIC(18,6),
    replacement_close       NUMERIC(18,6),
    replacement_volume      BIGINT,
    replacement_adj_close   NUMERIC(18,6),

    -- Durable database-side recording identity. application_name is diagnostic
    -- context, not trusted provider provenance; the later SourceObject work owns
    -- provider/run/content identity.
    recorded_at             TIMESTAMPTZ    NOT NULL,
    transaction_id          BIGINT         NOT NULL,
    recorded_by             TEXT           NOT NULL,
    recorded_application    TEXT           NOT NULL,

    CONSTRAINT price_revisions_payload_shape CHECK (
        (
            operation = 'update'
            AND replacement_symbol IS NOT NULL
            AND replacement_dt IS NOT NULL
            AND replacement_close IS NOT NULL
            AND ROW(
                prior_symbol, prior_dt, prior_open, prior_high, prior_low,
                prior_close, prior_volume, prior_adj_close
            ) IS DISTINCT FROM ROW(
                replacement_symbol, replacement_dt, replacement_open,
                replacement_high, replacement_low, replacement_close,
                replacement_volume, replacement_adj_close
            )
        )
        OR
        (
            operation = 'delete'
            AND replacement_symbol IS NULL
            AND replacement_dt IS NULL
            AND replacement_open IS NULL
            AND replacement_high IS NULL
            AND replacement_low IS NULL
            AND replacement_close IS NULL
            AND replacement_volume IS NULL
            AND replacement_adj_close IS NULL
        )
    )
);

CREATE INDEX price_revisions_prior_identity_idx
    ON public.price_revisions (prior_symbol, prior_dt, revision_id DESC);
CREATE INDEX price_revisions_replacement_identity_idx
    ON public.price_revisions (replacement_symbol, replacement_dt, revision_id DESC)
    WHERE operation = 'update';

COMMENT ON TABLE public.price_revisions IS
    'Append-only price projection revision ledger. An AFTER UPDATE OR DELETE '
    'trigger on prices atomically records the prior row and its replacement '
    '(or a delete tombstone), sufficient to reconstruct what ASXOS served '
    'before each post-migration destructive change. No historical backfill and '
    'no provider raw payloads are included in migration 0043.';
COMMENT ON COLUMN public.price_revisions.revision_id IS
    'Monotonic database identity and deterministic tie-breaker for revisions.';
COMMENT ON COLUMN public.price_revisions.recorded_at IS
    'Wall-clock time when Postgres captured the destructive change; not vendor known_at.';
COMMENT ON COLUMN public.price_revisions.transaction_id IS
    'pg_current_xact_id() of the price mutation, proving same-transaction capture.';
COMMENT ON COLUMN public.price_revisions.recorded_application IS
    'Postgres application_name at capture time; diagnostic only, not trusted source provenance.';

CREATE OR REPLACE FUNCTION public._capture_price_revision() RETURNS TRIGGER AS $$
DECLARE
    v_recorded_at          TIMESTAMPTZ := clock_timestamp();
    v_transaction_id       BIGINT := pg_current_xact_id()::text::bigint;
    v_recorded_application TEXT := COALESCE(
        NULLIF(current_setting('application_name', TRUE), ''),
        'unspecified'
    );
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Keep reruns idempotent: ON CONFLICT DO UPDATE may present the exact
        -- row already stored. That is not a destructive change and gets no
        -- revision. to_jsonb compares every current prices column; if a future
        -- column changes without this ledger being extended, the payload-shape
        -- constraint fails closed instead of silently losing that field.
        IF to_jsonb(OLD) IS NOT DISTINCT FROM to_jsonb(NEW) THEN
            RETURN NEW;
        END IF;

        INSERT INTO public.price_revisions (
            operation,
            prior_symbol, prior_dt, prior_open, prior_high, prior_low,
            prior_close, prior_volume, prior_adj_close,
            replacement_symbol, replacement_dt, replacement_open,
            replacement_high, replacement_low, replacement_close,
            replacement_volume, replacement_adj_close,
            recorded_at, transaction_id, recorded_by, recorded_application
        ) VALUES (
            'update',
            OLD.symbol, OLD.dt, OLD.open, OLD.high, OLD.low,
            OLD.close, OLD.volume, OLD.adj_close,
            NEW.symbol, NEW.dt, NEW.open, NEW.high, NEW.low,
            NEW.close, NEW.volume, NEW.adj_close,
            v_recorded_at, v_transaction_id, session_user, v_recorded_application
        );

        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        INSERT INTO public.price_revisions (
            operation,
            prior_symbol, prior_dt, prior_open, prior_high, prior_low,
            prior_close, prior_volume, prior_adj_close,
            replacement_symbol, replacement_dt, replacement_open,
            replacement_high, replacement_low, replacement_close,
            replacement_volume, replacement_adj_close,
            recorded_at, transaction_id, recorded_by, recorded_application
        ) VALUES (
            'delete',
            OLD.symbol, OLD.dt, OLD.open, OLD.high, OLD.low,
            OLD.close, OLD.volume, OLD.adj_close,
            NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
            v_recorded_at, v_transaction_id, session_user, v_recorded_application
        );

        RETURN OLD;
    END IF;

    RAISE EXCEPTION 'unexpected operation % for _capture_price_revision', TG_OP;
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public;

COMMENT ON FUNCTION public._capture_price_revision() IS
    'DB-enforced Stage 1 containment: captures final OLD/NEW prices values in '
    'the same transaction as every changed UPDATE or DELETE. SECURITY DEFINER '
    'lets an authorised prices writer trigger the audit even without direct '
    'INSERT rights on price_revisions; the fixed search_path prevents object '
    'shadowing.';

CREATE TRIGGER prices_revision_capture
    AFTER UPDATE OR DELETE ON public.prices
    FOR EACH ROW EXECUTE FUNCTION public._capture_price_revision();

COMMENT ON TRIGGER prices_revision_capture ON public.prices IS
    'Atomic revision capture for every changed UPDATE and every DELETE; no-op '
    'updates return without a ledger row.';

CREATE OR REPLACE FUNCTION public._reject_price_history_loss() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '% on %.% is forbidden by append-only price-history containment',
        TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = '55000';
END;
$$ LANGUAGE plpgsql
SET search_path = pg_catalog, public;

CREATE TRIGGER price_revisions_append_only
    BEFORE UPDATE OR DELETE OR TRUNCATE ON public.price_revisions
    FOR EACH STATEMENT EXECUTE FUNCTION public._reject_price_history_loss();

CREATE TRIGGER prices_reject_untracked_truncate
    BEFORE TRUNCATE ON public.prices
    FOR EACH STATEMENT EXECUTE FUNCTION public._reject_price_history_loss();

COMMENT ON TRIGGER price_revisions_append_only ON public.price_revisions IS
    'Rejects UPDATE, DELETE, and TRUNCATE so captured history remains append-only.';
COMMENT ON TRIGGER prices_reject_untracked_truncate ON public.prices IS
    'Rejects TRUNCATE because row-level revision capture cannot observe truncated rows.';

COMMIT;
