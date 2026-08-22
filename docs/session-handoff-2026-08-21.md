# Session handoff — 2026-08-21

**Status:** current
**Read priority:** read first
**Supersedes:** `docs/session-handoff-2026-08-20.md`

---

## STOP — read first

**1. Rule #11 (Model A quarantine) STANDS, and this session hardened it twice.** PR #144
deleted Model A's code; that is a fact about v1_5, not grounds to drop the rule
(`CLAUDE.md:25` pre-emptively forbids removal on that basis). Two live capital-facing paths
were still serving frozen Model A output as current and were closed in **#149** — see §2.
Removal still requires a **new** model clearing a pre-registered decay bar (positive,
monotonic conviction→21d return) AND earning `approved_for_allocation`.

**2. ⚠️ ONE VERIFICATION IS OWED, AND THIS SESSION COULD NOT PRODUCE IT.** #149 amputated the
two `/pm-review` agents that read the frozen `signals` table. The completion artifact — a
`/pm-review HUBS.NYSE` run showing **four** agents and **zero** Model A figures — is **not
observed**. It cannot be produced by the authoring session: agent and command definitions load
at session start, so that session still held the *pre-amputation* definitions. Running it there
would dispatch the OLD agents and reproduce the very leak just fixed. The ledger row therefore
reads `did_it_work: PENDING`, per L18. **A fresh session owes this run.** Until then, treat
`/pm-review`'s safety as *believed* rather than *demonstrated*.

**3. `0044` is APPLIED — the inbox row that says otherwise is stale until #150 merges.**
Verified at the primary source 2026-08-21: `supabase_migrations.schema_migrations` = **97**,
`rs_fundamentals_pit.currency` **present**, latest version `20260821080458`. The Saturday
deadline is discharged. Note the failure this caused: the 🔴 row stayed open all day, and **two
independent advisors read it and both escalated the migration as the single most time-critical
item in the repo.** `main`'s `REQUIRED_MIGRATIONS = 96` still lags the observed 97 (benign — the
check only hard-fails when the DB has *fewer* than required); the bump sits on unmerged branch
`claude/asx-stock-evaluation-p0hxx2`, and the repo copy of `0044` still reads "DRAFT - NOT
APPLIED". `0045_segment_map.sql` remains unapplied.

> **CORRECTION 2026-08-22 — the first residual is discharged; the second is not.**
> `REQUIRED_MIGRATIONS` is bumped **96 → 97** by the change that carries this annotation
> (`asxos/api/main.py:14`), re-measured against the live ledger the same day: count **97**,
> latest version `20260821080458`. The lag described above is closed on merge.
> **Still open (both `migrations/**`, Edit-denied to that change — handed to James):**
> the repo copy of `0044` still reads `DRAFT — NOT APPLIED` and its `COMMENT ON COLUMN`
> body still carries the superseded `102 symbols` figure that was corrected *at apply
> time*, so the file no longer matches the database; `0043`'s header still reads
> "PRODUCTION-READY — still unapplied" though it was applied 2026-08-12.
> `0045_segment_map.sql` is genuinely still unapplied — its "DRAFT — NOT APPLIED" header
> is **correct** and must not be "fixed" alongside the other two.
> The benign-lag reasoning above is now pinned by a test:
> `tests/test_api_main.py::test_migration_drift_passes_above_required` fails under a
> `count != REQUIRED_MIGRATIONS` mutation while the tests either side of it pass.

---

## What shipped

Three PRs merged to `main` (tip `ff377ef`):

| PR | Commit | What |
|---|---|---|
| **#147** | `a9785d4` | `/thesis` Phase A (render-only broker-note command), the `unrealised_fx_pnl_aud` FX-component fix, and the HUBS position review |
| **#148** | `31c78f4` | Closed the **MCP guard-wiring hole** |
| **#149** | `ff377ef` | **Patch 2** — both frozen-Model-A readers amputated out of `/pm-review` |

**#150 is open and draft** (`1840e78`): the session records — `arbi-run-ledger` mission row,
`decision-log` row, and the two 🔴 `james-inbox` rows closed. Needs James's ready-click.

### The two findings were both accidents of doing something else

