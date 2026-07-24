# asxos — Session handoff — 2026-07-24

**Status:** current
**Read priority:** read first (newest handoff; supersedes `session-handoff-2026-07-21.md` on priority)
**Owner:** arbi (`/arbi-close`)
**Session:** 2026-07-24 — continuation of the 2026-07-22 wake ("wake up @arbi — then start
building the two approved workflow proposals") → build + merge #67 → dev-loop → PR #64 triage →
clean-extract → #68 merged, #64 closed → close

---

## STOP — read first (live P0)

**Rule #11 — Model A quarantine STANDS.** Do not use Model A output (signals, candidate scans,
allocator runs, new thesis proposals) as a basis for real-capital decisions. Resolved against
Model A 2026-07-11 (`docs/model-a-decay-analysis-2026-07-11.md`: no usable edge on 19,032
matured signals; conviction inverted at the top). Standing policy for v1_5 — stays in this block
and in `CLAUDE.md` #11 until a *new* model version passes a pre-registered decay bar AND earns
`approved_for_allocation`. The `model_shelved` brief state shipped in #68 (Mission 1) is the
*display* consequence of this rule — a calm "Model A shelved" line replacing red "regime
unavailable" noise; it does not change the quarantine.

The product remains the **model-independent moat** (discipline, tax, themes, ETFs, governance).

---

## What happened this session

`main` moved `9dd5443` → **`e596748`** across three merges (#65 landed at the start of the
window; #67 and #68 this session). **Zero open PRs** at close. No arbi DB writes, no migrations
applied, no capital actions. Merges were James-authorized per-action ("if green, merge these
PR's"). One ops fix (Render env) was James-authorized.

1. **PR #67 merged (`a1d30f5`) — both 2026-07-21 proposals built.**
   - *Proposal A (workflow automation) Steps 1-2:* the theme governance write path was
     live-fire-verified; `sector-screener` and `theme-researcher` discovery agents materialized
     into `.claude/` (via the sanctioned GitHub-API draft route); `_KNOWN_AGENTS` extended to
     `{macro-economist, sector-screener, theme-researcher}`.
   - *Proposal B (macro-thesis learning loop) Layer A:* `machine_conditions` schema
     (backend-architect-designed) on `MacroThesisProposal`; **DRAFT** migration
     `0041_macro_thesis_learning_loop.sql` (machine_conditions JSONB + `macro_thesis_outcomes`
     ledger + #6/#7 falsifier backfill); `jobs/score_macro_theses.py` daily evaluator. Catalysts
     and #11's crosses_* stay prose-only (nested `A AND (B OR C)` + `crosses_*` grammar deferred).

2. **agent_runs #6/#7 dispositioned** per James's ruling from the prior wake: **run 6 rejected**
   (duplicative of the already-approved macro thesis #6, same evidence base); **run 7 approved**
   (the growth-leg bracket), with its manual-authorship provenance noted. No new hand-logged
   `agent_runs` rows — the agents now work through the repointed pipeline.

3. **Render drift fixed (James-authorized ops).** Live `asxos-compute-opportunity-cost` was
   missing `ASXOS_PERSONAL_USE=1` (which `render.yaml:578` declares) — the Saturday gated run
   would have hard-failed. Set via the Render REST API.

4. **PR #64 triaged, then clean-extracted → PR #68 (`e596748`).** #64 (27 commits, base
   `9dd5443`) was assessed for merge and found **~85% superseded by the already-merged #65**: its
   entire Waves 1-5 hygiene sprint duplicates #65's 2026-07-18 audit work
   (`compute_opportunity_cost` gate, `/health` CWE-209, `security_master` batching,
   `check_cron_health`, `derive_fundamentals_pit`, CBA discipline, brief personal-data gate), and
   in `regulatory.py` #64 holds the **opposite** decision from what #65 shipped (it argues against
   `defusedxml`; main shipped it). A full merge meant 10 conflicts + dragging contradictory history
   through main for two clean units. Per James's call (AskUserQuestion → "clean extract"), only the
   two genuinely net-new units were cherry-picked onto current main:
   - **Mission 1** — `fix(brief)`: deleted the false `_since_inception_returns` (which differenced
     a flow-affected `capital_aud` balance and reported a **false −75.7% loss** while the one
     holding, HUBS, is ≈ +19.6%) and added `discipline.unrealised_return()` — a native-currency
     `(current − entry)/entry` figure that reconciles with the brokerage statement (R10-safe: both
     legs native, no FX step). Plus the calm `model_shelved` brief state.
   - **Mission 2** — `feat(theses)`: Phase C broker-report thesis sections
     (`asx thesis add-section` / `asx thesis show --full-report`), backed by
     `theses.report_sections` (JSONB, migration 0040 — already applied to prod 2026-07-19). User
     text rendered with `markup=False` + `rich.markup.escape()`.

   The only non-trivial 3-way merge was `asxos/brief/compose.py` — verified gate-by-gate that all
   of #65's controls (personal-use gate, governance-status gate, single-pass trade-rows refactor)
   survived. **security-engineer PASS** and **portfolio-invariant-guard PASS** on the merged diff;
   ruff clean; 152 affected-file tests pass; CI (`full-check` + `targeted-ml-tests`) green
   first-shot. **PR #64 closed as superseded** with an explanatory comment.

---

## Pending, requiring James

1. **Apply DRAFT migration `0041_macro_thesis_learning_loop.sql`** to project `gxjqezqndltaelmyctnl`
   (via `mcp__supabase__apply_migration`), then **bump `REQUIRED_MIGRATIONS`** in
   `asxos/api/main.py` to the observed `SELECT count(*) FROM supabase_migrations.schema_migrations`
   (the observed count, not a guessed +1). **Then** wire the `asxos-score-macro-theses` Render
   cron. Sequence matters — a cron that runs before the column/table exist would hard-fail
   (CLAUDE.md #1). **Layer A is inert until this is done.** (arbi does not apply migrations.)
2. **CBA discipline auto-flag** — the one-word confirm on the 2026-07-16 ruling (widen thesis
   discipline to `watching`, `watching_stale` check) still open. (Note: #64's version of this was
   dropped as superseded; if wanted, it rides the discovery lane, not a #64 re-merge.)
3. **RLS / agent-DB-role posture** — `m14_candidate_agent_db_role_scoping` (autonomy precondition
   2) still open; prompt-level SELECT-only enforcement remains the only backstop on the agent MCP
   grant.

---

## Files to commit to `main` (this close's artifacts — reminder, not a push)

Per `docs/README.md` ("a handoff that lives only on a feature branch is a process defect"), these
must reach `main` to be seen next session. `/arbi-close` does not push/merge — land them via
`/ship` or a docs commit:

- `docs/session-handoff-2026-07-24.md` (this file)
- `docs/product/roadmap-state.md` (In-flight + ranked-queue + close addendum)
- `docs/product/decision-log.md` (the `close-2026-07-24` row)
- `docs/product/arbi-run-ledger.md` (the `close-2026-07-24` scored row, episode 4.6 — provisional)

---

## Next wake's ONE THING

**The macro-brief render layer (dev-loop #9)** — the Morningstar-style output James asked about.
The discovery pipeline now has governed macro theses (#6/#7), the macro→theme→sector→instrument
agents wired read-only, and the Layer A falsifier-scoring evaluator — but nothing renders it for
James to read. Build the brief section that surfaces the governed macro read + theme/thesis
discipline + Layer A outcomes. Then dev-loop #10 (`instrument-selector` + wire
`create_thesis_from_agent_run`, Phase E) closes the discovery chain.
