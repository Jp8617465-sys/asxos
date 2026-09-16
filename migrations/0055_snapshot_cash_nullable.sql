-- 0055_snapshot_cash_nullable.sql
-- #228 PR 2 (F-E2E r2 M1): "capital with an implied zero cash" becomes unrepresentable.
--
-- portfolio_daily_snapshots.cash_aud has never been a measurement. The snapshot
-- job writes profile.cash_floor_pct * profile.capital_aud — a risk-policy
-- constant times a configured baseline — and capital_aud = holdings_mv_aud +
-- that number. PR #266 (2026-09-14) stopped the decision engine READING the
-- placeholder as a balance (PortfolioState.cash_pct is None until an
-- authoritative source exists); this migration lets the WRITER stop inventing
-- one, by making the honest row representable: cash unknown => capital unknown.
--
-- Expand-only. Nothing is rewritten and nothing changes behaviour on apply:
-- the 74 existing rows (before-image 2026-09-16: 74 rows, 26 with non-zero
-- cash_aud, max 25000.000000, 0 NULLs, 2026-05-27 -> 2026-09-15) keep their
-- values, and the writer keeps writing numbers until it is re-pointed at
-- cash_balance_assertions (0056) in its own PR — the 23 readers of capital_aud
-- (brief wealth line, benchmark returns, discipline, monitors) must learn to
-- treat NULL as "not measured" first, and that is reader work, not schema work.
--
-- The paired CHECK is the invariant: a row may carry both figures or neither.
-- A NULL cash with a numeric capital would be exactly the "implied zero cash"
-- this migration exists to forbid; a numeric cash with a NULL capital is a
-- writer bug. Deliberately NOT a balance CHECK (capital = holdings + cash): the
-- writer quantises the sum and the parts separately, and a 1e-6 rounding
-- difference would fail the daily snapshot — step 3 of 12 in daily-brief.yml —
-- and cost the brief. That invariant belongs to the writer's tests.
--
-- Pre-apply dependent-object check (api-conventions.md), run 2026-09-16 through
-- supabase-ro: no view depends on portfolio_daily_snapshots.
--
-- Rollback: a forward migration (AGENTS.md §3). SET NOT NULL is only possible
-- while no NULL row exists, so re-contracting after the writer switches is a
-- backfill decision, never a revert.

ALTER TABLE portfolio_daily_snapshots
    ALTER COLUMN cash_aud DROP NOT NULL,
    ALTER COLUMN capital_aud DROP NOT NULL,
    ADD CONSTRAINT portfolio_daily_snapshots_cash_capital_paired
        CHECK ((cash_aud IS NULL) = (capital_aud IS NULL));

COMMENT ON COLUMN portfolio_daily_snapshots.cash_aud IS
    'AUD cash balance as at as_of. NULL = not measured (no cash_balance_assertions '
    'row at or before as_of). Until the writer is re-pointed (backlog C-27) the '
    'stored figure is profile.cash_floor_pct * profile.capital_aud, a policy '
    'placeholder, and decision_engine/portfolio_state.py deliberately does not '
    'read it (#228, #266).';
COMMENT ON COLUMN portfolio_daily_snapshots.capital_aud IS
    'holdings_mv_aud + cash_aud. NULL exactly when cash_aud is NULL (paired '
    'CHECK, migration 0055): capital cannot be stated while cash is unmeasured.';