**The MCP guard hole (#148).** Un-drafting #147 through the GitHub MCP server did not fire
`pr-draft-guard`. Root cause was **wiring, not logic**: MCP tool calls sit outside
`PreToolUse`'s supported-tool list, so that hook *and* `unattended-guard`'s entire `mcp__*`
case tree — including its fail-closed unknown-tool deny — had been **dead code since R13**.
Session `01YBEYvVFasrq89XhkncMKRD` independently logged the same hole the same hour as a fourth
R5/R16/R17 instance. Fixed by one `matcher: "mcp__.*"` block; 38 tests now pin **both** the hook
verdicts and the settings wiring, because a hook-only suite would have stayed green through the
entire incident. **Live-fire verified three times** — the agent's own un-draft attempts on #148
and #150 were denied by the fix it was shipping, while `merge_pull_request` passed the hook
silently and failed only at GitHub, proving the deny is targeted and the James-instructed
attended-merge path intact.

**The second Model A reader (#149).** `segval-live-validation-2026-08-20.md` Patch 2 named
`thesis-coherence-guard` alone. The pre-ship security review found a **second unamputated reader
still in the fan-out**: `portfolio-coherence-reviewer`, whose "Signal vs holding" section emitted
`Model A = SELL since [date], 34 days ago`. With `as_of` frozen that counter **grows forever** —
an ever-more-urgent-looking stale SELL feeding EXIT-CANDIDATE verdicts. Shipping to spec would
have closed the leak in the report and not in the product.

### 7a: diagnosed, then correctly abandoned

Routine `trig_01BA3VmfzoRMtjKnt6XNpgPH` (the arbi PM brief — **not** the investor brief, which
never stopped) and the secperf WRITE loop were **user-paused** 2026-07-18T23:18 UTC. Asked
directly, James said **"the briefs weren't worth reading"** — retiring the planned fix, since
patching the dead Render probe and re-arming would have re-subscribed him to rejected output.
guilfoyle then found the deeper cause: **7a has never produced a repo-observable artifact** (28
ledger rows, all `trigger: manual`, zero scheduled), so its quality and liveness problems are the
same problem, and `rubrics/arbi-daily-brief.md:6-15` contains **no clause permitting silence**.
arbi-red-team returned CHALLENGE; James stopped it at gate G1. Findings preserved in the task
list — the redesign should reuse `asxos/domain/brief/severity.py` (already an exception-based
severity model, already running on Actions) and move to the Actions substrate rather than re-arm
a Routine.

---

## Corrections this session made about its own work

Recorded here as well as in the ledger, because a handoff that only lists wins is the defect this
project keeps finding.

- **arbi's pause evidence was partly wrong.** "Zero commits 2026-07-18..21" is falsified by
  `decision-log.md:46` (nine merged PRs that day). The surviving claim is narrower: the *pause*
  is unrecorded. Caught by guilfoyle, not by arbi, after it had already reached a user-facing brief.
- **Patch 2 would have shipped incomplete** without the security review. The spec had a blind spot
  and the patch inherited it.
- The `/pm-review` safety controls are **prompt-level only**. `mcp__supabase-ro__execute_sql`
  permits any SELECT, so the frozen table stays reachable and *not reading it* is the control.
  `REVOKE SELECT ON signals` for the agent role (`m14_candidate_agent_db_role_scoping`) is the only
  mechanical control that would survive a prompt edit.

---

## Pending, requiring James

1. **Mark #150 ready** — the session records. The agent is mechanically blocked from un-drafting.
2. **Run `/pm-review HUBS.NYSE` in a fresh session** — the owed completion artifact (§2 above).
   Also invoke `thesis-coherence-guard` directly: thesis 2 has one revision and is past
   `revisit_due_at`, so expect **UNEXAMINED** or **NEEDS REVIEW**. An EXAMINED verdict or a crash
   means the promoted SQL is wrong.
3. **The A$701 HUBS acquisition-FX question** — `holding_lots.id=1` books `acquisition_fx_rate`
   0.6450 flagged "estimated"; vendor FX for 2026-05-31 was 0.7171. Only the brokerage statement
   settles it. It decides whether the position reads +16.0% or +29.0%, and an overstated cost base
   understates the assessable CGT gain.
4. **Production DB writes** — `timeline_days` 365→366 on thesis 2 (one day short of the CGT
   discount date; ~A$218 of discount on today's gain, ~A$732 at target), the Q2 falsifier
   adjudication (18 days overdue, through a −19% print), and the `snapshot_portfolio` backfill
   (all 56 historical rows still carry total P&L under the FX label).
5. **Three dark-launch surfaces expire 2026-08-31** — decide by 2026-08-28.
6. **The unrecorded secperf WRITE Routine.** `trig_011o24xerepfL9Cq3abtrJ3M` appears **nowhere**
   in this repo, violating `security-perf-mission-loop.md:301`'s record-on-creation obligation,
   and R16(3) says 7b unattended write authority must not rely on those hooks. It stays paused.
   Worth its own inbox row.

---

## End-state

- `main` @ `ff377ef`; branch `claude/hubspot-position-forecast-fkgw63` @ `1840e78` (PR #150, draft).
- Migrations: **97** applied (`20260821080458` latest); `REQUIRED_MIGRATIONS = 96` on `main` lags.
  *(Corrected 2026-08-22: bumped to **97** by the follow-on change — see the CORRECTION block
  in §3. `0045` remains unapplied; the on-disk ceiling is `0045`, the ledger is 97, and the
  constant is 97 — three legitimately different numbers.)*
- Tests: **2200 collected**; 20 collection errors, all the documented sandbox `joblib`/`lightgbm`
  gap — re-derived with `pytest tests/ -q --co | grep '^ERROR'` per `CLAUDE.md`, not trusted from
  a list. CI (`full-check`) is the real gate and was green on every merge.
- Rule #11 intact and strengthened; s766B firewall intact; migration `0042` untouched; no
  migration applied, no DB write, no capital action, no `--admin` bypass at any point.
