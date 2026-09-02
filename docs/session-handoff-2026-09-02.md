# Session handoff — 2026-09-02

**Status:** current
**Scope:** the 2026-09-02 `/arbi` wake, the Amendment H ruling, the campaign plan, and Wave 0 of the campaign
**Last verified:** 2026-09-02
**Read priority:** read first
**Superseded by:** N/A

Supersedes `session-handoff-2026-08-25.md` as the newest handoff. `docs/README.md`'s "read first"
pointer still names `session-handoff-2026-08-11.md`; that file is authority-guarded — the fix is
click **H-15** in `docs/product/james-inbox.md` (campaign node H1-F drafts the text).

---

## STOP — read this first: Model A's quarantine (rule #11) stands, untouched this session

Nothing this session read `signals` as evidence (the wake counted its rows — 64,189, frozen at
`as_of` 2026-08-05 — only to prove the backup regression is not a DB change). Rule #11 remains
**resolved against Model A** (`docs/model-a-decay-analysis-2026-07-11.md`) and stands as standing
policy. Amendment H does not touch it; every hard stop in `roadmap-state.md` Amendment H §4 restates it.

---

## What this session did

1. **`/arbi` wake** (first since 2026-08-21). Live probes: git, GitHub Actions API, Supabase
   read-only, a fresh `uv` venv running the full suite. `main` @ `55f2619`; **2735 passed / 1
   skipped** (CI run `33616132894` and local agree); ledger latest `20260901062502` (0048); 0045
   still unapplied; prices/snapshots current to 2026-09-01; all daily jobs green.
2. **Found a bug nobody had recorded: `backup.yml` has failed every scheduled run since
   2026-08-23** — 12 consecutive reds; last green 08-22 (`d15266f`). First red is `b352eef` (#163),
   the commit that added the frozen-evidence sha256 assertion to
   `scripts/backup_irreplaceable.sh:125-176`; it exits at `:170-173` before the dump `cp` at `:178`.
   **No irreplaceable-table dump and no restore drill for 11 days.** Live `signals` still holds
   exactly the 64,189 rows the script header records, so the DB did not change — the mismatch is
   the hard-coded digest vs the archive bytes in `$BACKUP_REPO` (not inspectable by an agent).
   The deadman secret `HEALTHCHECK_URL_BACKUP_IRREPLACEABLE` was never set, so nothing alerted.
3. **James ruled Amendment H** (recorded in `roadmap-state.md` after Amendment G, plus the
   `decision-log.md` row): pull the wake into a Stages 0→6 task list, authorise all work and
   agents, run it autonomously via `/arbi-mission`, decisions delegated to arbi. Sequencing is
   delegated; tier is not (I5/I6/P5/P6 stay James's single click each, mechanically enforced).
4. **Campaign plan written:** `docs/proposals/amendment-h-campaign-plan-2026-09-02.md` — Waves 0→8,
   nodes `H0-A`…`H7-A`, the 39-click James list `H-01`…`H-39`, the seven decisions arbi makes alone
   (D-1…D-7), and the honest limits (S3, Dagster, risk calibration, observation windows).
5. **Wave 0 opened:** this handoff, the back-filled ledger row for the 09-01/02 merge-train session
   (NOT SCORED — artifact-derived), the scored row for this session (**4.0 provisional**), and the
   `## Amendment H click-list` section in `james-inbox.md` with H-01…H-07.

## Merged since the 08-25 handoff (by the 09-01/02 attended session, no close)

#167, **#183** (Slice 1 decision spine; migration 0048 applied 2026-09-01; first real packet
`dpk-cba-1-2026-09-01`, honest-abstain), #161, #169 (`nightly-check`), #171 (Sydney clock), #170
(`RUNBOOK.md`), #180 (08-25 close), #181 (actions bump), #182 (`decision-flow-2026-08-30.md`),
#179 (Amendment G), #184 (follow-ups — closed the 08-25 pip-cache and CLAUDE.md drift defects).

## Pending, requiring James

- **H-01…H-07** (`james-inbox.md` §Amendment H click-list) — Wave 0. H-03/H-04/H-06 are the
  secret, the `.github` patch, and the dispatch that only you can do; without them the backup
  cannot be *observed* green even after the script fix merges.
- Dark surfaces **#1 and #4 expired 2026-08-31**, unruled — node H1-G drafts the verdict
  (recommendation: KEEP-DARK to 2026-11-30, tied to the Stage 4 case); click H-16.
- Carried: #178 Dependabot (H-12), Phase 2 CI deps (H-13), `render.yaml` (H-09), migrations
  0049–0052 as they arrive, S3 bucket (H-21), Dagster spend (H-22), P5-01 risk calibration (H-32).

## Honest frame

The product spine is real: a decision packet exists, persists, and abstains for the right
reasons. The floor under it was silently off for 11 days and the last two closes did not see it.
Amendment H does not change what only James can do; it removes the per-unit approval loop so his
involvement is the click-list and nothing else. The campaign cannot reach programme "done" this
session — the plan says so in §6 — and no Stage cell flips without its exit gate cited.
