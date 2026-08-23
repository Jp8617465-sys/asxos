# Session handoff — 2026-08-23

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-22.md`
**Written for:** a new session with zero context.
**Close:** `/arbi-close` after the Cursor ops session (0046 apply, #163 merge, D10-ops drafts). Ledger row `close-2026-08-23-cursor-d10-ops`. Score **4.2 provisional**.
**Competing close:** draft **#164** (`claude/arbi-close-2026-08-23`) is an earlier same-day close for the audit P0 / episode 3.9 session. It is BEHIND main. Prefer this handoff; then close or rebase #164.

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS.** Do not use Model A output —
signals, candidate scans, allocator runs, or new thesis proposals derived
from it — as a basis for real capital decisions. Removal still requires a
**new** model clearing a pre-registered decay bar AND earning
`approved_for_allocation`.

**2. Memory on `main` is L1–L45.** Promoted 2026-08-22 as **#159**. Live `dream-candidates/` has only `README.md` + `archive/`. Do not re-promote 17.x / 18.x / 22.x.

**3. D10 is ratified-but-not-in-force.** GitHub Issues are not the live queue. `roadmap-state.md` remains the single live queue until James says otherwise. #165 (allowlist) and #167 (snapshot export) are substrate, not a queue demotion.

**4. W1-2 (V1 brief section) stays CHALLENGEd.** Still not #1. Packet-first renderer stays P6-01 / Stage 6.

**5. The agent DB role is inert.** `asxos_agent_ro` exists; the MCP authenticates as `supabase_read_only_user`. See `docs/proposals/agent-db-role-the-control-is-inert-2026-08-22.md`.

**6. `gh issue list` 403s from this token** (`repository.issues`). Do not invent an issue backlog from a failed probe. The snapshot file is `[]` until the first green `issue-snapshot.yml` run on `main`.

**7. The harness rebuild remains on `main` as #158.** Review-gate gone. Attended Edit of `.claude/settings.json`, `.claude/hooks/**`, and `CLAUDE.md` is un-denied. `unattended-guard.sh` unchanged. User `defaultMode: auto` is not applied.

**8. `/pm-review HUBS.NYSE` owed by #149 is OBSERVED.** Four fan-out agents, zero Model A / `signals` figures, verdict **REVIEW**. Do not re-open the unsafe-until-patch-C claim.

---

## What this session did

James (Cursor Cloud Agent): finish the audit-P0 GitHub artifacts Claude could not land (`Edit(/.github/**)` denied), apply 0046, merge #163 if green, add the `gh issue` allowlist, add the §5.4 issue snapshot, then `/arbi-close`.

| Item | Result |
|---|---|
| #163 audit P0 | **MERGED** `b352eef` 2026-08-23 06:04 UTC by James (this agent cannot merge) |
| 0046 comment fix | **APPLIED** as `20260823054040` / `screening_runs_comment_fix` (James I5). Allowlist entry expired in the same squash |
| #165 `gh issue` allowlist | **draft, CLEAN, MERGEABLE** — four named Bash allows. Not D10-in-force |
| #167 issue snapshot | **draft, CLEAN, MERGEABLE** — cron `0 7 * * *`, `docs/ops/github-issues-snapshot.json` placeholder `[]` |
| Merge train | **advised, not executed** — I6. Safe order: #165 → #167 → #166. Rebase #164 after #166. Do not mix #161 |
| D10 / W1-2 / rule #11 | Unchanged |

## Merges this close (on `main`)

| PR | SHA | What |
|---|---|---|
| **#162** | `0a66cfc` | `migrations/` off authority paths (already on `main` before this session merged #163) |
| **#163** | `b352eef` | Audit P0/P1: schema reproducibility, UTC pin, verified backup, observable alerts, own `migration-drift.yml`, Sunday restore drill, 0046 file |

`main` tip at this close: `b352eef`. Required `full-check` on that push: run `32621965350`, **2640 passed, 1 skipped**, SUCCESS.

**Amendment E.** **renders:** TLS.AU FY2024 PIT abstain already on `main` via #155. **captures:** n/a. **defect:** holdout evals / `episode_score` trend on #159 still NOT RUN (L26 honesty). User `defaultMode` not applied. D10 not in force.

## Sprint-state at close

- Git: `main` @ `b352eef`. This close lives on `cursor/arbi-close-2026-08-23-8efa`.
- Open drafts at probe: **#170** RUNBOOK · **#169** nightly · **#168** CI hardening · **#167** issue snapshot · **#166** ADR/docs bundle · **#165** allowlist · **#164** earlier 08-23 close (BEHIND) · **#161** cheap cleanups (BEHIND). All CLEAN except #164/#161 BEHIND.
- Migrations: latest **applied** `20260823054040` (`screening_runs_comment_fix` = 0046). **0045 unapplied** (`segment_map` remains in `EXPECTED_UNAPPLIED`). 0042 reserved, not applied. Integer `REQUIRED_MIGRATIONS` is gone (name-diff in `asxos/schema_drift.py`). Disk: 45 `.sql` files (0042 absent).
- Tests: last green on `main` = **2640 passed, 1 skipped** (the skip is `tests/test_price_revision_migration_integration.py`, needs `MIGRATION_TEST_DATABASE_URL`). This close is docs-only.
- Issues: `gh issue list` 403 from this token.
- Memory: L1–L45 on `main` (unchanged this session).

## Must not

Apply 0045 / INSERT screening seed / touch 0042 / read signals as evidence / tax math / V1 brief section (W1-2) / capital / Model A for capital. Do not demote roadmap-state.md as the live queue. Do not mark PRs ready or squash them from this agent. Do not push the default branch. Do not treat PR 164 WHERE-I-STOPPED as current (it predates the 163 merge). Do not re-promote 17.x / 18.x / 22.x. Do not set defaultMode in project settings. Do not treat a spoken grant as a config write (L39).

## James still owns

Merge train 165 then 167 then 166 (governor ready+squash); rebase or close 164; leave 161 off that train; decide whether 168/169/170 join a later train. After 167 is on main: first workflow_dispatch of issue-snapshot.yml (may need a github-actions bot ruleset exception). D10 in-force. Apply 0045. MCP principal repoint. defaultMode auto in user settings. This close PR onto main.

## Next

James names the next unit. Written later-candidates that are not auto-#1: screening seed INSERT (I5), apply 0045 (I5), MCP principal repoint (James), D10 in-force (James). W1-2 stays CHALLENGEd.
