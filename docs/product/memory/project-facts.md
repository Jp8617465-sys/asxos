# arbi project-facts memory

**Status:** current
**Scope:** durable facts arbi should know that outlive a session (`AGENTS.md` §10)

Two kinds of entry live here. The first is a **pointer index** — the fact already has an
authoritative home, and duplicating it would create a second editable copy. The real files
win over the pointer. The second is a **standing fact** that has no other home, usually
because the mechanism that used to encode it was retired.

## Durable repo facts (follow these)

- **The docs source-of-truth map:** `../../README.md`
- **Agent authority and operating contract:** `../../../AGENTS.md`
- **Agent guide + stack + schema overview + delegation policy:** `../../../CLAUDE.md`
- **Auto-attaching conventions:** `../../../.claude/rules/` (`api-`, `ml-`, `job-`, `portfolio-conventions.md`)
- **Specialist roster + the canonical owner→agent table:** `../../../.claude/agents/README.md`
- **Current program state (reconciled):** `../roadmap-state.md`
- **Live-state probes:** `/sprint-state` + `/catchup` (git/PR/CI · Supabase-ro · GitHub Actions)
- **Schema is the migrations:** `../../../migrations/` (canonical; check
  `supabase_migrations.schema_migrations` for what is live, never the directory listing)
