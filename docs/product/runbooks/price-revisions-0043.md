# Migration 0043 — production apply and verification

**Status:** production-ready procedure; migration not yet applied
**Target:** Supabase project `gxjqezqndltaelmyctnl`
**Owner:** James authorises; an attended operator executes and records evidence

## Purpose

Apply prospective price-history containment without pretending to recover revisions
already lost. Migration `0043_price_revisions.sql` adds an append-only ledger and atomic
triggers around destructive `prices` updates and deletes. It does not backfill history,
archive provider payloads, or complete Stage 1.

## Preconditions

Stop if any item is not true:

1. The production-readiness PR is merged and `migration-integration`, `full-check`, and
   `targeted-ml-tests` are green on `main`.
2. A manual `backup.yml` run with `restore_drill=true` is green on that exact `main` SHA.
3. The database identity resolves to project `gxjqezqndltaelmyctnl`.
4. No price-ingestion job is running and no long-lived transaction is writing `prices`.
5. Live migration history still ends before 0043, and `price_revisions`,
   `prices_revision_capture`, and `prices_reject_untracked_truncate` do not already exist.
6. The operator has explicit authority to perform an I5 production migration.

Read-only preflight:

```sql
SELECT current_database(), current_user, version();
SELECT count(*) AS applied_migrations
FROM supabase_migrations.schema_migrations;

SELECT to_regclass('public.price_revisions') AS existing_ledger;
SELECT tgname, tgenabled
FROM pg_trigger
WHERE tgrelid = 'public.prices'::regclass
  AND NOT tgisinternal
ORDER BY tgname;

SELECT pid, application_name, state, xact_start, query_start
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
  AND xact_start IS NOT NULL
ORDER BY xact_start;
```

The migration performs its own exact `prices` column/primary-key assertion and uses a
five-second lock timeout. A schema mismatch or busy writer must fail the whole transaction;
do not weaken those checks to make the apply pass.

## Apply

Apply the exact repository file through the governed Supabase migration mechanism. Do not
paste a modified copy and do not apply migration 0042 as part of this operation.

```text
migrations/0043_price_revisions.sql
```

Record the Supabase migration result, resulting migration-history count, actor, timestamp,
and exact git SHA. The expected count is likely 96, but the observed live value is the only
authority.

## Verify without leaving a production mutation

First verify the objects:

```sql
SELECT to_regclass('public.price_revisions') AS ledger;
SELECT tgname, tgenabled
FROM pg_trigger
WHERE tgrelid IN (
    'public.prices'::regclass,
    'public.price_revisions'::regclass
)
  AND NOT tgisinternal
ORDER BY tgrelid::regclass::text, tgname;
```

Then run one material-update probe inside a transaction and roll it back. The query must
return exactly one update revision with the same transaction ID before `ROLLBACK`:

```sql
BEGIN;
SET LOCAL application_name = 'asxos-0043-production-probe';
SET LOCAL lock_timeout = '5s';

WITH target AS (
    SELECT symbol, dt
    FROM public.prices
    ORDER BY dt DESC, symbol
    LIMIT 1
)
UPDATE public.prices AS price
SET adj_close = COALESCE(price.adj_close, price.close) + 0.000001
FROM target
WHERE price.symbol = target.symbol
  AND price.dt = target.dt;

SELECT operation, prior_symbol, prior_dt,
       prior_adj_close, replacement_adj_close,
       transaction_id = pg_current_xact_id()::text::bigint AS same_transaction,
       recorded_application
FROM public.price_revisions
WHERE transaction_id = pg_current_xact_id()::text::bigint;

ROLLBACK;
```

Confirm the probe left nothing behind:

```sql
SELECT count(*)
FROM public.price_revisions
WHERE recorded_application = 'asxos-0043-production-probe';
```

Expected: `0`.

## Close the deployment

1. Run `backup.yml` again with `restore_drill=true`. Its logs must say that
   `price_revisions` was included, all 14 table counts matched, and its sequence was reset.
2. Create the small post-apply PR that changes `REQUIRED_MIGRATIONS` in
   `asxos/api/main.py` from 95 to the observed live count and records the applied migration.
   Do not merge that bump before the database apply: the API is designed to fail startup
   when its required count is ahead of production.
3. Observe the next normal price-ingestion run. It must succeed; revision growth may be zero
   when the provider returns byte-equivalent rows.
4. Record links to the migration result, transactional probe, backup/restore run, and price
   ingestion run in the programme handoff.

## Emergency response

The migration is transactional: any apply-time error rolls back all objects. After a
successful apply, if the capture trigger causes a confirmed price-ingestion outage:

1. stop the price writer;
2. preserve `price_revisions` and its append-only trigger;
3. with James's explicit approval, apply a new emergency migration that drops only
   `prices_revision_capture` from `public.prices`;
4. restore ingestion, diagnose, and reinstate capture through another reviewed migration.

Disabling capture reopens the evidence-loss window. Never drop or truncate the ledger as a
rollback technique.
