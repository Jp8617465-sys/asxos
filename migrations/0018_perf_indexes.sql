-- 0018_perf_indexes.sql
--
-- RECONSTRUCTED 2026-08-23 from live `pg_get_indexdef()`. This file did not
-- exist until now: the ledger row `20260602102212 / 0018_perf_indexes` has been
-- applied in production since 2026-06-02 with no corresponding file in this
-- repo, which is why a name-based drift check flagged it.
--
-- WHY IT MATTERS EVEN THOUGH PRODUCTION ALREADY HAS THESE: the restore drill in
-- .github/workflows/backup.yml rebuilds a recovery database by replaying
-- migrations/*.sql. Anything not declared here is absent from that rebuild, and
-- nothing detects it — the drill's assertions are row counts, which pass
-- regardless of indexes. A fresh dev database has the same gap. Applying this to
-- production is a no-op by construction.
--
-- HOW THE UNDECLARED SET WAS ESTABLISHED, and the trap in establishing it:
-- all 59 non-constraint production indexes were diffed against migrations/.
-- A first pass extracted `CREATE INDEX <name>` and reported ten undeclared.
-- SEVEN OF THOSE TEN WERE FALSE. This repo writes many indexes UNNAMED
-- (`CREATE INDEX ON brief_runs (as_of, composed_at DESC)` in 0015, and six more
-- in 0013/0014/0016/0019), and Postgres auto-names those `<table>_<cols>_idx` —
-- which is precisely the name the first pass then reported as missing. All seven
-- matched their auto-name exactly. If you re-run this analysis, match unnamed
-- statements too, or you will "rediscover" seven indexes that are already here.
--
-- Three survived. All three carry an explicit `idx_` prefix rather than
-- Postgres's auto-name, which is itself the evidence that they were written by
-- hand outside a migration. Only two are in this file:
--   * idx_signal_outcomes_model_date -> 0025, because files replay in filename
--     order and its table (signal_outcomes) is not created until 0025. It is
--     also the weakest attribution of the three: signal_outcomes was created
--     ad-hoc by the since-deleted jobs/track_signal_outcomes.py, and its sibling
--     idx_signal_outcomes_date is KNOWN to have been created the same way.
--
-- ATTRIBUTION IS INFERRED, NOT PROVEN. These two are grouped under 0018 because
-- 0018 is the only ledger row without a file that could plausibly have created
-- them. Cite this as "the set nothing declared", never as 0018's contents.
--
-- DDL is verbatim from pg_get_indexdef() with IF NOT EXISTS added. Column order
-- and the DESC marker are production's — do not "tidy" them; an index with
-- reordered columns is a different index.

BEGIN;

-- underlying_prices is created in 0014; safe to index here.
CREATE INDEX IF NOT EXISTS idx_underlying_prices_underlying_id_as_of
    ON public.underlying_prices USING btree (underlying_id, as_of DESC);

-- theme_holdings is created in 0012; safe to index here.
CREATE INDEX IF NOT EXISTS idx_theme_holdings_theme_id
    ON public.theme_holdings USING btree (theme_id);

COMMIT;