- **Tax spec source of truth:** `../../foundation/spec/tax-alpha.md`
- **Known sandbox test gaps (do not chase):** `../../../CLAUDE.md` (## Known test environment gaps)
- **CI: `full-check` (ruff 0.7.0 + mypy + pytest) + `targeted-ml-tests`.** Pin dev ruff to
  **0.7.0** to match CI (`lessons.md` L3).

## Standing facts about the tooling

Both were found by the `security-engineer` review on 2026-08-12 (findings H1 and H2) and
verified live against the hook that then enforced them. That hook was retired on 2026-09-10
with the rest of the guard set, so these are now facts arbi carries rather than rules
anything blocks. They are the reason two convenient-looking commands are the wrong reach.

- **`gh run rerun` re-injects a prior run's secrets.** It re-executes a previous run with all
  of its secrets available again, for up to 30 days, on **any** workflow — a strictly wider
  reach than dispatching a named lane, and not "read-only" in any sense. Re-dispatch the lane
  explicitly instead: `gh workflow run <lane>.yml --ref <branch>`.
- **`gh workflow run` plus command substitution smuggles an inner dispatch.** Command
  substitution is not a segment separator, so
  `gh workflow run backup.yml $(gh workflow run daily-brief.yml)` fires the *inner* workflow
  first, and a prefix-matching allow rule only ever sees the outer string. Never build a
  dispatch command out of substituted output; name the workflow literally.

## Standing facts about the infrastructure (verified 2026-09-14)

Each line names the probe that produced it. Re-probe before trusting a date-stamped fact.

- **Supabase plan is `pro`** — `mcp__Supabase__get_organization` on org `dukwxpqbrpjctjyugcek`
  returned `"plan": "pro"` on 2026-09-14 (James upgraded that day). `CLAUDE.md:38` still says
  "free tier" — stale, in the residue sweep. `BUILD_GUIDE.md`'s "downgrade Pro → free at M1"
  lines are dated history and stay as written. Pro includes scheduled daily backups; **PITR
  is a separately-priced add-on, not included** — do not write "7-day PITR" into any runbook
  without confirming it in the dashboard, which arbi cannot read.
- **Postgres engine is 17** (`17.6.1.063`, release channel `ga`) — `mcp__Supabase__get_project`
  on `gxjqezqndltaelmyctnl`, 2026-09-14. `backup.yml:6` already says 17 (verified 08-10);
  `CLAUDE.md:38` says 16 — stale, same sweep.
- **Both Actions secrets now exist**, created by James on 2026-09-14: `ARBI_GITHUB_TOKEN`
  (fine-grained PAT, `asxos` only, Actions / Contents / Issues / Pull requests / Workflows
  read-write, 90-day expiry — **it expires silently; every lane fails at checkout with no
  other symptom**) and `SUPABASE_ACCESS_TOKEN` (scoped token, one project: Migrations RW,
  Database / Logs / Advisors / Project Settings R). No `schedule:` is armed yet (A-22).
- **Supabase personal access tokens are now scoped** (public alpha, on James's account) —
  the rollout's "all-or-nothing" framing is out of date. Permission→tool table:
  `https://supabase.com/docs/guides/platform/personal-access-tokens` (`apply_migration` =
  Migrations RW; `execute_sql` = Database R).
- **James's laptop has the writable Supabase MCP** via the hosted server
  (`https://mcp.supabase.com/mcp?project_ref=gxjqezqndltaelmyctnl`, OAuth, `--scope user`),
  alongside `supabase-ro`. Convention: reads through `supabase-ro`; the writable server only
  when the task needs a write. Verified against head `20260903025557` on 2026-09-14.
- **The headless lanes may edit `.github/workflows/`, never `.claude/`.**
  `.github/runner/claude-user-settings.json` is the user-level settings file every lane copies
  to `~/.claude/settings.json`, so its `autoMode.allow` list is the lanes' real permission
  surface. It granted both paths — written in #254, missed by #256's `.claude/**` reservation —
  and was corrected on 2026-09-14 to name `.github/workflows/` alone. Pinned by
  `tests/test_claude_execute_harness.py::test_runner_settings_do_not_pre_approve_claude_dir_edits`,
  which fails against the pre-fix file. A grant here is self-modification with no human in the
  loop, which is the one thing `AGENTS.md` §8 reserves.

- **The RI valuation sweep sees 88.9% of ASX market cap, and only tangible-book businesses**
  — 2026-09-16 sweep, probed 2026-09-17. 1,879 active `au_equity`; 537 pass liquidity; 332
  valued ($3,363bn of $3,784bn); 16 clear all four gates, of which 8 are operating companies
  and 8 are LIC / A-REIT / one-off artefacts. 1,082 of 1,879 blocked `roe_non_positive` — CSL
  among them, correctly (TTM net income −US$2.64bn). Valued-by-count per sector: Real Estate
  78%, Financials 71%, Industrials 56%, Tech 26%, Energy 20%, Healthcare 17%, Materials 13%.
  The model values BHP at $23.87 vs $59.25 and CBA at $67.15 vs $152.50: the `zero_excess`
  terminal convention assigns nothing to franchise beyond the 10-year fade, so every one of
  the 8 surviving operating companies is a tangible-book business. That is the lens, not the
  market.
- **41% of the liquid universe is valued on accounts at least nine months old** — of the 537
  liquid names, latest `rs_fundamentals_pit.as_of` is 2026-06-30 for 317, 2025-12-31 for 92,
  2025-06-30 for 65, older for 18 (probed 2026-09-17). `HLI.AU` sits in the Dec-2025 bucket:
  the screen surfaced it knowing nothing of its H1-2026 result, special dividend, buyback or
  ING renewal. A name the screen finds is not a case the screen has made.
- **A second valuation method needs a migration** — `valuation_runs_method_check` is
  `CHECK (method = 'residual_income')` and `valuation_runs_terminal_convention_check` is
  `CHECK (terminal_convention = 'zero_excess')` (`pg_constraint`, 2026-09-17). Widening either
  is one expand-only ALTER, the 0057/0060 pattern; every existing row satisfies the wider
  constraint.
- **Relative-multiples coverage on the same 537 liquid names** (2026-09-17): P/E computable for
  354 (`eps_ttm > 0`), EV/EBITDA for 365 (`rs_financial_statements.line_items.ebitda > 0` on
  the latest yearly income row — the key is present on all 54,107 yearly income rows, non-null
  for 513 of the 537, positive for 365), EV/Sales for 464, P/B for 522.
  `rs_security_master.gics_sector` covers 537/537 in 16 groups where `universe.sector` covers
  535; `factor_scores.py` already reads the former. 518/537 carry ≥5 years of PIT history.
  Utilities has 6 liquid names — below any sensible peer-group floor.
- **`factor_scores.py` already computes a sector-neutral value z-score** (`earnings_yield`,
  `book_yield`) into `rs_factor_scores` (71,759 rows). The value×quality composite it feeds
  measured no detectable edge — best effective t 0.75 at 21d (selection probe, 2026-09-17).
  It is a *ranker* in the research store, retired from `weekly-research`, not a gate and not a
  valuation. Anything proposed as a "relative valuation lens" must state how it differs from
  this, or it is a duplicate.

Update this file when a durable convention is added or moved, or when a fact like the two
above would otherwise be lost with the mechanism that encoded it.
