**Status:** stale
**Scope:** old session prompt
**Last verified:** 2026-07-04
**Read priority:** archive — do not use as a session entry point
**Superseded by:** `CLAUDE.md` + `docs/session-handoff-2026-07-04.md` + `docs/README.md`

> **⚠️ STALE — do not paste into a new Claude session (banner added 2026-07-04).**
> This kickoff reflects 2026-06-28 state: an old branch, migrations 0029/0030, and
> `REQUIRED_MIGRATIONS = 84`. Current: migrations through 0036, `REQUIRED_MIGRATIONS = 90`
> (`asxos/api/main.py:15`). Session entry is now `CLAUDE.md` → `docs/session-handoff-2026-07-04.md`
> → `docs/README.md`. The "Conventions to honor" section below is still broadly correct;
> everything under "Branch / PR state" and "Already-applied DB state" is superseded.
>
> **⚠️ The banner itself has since gone stale — correction 2026-08-22.** Its "Current:"
> figures (`through 0036`, `REQUIRED_MIGRATIONS = 90`) are a 2026-07-04 observation, not
> today's state, and re-anchor a session four migration-epochs back exactly as the `84`
> below did. As of 2026-08-22: migration files run **through `0045`** on disk;
> `supabase_migrations.schema_migrations` = **97** (latest version `20260821080458`,
> `0044` applied 2026-08-21); `REQUIRED_MIGRATIONS = 97` in `asxos/api/main.py`. `0042`
> is **RESERVED** and must never be applied, and `0045` is drafted but **not** applied —
> so the on-disk file count, the ledger count and the constant are three different
> numbers by design. Session entry is now `CLAUDE.md` → the newest
> `docs/session-handoff-*.md` → `docs/README.md`. **Never read a migration count out of
> this file** — read `asxos/api/main.py` and the live ledger.
>
> **⚠️ The correction has itself gone stale, and the mechanism it names is gone —
> 2026-09-02.** `REQUIRED_MIGRATIONS` **no longer exists**: it was deleted on 2026-08-23 and
> replaced by a migration-name set difference (`asxos/schema_drift.py`, imported by
> `asxos/api/main.py`), so there is no count to read, bump, or compare, and every
> instruction above that says otherwise is describing a deleted constant. Live figures at
> this date: 47 migration files on disk (through `0048`); latest applied ledger version
> `20260901062502` (`0048_decision_packets`, applied 2026-09-01). `0042` remains RESERVED
> and `0045` remains drafted-not-applied. **This is the third recorded staleness of this
> same banner** (2026-07-04 → 2026-08-22 → now), which is the actual lesson: a doc that
> re-states a live number goes stale by construction. No further "Current:" figure will be
> written here. Read `supabase_migrations.schema_migrations`, never this file.

# asxos — next-session kickoff prompt

Paste the block below verbatim into a new Claude Code session to continue this work.

---

You are resuming asxos work. Read CLAUDE.md and the relevant `.claude/rules/` first.

**Branch / PR state**
- Active branch: `claude/edmund-yong-subagent-wecr3g` (was 52 commits ahead of main,
  full-check CI green on e040c29). There is an **open PR** for it — it may be merged
  or still iterating. Check the PR state before assuming it landed; do not re-open or
  duplicate it.
- If the PR has merged to main, branch off main for new work. If not, continue on the
  existing branch or a child branch as appropriate.

**Already-applied DB state — DO NOT re-apply**
- Migrations **0029** (widen `fundamentals.market_cap` + `universe.market_cap` to
  NUMERIC(24,6), with the `stock_universe` view drop/recreate/regrant) and **0030**
  (single-tenant wipe: 122 non-asxos tables dropped, archived in schema
  `archive_dropped_20260628`) are **ALREADY APPLIED to production**
  (project `gxjqezqndltaelmyctnl`). Do not re-run them. _(The `REQUIRED_MIGRATIONS = 84`
  figure that stood here is deleted, not corrected — the constant no longer exists; see the
  2026-09-02 note in the banner above.)_
- Verify live state via `mcp__supabase__*` (read-only) before any new migration. Drift is
  detected by the migration-name set difference in `asxos/schema_drift.py`; there is no
  count to guess or bump.

**Conventions to honor**
- Route work through the agent team per CLAUDE.md's delegation table (e.g.
  `backend-architect` for schema/route/job changes, `tax-spec-conformance` for
  `asxos/domain/tax/*`, `portfolio-invariant-guard` for `asxos/domain/portfolio/*`).
- The **review-gate** hook blocks `git commit` when `*.py` is staged until the review
  loop (`security-engineer` / `refactoring-expert` / `technical-writer`) has run for
  that exact staged diff and the keyed marker is written. Do not bypass.
- **Pre-apply dependent-object check** is mandatory before any `ALTER`/`DROP COLUMN`:
  run the `pg_depend` catalog query for views/rules/constraints/indexes on the target
  column (this caught `stock_universe` on 0029). See
  `docs/db-shared-project-audit-2026-06-28.md` §2.
- Spec-governed tax changes require a spec amendment in
  `docs/foundation/spec/tax-alpha.md` first (CLAUDE.md non-negotiable #8).
- **full-check must stay green.** Mind the documented sandbox test gaps (CLAUDE.md
  "Known test environment gaps") — do not add skip markers or workarounds for those.

**Where to start**
- The prioritized open backlog is in **`docs/next-session-backlog.md`** (P1/P2/P3).
  Pick from there; confirm priorities with me before starting a P1/P2 item.

Acknowledge the branch/PR and already-applied-migrations state, then propose which
backlog item to tackle first.
