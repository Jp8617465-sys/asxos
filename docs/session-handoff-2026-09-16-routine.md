# Session handoff — 2026-09-16, `daily-product` routine (first scheduled fire)

**Status:** current
**Read priority:** read after `docs/session-handoff-2026-09-14-4.md` (the Routines build) for
anything about how the overnight product fire behaves in practice; this file is the record of
the first one. Interactive-session handoffs keep the bare date; routine handoffs carry
`-routine`.

**STOP — read first.** Rule #11 stands: no Model A output as a basis for anything. Nothing in
this fire read `signals`.

## What fired

`trig_01TLku22ZdzveWG7iQ1ybXFE` → bound session `session_016GusBoDGMihXbXHbiMTpK1`, fire
2026-09-15T17:36:12Z (03:36 AEST 09-16), `doc_sha=50aff99`, START/END on #270. Budget 120 min.

**Gate (§1), all four held:** (a) `nightly-check` 34889454574 on `main` `success`; (b) no open
`incident` issue; (c) ledger #270 has no dangling START; (d) 0 open PRs, so the picker ran —
`scripts/backlog_next.py` exit 0, eligible 1, pick **E-11**, 42-row click list.

## The one thing — E-11, and what verifying it found

| Claim in the row / roadmap | Checked against | Result |
|---|---|---|
| "false pip-cache comment … inside merged #168 (`full-check.yml`)" | file at #168's head `e13b3f0`, blob `843350a` (GitHub API) | byte-identical to `main`; the comment carries only the residue "worth a step here at all" |
| the false sentence itself | commit `c35d435` message + PR #168 body | "there is no `cache:` key anywhere … This is the first one" — **immutable** |
| `roadmap-state.md:1210` "#184 fixed the false pip-cache comment" | PR #184 files | its `full-check.yml` patch is `cache: 'pip'` → `cache: pip`; comment untouched — **wrong** |
| how many workflows cache pip today | `grep "cache: pip" .github/workflows/*.yml` | nine |

Built: the four comment lines now state the true fact (same key the scheduled workflows use,
not a first). E-11 closed `done` with that note in `backlog.yaml`. Amendment E field:
**`defect:` commit `c35d435` (#168)**. Class **Amber** by shape (`.github/workflows/`);
exposes nothing — comment-only, no secret, trigger or branch change; reversal one revert.

## Also done this fire

- **Roadmap live block re-ranked.** The 09-14 block still ranked #1/#2/#3/#5 that the 09-14
  third session had discharged (#261, #230, #262, the wake). New block: DELETE verdict #1
  (portfolio brief) → DELETE verdict #3 (V2 dark path) → #228 PR 2 (migration, carried) →
  E-20 → carried items. The two DELETE verdicts were not `backlog.yaml` rows, so the picker
  would have chosen E-20 while the roadmap ranked the verdicts first — Amendment K says the
  roadmap wins and the file is wrong. Filed them as **A-34** and **A-35** (phase A ranks
  ahead of E; they overlap on `compose.py`, one per fire). `backlog_next.py` on the branch:
  eligible 3, picked A-34 then E-20 (the lane's max is 3), A-35 skipped for overlap with A-34.
- **A-34 / A-35 / E-20 filed.** The verdict rows are described above. E-20: `ingest_regulatory` reports `rows_written=1` every night while
  `regulatory_events` has 7 rows and none since 2026-09-03 (`max(ingested_at)`
  2026-09-03 22:44 UTC; `job_runs` ids 1155–1238 all `success`, `rows_written=1`).
  `upsert_events` returns `len(rows)` after `ON CONFLICT DO UPDATE`, so the figure is an
  upsert-touched count. Whether the RBA feed really carries one item is the open question.
- **`tests/test_backlog_next.py::TestSeed::test_seed_after_the_denied_set_trim_has_a_pick`**
  re-pinned to `picked == ["A-34", "E-20"]`, `skipped == ["A-35"]` (it pinned E-11).
- **L52** in `memory/lessons.md`: verify a "X is false" row against the artifact at the cited
  commit before building; the defect may be in an immutable message.

## Findings about the routine itself (for `docs/ops/routines/` — draft-only from here)

1. **The sandbox has no venv.** `python scripts/backlog_next.py` fails with
   `ModuleNotFoundError: No module named 'asxos'` until `uv venv .venv --python 3.12` +
   `pip install -e ".[dev]"` (one proxy timeout on the first attempt; the retry succeeded).
   System Python is 3.11; the project pins 3.12. The doc's gate (d).2 should say so, or exit 1
   will be misread as "schema error → that is the item".
2. **`HC_ROUTINE_PRODUCT_URL` is unset** in the bound session → `deadman=unset` in END.
3. **The bound session carries the write-capable `Supabase` connector as well as
   `supabase-ro`** (`ListConnectors`: both `connected`, both `enabledInChat`). The preamble's
   "no Supabase write tools" is prompt-level here, as `README.md` already says of UI-attached
   sessions. Not used this fire. A James-side fix is to detach `Supabase` from this session's
   environment; recorded, not escalated.
4. **`supabase-ro` tool names are UUID-prefixed** (`mcp__9d7520d7-…__execute_sql`), not
   `mcp__supabase-ro__*` as the tool map writes them. `ListConnectors` resolves the mapping.
5. **The clone is shallow** (52 commits, root `5632a97`): `git blame`/`git log -S` cannot
   see before 2026-09-05. Use the GitHub API for history questions.

## Verification

- `make check` on unmodified `main` (`50aff99`) in the routine sandbox: **4329 passed, 1 skipped**,
  ruff clean, mypy clean on 218 files. On the branch before push: **4329 passed, 1 skipped**, ruff
  and mypy clean (one test re-pinned, see above).
- Migrations unchanged: ledger head `20260914123930` (0054); 0045 unapplied; 0042 reserved.
- No migration, no capital action, no Model A output, no Supabase write.

## Yours

Nothing under `AGENTS.md` §2. Two things only James can do, neither blocking: set
`HC_ROUTINE_PRODUCT_URL` (Healthchecks) for the bound session; detach the write-capable
`Supabase` connector from the routine sessions' environment (finding 3).

## Next fire

(d).1 none → (d).2 exit 0, pick **A-34 — DELETE verdict #1 (portfolio brief)**, scope in
`dark-launch-exit-plan.md` §1. Amber by shape; `tests/test_brief_portfolio_section.py` and
`tests/test_brief_outcome.py` reference the gate and carry the test delta. Then A-35, then E-20.
