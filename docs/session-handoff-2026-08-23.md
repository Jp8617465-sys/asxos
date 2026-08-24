# Session handoff — 2026-08-23

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-22.md`
**Written for:** a new session with zero context.
**Two same-day closes** (Wave 4: do not silently pick one): design-bundle placement (`close-2026-08-23-bundle-placement`, **#166 merged** 2026-08-24 as `4cf8c39`) then Cursor D10-ops (`close-2026-08-23-cursor-d10-ops`, this PR **#172**). Scores **4.0** then **4.2** provisional.
**Competing close:** draft **#164** (`claude/arbi-close-2026-08-23`) is the earlier audit-P0 / episode 3.9 close. Rebase it after this PR.

**Since these closes:** #165 (`gh issue` allowlist) and #166 (ADR bundle) landed. #167 (issue snapshot) is the remaining D10 substrate. D10 is still not in force.

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

**9. The ADR is on `main` via #166 (`4cf8c39`).** D1–D14 are ratified and placed. Nothing in the ADR has been enacted beyond placement. Slice 0 (#163) already met the bundle's merge-before-Slice-1 gate. **#165 also merged.** D10 remains ratified-not-in-force.

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

Train remainder: **#167** (issue snapshot) then rebase or close **#164**. #165 and #166 are on `main`. Leave #161 off that train; decide whether #168/#169/#170 join a later train. After 167 is on main: first workflow_dispatch of issue-snapshot.yml (may need a github-actions bot ruleset exception). D10 in-force. Apply 0045. MCP principal repoint. defaultMode auto in user settings. This close PR onto main.

## Next

James names the next unit. Written later-candidates that are not auto-#1: screening seed INSERT (I5), apply 0045 (I5), MCP principal repoint (James), D10 in-force (James). W1-2 stays CHALLENGEd.

---

## Earlier same-day session — design-bundle placement (#166, merged)

The placement close is preserved here so the 08-23 handoff is one document, not two competing files. Ledger row `close-2026-08-23-bundle-placement`. Score **4.0 provisional**. Branch `claude/file-placement-review-0y5u8b` squash-merged as **#166** (`4cf8c39`) on 2026-08-24.

## What shipped

Three commits, **docs and issue forms only — zero lines of application code**. `full-check` and
`targeted-ml-tests` green on every head.

| Commit | Contents |
|---|---|
| `d966e90` | The 23 Aug design bundle: the ADR at `docs/product/architecture-decision-record.md`, two audits into `docs/archive/`, the ticketing research into `docs/research-archive/` |
| `411179e` | Four D11 issue forms under `.github/ISSUE_TEMPLATE/` — pushed via the GitHub API, not the working tree |
| `1e319c8` | One row in `docs/README.md` mapping the ADR — same API route |

Every placed file was byte-compared against its source. The three unmodified docs and all four
YAMLs are MD5-identical to the bundle; the ADR differs only by the two rows named below; the
pushed `docs/README.md` is MD5-identical to a locally-built expected copy (`2b66d175…`).

**Two deviations from the bundle's own README, both authorised by James in-session:** the audit
v2 was committed now rather than left as a chat artifact (its README said "move to
`docs/archive/` after Slice 0 merges" but never placed it in the repo to be moved), and the
work-management research went to `docs/research-archive/`, the destination that README names.

**Not placed, deliberately:** `claude-code-audit-prompt.md` (Slice 0 is in flight; verbatim at
ADR §10.1), the bundle README itself, and everything in the second zip — its four YAMLs are
MD5-identical to the bundle's and its ADR is the **older** copy, missing the §0 correction and
the Slice 1 `EvidencePacket` prerequisite.

---

## What the ADR got wrong about this repo

The bundle asked for contradictions to be found and a fifth corrections-log row added rather
than worked around. Done — §4 row 5 and a §9 change-log row are the only edits to the file.

1. **"`docs/product/` sits in `AUTHORITY_FRAGMENTS`" is false.** `authority-guard.sh:60-76`
   enumerates individual `docs/product/*.md` files plus `docs/product/rubrics/`; there is no
   directory prefix, and the `.claude/settings.json` deny array mirrors that same file list.
   **The ADR is unguarded as committed** — arbi can edit it directly — and it is not in
   CODEOWNERS. The governor-owned property it claims for itself does not exist until James
   adds the path to both lists. *This is the one worth acting on.*
2. **§0 says "Issue templates ×3"; there are four.** `config.yml` is load-bearing
   (`blank_issues_enabled: false`). §10.3 preserves only an abbreviated markdown sketch, not
   the issue-form YAML, so the ADR alone would not have preserved D11's enforcement. §10.3 also
   says `approval_tier` is required on all three, but the shipped forms pin data-infra and
   research to L3 by label and only `product.yml` carries the selector — that matches §5.5;
   §10.3's text is the stale half.
3. **Two competing architecture authorities.** `product/target-architecture.md` declares itself
   CANONICAL (ratified 2026-08-10, PR #79); the ADR's §2 and §6 overlap it, and
   `arbi-authority.md`'s source-of-truth ladder does not know the ADR exists.
4. **D10 vs this repo's queue.** The ADR calls `roadmap-state.md` frozen; `docs/README.md`,
   `roadmap-state.md:4` and `CLAUDE.md` all still call it the single live queue. The map row
   added this session **states the conflict rather than resolving it** — demoting the live
   queue is the governor's call.
5. **Two ADR versions shipped in one upload set.** Suggest §0 name a digest, not a filename.

**Verified correct, so do not re-litigate:** `types.py` 31,409 bytes · **zero INSERT/UPDATE to
`signal_outcomes`** anywhere in `asxos/`, `jobs/`, `scripts/` · D7 executed exactly as §10.2
specifies · `0042` absent, `0025`/`0045` present-unapplied.

⚠️ **Three figures I verified early in this session were overtaken by #163 landing, and the ADR
§3.5 text they came from is now stale.** Re-measured after merging `main`:

| ADR §3.5 / my earlier claim | Now |
|---|---|
| 43 migration files | **45** (`0018` reconstructed, `0046` added) |
| `REQUIRED_MIGRATIONS = 97` at `asxos/api/main.py:14` | **Deleted.** Replaced by `_check_migration_drift()` calling `scripts/check_migration_drift.py` — the name-set diff §10.1 commit 2 specified. The hand-maintained integer is gone |
| `0018` absent from the sequence | **Present** — `migrations/0018_perf_indexes.sql`, reconstructed from live `pg_get_indexdef()` with a provenance header, per §10.1 commit 6 |

**ADR §3.5 should be updated to match** — it still describes the pre-Slice-0 world. That is a
sixth corrections-log row, not written here: §3.5 is a *statement of fact about production* that
Slice 0 deliberately changed, so the correct edit is the governor's call on whether §3.5 gets
rewritten or superseded.

---

## Pending, requiring James

1. **Commit this branch to `main`.** **DONE 2026-08-24** — squash-merged as **#166** (`4cf8c39`).
2. **`gh issue create/list/view/edit` in `permissions.allow`** — **DONE 2026-08-24 as #165.** At close this was still refused. The
   repo would have allowed it (`.claude/settings.json` is in neither guard list since
   2026-08-22), but the harness's auto-mode classifier refused it, on the same principle ADR
   §10.2 states and for the same reason D7 went through Cursor. I did not route around it via
   the API, because unlike the map row this edit is nothing but self-benefit. The exact diff,
   four lines after `"Bash(gh pr comment:*)"`:
   ```json
         "Bash(gh issue create:*)",
         "Bash(gh issue list:*)",
         "Bash(gh issue view:*)",
         "Bash(gh issue edit:*)",
   ```
   Note `gh` is not installed in the remote container — these take effect in local sessions only.
3. **Decide whether the ADR should actually be guarded** (finding 1). One line in
   `authority-guard.sh`'s array plus one in the settings deny array plus a CODEOWNERS row, or an
   explicit decision that it stays editable.
4. **Rule on D10 vs `roadmap-state.md`** (finding 4). Until then both stand and D10 is
   ratified-but-not-in-force.
5. **D10's required mitigation does not exist.** §5.4 calls a periodic
   `gh issue list --json` export committed to the repo "required, not optional". Without it,
   off-repo issue state reproduces the exact §3.3 failure the ADR documents for
   `signal_outcomes` — evidence the repo cannot reproduce from itself. This is build work.
6. **`EvidencePacket` scoping** — the bundle asked how to scope a minimal first
   `DecisionPacket`. Deliberately **not answered**: it is the Slice 1 contract decision
   (ADR §5.3, delegable to arbi) that the bundle itself warns must not be made mid-build.
   Ask for it and it comes back as a written recommendation, not code.

---

## Boundaries held

No merge, no push to `main`, no migration applied, no DB write, no deploy, no capital action,
no Model A-derived claim. `0042` untouched; `0045` left unapplied. Two `AUTHORITY_FRAGMENTS`
paths (`.github/ISSUE_TEMPLATE/`, `docs/README.md`) were written **via the GitHub API on
James's explicit instruction**, as unmerged draft commits on a feature branch — the drafting
path the constitution permits, not a direct edit. The one change that would have widened arbi's
own capability was refused and left undone.
